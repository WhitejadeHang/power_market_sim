"""
结算模块
按照《重庆电力市场结算实施细则V2.0》实现

核心结算逻辑:
- 发电侧: 按节点电价结算
- 用电侧: 按统一结算点电价结算
- 小时结算电价: DA=4个15min均值, RT=12个5min均值
- 机组运行成本补偿: 启动+空载+电能量损益
"""
from __future__ import annotations
import numpy as np
from .models import (
    UnitMaster, UnitType, MarketResult, CoalUnitBid, HourlySettlement,
    DA_PERIODS, DA_PERIOD_HOURS, HOURS_PER_DAY,
)


class SettlementEngine:
    """结算引擎"""

    def __init__(
        self,
        units: dict[str, UnitMaster],
        da_result: MarketResult,
        rt_result: MarketResult | None = None,
        bids: dict[str, CoalUnitBid] | None = None,
    ):
        self.units = units
        self.da_result = da_result
        self.rt_result = rt_result
        self.bids = bids or {}

    def compute_hourly_da_prices(self) -> dict[str, np.ndarray]:
        """计算日前小时结算电价 (每小时=4个15min均值)"""
        hourly = {}
        for node, prices_96 in self.da_result.lmp.items():
            hp = np.zeros(HOURS_PER_DAY)
            for h in range(HOURS_PER_DAY):
                start = h * 4
                end = min(start + 4, len(prices_96))
                hp[h] = prices_96[start:end].mean()
            hourly[node] = hp
        return hourly

    def compute_unified_settlement_price_hourly(self) -> np.ndarray:
        """计算小时统一结算点电价"""
        if self.da_result.unified_settlement_price is None:
            self.da_result.compute_unified_settlement_price(self.units)
        usp_96 = self.da_result.unified_settlement_price
        usp_hourly = np.zeros(HOURS_PER_DAY)
        for h in range(HOURS_PER_DAY):
            start = h * 4
            end = min(start + 4, len(usp_96))
            usp_hourly[h] = usp_96[start:end].mean()
        return usp_hourly

    def settle_generator(self, unit_id: str) -> HourlySettlement:
        """计算单个发电机组的结算"""
        um = self.units[unit_id]
        ur = self.da_result.unit_results.get(unit_id)
        if ur is None:
            return HourlySettlement(unit_id=unit_id)

        settlement = HourlySettlement(unit_id=unit_id)

        # 小时节点电价
        node_prices = self.da_result.lmp.get(um.node, np.zeros(DA_PERIODS))
        for h in range(HOURS_PER_DAY):
            start = h * 4
            end = min(start + 4, len(node_prices))
            settlement.da_node_price_hourly[h] = node_prices[start:end].mean()

        # 小时上网电量 (扣除厂用电)
        aux_rate = um.aux_power_rate / 100.0
        for h in range(HOURS_PER_DAY):
            start = h * 4
            end = min(start + 4, len(ur.power))
            power_15min = ur.power[start:end]
            energy_mwh = power_15min.sum() * DA_PERIOD_HOURS * (1 - aux_rate)
            settlement.da_energy_mwh[h] = energy_mwh

        # 市场收益
        settlement.market_revenue = np.sum(
            settlement.da_node_price_hourly * settlement.da_energy_mwh
        )

        # 成本补偿 (仅煤机)
        if um.unit_type == UnitType.COAL and unit_id in self.bids:
            bid = self.bids[unit_id]
            settlement = self._compute_cost_compensation(
                settlement, ur, um, bid
            )

        return settlement

    def _compute_cost_compensation(
        self,
        settlement: HourlySettlement,
        ur,
        um: UnitMaster,
        bid: CoalUnitBid,
    ) -> HourlySettlement:
        """计算机组运行成本补偿
        R_补偿 = max(R_启动 + R_空载 + R_发电损益, 0)
        """
        T = len(ur.power)
        dt = DA_PERIOD_HOURS

        # 启动费用
        startup_cost = 0.0
        for t in range(1, T):
            if ur.commitment[t] == 1 and ur.commitment[t-1] == 0:
                startup_cost += bid.startup_cost_hot * 10000
        if ur.commitment[0] == 1:
            startup_cost += bid.startup_cost_hot * 10000
        settlement.startup_cost = startup_cost

        # 空载费用
        online_hours = ur.commitment.sum() * dt
        settlement.noload_cost = bid.noload_cost * 10000 * online_hours

        # 电能量成本与收益
        node_prices = self.da_result.lmp.get(um.node, np.zeros(T))
        total_energy_cost = 0.0
        total_market_revenue = 0.0
        aux_rate = um.aux_power_rate / 100.0

        for t in range(T):
            if ur.power[t] > 0.01:
                mc = bid.energy_curve.marginal_cost_at(ur.power[t])
                energy_cost_t = mc * ur.power[t] * dt
                net_power = ur.power[t] * (1 - aux_rate)
                market_rev_t = node_prices[t] * net_power * dt
                total_energy_cost += energy_cost_t
                total_market_revenue += market_rev_t

        settlement.energy_cost = total_energy_cost

        # 发电损益
        generation_pnl = total_market_revenue - total_energy_cost

        # 总运行成本补偿
        total_cost = settlement.startup_cost + settlement.noload_cost - generation_pnl
        settlement.cost_compensation = max(total_cost, 0)

        return settlement

    def settle_all(self) -> dict[str, HourlySettlement]:
        """计算所有机组结算"""
        results = {}
        for uid in self.units:
            if uid in self.da_result.unit_results:
                results[uid] = self.settle_generator(uid)
        return results

    def summary_report(self) -> str:
        """生成结算汇总报告"""
        settlements = self.settle_all()
        usp = self.compute_unified_settlement_price_hourly()

        lines = []
        lines.append("=" * 70)
        lines.append("重庆电力现货市场日前结算汇总报告")
        lines.append("=" * 70)
        lines.append("")

        # 统一结算点电价
        lines.append("统一结算点小时电价 (元/MWh):")
        for h in range(HOURS_PER_DAY):
            lines.append(f"  {h:02d}:00-{h+1:02d}:00  {usp[h]:.2f}")

        lines.append("")
        lines.append(f"  全天加权均价: {usp.mean():.2f} 元/MWh")
        lines.append("")

        # 各机组结算
        lines.append("发电侧结算明细:")
        lines.append(f"{'机组ID':<12} {'类型':<10} {'上网电量(MWh)':<14} "
                     f"{'市场收益(万元)':<14} {'成本补偿(万元)':<14}")
        lines.append("-" * 70)

        total_energy = 0
        total_revenue = 0
        total_compensation = 0

        for uid, s in settlements.items():
            um = self.units[uid]
            energy = s.da_energy_mwh.sum()
            revenue = s.market_revenue / 10000
            comp = s.cost_compensation / 10000
            total_energy += energy
            total_revenue += revenue
            total_compensation += comp
            lines.append(
                f"{uid:<12} {um.unit_type.value:<10} {energy:<14.1f} "
                f"{revenue:<14.2f} {comp:<14.2f}"
            )

        lines.append("-" * 70)
        lines.append(
            f"{'合计':<12} {'':<10} {total_energy:<14.1f} "
            f"{total_revenue:<14.2f} {total_compensation:<14.2f}"
        )
        lines.append("")
        lines.append(f"系统总发电成本: {self.da_result.system_cost/10000:.2f} 万元")

        return "\n".join(lines)
