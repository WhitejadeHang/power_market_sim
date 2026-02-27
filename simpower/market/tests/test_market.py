"""
重庆电力现货市场仿真系统 — 自动化测试
覆盖: 数据模型、报价校验、PyPSA出清(含网络约束)、LMP、结算、Agent
"""
import numpy as np
import pandas as pd
import pypsa
from simpower.market.models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, MarketResult, UnitResult,
    DA_PERIODS,
)
from simpower.market.bid_validator import BidValidator
from simpower.market.agents import BiddingAgent, PriceTakerAgent, LoadAgent
from simpower.market.ieee_network import (
    create_ieee6bus, generate_load_profile_96, generate_wind_profile_96,
)
from simpower.market.settlement import SettlementEngine


def make_coal_unit(uid="coal_1", rated=300, deep=120):
    return UnitMaster(
        unit_id=uid, name=f"Test {uid}", unit_type=UnitType.COAL,
        node="Bus1", rated_power=rated, deep_peak_power=deep,
        min_tech_power=rated * 0.5, max_power=rated, min_power=deep,
        ramp_rate=5.0, min_up_time_h=6, min_down_time_h=4, aux_power_rate=6.0,
    )


def make_coal_bid(uid="coal_1", deep=120, rated=300):
    return CoalUnitBid(
        unit_id=uid,
        startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=15,
        noload_cost=0.5,
        energy_curve=BidCurve(points=[
            BidPoint(deep, 200), BidPoint(int((deep + rated) / 2), 280),
            BidPoint(rated, 350),
        ]),
    )


# ============================================================
#  数据模型测试
# ============================================================

class TestModels:
    def test_bid_curve_segments(self):
        curve = BidCurve(points=[
            BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400),
        ])
        segs = curve.get_segments()
        assert len(segs) == 2
        assert segs[0] == (100, 200, 300)

    def test_bid_curve_marginal_cost(self):
        curve = BidCurve(points=[
            BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400),
        ])
        assert curve.marginal_cost_at(50) == 200
        assert curve.marginal_cost_at(150) == 300
        assert curve.marginal_cost_at(250) == 400

    def test_unit_capacity_class(self):
        u300 = make_coal_unit(rated=300)
        u600 = make_coal_unit(rated=600, deep=240)
        u1000 = make_coal_unit(rated=1000, deep=400)
        assert u300.capacity_class == 300
        assert u600.capacity_class == 600
        assert u1000.capacity_class == 1000

    def test_market_result_hourly_price(self):
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["Bus1"] = np.full(96, 300.0)
        hp = result.hourly_node_price("Bus1", 4)
        assert len(hp) == 24
        np.testing.assert_allclose(hp, 300.0)


# ============================================================
#  报价校验测试
# ============================================================

class TestBidValidator:
    def test_valid_coal_bid(self):
        result = BidValidator.validate_coal_bid(make_coal_bid(), make_coal_unit())
        assert result.valid, str(result)

    def test_wrong_first_point(self):
        bid = make_coal_bid()
        bid.energy_curve.points[0].power_mw = 50
        result = BidValidator.validate_coal_bid(bid, make_coal_unit())
        assert not result.valid

    def test_price_exceeds_limit(self):
        bid = make_coal_bid()
        bid.energy_curve.points[-1].price_yuan_mwh = 2000
        result = BidValidator.validate_coal_bid(bid, make_coal_unit())
        assert not result.valid

    def test_non_monotonic_price(self):
        bid = make_coal_bid()
        bid.energy_curve.points[1].price_yuan_mwh = 100
        result = BidValidator.validate_coal_bid(bid, make_coal_unit())
        assert not result.valid

    def test_startup_cost_order(self):
        bid = make_coal_bid()
        bid.startup_cost_hot = 50
        result = BidValidator.validate_coal_bid(bid, make_coal_unit())
        assert not result.valid

    def test_valid_storage_bid(self):
        unit = UnitMaster(
            unit_id="es", name="ES", unit_type=UnitType.STORAGE,
            node="Bus6", charge_power_mw=50, discharge_power_mw=50,
            storage_capacity_mwh=100,
        )
        bid = StorageBid(
            unit_id="es",
            energy_curve=BidCurve(points=[
                BidPoint(-50, 100), BidPoint(0, 300), BidPoint(50, 500),
            ]),
            end_of_day_soc=0.5,
        )
        result = BidValidator.validate_storage_bid(bid, unit)
        assert result.valid, str(result)

    def test_valid_renewable_bid(self):
        unit = UnitMaster(unit_id="re", name="RE", unit_type=UnitType.RENEWABLE,
                         node="Bus3", rated_power=100)
        bid = RenewableBid(
            unit_id="re",
            energy_curve=BidCurve(points=[BidPoint(0, 0), BidPoint(100, 50)]),
        )
        result = BidValidator.validate_renewable_bid(bid, unit)
        assert result.valid, str(result)

    def test_too_few_points(self):
        bid = CoalUnitBid(
            unit_id="c", energy_curve=BidCurve(points=[BidPoint(120, 200)]),
        )
        result = BidValidator.validate_coal_bid(bid, make_coal_unit())
        assert not result.valid


