"""
重庆电力现货市场仿真系统 — 自动化测试
覆盖: 数据模型、报价校验、PyPSA+Linopy出清(HiGHS/SCIP)、LMP、结算、Agent
"""
import numpy as np
import pandas as pd
import pypsa
from simpower.market.models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, MarketResult, UnitResult, DA_PERIODS,
)
from simpower.market.bid_validator import BidValidator
from simpower.market.agents import BiddingAgent, PriceTakerAgent
from simpower.market.ieee_network import (
    create_ieee6bus, generate_load_profile_96, generate_wind_profile_96,
)
from simpower.market.pypsa_clearing import (
    PyPSAMarketClearing, decompose_bid_to_segments,
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
#  数据模型
# ============================================================
class TestModels:
    def test_bid_curve_segments(self):
        curve = BidCurve(points=[BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400)])
        assert len(curve.get_segments()) == 2

    def test_bid_curve_marginal_cost(self):
        curve = BidCurve(points=[BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400)])
        assert curve.marginal_cost_at(150) == 300

    def test_unit_capacity_class(self):
        assert make_coal_unit(rated=300).capacity_class == 300
        assert make_coal_unit(rated=600, deep=240).capacity_class == 600

    def test_market_result_hourly_price(self):
        r = MarketResult(num_periods=96, period_hours=0.25)
        r.lmp["Bus1"] = np.full(96, 300.0)
        np.testing.assert_allclose(r.hourly_node_price("Bus1", 4), 300.0)


# ============================================================
#  报价校验
# ============================================================
class TestBidValidator:
    def test_valid_coal_bid(self):
        assert BidValidator.validate_coal_bid(make_coal_bid(), make_coal_unit()).valid

    def test_wrong_first_point(self):
        bid = make_coal_bid()
        bid.energy_curve.points[0].power_mw = 50
        assert not BidValidator.validate_coal_bid(bid, make_coal_unit()).valid

    def test_price_exceeds_limit(self):
        bid = make_coal_bid()
        bid.energy_curve.points[-1].price_yuan_mwh = 2000
        assert not BidValidator.validate_coal_bid(bid, make_coal_unit()).valid

    def test_non_monotonic(self):
        bid = make_coal_bid()
        bid.energy_curve.points[1].price_yuan_mwh = 100
        assert not BidValidator.validate_coal_bid(bid, make_coal_unit()).valid

    def test_startup_order(self):
        bid = make_coal_bid()
        bid.startup_cost_hot = 50
        assert not BidValidator.validate_coal_bid(bid, make_coal_unit()).valid

    def test_storage_bid(self):
        unit = UnitMaster(unit_id="es", name="ES", unit_type=UnitType.STORAGE,
                         node="Bus6", charge_power_mw=50, discharge_power_mw=50,
                         storage_capacity_mwh=100)
        bid = StorageBid(unit_id="es", energy_curve=BidCurve(points=[
            BidPoint(-50, 100), BidPoint(0, 300), BidPoint(50, 500)]),
            end_of_day_soc=0.5)
        assert BidValidator.validate_storage_bid(bid, unit).valid

    def test_renewable_bid(self):
        unit = UnitMaster(unit_id="re", name="RE", unit_type=UnitType.RENEWABLE,
                         node="Bus3", rated_power=100)
        bid = RenewableBid(unit_id="re", energy_curve=BidCurve(points=[
            BidPoint(0, 0), BidPoint(100, 50)]))
        assert BidValidator.validate_renewable_bid(bid, unit).valid

    def test_too_few_points(self):
        bid = CoalUnitBid(unit_id="c", energy_curve=BidCurve(points=[BidPoint(120, 200)]))
        assert not BidValidator.validate_coal_bid(bid, make_coal_unit()).valid


