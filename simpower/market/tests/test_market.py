"""
重庆电力现货市场仿真系统 — 自动化测试
覆盖: 数据模型、报价校验、SCUC/SCED出清、结算、Agent框架
"""
import pytest
import numpy as np
from simpower.market.models import (
    UnitMaster, UnitType, ParticipationMode,
    BidCurve, BidPoint, CoalUnitBid, StorageBid, RenewableBid,
    PriceTakerSchedule, LoadBid, UnitBoundary96,
    MarketResult, UnitResult,
    DA_PERIODS, DA_PERIOD_HOURS, HOURS_PER_DAY,
    PRICE_BID_UPPER, PRICE_BID_LOWER,
)
from simpower.market.bid_validator import BidValidator
from simpower.market.clearing import SCUCSolver
from simpower.market.settlement import SettlementEngine
from simpower.market.agents import BiddingAgent, PriceTakerAgent, LoadAgent
from simpower.market.runner import MarketRunner


# ============================================================
#  Fixtures
# ============================================================

def make_coal_unit(uid="coal_1", rated=300, deep=120):
    return UnitMaster(
        unit_id=uid, name=f"Test Coal {uid}", unit_type=UnitType.COAL,
        node="node_A", rated_power=rated, deep_peak_power=deep,
        min_tech_power=rated*0.5, max_power=rated, min_power=deep,
        ramp_rate=5.0, min_up_time_h=6, min_down_time_h=4,
        aux_power_rate=6.0,
    )


def make_storage_unit(uid="es_1", charge=50, discharge=50, capacity=100):
    return UnitMaster(
        unit_id=uid, name=f"Test Storage {uid}", unit_type=UnitType.STORAGE,
        node="node_A", charge_power_mw=charge, discharge_power_mw=discharge,
        storage_capacity_mwh=capacity, initial_soc=0.5,
        soc_max=0.95, soc_min=0.05,
        participation_mode=ParticipationMode.BID_PRICE_QTY,
    )


def make_re_unit(uid="re_1", rated=100):
    return UnitMaster(
        unit_id=uid, name=f"Test RE {uid}", unit_type=UnitType.RENEWABLE,
        node="node_B", rated_power=rated,
        participation_mode=ParticipationMode.BID_PRICE_QTY,
    )


def make_coal_bid(uid="coal_1", deep=120, rated=300):
    curve = BidCurve(points=[
        BidPoint(power_mw=deep, price_yuan_mwh=200),
        BidPoint(power_mw=int((deep+rated)/2), price_yuan_mwh=280),
        BidPoint(power_mw=rated, price_yuan_mwh=350),
    ])
    return CoalUnitBid(
        unit_id=uid,
        startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=15,
        noload_cost=0.5,
        energy_curve=curve,
    )


# ============================================================
#  Test: Data Models
# ============================================================

class TestModels:
    def test_bid_curve_segments(self):
        curve = BidCurve(points=[
            BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400),
        ])
        segs = curve.get_segments()
        assert len(segs) == 2
        assert segs[0] == (100, 200, 300)
        assert segs[1] == (200, 300, 400)

    def test_bid_curve_marginal_cost(self):
        curve = BidCurve(points=[
            BidPoint(100, 200), BidPoint(200, 300), BidPoint(300, 400),
        ])
        assert curve.marginal_cost_at(50) == 200
        assert curve.marginal_cost_at(150) == 300
        assert curve.marginal_cost_at(250) == 400
        assert curve.marginal_cost_at(350) == 400

    def test_unit_master_defaults(self):
        u = make_coal_unit()
        assert u.max_power == 300
        assert u.min_power == 120
        assert u.min_tech_power == 150
        assert u.capacity_class == 300

    def test_unit_master_600mw(self):
        u = make_coal_unit(rated=600, deep=240)
        assert u.capacity_class == 600

    def test_market_result_hourly(self):
        prices = np.arange(96, dtype=float)
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["node_A"] = prices
        hourly = result.hourly_node_price("node_A", 4)
        assert len(hourly) == 24
        assert hourly[0] == np.mean([0, 1, 2, 3])


# ============================================================
#  Test: Bid Validator
# ============================================================