# ============================================================
#  IEEE 网络测试
# ============================================================

class TestIEEENetwork:
    def test_ieee6bus_topology(self):
        n = create_ieee6bus()
        assert len(n.buses) == 6
        assert len(n.lines) == 11

    def test_load_profile_96(self):
        profile = generate_load_profile_96(300, seed=42)
        assert len(profile) == 96
        assert profile.min() > 0
        assert profile.max() <= 360

    def test_wind_profile_96(self):
        wf = generate_wind_profile_96(200, seed=42)
        assert len(wf) == 96
        assert wf.min() >= 0
        assert wf.max() <= 200


# ============================================================
#  PyPSA 出清 + LMP 测试
# ============================================================

class TestPyPSAClearing:
    def test_two_bus_lmp_no_congestion(self):
        """双节点无阻塞: LMP应相同"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A")
        n.add("Bus", "B")
        n.add("Line", "AB", bus0="A", bus1="B", s_nom=500, x=0.1, r=0.01)
        n.add("Generator", "g1", bus="A", p_nom=300, marginal_cost=250)
        n.add("Generator", "g2", bus="B", p_nom=300, marginal_cost=350)
        n.add("Load", "l1", bus="B", p_set=200)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        lmp_a = n.buses_t.marginal_price["A"].values
        lmp_b = n.buses_t.marginal_price["B"].values
        np.testing.assert_allclose(lmp_a, lmp_b, atol=0.1)
        np.testing.assert_allclose(lmp_a, 250, atol=0.1)

    def test_two_bus_lmp_with_congestion(self):
        """双节点有阻塞: LMP应分裂"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A")
        n.add("Bus", "B")
        n.add("Line", "AB", bus0="A", bus1="B", s_nom=100, x=0.1, r=0.01)
        n.add("Generator", "g1", bus="A", p_nom=300, marginal_cost=200)
        n.add("Generator", "g2", bus="B", p_nom=300, marginal_cost=400)
        n.add("Load", "l1", bus="B", p_set=200)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        lmp_a = n.buses_t.marginal_price["A"].values
        lmp_b = n.buses_t.marginal_price["B"].values
        assert lmp_b[0] > lmp_a[0] + 0.1, f"Expected LMP split, got A={lmp_a[0]}, B={lmp_b[0]}"

    def test_6bus_96period_feasible(self):
        """IEEE 6-bus 96时段完整出清可行性"""
        n = create_ieee6bus()
        snap = pd.date_range("2025-01-15", periods=96, freq="15min")
        n.set_snapshots(snap)
        n.add("Generator", "G1", bus="Bus1", p_nom=400, marginal_cost=260)
        n.add("Generator", "G2", bus="Bus2", p_nom=400, marginal_cost=310)
        wind = generate_wind_profile_96(200, seed=42)
        n.add("Generator", "W1", bus="Bus3", p_nom=200, marginal_cost=0,
              p_max_pu=wind / 200)
        n.add("Load", "L4", bus="Bus4", p_set=generate_load_profile_96(300, seed=10))
        n.add("Load", "L5", bus="Bus5", p_set=generate_load_profile_96(200, seed=20))
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        assert n.generators_t.p["G1"].sum() > 0

    def test_storage_charge_discharge(self):
        """储能充放电测试: 低价时充电, 高价时放电"""
        n = pypsa.Network()
        snap = pd.date_range("2025-01-15", periods=8, freq="15min")
        n.set_snapshots(snap)
        n.add("Bus", "B1")
        # 两个不同边际成本的机组 → 负荷变化时产生价差
        n.add("Generator", "G_cheap", bus="B1", p_nom=200, marginal_cost=100)
        n.add("Generator", "G_expensive", bus="B1", p_nom=300, marginal_cost=500)
        demand = [150, 150, 150, 150, 350, 350, 350, 350]
        n.add("Load", "L1", bus="B1", p_set=demand)
        n.add("StorageUnit", "ES", bus="B1", p_nom=100, max_hours=2,
              efficiency_store=0.9, efficiency_dispatch=0.9,
              marginal_cost=1, cyclic_state_of_charge=True)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        p = n.storage_units_t.p["ES"].values
        assert np.any(p < -1), "储能应在低价(低负荷)时充电"
        assert np.any(p > 1), "储能应在高价(高负荷)时放电"


