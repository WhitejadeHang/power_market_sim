"""
实时市场滚动出清模块
按照实施细则6.1节: 实时以5分钟为周期, 滚动出清未来2小时(24个5分钟时段)
T-5分钟出清 T~T+115, 其中T为正式出清, T+5~T+115为预出清
"""
from __future__ import annotations
import logging
import numpy as np
from .models import (
    UnitMaster, UnitBoundary96, MarketResult, UnitResult,
    CoalUnitBid, StorageBid, RenewableBid, PriceTakerSchedule,
    SystemTopology, RT_PERIODS, RT_PERIOD_HOURS,
)
from .clearing import SCUCSolver

logger = logging.getLogger(__name__)


class RTSCEDRollingSolver:
    """实时滚动SCED求解器
    每5分钟执行一次, 出清未来2小时 (24×5min)
    基于日前封存的申报信息
    """

    def __init__(
        self,
        units: dict[str, UnitMaster],
        bids: dict[str, CoalUnitBid | StorageBid | RenewableBid],
        da_commitment: MarketResult,
        solver_name: str = "glpk",
    ):
        self.units = units
        self.bids = bids
        self.da_commitment = da_commitment
        self.solver_name = solver_name
        self.results: list[MarketResult] = []

    def run_single_window(
        self,
        window_start_5min: int,
        rt_demand: np.ndarray,
        rt_renewable_forecast: dict[str, np.ndarray] | None = None,
        price_takers: dict[str, PriceTakerSchedule] | None = None,
    ) -> MarketResult:
        """执行单次滚动出清
        Args:
            window_start_5min: 滚动窗口起始的5分钟序号 (0-287)
            rt_demand: 未来24个5分钟的系统需求 shape=(24,)
            rt_renewable_forecast: 新能源预测
            price_takers: 价格接受者曲线
        """
        # 从日前开机组合中提取对应时段的开机状态
        boundaries = {}
        for uid, ur in self.da_commitment.unit_results.items():
            if uid in self.units and self.units[uid].unit_type.value == "coal":
                da_period = window_start_5min // 3
                commit_val = ur.commitment[min(da_period, len(ur.commitment)-1)]
                bnd = UnitBoundary96(unit_id=uid)
                bnd.status_96 = np.full(RT_PERIODS, commit_val)
                boundaries[uid] = bnd

        solver = SCUCSolver(
            units=self.units,
            bids=self.bids,
            boundaries=boundaries,
            system_demand=rt_demand,
            price_takers=price_takers or {},
            renewable_forecast=rt_renewable_forecast or {},
            solver_name=self.solver_name,
            num_periods=RT_PERIODS,
            period_hours=RT_PERIOD_HOURS,
        )

        result = solver.solve(include_commitment=True)
        self.results.append(result)
        return result

    def run_full_day(
        self,
        rt_demand_288: np.ndarray,
        rt_renewable_forecast_288: dict[str, np.ndarray] | None = None,
        price_takers: dict[str, PriceTakerSchedule] | None = None,
    ) -> list[MarketResult]:
        """模拟运行日全天288个5分钟周期的滚动出清
        仅按小时取样运行 (24次) 以控制计算量
        """
        logger.info("开始实时滚动出清 (每小时取样)...")
        all_results = []
        for hour in range(24):
            t_start = hour * 12   # 每小时12个5分钟
            window_demand = rt_demand_288[t_start:t_start+RT_PERIODS]
            if len(window_demand) < RT_PERIODS:
                pad = RT_PERIODS - len(window_demand)
                window_demand = np.pad(window_demand, (0, pad), mode='edge')

            window_re = {}
            if rt_renewable_forecast_288:
                for uid, fc in rt_renewable_forecast_288.items():
                    window_fc = fc[t_start:t_start+RT_PERIODS]
                    if len(window_fc) < RT_PERIODS:
                        window_fc = np.pad(window_fc, (0, RT_PERIODS-len(window_fc)), mode='edge')
                    window_re[uid] = window_fc

            result = self.run_single_window(
                window_start_5min=t_start,
                rt_demand=window_demand,
                rt_renewable_forecast=window_re,
                price_takers=price_takers,
            )
            all_results.append(result)
            logger.info(f"  Hour {hour:02d}: 出清完成, cost={result.system_cost:.0f}")

        return all_results
