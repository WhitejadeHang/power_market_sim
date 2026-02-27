"""
重庆电力现货市场仿真 — IEEE 6-bus 网络约束出清
==================================================

建模框架: PyPSA → Linopy → HiGHS / SCIP
报价建模: 分段线性化 (每台煤机报价曲线分解为多个 segment generator)
网络约束: DC-OPF 线路潮流约束, 自动产生 LMP 阻塞分量

场景:
  - IEEE 6-bus, 11条线路, 部分线路容量受限
  - 4台煤机 (分段报价), 1风电, 1储能, 1 CHP
  - 96×15min (完整24小时日前出清)
"""
from __future__ import annotations
import logging
import numpy as np
import pandas as pd

from .models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, DA_PERIODS,
)
from .bid_validator import BidValidator
from .ieee_network import create_ieee6bus, generate_load_profile_96, generate_wind_profile_96
from .pypsa_clearing import PyPSAMarketClearing, decompose_bid_to_segments
from .settlement import SettlementEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)
T = DA_PERIODS


def create_units() -> dict[str, UnitMaster]:
    return {
        "Coal_B1_1": UnitMaster(
            unit_id="Coal_B1_1", name="渝北#1", unit_type=UnitType.COAL,
            node="Bus1", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=5.0,
            min_up_time_h=8, min_down_time_h=4, aux_power_rate=6.5,
        ),
        "Coal_B1_2": UnitMaster(
            unit_id="Coal_B1_2", name="渝北#2", unit_type=UnitType.COAL,
            node="Bus1", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=5.0,
            min_up_time_h=8, min_down_time_h=4, aux_power_rate=6.5,
        ),
        "Coal_B2_1": UnitMaster(
            unit_id="Coal_B2_1", name="江津#1", unit_type=UnitType.COAL,
            node="Bus2", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=6.0,
            min_up_time_h=6, min_down_time_h=4, aux_power_rate=6.0,
        ),
        "Coal_B2_2": UnitMaster(
            unit_id="Coal_B2_2", name="合川#1", unit_type=UnitType.COAL,
            node="Bus2", rated_power=300, deep_peak_power=120,
            min_power=120, max_power=300, ramp_rate=6.0,
            min_up_time_h=6, min_down_time_h=4, aux_power_rate=6.0,
        ),
        "Wind_B3": UnitMaster(
            unit_id="Wind_B3", name="巫山风电", unit_type=UnitType.RENEWABLE,
            node="Bus3", rated_power=200,
        ),
        "ESS_B6": UnitMaster(
            unit_id="ESS_B6", name="渝中储能", unit_type=UnitType.STORAGE,
            node="Bus6", rated_power=100, charge_power_mw=100, discharge_power_mw=100,
            storage_capacity_mwh=200, initial_soc=0.5, soc_max=0.95, soc_min=0.05,
            charge_efficiency=0.92, discharge_efficiency=0.92,
        ),
        "CHP_B1": UnitMaster(
            unit_id="CHP_B1", name="重庆热电", unit_type=UnitType.CHP,
            node="Bus1", rated_power=100,
        ),
    }


def create_bids(units):
    bids = {}

    bids["Coal_B1_1"] = CoalUnitBid(
        unit_id="Coal_B1_1",
        startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=12, noload_cost=0.5,
        energy_curve=BidCurve(points=[
            BidPoint(120, 220), BidPoint(180, 260), BidPoint(240, 300), BidPoint(300, 340),
        ]),
    )
    bids["Coal_B1_2"] = CoalUnitBid(
        unit_id="Coal_B1_2",
        startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=12, noload_cost=0.5,
        energy_curve=BidCurve(points=[
            BidPoint(120, 240), BidPoint(200, 290), BidPoint(300, 370),
        ]),
    )
    bids["Coal_B2_1"] = CoalUnitBid(
        unit_id="Coal_B2_1",
        startup_cost_cold=28, startup_cost_warm=18, startup_cost_hot=10, noload_cost=0.4,
        energy_curve=BidCurve(points=[
            BidPoint(120, 260), BidPoint(200, 330), BidPoint(300, 420),
        ]),
    )
    bids["Coal_B2_2"] = CoalUnitBid(
        unit_id="Coal_B2_2",
        startup_cost_cold=28, startup_cost_warm=18, startup_cost_hot=10, noload_cost=0.4,
        energy_curve=BidCurve(points=[
            BidPoint(120, 300), BidPoint(200, 380), BidPoint(300, 480),
        ]),
    )
    bids["Wind_B3"] = RenewableBid(
        unit_id="Wind_B3",
        energy_curve=BidCurve(points=[BidPoint(0, 0), BidPoint(200, 10)]),
    )
    bids["ESS_B6"] = StorageBid(
        unit_id="ESS_B6",
        energy_curve=BidCurve(points=[
            BidPoint(-100, 150), BidPoint(0, 280), BidPoint(100, 450),
        ]),
        end_of_day_soc=0.5,
    )
    return bids


