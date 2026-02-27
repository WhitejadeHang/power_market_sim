"""
重庆电力现货市场仿真 — 演示场景
构建一个简化的重庆电网场景, 包含:
  - 4台燃煤机组 (不同容量等级)
  - 1个新能源场站 (风电)
  - 1个独立储能
  - 1个热电联产 (价格接受者)
  - 系统负荷曲线 (典型冬季日)
"""
from __future__ import annotations
import logging
import numpy as np
import sys
from .models import (
    UnitMaster, UnitType, ParticipationMode,
    UnitBoundary96, DA_PERIODS, HOURS_PER_DAY,
)
from .agents import BiddingAgent, PriceTakerAgent, LoadAgent
from .runner import MarketRunner

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)


def create_demo_units() -> dict[str, UnitMaster]:
    """创建演示用机组"""
    units = {}

    # 煤机1: 300MW级
    units["coal_1"] = UnitMaster(
        unit_id="coal_1", name="渝北电厂#1", unit_type=UnitType.COAL,
        node="node_A", rated_power=300, deep_peak_power=120,
        min_tech_power=150, max_power=300, min_power=120,
        ramp_rate=5.0, min_up_time_h=8, min_down_time_h=4,
        cold_start_time_h=8, warm_start_time_h=4, hot_start_time_h=2,
        aux_power_rate=6.5,
    )

    # 煤机2: 300MW级
    units["coal_2"] = UnitMaster(
        unit_id="coal_2", name="渝北电厂#2", unit_type=UnitType.COAL,
        node="node_A", rated_power=300, deep_peak_power=120,
        min_tech_power=150, max_power=300, min_power=120,
        ramp_rate=5.0, min_up_time_h=8, min_down_time_h=4,
        cold_start_time_h=8, warm_start_time_h=4, hot_start_time_h=2,
        aux_power_rate=6.5,
    )

    # 煤机3: 600MW级
    units["coal_3"] = UnitMaster(
        unit_id="coal_3", name="江津电厂#1", unit_type=UnitType.COAL,
        node="node_B", rated_power=600, deep_peak_power=240,
        min_tech_power=300, max_power=600, min_power=240,
        ramp_rate=8.0, min_up_time_h=12, min_down_time_h=8,
        cold_start_time_h=12, warm_start_time_h=6, hot_start_time_h=3,
        aux_power_rate=5.8,
    )

    # 煤机4: 600MW级
    units["coal_4"] = UnitMaster(
        unit_id="coal_4", name="合川电厂#1", unit_type=UnitType.COAL,
        node="node_B", rated_power=600, deep_peak_power=240,
        min_tech_power=300, max_power=600, min_power=240,
        ramp_rate=8.0, min_up_time_h=12, min_down_time_h=8,
        cold_start_time_h=12, warm_start_time_h=6, hot_start_time_h=3,
        aux_power_rate=5.8,
    )

    # 新能源: 200MW 风电场
    units["wind_1"] = UnitMaster(
        unit_id="wind_1", name="巫山风电场", unit_type=UnitType.RENEWABLE,
        node="node_C", rated_power=200,
        participation_mode=ParticipationMode.BID_PRICE_QTY,
    )

    # 独立储能: 100MW/200MWh
    units["storage_1"] = UnitMaster(
        unit_id="storage_1", name="渝中储能站", unit_type=UnitType.STORAGE,
        node="node_A",
        rated_power=100, charge_power_mw=100, discharge_power_mw=100,
        storage_capacity_mwh=200, initial_soc=0.5,
        soc_max=0.95, soc_min=0.05,
        charge_efficiency=0.92, discharge_efficiency=0.92,
        participation_mode=ParticipationMode.BID_PRICE_QTY,
    )

    # 热电联产: 150MW (价格接受者)
    units["chp_1"] = UnitMaster(
        unit_id="chp_1", name="重庆热电厂", unit_type=UnitType.CHP,
        node="node_A", rated_power=150,
        participation_mode=ParticipationMode.BID_QTY_ONLY,
    )

    return units


def create_demo_demand() -> np.ndarray:
    """创建典型冬季日负荷曲线 (24点)"""
    demand_24 = np.array([
        900, 850, 800, 780, 800, 850,    # 00-05
        950, 1100, 1250, 1350, 1400, 1380,  # 06-11
        1300, 1250, 1300, 1350, 1400, 1500,  # 12-17
        1550, 1500, 1400, 1300, 1150, 1000,  # 18-23
    ], dtype=float)
    return demand_24


