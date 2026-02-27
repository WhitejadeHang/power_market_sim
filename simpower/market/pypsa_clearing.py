"""
基于 PyPSA 的市场出清引擎
==========================
核心改造: 用 PyPSA + HiGHS/SCIP 替代 Pyomo 手写模型

功能:
- DA_SCUC: 日前安全约束机组组合 (MILP, 含 unit commitment 二进制变量)
- DA_SCED: 日前安全约束经济调度 (LP, 固定开机组合, 提取 LMP)
- RT_SCED: 实时滚动经济调度 (LP, 5min×24 窗口)

网络约束通过 PyPSA 的 DC-OPF 线性化潮流实现, 自动计算:
  - 线路潮流约束
  - 节点功率平衡
  - 节点边际电价 (LMP = bus.marginal_price)
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import pypsa
from dataclasses import dataclass, field
from .models import (
    UnitMaster, UnitType, UnitBoundary96,
    BidCurve, CoalUnitBid, StorageBid, RenewableBid, PriceTakerSchedule,
    MarketResult, UnitResult,
    DA_PERIODS, DA_PERIOD_HOURS, HOURS_PER_DAY,
    PRICE_CLEAR_UPPER, PRICE_CLEAR_LOWER,
)

logger = logging.getLogger(__name__)


@dataclass
class ClearingConfig:
    """出清配置"""
    solver_name: str = "highs"
    num_periods: int = DA_PERIODS
    period_minutes: int = 15
    reserve_up_mw: float = 0.0
    reserve_down_mw: float = 0.0
    include_unit_commitment: bool = True
    line_margin_factor: float = 1.0


class PyPSAClearing:
    """
    基于 PyPSA 的市场出清核心类
    
    用法:
      1. 传入基础网络拓扑 (pypsa.Network, 含 Bus + Line)
      2. 调用 setup_market_participants() 注入发电机、负荷、储能
      3. 调用 run_scuc() 或 run_sced() 执行出清
      4. 从结果提取 LMP、出力计划、SOC 等
    """

    def __init__(
        self,
        base_network: pypsa.Network,
        config: ClearingConfig | None = None,
    ):
        self.base_network = base_network
        self.config = config or ClearingConfig()
        self.network: pypsa.Network | None = None
        self._unit_map: dict[str, dict] = {}
        self._storage_map: dict[str, dict] = {}

    def _create_snapshots(self) -> pd.DatetimeIndex:
        T = self.config.num_periods
        freq = f"{self.config.period_minutes}min"
        return pd.date_range("2025-01-15 00:00", periods=T, freq=freq)

    def setup_market_participants(
        self,
        units: dict[str, UnitMaster],
        bids: dict[str, CoalUnitBid | StorageBid | RenewableBid],
        load_profiles: dict[str, np.ndarray],
        renewable_forecasts: dict[str, np.ndarray] | None = None,
        price_taker_schedules: dict[str, PriceTakerSchedule] | None = None,
        boundaries: dict[str, UnitBoundary96] | None = None,
        commitment_fixed: dict[str, np.ndarray] | None = None,
    ):
        """将市场主体信息注入 PyPSA 网络"""
        snapshots = self._create_snapshots()
        T = self.config.num_periods

        n = self.base_network.copy()
        n.set_snapshots(snapshots)

        renewable_forecasts = renewable_forecasts or {}
        price_taker_schedules = price_taker_schedules or {}
        boundaries = boundaries or {}
        commitment_fixed = commitment_fixed or {}

        # === 添加负荷 ===
        for load_id, profile in load_profiles.items():
            bus = load_id.split("_")[-1] if "_" in load_id else "Bus4"
            for b in n.buses.index:
                if b.lower().replace("bus", "") == bus.lower().replace("bus", ""):
                    bus = b
                    break
            p = profile[:T] if len(profile) >= T else np.pad(profile, (0, T - len(profile)), mode='edge')
            n.add("Load", load_id, bus=bus, p_set=p)

        # === 添加发电机 (煤机/新能源) ===
        for uid, unit in units.items():
            bid = bids.get(uid)
            bnd = boundaries.get(uid)

            if unit.unit_type == UnitType.COAL:
                self._add_coal_generator(n, uid, unit, bid, bnd, commitment_fixed.get(uid), T)

            elif unit.unit_type == UnitType.RENEWABLE:
                fc = renewable_forecasts.get(uid, np.full(T, unit.rated_power * 0.3))
                self._add_renewable_generator(n, uid, unit, bid, fc, T)

            elif unit.unit_type == UnitType.STORAGE:
                self._add_storage(n, uid, unit, bid, bnd, T)

            elif unit.unit_type in (UnitType.CHP, UnitType.SELF_GEN):
                sched = price_taker_schedules.get(uid)
                self._add_price_taker(n, uid, unit, sched, T)

        self.network = n

    def _add_coal_generator(self, n, uid, unit, bid, bnd, commitment, T):
        """添加煤机发电机 — 用分段线性报价"""
        p_min = unit.min_power
        p_max = unit.max_power

        if bnd is not None:
            p_max_t = np.minimum(p_max, bnd.pmax_96[:T])
            p_min_t = np.maximum(p_min, bnd.pmin_96[:T])
        else:
            p_max_t = np.full(T, p_max)
            p_min_t = np.full(T, p_min)

        # 报价曲线 → 边际成本 (取加权平均作为简化)
        mc = 300.0
        if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
            pts = bid.energy_curve.points
            mc = sum(p.price_yuan_mwh for p in pts) / len(pts)

        # 启动/空载成本
        start_up_cost = 0.0
        shut_down_cost = 0.0
        if bid and hasattr(bid, 'startup_cost_hot'):
            start_up_cost = bid.startup_cost_hot * 10000  # 万元→元
        if bid and hasattr(bid, 'noload_cost'):
            shut_down_cost = 0

        committable = self.config.include_unit_commitment and commitment is None
        
        n.add("Generator", uid,
              bus=unit.node,
              carrier="coal",
              p_nom=p_max,
              marginal_cost=mc,
              p_min_pu=p_min_t / p_max if p_max > 0 else np.zeros(T),
              p_max_pu=p_max_t / p_max if p_max > 0 else np.ones(T),
              committable=committable,
              min_up_time=max(1, int(unit.min_up_time_h / (self.config.period_minutes / 60))),
              min_down_time=max(1, int(unit.min_down_time_h / (self.config.period_minutes / 60))),
              start_up_cost=start_up_cost,
              shut_down_cost=shut_down_cost,
              ramp_limit_up=unit.ramp_rate * self.config.period_minutes / p_max if unit.ramp_rate > 0 and p_max > 0 else 1.0,
              ramp_limit_down=unit.ramp_rate * self.config.period_minutes / p_max if unit.ramp_rate > 0 and p_max > 0 else 1.0,
              )

        if commitment is not None:
            # 固定开机状态 (SCED阶段)
            status = commitment[:T]
            n.generators.loc[uid, "committable"] = False
            n.generators_t.p_min_pu[uid] = p_min_t / p_max * status
            n.generators_t.p_max_pu[uid] = p_max_t / p_max * status

        self._unit_map[uid] = {"type": "coal", "bus": unit.node, "p_nom": p_max}

    def _add_renewable_generator(self, n, uid, unit, bid, forecast, T):
        """添加新能源发电机"""
        mc = 0.0
        if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
            mc = bid.energy_curve.points[0].price_yuan_mwh

        p_max_pu = forecast[:T] / unit.rated_power if unit.rated_power > 0 else np.zeros(T)
        p_max_pu = np.clip(p_max_pu, 0, 1)

        n.add("Generator", uid,
              bus=unit.node,
              carrier="wind",
              p_nom=unit.rated_power,
              marginal_cost=mc,
              p_max_pu=p_max_pu,
              p_min_pu=0,
              committable=False,
              )
        self._unit_map[uid] = {"type": "renewable", "bus": unit.node, "p_nom": unit.rated_power}

    def _add_storage(self, n, uid, unit, bid, bnd, T):
        """添加独立储能 — 使用 PyPSA StorageUnit"""
        mc_dis = 0.0
        mc_ch = 0.0
        if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
            pts = bid.energy_curve.points
            pos_pts = [p for p in pts if p.power_mw > 0]
            neg_pts = [p for p in pts if p.power_mw < 0]
            if pos_pts:
                mc_dis = sum(p.price_yuan_mwh for p in pos_pts) / len(pos_pts)
            if neg_pts:
                mc_ch = -sum(p.price_yuan_mwh for p in neg_pts) / len(neg_pts)

        soc_end = unit.initial_soc
        if bid and hasattr(bid, 'end_of_day_soc') and bid.end_of_day_soc is not None:
            soc_end = bid.end_of_day_soc

        n.add("StorageUnit", uid,
              bus=unit.node,
              carrier="battery",
              p_nom=unit.discharge_power_mw,
              max_hours=unit.storage_capacity_mwh / unit.discharge_power_mw if unit.discharge_power_mw > 0 else 4,
              efficiency_store=unit.charge_efficiency,
              efficiency_dispatch=unit.discharge_efficiency,
              marginal_cost=mc_dis,
              marginal_cost_storage=mc_ch,
              state_of_charge_initial=unit.initial_soc,
              cyclic_state_of_charge=False,
              cyclic_state_of_charge_per_period=False,
              )
        self._storage_map[uid] = {"bus": unit.node, "cap": unit.storage_capacity_mwh}

    def _add_price_taker(self, n, uid, unit, sched, T):
        """添加价格接受者 (CHP/自备电厂) — 作为固定出力发电机"""
        if sched is not None:
            p_set = sched.schedule_mw[:T]
        else:
            p_set = np.full(T, unit.rated_power * 0.6)

        p_max = max(unit.rated_power, p_set.max() + 1)
        n.add("Generator", uid,
              bus=unit.node,
              carrier="chp",
              p_nom=p_max,
              marginal_cost=-0.01,   # 负成本确保优先出清
              p_min_pu=p_set / p_max,
              p_max_pu=p_set / p_max,
              committable=False,
              )
        self._unit_map[uid] = {"type": "price_taker", "bus": unit.node, "p_nom": p_max}

    def run_scuc(self) -> MarketResult:
        """执行 SCUC (带机组组合的优化)"""
        if self.network is None:
            raise RuntimeError("请先调用 setup_market_participants()")

        logger.info(f"SCUC 出清: {self.config.num_periods}个时段, 求解器={self.config.solver_name}")
        n = self.network

        status, _ = n.optimize(
            solver_name=self.config.solver_name,
            include_objective_constant=False,
        )
        logger.info(f"SCUC 求解状态: {status}")

        if status != "ok":
            logger.error(f"SCUC 求解失败: {status}")

        return self._extract_results(n)

    def run_sced(self, commitment: dict[str, np.ndarray] | None = None) -> MarketResult:
        """执行 SCED (固定开机组合的经济调度)
        
        若传入 commitment, 则将对应发电机设为不可提交并固定出力上下限。
        LMP 自动从 PyPSA bus.marginal_price 提取。
        """
        if self.network is None:
            raise RuntimeError("请先调用 setup_market_participants()")

        n = self.network
        T = self.config.num_periods

        if commitment:
            for uid, status_arr in commitment.items():
                if uid in n.generators.index:
                    n.generators.loc[uid, "committable"] = False
                    p_nom = n.generators.loc[uid, "p_nom"]
                    orig_min = n.generators_t.p_min_pu.get(uid, pd.Series(0.0, index=n.snapshots))
                    orig_max = n.generators_t.p_max_pu.get(uid, pd.Series(1.0, index=n.snapshots))
                    s = status_arr[:T]
                    if isinstance(orig_min, (int, float)):
                        orig_min = pd.Series(orig_min, index=n.snapshots)
                    if isinstance(orig_max, (int, float)):
                        orig_max = pd.Series(orig_max, index=n.snapshots)
                    n.generators_t.p_min_pu[uid] = orig_min.values * s
                    n.generators_t.p_max_pu[uid] = orig_max.values * s

        logger.info(f"SCED 出清: {T}个时段, 求解器={self.config.solver_name}")

        status, _ = n.optimize(
            solver_name=self.config.solver_name,
            include_objective_constant=False,
        )
        logger.info(f"SCED 求解状态: {status}")

        return self._extract_results(n)

    def _extract_results(self, n: pypsa.Network) -> MarketResult:
        """从 PyPSA 网络提取出清结果"""
        T = self.config.num_periods
        period_hours = self.config.period_minutes / 60.0

        result = MarketResult(num_periods=T, period_hours=period_hours)

        # LMP (节点边际电价)
        for bus in n.buses.index:
            if bus in n.buses_t.marginal_price.columns:
                lmp = n.buses_t.marginal_price[bus].values.copy()
                lmp = np.clip(lmp, PRICE_CLEAR_LOWER, PRICE_CLEAR_UPPER)
                result.lmp[bus] = lmp

        # 发电机出力
        for gen_id in n.generators.index:
            power = n.generators_t.p[gen_id].values.copy() if gen_id in n.generators_t.p.columns else np.zeros(T)
            
            # 开机状态
            if gen_id in getattr(n, 'generators_t', pd.DataFrame()).get('status', pd.DataFrame()).columns if hasattr(n.generators_t, 'status') else False:
                commitment = n.generators_t.status[gen_id].values
            else:
                commitment = (power > 0.01).astype(float)

            result.unit_results[gen_id] = UnitResult(
                unit_id=gen_id,
                commitment=commitment,
                power=power,
            )

        # 储能
        for su_id in n.storage_units.index:
            p = n.storage_units_t.p[su_id].values.copy() if su_id in n.storage_units_t.p.columns else np.zeros(T)
            soc = n.storage_units_t.state_of_charge[su_id].values.copy() if su_id in n.storage_units_t.state_of_charge.columns else np.zeros(T)
            cap = self._storage_map.get(su_id, {}).get("cap", 1.0)

            p_dis = np.maximum(p, 0)
            p_ch = np.maximum(-p, 0)

            result.unit_results[su_id] = UnitResult(
                unit_id=su_id,
                commitment=np.ones(T),
                power=p,
                charge_power=p_ch,
                discharge_power=p_dis,
                soc=soc / cap if cap > 0 else soc,
            )

        # 系统成本
        result.system_cost = float(n.objective) if n.objective is not None else 0.0

        # 统一结算点电价
        self._compute_unified_price(result, n)

        return result

    def _compute_unified_price(self, result: MarketResult, n: pypsa.Network):
        """计算统一结算点电价 = 发电侧节点电价按上网电量加权平均"""
        T = result.num_periods
        usp = np.zeros(T)
        for t in range(T):
            weighted = 0.0
            total_gen = 0.0
            for gen_id, ur in result.unit_results.items():
                if ur.power[t] > 0.01:
                    bus = None
                    if gen_id in n.generators.index:
                        bus = n.generators.loc[gen_id, "bus"]
                    elif gen_id in n.storage_units.index:
                        bus = n.storage_units.loc[gen_id, "bus"]
                    if bus and bus in result.lmp:
                        weighted += result.lmp[bus][t] * ur.power[t]
                        total_gen += ur.power[t]
            usp[t] = weighted / total_gen if total_gen > 0 else 0.0
        result.unified_settlement_price = usp
