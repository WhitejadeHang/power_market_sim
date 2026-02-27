"""
报价校验模块
按照《重庆电力现货交易实施细则V2.0》5.5节要求，对各类主体报价进行硬校验。
校验不通过不允许提交。
"""
from __future__ import annotations
from dataclasses import dataclass, field
from .models import (
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    UnitMaster, UnitType, StartupState,
    PRICE_BID_UPPER, PRICE_BID_LOWER, STARTUP_COST_LIMITS,
)


@dataclass
class ValidationError:
    field: str
    message: str


@dataclass
class ValidationResult:
    valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)

    def add_error(self, fld: str, msg: str):
        self.valid = False
        self.errors.append(ValidationError(fld, msg))

    def __str__(self):
        if self.valid:
            return "校验通过"
        return "校验失败:\n" + "\n".join(
            f"  [{e.field}] {e.message}" for e in self.errors
        )


class BidValidator:
    """报价校验器"""

    @staticmethod
    def validate_coal_bid(bid: CoalUnitBid, unit: UnitMaster) -> ValidationResult:
        """校验燃煤机组报价"""
        result = ValidationResult()
        curve = bid.energy_curve

        # 1. 报价点数: 2-10
        if not (2 <= curve.num_points <= 10):
            result.add_error("num_points", f"报价点数须为2-10, 当前{curve.num_points}")

        if curve.num_points >= 2:
            # 2. 第一个点=深调极限出力
            if abs(curve.points[0].power_mw - unit.deep_peak_power) > 0.5:
                result.add_error(
                    "first_point",
                    f"第一个报价点出力({curve.points[0].power_mw}MW)"
                    f"须等于深调极限出力({unit.deep_peak_power}MW)"
                )

            # 3. 最后一个点=额定有功功率
            if abs(curve.points[-1].power_mw - unit.rated_power) > 0.5:
                result.add_error(
                    "last_point",
                    f"最后一个报价点出力({curve.points[-1].power_mw}MW)"
                    f"须等于额定有功功率({unit.rated_power}MW)"
                )

            # 4. 单调递增
            for i in range(1, curve.num_points):
                if curve.points[i].power_mw <= curve.points[i-1].power_mw:
                    result.add_error("monotonic_power", f"第{i+1}点出力须大于第{i}点")
                if curve.points[i].price_yuan_mwh < curve.points[i-1].price_yuan_mwh:
                    result.add_error("monotonic_price", f"第{i+1}点价格须不小于第{i}点")

            # 5. 最小出力跨度
            span = unit.rated_power - unit.deep_peak_power
            min_step = max(span * 0.05, 1.0)
            for i in range(1, curve.num_points):
                step = curve.points[i].power_mw - curve.points[i-1].power_mw
                if step < min_step - 0.01:
                    result.add_error(
                        "min_step",
                        f"第{i}~{i+1}点跨度{step:.1f}MW < 最小跨度{min_step:.1f}MW"
                    )

        # 6. 价格上下限
        for i, pt in enumerate(curve.points):
            if pt.price_yuan_mwh < PRICE_BID_LOWER or pt.price_yuan_mwh > PRICE_BID_UPPER:
                result.add_error(
                    "price_limit",
                    f"第{i+1}点价格{pt.price_yuan_mwh}超出限价[{PRICE_BID_LOWER},{PRICE_BID_UPPER}]"
                )

        # 7. 启动费用上下限
        cap_class = unit.capacity_class
        limits = STARTUP_COST_LIMITS.get(cap_class, STARTUP_COST_LIMITS[300])
        for state_name, (lo, hi) in [
            ("cold", limits["cold"]),
            ("warm", limits["warm"]),
            ("hot", limits["hot"]),
        ]:
            cost = bid.startup_cost(StartupState[state_name.upper()])
            if cost < lo or cost > hi:
                result.add_error(
                    f"startup_{state_name}",
                    f"{state_name}态启动费用{cost}万元超出[{lo},{hi}]"
                )

        # 8. 冷>温>热
        if not (bid.startup_cost_cold >= bid.startup_cost_warm >= bid.startup_cost_hot):
            result.add_error("startup_order", "启动费用须满足: 冷态 >= 温态 >= 热态")

        # 9. 空载费用上下限
        noload_limits = limits["noload"]
        if bid.noload_cost < noload_limits[0] or bid.noload_cost > noload_limits[1]:
            result.add_error(
                "noload",
                f"空载费用{bid.noload_cost}万元/h超出[{noload_limits[0]},{noload_limits[1]}]"
            )

        # 10. 最小单位校验
        for pt in curve.points:
            if pt.power_mw != round(pt.power_mw):
                result.add_error("unit_power", f"电力{pt.power_mw}MW须为整数")
            if pt.price_yuan_mwh != round(pt.price_yuan_mwh):
                result.add_error("unit_price", f"价格{pt.price_yuan_mwh}须为整数")

        return result

    @staticmethod
    def validate_storage_bid(bid: StorageBid, unit: UnitMaster) -> ValidationResult:
        """校验独立储能报价"""
        result = ValidationResult()
        curve = bid.energy_curve

        if not (2 <= curve.num_points <= 10):
            result.add_error("num_points", f"报价点数须为2-10, 当前{curve.num_points}")

        if curve.num_points >= 2:
            # 第一个点=额定充电功率(负值)
            expected_first = -unit.charge_power_mw
            if abs(curve.points[0].power_mw - expected_first) > 0.5:
                result.add_error(
                    "first_point",
                    f"第一个报价点({curve.points[0].power_mw}MW)"
                    f"须等于额定充电功率负值({expected_first}MW)"
                )

            # 最后一个点=额定放电功率(正值)
            if abs(curve.points[-1].power_mw - unit.discharge_power_mw) > 0.5:
                result.add_error(
                    "last_point",
                    f"最后一个报价点({curve.points[-1].power_mw}MW)"
                    f"须等于额定放电功率({unit.discharge_power_mw}MW)"
                )

            # 单调递增
            for i in range(1, curve.num_points):
                if curve.points[i].power_mw <= curve.points[i-1].power_mw:
                    result.add_error("monotonic_power", f"第{i+1}点出力须大于第{i}点")
                if curve.points[i].price_yuan_mwh < curve.points[i-1].price_yuan_mwh:
                    result.add_error("monotonic_price", f"第{i+1}点价格须不小于第{i}点")

            # 最小跨度
            span = unit.discharge_power_mw + unit.charge_power_mw
            min_step = max(span * 0.05, 1.0)
            for i in range(1, curve.num_points):
                step = curve.points[i].power_mw - curve.points[i-1].power_mw
                if step < min_step - 0.01:
                    result.add_error("min_step", f"第{i}~{i+1}点跨度不足")

        # 价格上下限
        for i, pt in enumerate(curve.points):
            if pt.price_yuan_mwh < PRICE_BID_LOWER or pt.price_yuan_mwh > PRICE_BID_UPPER:
                result.add_error("price_limit", f"第{i+1}点价格超限")

        # SOC期望值
        if bid.end_of_day_soc is not None:
            if not (0.0 <= bid.end_of_day_soc <= 1.0):
                result.add_error("soc", f"日末SOC期望值须在[0,1], 当前{bid.end_of_day_soc}")

        return result

    @staticmethod
    def validate_renewable_bid(bid: RenewableBid, unit: UnitMaster) -> ValidationResult:
        """校验新能源场站报价 — 参照燃煤机组"""
        result = ValidationResult()
        curve = bid.energy_curve

        if not (2 <= curve.num_points <= 10):
            result.add_error("num_points", f"报价点数须为2-10, 当前{curve.num_points}")

        if curve.num_points >= 2:
            # 第一点=0, 最后一点=额定
            if abs(curve.points[0].power_mw) > 0.5:
                result.add_error("first_point", "新能源第一个报价点出力须为0")
            if abs(curve.points[-1].power_mw - unit.rated_power) > 0.5:
                result.add_error("last_point", f"最后点须等于额定功率{unit.rated_power}MW")

            for i in range(1, curve.num_points):
                if curve.points[i].power_mw <= curve.points[i-1].power_mw:
                    result.add_error("monotonic_power", f"第{i+1}点出力须大于第{i}点")
                if curve.points[i].price_yuan_mwh < curve.points[i-1].price_yuan_mwh:
                    result.add_error("monotonic_price", f"第{i+1}点价格须不小于第{i}点")

        for pt in curve.points:
            if pt.price_yuan_mwh < PRICE_BID_LOWER or pt.price_yuan_mwh > PRICE_BID_UPPER:
                result.add_error("price_limit", "价格超限")

        return result