# ============================================================
#  报价分段分解
# ============================================================
class TestBidDecomposition:
    def test_coal_3point_decomposition(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        segs = decompose_bid_to_segments("coal_1", bid, unit)
        assert len(segs) == 3  # seg0(base) + seg1 + seg2
        assert segs[0]["p_nom"] == 120  # deep peak
        total_nom = sum(s["p_nom"] for s in segs)
        assert abs(total_nom - 300) < 1  # total = rated

    def test_coal_4point_decomposition(self):
        unit = make_coal_unit()
        bid = CoalUnitBid(unit_id="c", energy_curve=BidCurve(points=[
            BidPoint(120, 200), BidPoint(180, 260),
            BidPoint(240, 300), BidPoint(300, 340)]))
        segs = decompose_bid_to_segments("c", bid, unit)
        assert len(segs) == 4
        assert segs[0]["marginal_cost"] == 200
        assert segs[3]["marginal_cost"] == 340

    def test_segment_monotonic_cost(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        segs = decompose_bid_to_segments("c", bid, unit)
        costs = [s["marginal_cost"] for s in segs]
        assert costs == sorted(costs)


# ============================================================
#  IEEE 网络
# ============================================================
class TestIEEENetwork:
    def test_6bus_topology(self):
        n = create_ieee6bus()
        assert len(n.buses) == 6
        assert len(n.lines) == 11

    def test_load_profile(self):
        p = generate_load_profile_96(300, seed=42)
        assert len(p) == 96
        assert p.min() > 0

    def test_wind_profile(self):
        w = generate_wind_profile_96(200, seed=42)
        assert len(w) == 96
        assert 0 <= w.min() and w.max() <= 200


# ============================================================
#  PyPSA + Linopy 出清 (HiGHS)
# ============================================================
class TestPyPSALinopyClearing:
    def test_two_bus_lmp_no_congestion(self):
        """双节点无阻塞: LMP一致"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A"); n.add("Bus", "B")
        n.add("Line", "AB", bus0="A", bus1="B", s_nom=500, x=0.1, r=0.01)
        n.add("Generator", "g1", bus="A", p_nom=300, marginal_cost=250)
        n.add("Generator", "g2", bus="B", p_nom=300, marginal_cost=350)
        n.add("Load", "l1", bus="B", p_set=200)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        lmp_a = n.buses_t.marginal_price["A"].values
        lmp_b = n.buses_t.marginal_price["B"].values
        np.testing.assert_allclose(lmp_a, lmp_b, atol=0.1)

    def test_two_bus_lmp_with_congestion(self):
        """双节点线路阻塞 → LMP分裂"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A"); n.add("Bus", "B")
        n.add("Line", "AB", bus0="A", bus1="B", s_nom=100, x=0.1, r=0.01)
        n.add("Generator", "g1", bus="A", p_nom=300, marginal_cost=200)
        n.add("Generator", "g2", bus="B", p_nom=300, marginal_cost=400)
        n.add("Load", "l1", bus="B", p_set=200)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        assert n.buses_t.marginal_price["B"].iloc[0] > n.buses_t.marginal_price["A"].iloc[0] + 0.1

    def test_segment_generators_merit_order(self):
        """分段报价: 低价段优先出清"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A")
        n.add("Generator", "seg0", bus="A", p_nom=100, marginal_cost=200)
        n.add("Generator", "seg1", bus="A", p_nom=100, marginal_cost=300)
        n.add("Generator", "seg2", bus="A", p_nom=100, marginal_cost=400)
        n.add("Load", "l1", bus="A", p_set=180)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        assert n.generators_t.p["seg0"].iloc[0] == 100  # 满发
        assert abs(n.generators_t.p["seg1"].iloc[0] - 80) < 1
        assert n.generators_t.p["seg2"].iloc[0] < 1

    def test_6bus_96period_clearing(self):
        """IEEE 6-bus 96时段完整出清"""
        n = create_ieee6bus()
        snap = pd.date_range("2025-01-15", periods=96, freq="15min")
        n.set_snapshots(snap)
        n.add("Generator", "G1", bus="Bus1", p_nom=400, marginal_cost=260)
        n.add("Generator", "G2", bus="Bus2", p_nom=400, marginal_cost=310)
        wind = generate_wind_profile_96(200, seed=42)
        n.add("Generator", "W1", bus="Bus3", p_nom=200, marginal_cost=0, p_max_pu=wind/200)
        n.add("Load", "L4", bus="Bus4", p_set=generate_load_profile_96(300, seed=10))
        n.add("Load", "L5", bus="Bus5", p_set=generate_load_profile_96(200, seed=20))
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        assert n.generators_t.p.shape[0] == 96

    def test_scip_solver(self):
        """SCIP 求解器可用"""
        n = pypsa.Network()
        n.set_snapshots(range(2))
        n.add("Bus", "A")
        n.add("Generator", "g1", bus="A", p_nom=200, marginal_cost=100)
        n.add("Load", "l1", bus="A", p_set=100)
        status, _ = n.optimize(solver_name="scip", include_objective_constant=False)
        assert status == "ok"

    def test_storage_arbitrage(self):
        """储能价差套利"""
        n = pypsa.Network()
        snap = pd.date_range("2025-01-15", periods=8, freq="15min")
        n.set_snapshots(snap)
        n.add("Bus", "B1")
        n.add("Generator", "cheap", bus="B1", p_nom=200, marginal_cost=100)
        n.add("Generator", "expensive", bus="B1", p_nom=300, marginal_cost=500)
        n.add("Load", "L1", bus="B1", p_set=[150, 150, 150, 150, 350, 350, 350, 350])
        n.add("StorageUnit", "ES", bus="B1", p_nom=100, max_hours=2,
              efficiency_store=0.9, efficiency_dispatch=0.9,
              marginal_cost=1, cyclic_state_of_charge=True)
        status, _ = n.optimize(solver_name="highs", include_objective_constant=False)
        assert status == "ok"
        p = n.storage_units_t.p["ES"].values
        assert np.any(p < -1), "低价充电"
        assert np.any(p > 1), "高价放电"

    def test_extra_functionality_linopy(self):
        """通过 extra_functionality 向 Linopy 模型注入自定义约束"""
        n = pypsa.Network()
        n.set_snapshots(range(4))
        n.add("Bus", "A")
        n.add("Generator", "g1", bus="A", p_nom=200, marginal_cost=100)
        n.add("Generator", "g2", bus="A", p_nom=200, marginal_cost=200)
        n.add("Load", "l1", bus="A", p_set=150)

        def limit_g1(n, snapshots):
            m = n.model
            g1_p = m.variables['Generator-p'].sel(name='g1')
            m.add_constraints(g1_p <= 100, name='g1_limit')

        status, _ = n.optimize(solver_name="highs",
                               extra_functionality=limit_g1,
                               include_objective_constant=False)
        assert status == "ok"
        assert n.generators_t.p["g1"].max() <= 100.1


# ============================================================
#  PyPSAMarketClearing 引擎集成测试
# ============================================================
class TestMarketClearingEngine:
    def test_full_clearing_pipeline(self):
        """完整出清引擎: build_network → run_sced → extract_results"""
        base = create_ieee6bus()
        units = {
            "G1": make_coal_unit("G1", rated=400, deep=160),
            "G2": make_coal_unit("G2", rated=400, deep=160),
        }
        units["G1"].node = "Bus1"
        units["G2"].node = "Bus2"
        bids = {
            "G1": CoalUnitBid(unit_id="G1", energy_curve=BidCurve(points=[
                BidPoint(160, 200), BidPoint(400, 350)])),
            "G2": CoalUnitBid(unit_id="G2", energy_curve=BidCurve(points=[
                BidPoint(160, 250), BidPoint(400, 400)])),
        }
        loads = {
            "Load_Bus4": generate_load_profile_96(200, seed=10),
            "Load_Bus5": generate_load_profile_96(150, seed=20),
        }
        engine = PyPSAMarketClearing(base_network=base, solver_name="highs", num_periods=96)
        engine.build_network(units=units, bids=bids, load_profiles=loads)
        result = engine.run_sced()
        assert "G1" in result.unit_results
        assert "G2" in result.unit_results
        assert result.system_cost > 0
        assert len(result.lmp) > 0


# ============================================================
#  结算
# ============================================================
class TestSettlement:
    def test_hourly_prices(self):
        units = {"g1": make_coal_unit()}
        r = MarketResult(num_periods=96, period_hours=0.25)
        r.lmp["Bus1"] = np.full(96, 300.0)
        r.unit_results["g1"] = UnitResult("g1", np.ones(96), np.full(96, 200.0))
        r.compute_unified_settlement_price(units)
        engine = SettlementEngine(units=units, da_result=r)
        np.testing.assert_allclose(engine.compute_hourly_da_prices()["Bus1"], 300.0)

    def test_report_content(self):
        units = {"g1": make_coal_unit()}
        r = MarketResult(num_periods=96, period_hours=0.25)
        r.lmp["Bus1"] = np.full(96, 300.0)
        r.unit_results["g1"] = UnitResult("g1", np.ones(96), np.full(96, 200.0))
        r.compute_unified_settlement_price(units)
        report = SettlementEngine(units=units, da_result=r, bids={"g1": make_coal_bid()}).summary_report()
        assert "结算汇总" in report


# ============================================================
#  Agent
# ============================================================
class TestAgents:
    def test_coal_agent(self):
        assert isinstance(BiddingAgent("a", make_coal_unit()).generate_bid(), CoalUnitBid)

    def test_storage_agent(self):
        u = UnitMaster(unit_id="es", name="ES", unit_type=UnitType.STORAGE,
                      node="Bus6", charge_power_mw=50, discharge_power_mw=50,
                      storage_capacity_mwh=100)
        assert isinstance(BiddingAgent("a", u).generate_bid(), StorageBid)

    def test_price_taker(self):
        u = UnitMaster(unit_id="chp", name="CHP", unit_type=UnitType.CHP,
                      node="Bus1", rated_power=100)
        assert isinstance(PriceTakerAgent("a", u).generate_bid(), PriceTakerSchedule)


# ============================================================
#  集成: 完整 demo 可运行
# ============================================================
class TestIntegration:
    def test_demo_runs_highs(self):
        from simpower.market.demo import create_units, create_bids, build_market_network_and_run
        result = build_market_network_and_run("highs")
        assert result is not None
        assert result.system_cost > 0
        assert len(result.lmp) == 6
