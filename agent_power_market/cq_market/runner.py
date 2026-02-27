"""
市场运行主流程编排
实现完整的日前市场交易出清流程:
  1. Agent 生成报价 → BidValidator 校验
  2. SCUC 日前机组组合
  3. SCED 日前经济调度 + LMP
  4. 可靠性机组组合出清
  5. 结算计算
"""
from __future__ import annotations
import logging
import numpy as np
from .models import (
    UnitMaster, UnitType, UnitBoundary96, MarketResult, SystemTopology,
    CoalUnitBid, StorageBid, RenewableBid, PriceTakerSchedule, LoadBid,
    DA_PERIODS, DA_PERIOD_HOURS, HOURS_PER_DAY,
)
from .bid_validator import BidValidator, ValidationResult
from .clearing import SCUCSolver, SCEDSolver
from .settlement import SettlementEngine
from .agents import BaseAgent, BiddingAgent, PriceTakerAgent, LoadAgent

logger = logging.getLogger(__name__)


class MarketRunner:
    """市场运行编排器"""

    def __init__(
        self,
        units: dict[str, UnitMaster],
        agents: list[BaseAgent],
        load_agents: list[LoadAgent] | None = None,
        boundaries: dict[str, UnitBoundary96] | None = None,
        renewable_forecast: dict[str, np.ndarray] | None = None,
        topology: SystemTopology | None = None,
        reserve_up: float = 0.0,
        reserve_down: float = 0.0,
        solver_name: str = "glpk",
    ):
        self.units = units
        self.agents = {a.agent_id: a for a in agents}
        self.load_agents = load_agents or []
        self.boundaries = boundaries or {}
        self.renewable_forecast = renewable_forecast or {}
        self.topology = topology
        self.reserve_up = reserve_up
        self.reserve_down = reserve_down
        self.solver_name = solver_name

        # 结果
        self.bids: dict[str, CoalUnitBid | StorageBid | RenewableBid] = {}
        self.price_taker_schedules: dict[str, PriceTakerSchedule] = {}
        self.load_bids: list[LoadBid] = []
        self.system_demand: np.ndarray = np.zeros(DA_PERIODS)
        self.validation_results: dict[str, ValidationResult] = {}
        self.da_market_result: MarketResult | None = None
        self.da_reliability_result: MarketResult | None = None
        self.settlement_report: str = ""

    def step1_collect_bids(self):
        """Step 1: 收集所有Agent的报价/申报"""
        logger.info("Step 1: 收集报价...")
        for agent_id, agent in self.agents.items():
            bid = agent.generate_bid()
            if isinstance(bid, (CoalUnitBid, StorageBid, RenewableBid)):
                self.bids[agent.unit.unit_id] = bid
            elif isinstance(bid, PriceTakerSchedule):
                self.price_taker_schedules[agent.unit.unit_id] = bid
        logger.info(f"  收到 {len(self.bids)} 个报价, {len(self.price_taker_schedules)} 个调度曲线")

    def step2_validate_bids(self) -> bool:
        """Step 2: 校验所有报价"""
        logger.info("Step 2: 校验报价...")
        all_valid = True
        for uid, bid in self.bids.items():
            unit = self.units[uid]
            if isinstance(bid, CoalUnitBid):
                vr = BidValidator.validate_coal_bid(bid, unit)
            elif isinstance(bid, StorageBid):
                vr = BidValidator.validate_storage_bid(bid, unit)
            elif isinstance(bid, RenewableBid):
                vr = BidValidator.validate_renewable_bid(bid, unit)
            else:
                continue
            self.validation_results[uid] = vr
            if not vr.valid:
                logger.warning(f"  机组 {uid} 报价校验失败: {vr}")
                all_valid = False
            else:
                logger.info(f"  机组 {uid} 报价校验通过")
        return all_valid

    def step3_prepare_demand(self):
        """Step 3: 准备系统负荷曲线"""
        logger.info("Step 3: 准备负荷曲线...")
        for la in self.load_agents:
            lb = la.generate_bid()
            self.load_bids.append(lb)

        total_demand_24 = np.zeros(HOURS_PER_DAY)
        for lb in self.load_bids:
            total_demand_24 += lb.demand_mw

        # 24点 → 96点 (每小时内恒定)
        self.system_demand = np.repeat(total_demand_24, 4)
        logger.info(f"  系统峰值负荷: {self.system_demand.max():.0f} MW, "
                    f"谷值: {self.system_demand.min():.0f} MW")

    def step4_da_market_clear(self) -> MarketResult:
        """Step 4: 日前市场交易出清 (SCUC + SCED)"""
        logger.info("Step 4: 日前市场交易出清...")

        # 4a. SCUC
        logger.info("  4a. SCUC - 安全约束机组组合...")
        scuc = SCUCSolver(
            units=self.units,
            bids=self.bids,
            boundaries=self.boundaries,
            system_demand=self.system_demand,
            price_takers=self.price_taker_schedules,
            renewable_forecast=self.renewable_forecast,
            topology=self.topology,
            reserve_up=self.reserve_up,
            solver_name=self.solver_name,
        )
        scuc_result = scuc.solve(include_commitment=True)
        logger.info(f"    SCUC完成, 系统成本: {scuc_result.system_cost:.0f}")

        # 4b. SCED
        logger.info("  4b. SCED - 安全约束经济调度 + LMP...")
        sced = SCEDSolver(
            commitment_result=scuc_result,
            units=self.units,
            bids=self.bids,
            boundaries=self.boundaries,
            system_demand=self.system_demand,
            price_takers=self.price_taker_schedules,
            renewable_forecast=self.renewable_forecast,
            topology=self.topology,
            solver_name=self.solver_name,
        )
        self.da_market_result = sced.solve()

        if self.da_market_result.unified_settlement_price is not None:
            avg_price = self.da_market_result.unified_settlement_price.mean()
            logger.info(f"    SCED完成, 平均统一结算点电价: {avg_price:.2f} 元/MWh")

        return self.da_market_result

    def step5_da_reliability_clear(self) -> MarketResult:
        """Step 5: 可靠性机组组合出清 (用于实际执行)"""
        logger.info("Step 5: 可靠性机组组合出清...")
        # 可靠性出清使用调度预测负荷 (此处简化为与市场出清相同需求)
        scuc = SCUCSolver(
            units=self.units,
            bids=self.bids,
            boundaries=self.boundaries,
            system_demand=self.system_demand,
            price_takers=self.price_taker_schedules,
            renewable_forecast=self.renewable_forecast,
            topology=self.topology,
            reserve_up=self.reserve_up,
            solver_name=self.solver_name,
        )
        self.da_reliability_result = scuc.solve(include_commitment=True)
        logger.info(f"  可靠性出清完成")
        return self.da_reliability_result

    def step6_settlement(self) -> str:
        """Step 6: 结算计算"""
        logger.info("Step 6: 结算计算...")
        if self.da_market_result is None:
            raise RuntimeError("请先执行日前市场出清")

        engine = SettlementEngine(
            units=self.units,
            da_result=self.da_market_result,
            bids={k: v for k, v in self.bids.items() if isinstance(v, CoalUnitBid)},
        )
        self.settlement_report = engine.summary_report()
        logger.info("  结算完成")
        return self.settlement_report

    def run_full_day_ahead(self) -> str:
        """运行完整日前市场流程"""
        logger.info("=" * 60)
        logger.info("重庆电力现货市场日前出清仿真")
        logger.info("=" * 60)

        self.step1_collect_bids()
        valid = self.step2_validate_bids()
        if not valid:
            logger.warning("存在报价校验失败, 继续出清 (使用缺省参数)")

        self.step3_prepare_demand()
        self.step4_da_market_clear()
        self.step5_da_reliability_clear()
        report = self.step6_settlement()

        logger.info("=" * 60)
        logger.info("日前市场流程完成")
        logger.info("=" * 60)

        return report