def create_wind_forecast() -> np.ndarray:
    """创建风电出力预测曲线 (96点)"""
    hours = np.arange(DA_PERIODS) * 0.25
    base = 80 + 40 * np.sin(hours / 24 * 2 * np.pi - np.pi/2)
    noise = np.random.default_rng(42).normal(0, 10, DA_PERIODS)
    forecast = np.clip(base + noise, 0, 200)
    return forecast


def create_chp_schedule() -> np.ndarray:
    """创建热电联产自调度曲线 (96点)"""
    schedule = np.full(DA_PERIODS, 100.0)
    for i in range(DA_PERIODS):
        hour = i * 0.25
        if 6 <= hour < 22:
            schedule[i] = 120.0
        else:
            schedule[i] = 80.0
    return schedule


def run_demo():
    """运行完整演示"""
    print("=" * 70)
    print("重庆电力现货市场仿真系统 v1.0")
    print("按照《重庆电力现货交易实施细则V2.0》实现")
    print("=" * 70)
    print()

    # 1. 创建机组
    units = create_demo_units()
    print(f"系统共 {len(units)} 个机组:")
    for uid, u in units.items():
        print(f"  {uid}: {u.name} ({u.unit_type.value}) {u.rated_power}MW @ {u.node}")
    print()

    # 2. 创建Agent
    agents = []

    # 煤机Agent (报量报价)
    for uid in ["coal_1", "coal_2", "coal_3", "coal_4"]:
        agent = BiddingAgent(uid, units[uid], strategy="marginal_cost")
        agent.markup_pct = {"coal_1": 0.0, "coal_2": 0.05, "coal_3": -0.02, "coal_4": 0.03}[uid]
        agents.append(agent)

    # 新能源Agent (报量报价)
    agents.append(BiddingAgent("wind_1", units["wind_1"]))

    # 储能Agent (报量报价)
    agents.append(BiddingAgent("storage_1", units["storage_1"]))

    # 热电联产Agent (价格接受者)
    chp_schedule = create_chp_schedule()
    agents.append(PriceTakerAgent("chp_1", units["chp_1"], base_schedule=chp_schedule))

    # 3. 用电侧Agent
    load_unit = UnitMaster(
        unit_id="load_sys", name="系统负荷", unit_type=UnitType.COAL, node="default"
    )
    load_demand = create_demo_demand()
    load_agents = [LoadAgent("load_sys", load_unit, base_demand=load_demand)]

    # 4. 风电预测
    wind_forecast = {"wind_1": create_wind_forecast()}

    # 5. 运行市场
    runner = MarketRunner(
        units=units,
        agents=agents,
        load_agents=load_agents,
        renewable_forecast=wind_forecast,
        reserve_up=100.0,
        solver_name="glpk",
    )

    report = runner.run_full_day_ahead()
    print()
    print(report)

    # 6. 输出关键结果
    if runner.da_market_result:
        print()
        print("=" * 70)
        print("关键出清结果")
        print("=" * 70)

        result = runner.da_market_result
        print()
        print("各机组出力计划 (每4小时取样, MW):")
        sample_periods = [0, 16, 32, 48, 64, 80]
        hours_label = ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00"]
        header = f"{'机组':<12}" + "".join(f"{h:<10}" for h in hours_label)
        print(header)
        print("-" * 70)

        for uid, ur in result.unit_results.items():
            row = f"{uid:<12}"
            for t in sample_periods:
                if t < len(ur.power):
                    row += f"{ur.power[t]:<10.1f}"
                else:
                    row += f"{'N/A':<10}"
            print(row)

        # 储能SOC
        for uid, ur in result.unit_results.items():
            if ur.soc is not None:
                print(f"\n{uid} SOC变化:")
                row = f"{'SOC(%)':<12}"
                for t in sample_periods:
                    if t < len(ur.soc):
                        row += f"{ur.soc[t]*100:<10.1f}"
                print(row)

        # LMP
        if result.lmp:
            print("\n节点电价 (元/MWh, 取样):")
            for node, prices in result.lmp.items():
                row = f"{node:<12}"
                for t in sample_periods:
                    if t < len(prices):
                        row += f"{prices[t]:<10.1f}"
                print(row)

        if result.unified_settlement_price is not None:
            print(f"\n统一结算点电价均值: {result.unified_settlement_price.mean():.2f} 元/MWh")

    return runner


if __name__ == "__main__":
    run_demo()
