"""
数据模型定义
按照《重庆电力现货交易实施细则V2.0》规则定义所有数据结构
"""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional
import numpy as np


# ============================================================
#  枚举类型
# ============================================================

class UnitType(Enum):
    """机组类型"""
    COAL = "coal"                # 常规燃煤机组
    RENEWABLE = "renewable"      # 新能源场站
    STORAGE = "storage"          # 独立储能
    CHP = "chp"                  # 热电联产
    SELF_GEN = "self_gen"        # 并网自备电厂
    # 以下为非市场机组
    GAS = "gas"                  # 燃气机组
    HYDRO = "hydro"              # 水电
    BIOMASS = "biomass"          # 生物质


class ParticipationMode(Enum):
    """参与方式"""
    BID_PRICE_QTY = "bid_price_qty"    # 报量报价
    BID_QTY_ONLY = "bid_qty_only"      # 报量不报价（价格接受者）
    PRICE_TAKER = "price_taker"        # 纯价格接受者


class StartupState(Enum):
    """启动状态"""
    COLD = "cold"        # 冷态（停机>72h）
    WARM = "warm"        # 温态
    HOT = "hot"          # 热态（停机<10h）


class UnitStatus(Enum):
    """机组状态"""
    AVAILABLE = "available"      # 可用
    UNAVAILABLE = "unavailable"  # 不可用（检修/非计划停运）


class UnitCommitStatus(Enum):
    """机组开停机状态"""
    ON = 1
    OFF = 0


class SpecialUnitFlag(Enum):
    """特殊机组标记"""
    NORMAL = auto()
    MUST_ON = auto()           # 必开
    MUST_OFF = auto()          # 必停
    STARTUP_PROCESS = auto()   # 开机过程
    SHUTDOWN_PROCESS = auto()  # 停机过程
    TESTING = auto()           # 试验/调试
    FUEL_CONSTRAINED = auto()  # 一次能源供应约束


# ============================================================
#  市场参数常量（附件一）
# ============================================================

# 电能量申报/出清价格上下限 (元/MWh)
PRICE_BID_UPPER = 1500.0
PRICE_BID_LOWER = 0.0
PRICE_CLEAR_UPPER = 1500.0
PRICE_CLEAR_LOWER = 0.0

# 启动费用上下限（万元/次） -> 表1按装机容量分级
STARTUP_COST_LIMITS = {
    300: {"cold": (5, 60), "warm": (5, 45), "hot": (5, 30), "noload": (0, 1)},
    600: {"cold": (5, 90), "warm": (5, 60), "hot": (5, 40), "noload": (0, 2)},
    1000: {"cold": (5, 110), "warm": (5, 75), "hot": (5, 50), "noload": (0, 3)},
}

# 惩罚因子（附件五）
PENALTY_SECTION_CLEARING = 50_000_000   # 断面约束松弛 - 出清
PENALTY_SECTION_PRICING = 1500          # 断面约束松弛 - 定价
PENALTY_BALANCE_CLEARING = 5_000_000    # 平衡约束松弛 - 出清

# 时间粒度
DA_PERIODS = 96          # 日前96个15分钟
DA_PERIOD_HOURS = 0.25   # 15分钟 = 0.25小时
RT_PERIODS = 24          # 实时24个5分钟（2小时窗口）
RT_PERIOD_HOURS = 1/12   # 5分钟
HOURS_PER_DAY = 24
SETTLEMENT_PERIODS = 24  # 24小时结算时段


# ============================================================
#  核心数据模型
# ============================================================

@dataclass
class BidPoint:
    """报价点: 一个(出力, 价格)对"""
    power_mw: float       # 出力 (MW), 储能充电为负
    price_yuan_mwh: float # 电能量价格 (元/MWh)


@dataclass
class BidCurve:
    """电能量报价曲线 (2-10个点)"""
    points: list[BidPoint] = field(default_factory=list)

    @property
    def num_points(self) -> int:
        return len(self.points)

    @property
    def min_power(self) -> float:
        return self.points[0].power_mw if self.points else 0.0

    @property
    def max_power(self) -> float:
        return self.points[-1].power_mw if self.points else 0.0

    def get_segments(self) -> list[tuple[float, float, float]]:
        """将报价曲线转换为分段线性区间列表
        返回: [(段起始MW, 段结束MW, 段价格元/MWh), ...]
        """
        segments = []
        for i in range(len(self.points) - 1):
            p0 = self.points[i]
            p1 = self.points[i + 1]
            segments.append((p0.power_mw, p1.power_mw, p1.price_yuan_mwh))
        return segments

    def marginal_cost_at(self, power_mw: float) -> float:
        """给定出力下的边际成本"""
        if not self.points:
            return 0.0
        if power_mw <= self.points[0].power_mw:
            return self.points[0].price_yuan_mwh
        for i in range(len(self.points) - 1):
            if self.points[i].power_mw <= power_mw <= self.points[i+1].power_mw:
                return self.points[i+1].price_yuan_mwh
        return self.points[-1].price_yuan_mwh