# ============================================================
#  结算测试
# ============================================================

class TestSettlement:
    def test_hourly_da_prices(self):
        units = {"g1": make_coal_unit()}
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["Bus1"] = np.full(96, 300.0)
        result.unit_results["g1"] = UnitResult("g1", np.ones(96), np.full(96, 200.0))
        result.compute_unified_settlement_price(units)
        engine = SettlementEngine(units=units, da_result=result)
        hp = engine.compute_hourly_da_prices()
        assert "Bus1" in hp
        np.testing.assert_allclose(hp["Bus1"], 300.0)

    def test_settlement_report_content(self):
        units = {"g1": make_coal_unit()}
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["Bus1"] = np.full(96, 300.0)
        result.unit_results["g1"] = UnitResult("g1", np.ones(96), np.full(96, 200.0))
        result.compute_unified_settlement_price(units)
        engine = SettlementEngine(units=units, da_result=result, bids={"g1": make_coal_bid()})
        report = engine.summary_report()
        assert "结算汇总报告" in report
        assert "g1" in report


# ============================================================
#  Agent 测试
# ============================================================

class TestAgents:
    def test_coal_agent(self):
        agent = BiddingAgent("a1", make_coal_unit(), strategy="marginal_cost")
        bid = agent.generate_bid()
        assert isinstance(bid, CoalUnitBid)
        assert len(bid.energy_curve.points) >= 2

    def test_storage_agent(self):
        unit = UnitMaster(unit_id="es", name="ES", unit_type=UnitType.STORAGE,
                         node="Bus6", charge_power_mw=50, discharge_power_mw=50,
                         storage_capacity_mwh=100)
        agent = BiddingAgent("a2", unit)
        bid = agent.generate_bid()
        assert isinstance(bid, StorageBid)

    def test_renewable_agent(self):
        unit = UnitMaster(unit_id="re", name="RE", unit_type=UnitType.RENEWABLE,
                         node="Bus3", rated_power=100)
        agent = BiddingAgent("a3", unit)
        bid = agent.generate_bid()
        assert isinstance(bid, RenewableBid)

    def test_price_taker_agent(self):
        unit = UnitMaster(unit_id="chp", name="CHP", unit_type=UnitType.CHP,
                         node="Bus1", rated_power=100)
        agent = PriceTakerAgent("pt1", unit)
        sched = agent.generate_bid()
        assert isinstance(sched, PriceTakerSchedule)
        assert len(sched.schedule_mw) == DA_PERIODS


# ============================================================
#  集成测试
# ============================================================

class TestIntegration:
    def test_full_demo_runs(self):
        """完整demo可运行"""
        from simpower.market.demo import build_market_network
        n, units, bids = build_market_network()
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        assert n.generators_t.p.shape[0] == 96
        assert len(n.buses_t.marginal_price.columns) == 6
        lmp = n.buses_t.marginal_price
        assert lmp.max().max() > 0, "LMP应为正值"
