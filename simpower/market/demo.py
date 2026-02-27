"""
重庆电力现货市场仿真 — IEEE 6-bus 网络约束出清
==================================================

场景:
  - IEEE 6-bus 标准测试网络, 11条输电线路 (部分线路容量受限产生阻塞)
  - 4台煤机 (Bus1×2 + Bus2×2), 1个风电 (Bus3), 1个储能 (Bus6), 1个CHP (Bus1)
  - 3个负荷节点 (Bus3/Bus4/Bus5)
  - 96×15min 完整日前出清
  - PyPSA DC-OPF + HiGHS 求解, 自动提取各节点 LMP

输出:
  - 各节点96点 LMP (含阻塞分量)
  - 各机组出力计划 + 储能SOC
  - 线路潮流与阻塞分析
  - 统一结算点电价 + 结算报告
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd
import pypsa

from .models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, MarketResult, UnitResult,
    DA_PERIODS, HOURS_PER_DAY,
)
from .bid_validator import BidValidator
from .ieee_network import (
    create_ieee6bus, generate_load_profile_96, generate_wind_profile_96,
)
from .settlement import SettlementEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

T = DA_PERIODS


def build_market_network() -> tuple[pypsa.Network, dict[str, UnitMaster], dict]:
    """构建完整的市场网络: 拓扑 + 发电机 + 负荷 + 储能"""

    # === 基础拓扑 ===
    base = create_ieee6bus()
    snap = pd.date_range("2025-01-15 00:00", periods=T, freq="15min")
    base.set_snapshots(snap)

    # === 机组主数据 ===
    units = {
        "Coal_B1_1": UnitMaster(
            unit_id="Coal_B1_1", name="渝北电厂#1", unit_type=UnitType.COAL,
            node="Bus1", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=5.0,
            min_up_time_h=8, min_down_time_h=4, aux_power_rate=6.5,
        ),
        "Coal_B1_2": UnitMaster(
            unit_id="Coal_B1_2", name="渝北电厂#2", unit_type=UnitType.COAL,
            node="Bus1", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=5.0,
            min_up_time_h=8, min_down_time_h=4, aux_power_rate=6.5,
        ),
        "Coal_B2_1": UnitMaster(
            unit_id="Coal_B2_1", name="江津电厂#1", unit_type=UnitType.COAL,
            node="Bus2", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=6.0,
            min_up_time_h=6, min_down_time_h=4, aux_power_rate=6.0,
        ),
        "Coal_B2_2": UnitMaster(
            unit_id="Coal_B2_2", name="合川电厂#1", unit_type=UnitType.COAL,
            node="Bus2", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=6.0,
            min_up_time_h=6, min_down_time_h=4, aux_power_rate=6.0,
        ),
        "Wind_B3": UnitMaster(
            unit_id="Wind_B3", name="巫山风电场", unit_type=UnitType.RENEWABLE,
            node="Bus3", rated_power=200,
        ),
        "ESS_B6": UnitMaster(
            unit_id="ESS_B6", name="渝中储能站", unit_type=UnitType.STORAGE,
            node="Bus6", rated_power=100, charge_power_mw=100, discharge_power_mw=100,
            storage_capacity_mwh=200, initial_soc=0.5, soc_max=0.95, soc_min=0.05,
            charge_efficiency=0.92, discharge_efficiency=0.92,
        ),
        "CHP_B1": UnitMaster(
            unit_id="CHP_B1", name="重庆热电", unit_type=UnitType.CHP,
            node="Bus1", rated_power=100,
        ),
    }

    # === 报价 ===
    bids = {
        "Coal_B1_1": CoalUnitBid(
            unit_id="Coal_B1_1",
            startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=12, noload_cost=0.5,
            energy_curve=BidCurve(points=[
                BidPoint(120, 220), BidPoint(200, 260), BidPoint(300, 340),
            ]),
        ),
        "Coal_B1_2": CoalUnitBid(
            unit_id="Coal_B1_2",
            startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=12, noload_cost=0.5,
            energy_curve=BidCurve(points=[
                BidPoint(120, 230), BidPoint(200, 280), BidPoint(300, 360),
            ]),
        ),
        "Coal_B2_1": CoalUnitBid(
            unit_id="Coal_B2_1",
            startup_cost_cold=28, startup_cost_warm=18, startup_cost_hot=10, noload_cost=0.4,
            energy_curve=BidCurve(points=[
                BidPoint(120, 250), BidPoint(200, 310), BidPoint(300, 400),
            ]),
        ),
        "Coal_B2_2": CoalUnitBid(
            unit_id="Coal_B2_2",
            startup_cost_cold=28, startup_cost_warm=18, startup_cost_hot=10, noload_cost=0.4,
            energy_curve=BidCurve(points=[
                BidPoint(120, 290), BidPoint(200, 360), BidPoint(300, 450),
            ]),
        ),
    }

    # === 校验报价 ===
    for uid, bid in bids.items():
        vr = BidValidator.validate_coal_bid(bid, units[uid])
        logger.info(f"  报价校验 {uid}: {'✓' if vr.valid else '✗ ' + str(vr)}")

    # === 添加发电机到 PyPSA 网络 ===
    n = base

    # 煤机: 使用平均边际成本
    for uid in ["Coal_B1_1", "Coal_B1_2", "Coal_B2_1", "Coal_B2_2"]:
        u = units[uid]
        b = bids[uid]
        mc = sum(p.price_yuan_mwh for p in b.energy_curve.points) / len(b.energy_curve.points)
        n.add("Generator", uid, bus=u.node, p_nom=u.max_power,
              marginal_cost=mc, p_min_pu=0, carrier="coal")

    # 风电
    wind_fc = generate_wind_profile_96(200, seed=123)
    n.add("Generator", "Wind_B3", bus="Bus3", p_nom=200,
          marginal_cost=0, p_max_pu=wind_fc / 200, carrier="wind")

    # CHP (固定出力)
    chp_hours = np.arange(T) * 0.25
    chp_sched = np.where((chp_hours >= 6) & (chp_hours < 22), 80, 50).astype(float)
    n.add("Generator", "CHP_B1", bus="Bus1", p_nom=100,
          marginal_cost=-0.01, p_min_pu=chp_sched / 100, p_max_pu=chp_sched / 100,
          carrier="chp")

    # 储能
    n.add("StorageUnit", "ESS_B6", bus="Bus6", p_nom=100,
          max_hours=2, efficiency_store=0.92, efficiency_dispatch=0.92,
          marginal_cost=10, state_of_charge_initial=0.5,
          cyclic_state_of_charge=True, carrier="battery")

    # === 负荷 ===
    load3 = generate_load_profile_96(300, seed=10)
    load4 = generate_load_profile_96(450, seed=20)
    load5 = generate_load_profile_96(350, seed=30)
    n.add("Load", "Load_Bus3", bus="Bus3", p_set=load3)
    n.add("Load", "Load_Bus4", bus="Bus4", p_set=load4)
    n.add("Load", "Load_Bus5", bus="Bus5", p_set=load5)

    total_load = load3 + load4 + load5
    logger.info(f"  系统负荷: 峰值={total_load.max():.0f}MW, 谷值={total_load.min():.0f}MW, 均值={total_load.mean():.0f}MW")
    logger.info(f"  风电预测: 均值={wind_fc.mean():.0f}MW, 峰值={wind_fc.max():.0f}MW")

    return n, units, bids


def run_demo():
    print("=" * 72)
    print("  重庆电力现货市场仿真系统")
    print("  IEEE 6-bus 网络 | PyPSA DC-OPF + HiGHS | 96×15min | Agent报价")
    print("=" * 72)
    print()

    # --- 构建网络 ---
    logger.info("构建 IEEE 6-bus 市场网络...")
    n, units, bids = build_market_network()
    logger.info(f"网络: {len(n.buses)}节点, {len(n.lines)}线路, "
                f"{len(n.generators)}发电机, {len(n.storage_units)}储能, {len(n.loads)}负荷")

    # --- 出清 (DC-OPF) ---
    logger.info("日前市场出清 — PyPSA DC-OPF + HiGHS 求解器...")
    status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
    logger.info(f"求解状态: {status}")

    if status != "ok":
        logger.error(f"出清失败: {status}")
        return None, None

    # --- 提取结果 ---
    result = MarketResult(num_periods=T, period_hours=0.25)

    for bus in n.buses.index:
        if bus in n.buses_t.marginal_price.columns:
            result.lmp[bus] = np.clip(n.buses_t.marginal_price[bus].values, 0, 1500)

    for gen_id in n.generators.index:
        power = n.generators_t.p[gen_id].values if gen_id in n.generators_t.p.columns else np.zeros(T)
        result.unit_results[gen_id] = UnitResult(
            unit_id=gen_id, commitment=(power > 0.01).astype(float), power=power,
        )

    for su_id in n.storage_units.index:
        p = n.storage_units_t.p[su_id].values if su_id in n.storage_units_t.p.columns else np.zeros(T)
        soc = n.storage_units_t.state_of_charge[su_id].values if su_id in n.storage_units_t.state_of_charge.columns else np.zeros(T)
        cap = units[su_id].storage_capacity_mwh if su_id in units else 200
        result.unit_results[su_id] = UnitResult(
            unit_id=su_id, commitment=np.ones(T), power=p,
            charge_power=np.maximum(-p, 0), discharge_power=np.maximum(p, 0),
            soc=soc / cap,
        )

    result.system_cost = float(n.objective) if n.objective else 0

    # 统一结算点电价
    usp = np.zeros(T)
    for t in range(T):
        wt, tot = 0.0, 0.0
        for uid, ur in result.unit_results.items():
            if ur.power[t] > 0.01 and uid in units:
                bus = units[uid].node
                if bus in result.lmp:
                    wt += result.lmp[bus][t] * ur.power[t]
                    tot += ur.power[t]
        usp[t] = wt / tot if tot > 0 else 0
    result.unified_settlement_price = usp

    # === 结算 ===
    engine = SettlementEngine(
        units=units, da_result=result,
        bids={k: v for k, v in bids.items() if isinstance(v, CoalUnitBid)},
    )

    # ============================================================
    #  输出结果
    # ============================================================
    print()
    print(engine.summary_report())

    # --- LMP ---
    print()
    print("=" * 72)
    print("节点边际电价 (LMP) — 每4小时取样 (元/MWh)")
    print("=" * 72)
    hrs = [f"{h:02d}:00" for h in range(0, 24, 4)]
    st = list(range(0, 96, 16))
    print(f"{'节点':<10}" + "".join(f"{h:<10}" for h in hrs))
    print("-" * 72)
    for bus in sorted(result.lmp):
        p = result.lmp[bus]
        print(f"{bus:<10}" + "".join(f"{p[t]:<10.1f}" for t in st))
    print(f"{'统一结算':<10}" + "".join(f"{usp[t]:<10.1f}" for t in st))

    # LMP差异分析
    lmp_all = np.array(list(result.lmp.values()))
    lmp_spread = lmp_all.max(axis=0) - lmp_all.min(axis=0)
    congested_periods = np.sum(lmp_spread > 0.1)
    print(f"\n阻塞分析: {congested_periods}/{T} 个时段存在节点电价分裂 (LMP差异>0.1)")
    if congested_periods > 0:
        print(f"  最大LMP价差: {lmp_spread.max():.1f} 元/MWh")
    print(f"全天统一结算点电价: 均值={usp.mean():.1f}, 最高={usp.max():.1f}, 最低={usp.min():.1f}")

    # --- 机组出力 ---
    print()
    print("=" * 72)
    print("各机组出力计划 (MW) — 每4小时取样")
    print("=" * 72)
    print(f"{'机组':<12}" + "".join(f"{h:<10}" for h in hrs))
    print("-" * 72)
    for uid, ur in result.unit_results.items():
        print(f"{uid:<12}" + "".join(f"{ur.power[t]:<10.1f}" for t in st))

    # --- 储能 ---
    for uid, ur in result.unit_results.items():
        if ur.soc is not None:
            print(f"\n{uid} SOC(%)  " + "".join(f"{ur.soc[t]*100:<10.1f}" for t in st))

    # --- 线路潮流 ---
    print()
    print("=" * 72)
    print("线路潮流 (MW) / 容量利用率 — 每4小时取样")
    print("=" * 72)
    for lid in n.lines.index:
        if lid in n.lines_t.p0.columns:
            flow = n.lines_t.p0[lid].values
            cap = n.lines.loc[lid, "s_nom"]
            peak_util = np.max(np.abs(flow)) / cap * 100 if cap > 0 else 0
            congested = "⚠" if peak_util > 95 else " "
            row = f"{lid:<24}{congested}"
            for t in st:
                f_t = flow[t]
                u_t = abs(f_t) / cap * 100 if cap > 0 else 0
                row += f"{f_t:>6.0f}({u_t:>2.0f}%)"
            print(row)

    # --- 总结 ---
    print()
    print("=" * 72)
    total_gen = sum(ur.power[ur.power > 0].sum() for ur in result.unit_results.values()) * 0.25
    print(f"系统总成本: {result.system_cost:,.0f} 元")
    print(f"总发电量: {total_gen:,.0f} MWh")
    print(f"求解器: HiGHS | 网络: IEEE 6-bus DC-OPF | 时段: {T}×15min")

    return result, n


if __name__ == "__main__":
    run_demo()