@dataclass
class CoalUnitBid:
    """燃煤机组完整报价"""
    unit_id: str
    startup_cost_cold: float = 0.0    # 冷态启动费用 (万元/次)
    startup_cost_warm: float = 0.0    # 温态启动费用
    startup_cost_hot: float = 0.0     # 热态启动费用
    noload_cost: float = 0.0          # 空载费用 (万元/小时)
    energy_curve: BidCurve = field(default_factory=BidCurve)

    def startup_cost(self, state: StartupState) -> float:
        mapping = {
            StartupState.COLD: self.startup_cost_cold,
            StartupState.WARM: self.startup_cost_warm,
            StartupState.HOT: self.startup_cost_hot,
        }
        return mapping[state]


@dataclass
class StorageBid:
    """独立储能报价"""
    unit_id: str
    energy_curve: BidCurve = field(default_factory=BidCurve)
    end_of_day_soc: Optional[float] = None   # 日末SOC期望值 (0-1)
    participate_da: bool = True               # 是否参与日前


@dataclass
class RenewableBid:
    """新能源场站报价"""
    unit_id: str
    energy_curve: BidCurve = field(default_factory=BidCurve)
    participate_da: bool = True


@dataclass
class PriceTakerSchedule:
    """价格接受者调度曲线 (热电联产/自备电厂)"""
    unit_id: str
    schedule_mw: np.ndarray = field(default_factory=lambda: np.zeros(DA_PERIODS))


@dataclass
class LoadBid:
    """用电侧申报"""
    load_id: str
    demand_mw: np.ndarray = field(default_factory=lambda: np.zeros(HOURS_PER_DAY))
    node: str = "default"


# ============================================================
#  机组静态参数 (unit_master)
# ============================================================

@dataclass
class UnitMaster:
    """机组主数据（静态参数）"""
    unit_id: str
    name: str
    unit_type: UnitType
    node: str = "default"
    participation_mode: ParticipationMode = ParticipationMode.BID_PRICE_QTY

    # 容量参数 (MW)
    rated_power: float = 0.0          # 额定有功功率
    min_tech_power: float = 0.0       # 最小技术出力 = 额定*50%
    deep_peak_power: float = 0.0      # 深调极限出力
    max_power: float = 0.0            # 最大可调出力（默认=额定）
    min_power: float = 0.0            # 最小可调出力（默认=深调极限）

    # 爬坡参数 (MW/min)
    ramp_rate: float = 0.0            # 有功功率调节速率
    deep_ramp_rate: float = 0.0       # 深调工况调节速率

    # 启停参数
    min_up_time_h: float = 6.0        # 最小连续开机时间 (h)
    min_down_time_h: float = 0.0      # 最小连续停机时间 (h)
    cold_start_time_h: float = 0.0    # 冷态启动时间 (h)
    warm_start_time_h: float = 0.0    # 温态启动时间 (h)
    hot_start_time_h: float = 0.0     # 热态启动时间 (h)
    daily_status_changes: int = 2     # 日内允许状态变化次数

    # 厂用电
    aux_power_rate: float = 0.0       # 综合厂用电率 (%)

    # 储能专用
    storage_capacity_mwh: float = 0.0     # 额定容量 (MWh)
    charge_power_mw: float = 0.0          # 额定充电功率 (MW, 正值)
    discharge_power_mw: float = 0.0       # 额定放电功率 (MW, 正值)
    charge_efficiency: float = 0.95       # 充电效率
    discharge_efficiency: float = 0.95    # 放电效率
    soc_max: float = 1.0                  # 最大荷电状态
    soc_min: float = 0.0                  # 最小荷电状态
    initial_soc: float = 0.5              # 初始SOC

    # 开停机曲线 (15min间隔的出力序列)
    startup_curve: Optional[list[float]] = None   # 典型开机曲线
    shutdown_curve: Optional[list[float]] = None  # 典型停机曲线

    # 缺省报价
    default_bid: Optional[CoalUnitBid] = None

    def __post_init__(self):
        if self.max_power == 0:
            self.max_power = self.rated_power
        if self.min_power == 0:
            self.min_power = self.deep_peak_power
        if self.min_tech_power == 0 and self.unit_type == UnitType.COAL:
            self.min_tech_power = self.rated_power * 0.5

    @property
    def capacity_class(self) -> int:
        """按装机容量分级: 300/600/1000"""
        if self.rated_power >= 1000:
            return 1000
        elif self.rated_power >= 600:
            return 600
        return 300