def run_demo(solver_name: str = "highs"):
    print("=" * 72)
    print("  重庆电力现货市场仿真系统")
    print(f"  IEEE 6-bus | PyPSA→Linopy→{solver_name.upper()} | 分段报价 | 96×15min")
    print("=" * 72)
    print()

    # 1. 网络 + 机组 + 报价
    units = create_units()
    bids = create_bids(units)
    base_net = create_ieee6bus()

    logger.info(f"网络: {len(base_net.buses)}节点, {len(base_net.lines)}线路")
    for uid, u in units.items():
        logger.info(f"  {uid}: {u.name} ({u.unit_type.value}) {u.rated_power}MW @ {u.node}")

    # 2. 报价校验
    logger.info("报价校验...")
    for uid, bid in bids.items():
        if isinstance(bid, CoalUnitBid):
            vr = BidValidator.validate_coal_bid(bid, units[uid])
            logger.info(f"  {uid}: {'✓' if vr.valid else '✗'}")

    # 3. 分段分解展示
    logger.info("报价曲线分段分解:")
    for uid in ["Coal_B1_1", "Coal_B2_2"]:
        if uid in bids and isinstance(bids[uid], CoalUnitBid):
            segs = decompose_bid_to_segments(uid, bids[uid], units[uid])
            for s in segs:
                logger.info(f"  {s['name']}: {s['p_nom']:.0f}MW @ {s['marginal_cost']:.0f}元/MWh")

    # 4. 负荷 / 新能源
    load_profiles = {
        "Load_Bus3": generate_load_profile_96(300, seed=10),
        "Load_Bus4": generate_load_profile_96(450, seed=20),
        "Load_Bus5": generate_load_profile_96(350, seed=30),
    }
    total_load = sum(load_profiles.values())
    logger.info(f"系统负荷: 峰值={total_load.max():.0f}MW, 谷值={total_load.min():.0f}MW")

    wind_fc = {"Wind_B3": generate_wind_profile_96(200, seed=123)}
    logger.info(f"风电预测: 均值={wind_fc['Wind_B3'].mean():.0f}MW")

    chp_hours = np.arange(T) * 0.25
    chp_sched = np.where((chp_hours >= 6) & (chp_hours < 22), 80, 50).astype(float)
    pt_schedules = {"CHP_B1": PriceTakerSchedule(unit_id="CHP_B1", schedule_mw=chp_sched)}

    # 5. 构建出清网络
    engine = PyPSAMarketClearing(
        base_network=base_net,
        solver_name=solver_name,
        num_periods=T,
        period_minutes=15,
    )
    engine.build_network(
        units=units, bids=bids,
        load_profiles=load_profiles,
        renewable_forecasts=wind_fc,
        price_taker_schedules=pt_schedules,
    )
    logger.info(f"PyPSA 网络: {len(engine.network.generators)}个发电机 "
                f"(含{sum(len(v) for v in engine._segment_map.values())}个分段), "
                f"{len(engine.network.storage_units)}个储能, "
                f"{len(engine.network.loads)}个负荷")

    # 6. SCED 出清
    logger.info(f"日前 SCED 出清 (PyPSA → Linopy → {solver_name.upper()})...")
    result = engine.run_sced()

    # 7. 结算
    settlement = SettlementEngine(
        units=units, da_result=result,
        bids={k: v for k, v in bids.items() if isinstance(v, CoalUnitBid)},
    )

    # ============================================================
    #  输出
    # ============================================================
    print()
    print(settlement.summary_report())

    # LMP
    print()
    print("=" * 72)
    print("节点边际电价 LMP (元/MWh) — 每4小时取样")
    print("=" * 72)
    hrs = [f"{h:02d}:00" for h in range(0, 24, 4)]
    st = list(range(0, 96, 16))
    print(f"{'节点':<10}" + "".join(f"{h:<10}" for h in hrs))
    print("-" * 72)
    for bus in sorted(result.lmp):
        p = result.lmp[bus]
        print(f"{bus:<10}" + "".join(f"{p[t]:<10.1f}" for t in st))
    if result.unified_settlement_price is not None:
        usp = result.unified_settlement_price
        print(f"{'统一结算':<10}" + "".join(f"{usp[t]:<10.1f}" for t in st))

    # LMP分析
    lmp_all = np.array([v for k, v in result.lmp.items() if not k.startswith("slack")])
    if len(lmp_all) > 0:
        spread = lmp_all.max(axis=0) - lmp_all.min(axis=0)
        cong = np.sum(spread > 0.1)
        print(f"\n阻塞: {cong}/{T}时段LMP分裂, 最大价差={spread.max():.1f}元/MWh")

    # 机组出力
    print()
    print("=" * 72)
    print("各机组出力 (MW) — 每4小时取样")
    print("=" * 72)
    print(f"{'机组':<12}" + "".join(f"{h:<10}" for h in hrs))
    print("-" * 72)
    for uid, ur in result.unit_results.items():
        print(f"{uid:<12}" + "".join(f"{ur.power[t]:<10.1f}" for t in st))

    for uid, ur in result.unit_results.items():
        if ur.soc is not None:
            print(f"\n{uid} SOC(%) " + "".join(f"{ur.soc[t]*100:<10.1f}" for t in st))

    # 线路潮流
    if engine.network is not None:
        net = engine.network
        print()
        print("=" * 72)
        print("线路潮流 (MW) / 利用率 — 每4小时取样")
        print("=" * 72)
        for lid in net.lines.index:
            if lid in net.lines_t.p0.columns:
                flow = net.lines_t.p0[lid].values
                cap = net.lines.loc[lid, "s_nom"]
                peak = np.max(np.abs(flow)) / cap * 100 if cap > 0 else 0
                tag = "⚠" if peak > 95 else " "
                row = f"{lid:<24}{tag}"
                for t in st:
                    u = abs(flow[t]) / cap * 100 if cap > 0 else 0
                    row += f"{flow[t]:>6.0f}({u:>2.0f}%)"
                print(row)

    # Linopy 模型信息
    print()
    print("=" * 72)
    print("优化模型信息 (Linopy)")
    print("=" * 72)
    if hasattr(engine.network, 'model') and engine.network.model is not None:
        m = engine.network.model
        print(f"  模型框架: Linopy {linopy_version()}")
        print(f"  求解器: {solver_name.upper()}")
        print(f"  变量组数: {len(m.variables)}")
        print(f"  约束组数: {len(m.constraints)}")
        print(f"  变量列表: {', '.join(str(v) for v in m.variables)}")
        print(f"  约束列表: {', '.join(str(c) for c in m.constraints)}")
    print(f"  目标函数值: {result.system_cost:,.0f} 元")
    total_gen = sum(ur.power[ur.power > 0].sum() for ur in result.unit_results.values()) * 0.25
    print(f"  总发电量: {total_gen:,.0f} MWh")

    return result, engine


