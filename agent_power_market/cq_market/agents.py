"""
市场主体Agent框架
按照规则区分"报量报价"和"价格接受者"两类Agent，灵活可扩展。
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
import numpy as np
from .models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, LoadBid, MarketResult,
    DA_PERIODS, HOURS_PER_DAY,
    PRICE_BID_UPPER,
)


class BaseAgent(ABC):
    """Agent 基类"""

    def __init__(self, agent_id: str, unit: UnitMaster):
        self.agent_id = agent_id
        self.unit = unit
        self.history: list[dict] = []

    @abstractmethod
    def generate_bid(self, market_info: dict | None = None):
        """生成报价/申报曲线"""
        ...

    def record(self, entry: dict):
        self.history.append(entry)


class BiddingAgent(BaseAgent):
    """报量报价Agent (煤机/新能源/储能)
    可由外部策略驱动报价曲线和费用参数
    """

    def __init__(self, agent_id: str, unit: UnitMaster, strategy: str = "marginal_cost"):
        super().__init__(agent_id, unit)
        self.strategy = strategy
        self.markup_pct: float = 0.0     # 加价比例

    def generate_bid(self, market_info: dict | None = None):
        if self.unit.unit_type == UnitType.COAL:
            return self._generate_coal_bid(market_info)
        elif self.unit.unit_type == UnitType.STORAGE:
            return self._generate_storage_bid(market_info)
        elif self.unit.unit_type == UnitType.RENEWABLE:
            return self._generate_renewable_bid(market_info)
        raise ValueError(f"不支持的机组类型: {self.unit.unit_type}")

    def _generate_coal_bid(self, market_info) -> CoalUnitBid:
        u = self.unit
        base_price = 300.0
        if self.strategy == "marginal_cost":
            base_price = 280 + self.markup_pct * 280
        elif self.strategy == "competitive":
            base_price = 250 + self.markup_pct * 250

        n_points = 5
        powers = np.linspace(u.deep_peak_power, u.rated_power, n_points)
        prices = [base_price + i * 20 for i in range(n_points)]

        curve = BidCurve(points=[
            BidPoint(power_mw=round(p), price_yuan_mwh=round(c))
            for p, c in zip(powers, prices)
        ])

        cap = u.capacity_class
        cold_cost = {"300": 30, "600": 50, "1000": 70}.get(str(cap), 30)
        warm_cost = cold_cost * 0.7
        hot_cost = cold_cost * 0.5

        bid = CoalUnitBid(
            unit_id=u.unit_id,
            startup_cost_cold=cold_cost,
            startup_cost_warm=warm_cost,
            startup_cost_hot=hot_cost,
            noload_cost=0.5 if cap <= 300 else 1.0,
            energy_curve=curve,
        )
        self.record({"type": "coal_bid", "bid": bid})
        return bid

    def _generate_storage_bid(self, market_info) -> StorageBid:
        u = self.unit
        points = [
            BidPoint(power_mw=round(-u.charge_power_mw), price_yuan_mwh=100),
            BidPoint(power_mw=0, price_yuan_mwh=300),
            BidPoint(power_mw=round(u.discharge_power_mw), price_yuan_mwh=500),
        ]
        return StorageBid(
            unit_id=u.unit_id,
            energy_curve=BidCurve(points=points),
            end_of_day_soc=0.5,
        )

    def _generate_renewable_bid(self, market_info) -> RenewableBid:
        u = self.unit
        points = [
            BidPoint(power_mw=0, price_yuan_mwh=0),
            BidPoint(power_mw=round(u.rated_power), price_yuan_mwh=50),
        ]
        return RenewableBid(
            unit_id=u.unit_id,
            energy_curve=BidCurve(points=points),
            participate_da=True,
        )


class PriceTakerAgent(BaseAgent):
    """价格接受者Agent (热电联产/自备电厂/用电侧)"""

    def __init__(self, agent_id: str, unit: UnitMaster, base_schedule: np.ndarray | None = None):
        super().__init__(agent_id, unit)
        self.base_schedule = base_schedule

    def generate_bid(self, market_info=None) -> PriceTakerSchedule:
        if self.base_schedule is not None:
            schedule = self.base_schedule.copy()
        else:
            schedule = np.full(DA_PERIODS, self.unit.rated_power * 0.6)
        return PriceTakerSchedule(unit_id=self.unit.unit_id, schedule_mw=schedule)


class LoadAgent(BaseAgent):
    """用电侧Agent"""

    def __init__(self, agent_id: str, unit: UnitMaster, base_demand: np.ndarray | None = None):
        super().__init__(agent_id, unit)
        self.base_demand = base_demand

    def generate_bid(self, market_info=None) -> LoadBid:
        if self.base_demand is not None:
            demand = self.base_demand.copy()
        else:
            demand = np.full(HOURS_PER_DAY, 500.0)  # 500MW flat
        return LoadBid(load_id=self.agent_id, demand_mw=demand, node=self.unit.node)