# ============================================================
#  运行边界 (unit_boundary_96)
# ============================================================

@dataclass
class UnitBoundary96:
    """机组运行日96点运行边界"""
    unit_id: str
    pmax_96: np.ndarray = field(default_factory=lambda: np.full(DA_PERIODS, np.inf))
    pmin_96: np.ndarray = field(default_factory=lambda: np.zeros(DA_PERIODS))
    status_96: np.ndarray = field(default_factory=lambda: np.ones(DA_PERIODS))  # 1=可用
    earliest_online_period: int = 0     # 最早可并网时段
    # 储能SOC边界
    soc_max_96: Optional[np.ndarray] = None
    soc_min_96: Optional[np.ndarray] = None
    # 特殊标记
    special_flags: np.ndarray = field(
        default_factory=lambda: np.full(DA_PERIODS, SpecialUnitFlag.NORMAL.value)
    )
    # 试验出力计划
    test_power_96: Optional[np.ndarray] = None
    # 必开最小出力
    must_on_min_power: Optional[float] = None


# ============================================================
#  市场出清结果
# ============================================================

@dataclass
class UnitResult:
    """单个机组的出清结果"""
    unit_id: str
    commitment: np.ndarray    # 开机状态 (0/1), shape=(T,)
    power: np.ndarray         # 出力 (MW), shape=(T,)
    # 储能
    charge_power: Optional[np.ndarray] = None
    discharge_power: Optional[np.ndarray] = None
    soc: Optional[np.ndarray] = None


@dataclass
class MarketResult:
    """市场出清结果"""
    num_periods: int
    period_hours: float
    unit_results: dict[str, UnitResult] = field(default_factory=dict)
    lmp: dict[str, np.ndarray] = field(default_factory=dict)          # 节点电价 {node: array}
    unified_settlement_price: Optional[np.ndarray] = None             # 统一结算点电价
    system_cost: float = 0.0
    slack_balance: Optional[np.ndarray] = None                        # 平衡松弛

    def hourly_node_price(self, node: str, periods_per_hour: int = 4) -> np.ndarray:
        """计算小时结算节点电价（时段内算术平均）"""
        if node not in self.lmp:
            return np.array([])
        prices = self.lmp[node]
        n_hours = len(prices) // periods_per_hour
        return np.array([
            prices[h*periods_per_hour:(h+1)*periods_per_hour].mean()
            for h in range(n_hours)
        ])

    def compute_unified_settlement_price(
        self, units: dict[str, UnitMaster]
    ) -> np.ndarray:
        """计算统一结算点电价 = 发电侧所有节点电价按上网电量加权平均"""
        T = self.num_periods
        usp = np.zeros(T)
        for t in range(T):
            total_energy = 0.0
            weighted_price = 0.0
            for uid, ur in self.unit_results.items():
                if uid not in units:
                    continue
                um = units[uid]
                node = um.node
                if node not in self.lmp:
                    continue
                net_power = ur.power[t] * (1 - um.aux_power_rate / 100.0)
                if net_power > 0:
                    weighted_price += self.lmp[node][t] * net_power
                    total_energy += net_power
            usp[t] = weighted_price / total_energy if total_energy > 0 else 0.0
        self.unified_settlement_price = usp
        return usp


# ============================================================
#  结算数据
# ============================================================

@dataclass
class HourlySettlement:
    """小时结算数据"""
    unit_id: str
    da_node_price_hourly: np.ndarray = field(
        default_factory=lambda: np.zeros(HOURS_PER_DAY)
    )
    rt_node_price_hourly: np.ndarray = field(
        default_factory=lambda: np.zeros(HOURS_PER_DAY)
    )
    da_energy_mwh: np.ndarray = field(
        default_factory=lambda: np.zeros(HOURS_PER_DAY)
    )
    rt_energy_mwh: np.ndarray = field(
        default_factory=lambda: np.zeros(HOURS_PER_DAY)
    )
    startup_cost: float = 0.0
    noload_cost: float = 0.0
    energy_cost: float = 0.0
    market_revenue: float = 0.0
    cost_compensation: float = 0.0  # 运行成本补偿


@dataclass
class SystemTopology:
    """简化的电网拓扑"""
    nodes: list[str] = field(default_factory=list)
    lines: list[dict] = field(default_factory=list)     # [{from, to, capacity, ptdf}]
    sections: list[dict] = field(default_factory=list)   # 断面约束
    reference_node: str = ""

    def get_ptdf(self, line_idx: int, node: str) -> float:
        """获取功率转移分布因子"""
        if line_idx < len(self.lines):
            ptdf = self.lines[line_idx].get("ptdf", {})
            return ptdf.get(node, 0.0)
        return 0.0