def linopy_version():
    try:
        import linopy
        return linopy.__version__
    except Exception:
        return "unknown"


def build_market_network_and_run(solver_name: str = "highs") -> MarketResult:
    """用于测试的简化入口"""
    units = create_units()
    bids = create_bids(units)
    base_net = create_ieee6bus()
    load_profiles = {
        "Load_Bus3": generate_load_profile_96(300, seed=10),
        "Load_Bus4": generate_load_profile_96(450, seed=20),
        "Load_Bus5": generate_load_profile_96(350, seed=30),
    }
    wind_fc = {"Wind_B3": generate_wind_profile_96(200, seed=123)}
    chp_hours = np.arange(T) * 0.25
    chp_sched = np.where((chp_hours >= 6) & (chp_hours < 22), 80, 50).astype(float)
    pt_schedules = {"CHP_B1": PriceTakerSchedule(unit_id="CHP_B1", schedule_mw=chp_sched)}

    engine = PyPSAMarketClearing(base_network=base_net, solver_name=solver_name,
                                  num_periods=T, period_minutes=15)
    engine.build_network(units=units, bids=bids, load_profiles=load_profiles,
                         renewable_forecasts=wind_fc, price_taker_schedules=pt_schedules)
    return engine.run_sced()


if __name__ == "__main__":
    import sys
    solver = sys.argv[1] if len(sys.argv) > 1 else "highs"
    run_demo(solver_name=solver)