class TestBidValidator:
    def test_valid_coal_bid(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        result = BidValidator.validate_coal_bid(bid, unit)
        assert result.valid, str(result)

    def test_coal_bid_wrong_first_point(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        bid.energy_curve.points[0].power_mw = 50  # wrong
        result = BidValidator.validate_coal_bid(bid, unit)
        assert not result.valid
        assert any("第一个报价点" in e.message for e in result.errors)

    def test_coal_bid_price_exceeds_limit(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        bid.energy_curve.points[-1].price_yuan_mwh = 2000
        result = BidValidator.validate_coal_bid(bid, unit)
        assert not result.valid
        assert any("超出限价" in e.message for e in result.errors)

    def test_coal_bid_non_monotonic(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        bid.energy_curve.points[1].price_yuan_mwh = 100  # lower than first
        result = BidValidator.validate_coal_bid(bid, unit)
        assert not result.valid

    def test_coal_bid_startup_order(self):
        unit = make_coal_unit()
        bid = make_coal_bid()
        bid.startup_cost_hot = 50  # higher than cold=30
        result = BidValidator.validate_coal_bid(bid, unit)
        assert not result.valid
        assert any("冷态 >= 温态 >= 热态" in e.message for e in result.errors)

    def test_valid_storage_bid(self):
        unit = make_storage_unit()
        bid = StorageBid(
            unit_id="es_1",
            energy_curve=BidCurve(points=[
                BidPoint(-50, 100), BidPoint(0, 300), BidPoint(50, 500),
            ]),
            end_of_day_soc=0.5,
        )
        result = BidValidator.validate_storage_bid(bid, unit)
        assert result.valid, str(result)

    def test_storage_bid_soc_invalid(self):
        unit = make_storage_unit()
        bid = StorageBid(
            unit_id="es_1",
            energy_curve=BidCurve(points=[
                BidPoint(-50, 100), BidPoint(50, 500),
            ]),
            end_of_day_soc=1.5,
        )
        result = BidValidator.validate_storage_bid(bid, unit)
        assert not result.valid

    def test_valid_renewable_bid(self):
        unit = make_re_unit()
        bid = RenewableBid(
            unit_id="re_1",
            energy_curve=BidCurve(points=[
                BidPoint(0, 0), BidPoint(100, 50),
            ]),
        )
        result = BidValidator.validate_renewable_bid(bid, unit)
        assert result.valid, str(result)

    def test_too_few_points(self):
        unit = make_coal_unit()
        bid = CoalUnitBid(
            unit_id="coal_1",
            energy_curve=BidCurve(points=[BidPoint(120, 200)]),
        )
        result = BidValidator.validate_coal_bid(bid, unit)
        assert not result.valid
        assert any("2-10" in e.message for e in result.errors)


# ============================================================
#  Test: SCUC Solver
# ============================================================

class TestSCUC:
    def test_single_unit_dispatch(self):
        """单机单时段出清测试: 需求在机组出力范围内"""
        unit = make_coal_unit("g1", rated=300, deep=120)
        bid = make_coal_bid("g1", deep=120, rated=300)
        demand = np.full(4, 200.0)

        solver = SCUCSolver(
            units={"g1": unit},
            bids={"g1": bid},
            boundaries={},
            system_demand=demand,
            solver_name="glpk",
            num_periods=4,
            period_hours=0.25,
        )
        result = solver.solve()
        assert "g1" in result.unit_results
        ur = result.unit_results["g1"]
        # 单机必须满足需求 (可能使用平衡松弛)
        total_gen = ur.power.sum()
        total_demand = demand.sum()
        slack = result.slack_balance
        total_served = total_gen + (slack.sum() if slack is not None else 0)
        assert abs(total_served - total_demand) < 1.0

    def test_two_unit_merit_order(self):
        """两机经济排序测试: 便宜机组优先"""
        cheap = make_coal_unit("cheap", rated=300, deep=120)
        expensive = make_coal_unit("expensive", rated=300, deep=120)

        cheap_bid = CoalUnitBid(
            unit_id="cheap",
            startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=15,
            noload_cost=0.5,
            energy_curve=BidCurve(points=[
                BidPoint(120, 100), BidPoint(300, 200),
            ]),
        )
        exp_bid = CoalUnitBid(
            unit_id="expensive",
            startup_cost_cold=30, startup_cost_warm=20, startup_cost_hot=15,
            noload_cost=0.5,
            energy_curve=BidCurve(points=[
                BidPoint(120, 400), BidPoint(300, 600),
            ]),
        )
        demand = np.full(4, 350.0)

        solver = SCUCSolver(
            units={"cheap": cheap, "expensive": expensive},
            bids={"cheap": cheap_bid, "expensive": exp_bid},
            boundaries={},
            system_demand=demand,
            solver_name="glpk",
            num_periods=4,
            period_hours=0.25,
        )
        result = solver.solve()
        cheap_power = result.unit_results["cheap"].power
        exp_power = result.unit_results["expensive"].power
        for t in range(4):
            assert cheap_power[t] >= exp_power[t] - 1.0

    def test_storage_charge_discharge(self):
        """储能充放电测试"""
        coal = make_coal_unit("g1", rated=500, deep=200)
        es = make_storage_unit("es1", charge=50, discharge=50, capacity=100)

        coal_bid = make_coal_bid("g1", deep=200, rated=500)
        es_bid = StorageBid(
            unit_id="es1",
            energy_curve=BidCurve(points=[
                BidPoint(-50, 100), BidPoint(0, 250), BidPoint(50, 400),
            ]),
        )
        demand = np.array([200, 200, 300, 300])

        solver = SCUCSolver(
            units={"g1": coal, "es1": es},
            bids={"g1": coal_bid, "es1": es_bid},
            boundaries={},
            system_demand=demand,
            solver_name="glpk",
            num_periods=4,
            period_hours=0.25,
        )
        result = solver.solve()
        assert "es1" in result.unit_results
        es_result = result.unit_results["es1"]
        assert es_result.soc is not None


# ============================================================
#  Test: Settlement
# ============================================================

class TestSettlement:
    def test_hourly_prices(self):
        """小时电价计算测试"""
        units = {"g1": make_coal_unit()}
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["node_A"] = np.full(96, 300.0)
        result.unit_results["g1"] = UnitResult(
            unit_id="g1",
            commitment=np.ones(96),
            power=np.full(96, 200.0),
        )
        result.compute_unified_settlement_price(units)

        engine = SettlementEngine(units=units, da_result=result)
        hourly = engine.compute_hourly_da_prices()
        assert "node_A" in hourly
        assert len(hourly["node_A"]) == 24
        np.testing.assert_allclose(hourly["node_A"], 300.0)

    def test_unified_settlement_price(self):
        """统一结算点电价测试"""
        units = {"g1": make_coal_unit()}
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["node_A"] = np.full(96, 300.0)
        result.unit_results["g1"] = UnitResult(
            unit_id="g1",
            commitment=np.ones(96),
            power=np.full(96, 200.0),
        )
        usp = result.compute_unified_settlement_price(units)
        np.testing.assert_allclose(usp, 300.0, atol=0.01)

    def test_settlement_report(self):
        """结算报告生成测试"""
        units = {"g1": make_coal_unit()}
        bid = make_coal_bid()
        result = MarketResult(num_periods=96, period_hours=0.25)
        result.lmp["node_A"] = np.full(96, 300.0)
        result.unit_results["g1"] = UnitResult(
            unit_id="g1",
            commitment=np.ones(96),
            power=np.full(96, 200.0),
        )
        result.compute_unified_settlement_price(units)

        engine = SettlementEngine(
            units=units, da_result=result, bids={"g1": bid}
        )
        report = engine.summary_report()
        assert "结算汇总报告" in report
        assert "g1" in report


# ============================================================
#  Test: Agents
# ============================================================

class TestAgents:
    def test_bidding_agent_coal(self):
        unit = make_coal_unit()
        agent = BiddingAgent("a1", unit, strategy="marginal_cost")
        bid = agent.generate_bid()
        assert isinstance(bid, CoalUnitBid)
        assert len(bid.energy_curve.points) >= 2

    def test_bidding_agent_storage(self):
        unit = make_storage_unit()
        agent = BiddingAgent("a2", unit)
        bid = agent.generate_bid()
        assert isinstance(bid, StorageBid)

    def test_bidding_agent_renewable(self):
        unit = make_re_unit()
        agent = BiddingAgent("a3", unit)
        bid = agent.generate_bid()
        assert isinstance(bid, RenewableBid)

    def test_price_taker_agent(self):
        unit = UnitMaster(
            unit_id="chp1", name="CHP", unit_type=UnitType.CHP,
            node="node_A", rated_power=100,
        )
        agent = PriceTakerAgent("pt1", unit)
        sched = agent.generate_bid()
        assert isinstance(sched, PriceTakerSchedule)
        assert len(sched.schedule_mw) == DA_PERIODS


# ============================================================
#  Test: Full Pipeline (Integration)
# ============================================================

class TestIntegration:
    def test_full_pipeline(self):
        """完整日前市场出清流程测试"""
        units = {
            "g1": make_coal_unit("g1", rated=300, deep=120),
            "g2": make_coal_unit("g2", rated=300, deep=120),
        }
        agents = [
            BiddingAgent("g1", units["g1"]),
            BiddingAgent("g2", units["g2"]),
        ]
        load_unit = UnitMaster(
            unit_id="load", name="Load", unit_type=UnitType.COAL, node="default"
        )
        demand = np.full(24, 400.0)
        load_agents = [LoadAgent("load", load_unit, base_demand=demand)]

        runner = MarketRunner(
            units=units,
            agents=agents,
            load_agents=load_agents,
            solver_name="glpk",
        )
        report = runner.run_full_day_ahead()
        assert runner.da_market_result is not None
        assert "g1" in runner.da_market_result.unit_results
        assert "g2" in runner.da_market_result.unit_results
        total_power = sum(
            ur.power.mean()
            for ur in runner.da_market_result.unit_results.values()
        )
        assert total_power > 350  # should meet ~400MW demand
