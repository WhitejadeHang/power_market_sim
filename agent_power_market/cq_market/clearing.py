"""
市场出清引擎
实现 SCUC (安全约束机组组合) 和 SCED (安全约束经济调度)
按照《重庆电力现货交易实施细则V2.0》附件二、附件三数学模型实现
"""
from __future__ import annotations
import logging
import numpy as np
from pyomo.environ import (
    ConcreteModel, Set, Param, Var, Objective, Constraint,
    Binary, NonNegativeReals, Reals, minimize, SolverFactory, value as pyo_value,
    Suffix,
)
from .models import (
    UnitMaster, UnitType, UnitBoundary96, BidCurve,
    CoalUnitBid, StorageBid, RenewableBid, PriceTakerSchedule,
    MarketResult, UnitResult, SystemTopology, SpecialUnitFlag,
    DA_PERIODS, DA_PERIOD_HOURS, HOURS_PER_DAY,
    PENALTY_BALANCE_CLEARING, PENALTY_SECTION_CLEARING, PENALTY_SECTION_PRICING,
    PRICE_CLEAR_UPPER, PRICE_CLEAR_LOWER,
)

logger = logging.getLogger(__name__)


def _decompose_bid_segments(curve: BidCurve, num_steps: int = 10):
    """将报价曲线阶梯化分解为多个等宽区间 (段出力宽度, 段价格)"""
    if not curve.points or len(curve.points) < 2:
        return []
    segments = []
    raw_segs = curve.get_segments()
    for p_start, p_end, price in raw_segs:
        width = p_end - p_start
        if width > 0:
            segments.append((width, price))
    return segments


class SCUCSolver:
    """日前安全约束机组组合 (MILP)
    
    目标: min Σ(运行费用 + 启动费用 + 空载费用 + 松弛惩罚)
    约束: 系统平衡、备用、机组出力上下限、爬坡、最小开停时间、储能SOC
    """

    def __init__(
        self,
        units: dict[str, UnitMaster],
        bids: dict[str, CoalUnitBid | StorageBid | RenewableBid],
        boundaries: dict[str, UnitBoundary96],
        system_demand: np.ndarray,
        price_takers: dict[str, PriceTakerSchedule] | None = None,
        renewable_forecast: dict[str, np.ndarray] | None = None,
        topology: SystemTopology | None = None,
        reserve_up: float = 0.0,
        reserve_down: float = 0.0,
        solver_name: str = "glpk",
        num_periods: int = DA_PERIODS,
        period_hours: float = DA_PERIOD_HOURS,
    ):
        self.units = units
        self.bids = bids
        self.boundaries = boundaries
        self.system_demand = system_demand
        self.price_takers = price_takers or {}
        self.renewable_forecast = renewable_forecast or {}
        self.topology = topology
        self.reserve_up = reserve_up
        self.reserve_down = reserve_down
        self.solver_name = solver_name
        self.num_periods = num_periods
        self.period_hours = period_hours

        self._thermal_units = []
        self._storage_units = []
        self._renewable_units = []
        self._price_taker_units = []
        self._classify_units()

    def _classify_units(self):
        for uid, u in self.units.items():
            if u.unit_type == UnitType.STORAGE:
                self._storage_units.append(uid)
            elif u.unit_type == UnitType.RENEWABLE:
                self._renewable_units.append(uid)
            elif u.unit_type in (UnitType.CHP, UnitType.SELF_GEN):
                self._price_taker_units.append(uid)
            elif u.unit_type == UnitType.COAL:
                self._thermal_units.append(uid)

    def build_model(self, include_commitment: bool = True) -> ConcreteModel:
        m = ConcreteModel("SCUC" if include_commitment else "SCED")

        T = self.num_periods
        dt = self.period_hours

        # ---------- Sets ----------
        m.T = Set(initialize=range(T))
        m.G = Set(initialize=self._thermal_units)
        m.ES = Set(initialize=self._storage_units)
        m.RE = Set(initialize=self._renewable_units)

        # ---------- Bid segments for thermal ----------
        thermal_segments = {}
        for uid in self._thermal_units:
            bid = self.bids.get(uid)
            if bid and hasattr(bid, 'energy_curve'):
                segs = _decompose_bid_segments(bid.energy_curve)
                thermal_segments[uid] = segs
            else:
                thermal_segments[uid] = [(self.units[uid].rated_power, 300.0)]

        max_segs = max((len(v) for v in thermal_segments.values()), default=1)
        m.M = Set(initialize=range(max_segs))

        # ---------- Parameters ----------
        def demand_init(m, t):
            return self.system_demand[t] if t < len(self.system_demand) else 0
        m.Demand = Param(m.T, initialize=demand_init)

        # Price-taker fixed injection
        pt_total = np.zeros(T)
        for uid in self._price_taker_units:
            if uid in self.price_takers:
                pt_total += self.price_takers[uid].schedule_mw[:T]
        m.PT_inject = Param(m.T, initialize={t: pt_total[t] for t in range(T)})

        # ---------- Variables ----------
        # Thermal
        if include_commitment:
            m.u = Var(m.G, m.T, domain=Binary)          # commitment
            m.v = Var(m.G, m.T, domain=Binary)          # startup indicator
            m.w = Var(m.G, m.T, domain=Binary)          # shutdown indicator
        else:
            m.u = Var(m.G, m.T, domain=Binary)

        m.p = Var(m.G, m.T, domain=NonNegativeReals)     # total power
        m.p_seg = Var(m.G, m.M, m.T, domain=NonNegativeReals)

        # Storage
        m.p_dis = Var(m.ES, m.T, domain=NonNegativeReals)
        m.p_ch = Var(m.ES, m.T, domain=NonNegativeReals)
        m.soc = Var(m.ES, m.T, bounds=(0, 1))
        m.es_dis_flag = Var(m.ES, m.T, domain=Binary)
        m.es_ch_flag = Var(m.ES, m.T, domain=Binary)

        # Renewables
        m.p_re = Var(m.RE, m.T, domain=NonNegativeReals)

        # Balance slack
        m.slack_pos = Var(m.T, domain=NonNegativeReals)
        m.slack_neg = Var(m.T, domain=NonNegativeReals)

        # ---------- Objective ----------
        def obj_rule(m):
            cost = 0
            for g in m.G:
                segs = thermal_segments.get(g, [])
                bid = self.bids.get(g)
                for t in m.T:
                    for s in m.M:
                        if s < len(segs):
                            _, price = segs[s]
                            cost += price * m.p_seg[g, s, t] * dt
                    if include_commitment and bid and hasattr(bid, 'noload_cost'):
                        cost += bid.noload_cost * 10000 * m.u[g, t] * dt
                        cost += bid.startup_cost_hot * 10000 * m.v[g, t]
            # Storage cost (simplified)
            for es in m.ES:
                bid = self.bids.get(es)
                if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
                    avg_price = np.mean([p.price_yuan_mwh for p in bid.energy_curve.points])
                    for t in m.T:
                        cost += avg_price * m.p_dis[es, t] * dt
                        cost -= avg_price * 0.5 * m.p_ch[es, t] * dt
            # Renewable cost
            for re in m.RE:
                bid = self.bids.get(re)
                if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
                    price = bid.energy_curve.points[0].price_yuan_mwh if bid.energy_curve.points else 0
                    for t in m.T:
                        cost += price * m.p_re[re, t] * dt
            # Slack penalty
            for t in m.T:
                cost += PENALTY_BALANCE_CLEARING * (m.slack_pos[t] + m.slack_neg[t])
            return cost
        m.obj = Objective(rule=obj_rule, sense=minimize)

        # ---------- Constraints ----------

        # (1) System balance
        def balance_rule(m, t):
            gen_total = sum(m.p[g, t] for g in m.G)
            re_total = sum(m.p_re[re, t] for re in m.RE)
            es_net = sum(m.p_dis[es, t] - m.p_ch[es, t] for es in m.ES)
            return (gen_total + re_total + es_net + m.PT_inject[t]
                    + m.slack_pos[t] - m.slack_neg[t]
                    == m.Demand[t])
        m.balance = Constraint(m.T, rule=balance_rule)

        # (2) Thermal: power = sum of segments
        def power_sum_rule(m, g, t):
            segs = thermal_segments.get(g, [])
            return m.p[g, t] == sum(m.p_seg[g, s, t] for s in m.M if s < len(segs))
        m.power_sum = Constraint(m.G, m.T, rule=power_sum_rule)

        # (3) Segment upper bounds
        def seg_upper_rule(m, g, s, t):
            segs = thermal_segments.get(g, [])
            if s < len(segs):
                width, _ = segs[s]
                return m.p_seg[g, s, t] <= width
            return m.p_seg[g, s, t] == 0
        m.seg_upper = Constraint(m.G, m.M, m.T, rule=seg_upper_rule)

        # (4) Thermal output bounds
        def gen_upper_rule(m, g, t):
            u = self.units[g]
            bnd = self.boundaries.get(g)
            pmax = min(u.max_power, bnd.pmax_96[t] if bnd else u.max_power)
            return m.p[g, t] <= pmax * m.u[g, t]
        m.gen_upper = Constraint(m.G, m.T, rule=gen_upper_rule)

        def gen_lower_rule(m, g, t):
            u = self.units[g]
            bnd = self.boundaries.get(g)
            pmin = max(u.min_power, bnd.pmin_96[t] if bnd else u.min_power)
            return m.p[g, t] >= pmin * m.u[g, t]
        m.gen_lower = Constraint(m.G, m.T, rule=gen_lower_rule)

        # (5) Ramp constraints
        def ramp_up_rule(m, g, t):
            if t == 0:
                return Constraint.Skip
            u = self.units[g]
            ramp = u.ramp_rate * (dt * 60) if u.ramp_rate > 0 else u.max_power
            return m.p[g, t] - m.p[g, t-1] <= ramp
        m.ramp_up = Constraint(m.G, m.T, rule=ramp_up_rule)

        def ramp_down_rule(m, g, t):
            if t == 0:
                return Constraint.Skip
            u = self.units[g]
            ramp = u.ramp_rate * (dt * 60) if u.ramp_rate > 0 else u.max_power
            return m.p[g, t-1] - m.p[g, t] <= ramp
        m.ramp_down = Constraint(m.G, m.T, rule=ramp_down_rule)

        if include_commitment:
            # (6) Startup/shutdown logic: v[t] - w[t] = u[t] - u[t-1]
            def startup_logic_rule(m, g, t):
                if t == 0:
                    return m.v[g, t] - m.w[g, t] == m.u[g, t]
                return m.v[g, t] - m.w[g, t] == m.u[g, t] - m.u[g, t-1]
            m.startup_logic = Constraint(m.G, m.T, rule=startup_logic_rule)

            # (7) Min up/down time (simplified for 15-min periods)
            def min_up_rule(m, g, t):
                u = self.units[g]
                L = int(u.min_up_time_h / dt)
                if t < L:
                    return Constraint.Skip
                return sum(m.v[g, k] for k in range(t - L + 1, t + 1)) <= m.u[g, t]
            m.min_up = Constraint(m.G, m.T, rule=min_up_rule)

            def min_down_rule(m, g, t):
                u = self.units[g]
                L = int(u.min_down_time_h / dt)
                if L == 0 or t < L:
                    return Constraint.Skip
                return sum(m.w[g, k] for k in range(t - L + 1, t + 1)) <= 1 - m.u[g, t]
            m.min_down = Constraint(m.G, m.T, rule=min_down_rule)

        # (8) Renewable upper bound
        def re_upper_rule(m, re, t):
            fc = self.renewable_forecast.get(re)
            if fc is not None and t < len(fc):
                return m.p_re[re, t] <= fc[t]
            return m.p_re[re, t] <= self.units[re].rated_power
        m.re_upper = Constraint(m.RE, m.T, rule=re_upper_rule)

        # (9) Storage constraints
        def es_dis_upper(m, es, t):
            u = self.units[es]
            return m.p_dis[es, t] <= u.discharge_power_mw * m.es_dis_flag[es, t]
        m.es_dis_upper = Constraint(m.ES, m.T, rule=es_dis_upper)

        def es_ch_upper(m, es, t):
            u = self.units[es]
            return m.p_ch[es, t] <= u.charge_power_mw * m.es_ch_flag[es, t]
        m.es_ch_upper = Constraint(m.ES, m.T, rule=es_ch_upper)

        def es_exclusive(m, es, t):
            return m.es_dis_flag[es, t] + m.es_ch_flag[es, t] <= 1
        m.es_exclusive = Constraint(m.ES, m.T, rule=es_exclusive)

        # SOC dynamics
        def soc_rule(m, es, t):
            u = self.units[es]
            cap = u.storage_capacity_mwh
            if cap <= 0:
                return Constraint.Skip
            if t == 0:
                return m.soc[es, t] == u.initial_soc + (
                    m.p_ch[es, t] * u.charge_efficiency * dt
                    - m.p_dis[es, t] * dt / u.discharge_efficiency
                ) / cap
            return m.soc[es, t] == m.soc[es, t-1] + (
                m.p_ch[es, t] * u.charge_efficiency * dt
                - m.p_dis[es, t] * dt / u.discharge_efficiency
            ) / cap
        m.soc_dynamics = Constraint(m.ES, m.T, rule=soc_rule)

        def soc_bounds(m, es, t):
            u = self.units[es]
            bnd = self.boundaries.get(es)
            lo = u.soc_min
            hi = u.soc_max
            if bnd and bnd.soc_min_96 is not None:
                lo = bnd.soc_min_96[t]
            if bnd and bnd.soc_max_96 is not None:
                hi = bnd.soc_max_96[t]
            m.soc[es, t].setlb(lo)
            m.soc[es, t].setub(hi)
            return Constraint.Skip
        m.soc_bounds = Constraint(m.ES, m.T, rule=soc_bounds)

        # End-of-day SOC constraint
        def soc_end_rule(m, es):
            bid = self.bids.get(es)
            if bid and hasattr(bid, 'end_of_day_soc') and bid.end_of_day_soc is not None:
                return m.soc[es, T-1] == bid.end_of_day_soc
            return Constraint.Skip
        m.soc_end = Constraint(m.ES, rule=soc_end_rule)

        # (10) Must-on units
        for uid, bnd in self.boundaries.items():
            if uid in self._thermal_units:
                for t in range(T):
                    if bnd.special_flags[t] == SpecialUnitFlag.MUST_ON.value:
                        m.u[uid, t].fix(1)

        # (11) Reserve (simplified)
        if self.reserve_up > 0:
            def reserve_up_rule(m, t):
                return (sum(
                    self.units[g].max_power * m.u[g, t] for g in m.G
                ) >= m.Demand[t] + self.reserve_up)
            m.reserve_up_con = Constraint(m.T, rule=reserve_up_rule)

        return m

    def solve(self, include_commitment: bool = True) -> MarketResult:
        m = self.build_model(include_commitment=include_commitment)

        solver = SolverFactory(self.solver_name)
        if self.solver_name == "glpk":
            solver.options["tmlim"] = 300
        results = solver.solve(m, tee=False)

        status = results.solver.termination_condition
        logger.info(f"SCUC solver status: {status}")

        T = self.num_periods
        market_result = MarketResult(
            num_periods=T,
            period_hours=self.period_hours,
        )

        # Extract results
        for g in self._thermal_units:
            commitment = np.array([round(pyo_value(m.u[g, t])) for t in range(T)])
            power = np.array([pyo_value(m.p[g, t]) for t in range(T)])
            market_result.unit_results[g] = UnitResult(
                unit_id=g, commitment=commitment, power=power
            )

        for re in self._renewable_units:
            power = np.array([pyo_value(m.p_re[re, t]) for t in range(T)])
            market_result.unit_results[re] = UnitResult(
                unit_id=re,
                commitment=np.ones(T),
                power=power,
            )

        for es in self._storage_units:
            p_dis = np.array([pyo_value(m.p_dis[es, t]) for t in range(T)])
            p_ch = np.array([pyo_value(m.p_ch[es, t]) for t in range(T)])
            soc = np.array([pyo_value(m.soc[es, t]) for t in range(T)])
            market_result.unit_results[es] = UnitResult(
                unit_id=es,
                commitment=np.ones(T),
                power=p_dis - p_ch,
                charge_power=p_ch,
                discharge_power=p_dis,
                soc=soc,
            )

        for uid in self._price_taker_units:
            if uid in self.price_takers:
                sched = self.price_takers[uid].schedule_mw[:T]
                market_result.unit_results[uid] = UnitResult(
                    unit_id=uid,
                    commitment=np.ones(T),
                    power=sched.copy(),
                )

        market_result.system_cost = pyo_value(m.obj)
        market_result.slack_balance = np.array([
            pyo_value(m.slack_pos[t]) - pyo_value(m.slack_neg[t])
            for t in range(T)
        ])

        return market_result


class SCEDSolver(SCUCSolver):
    """安全约束经济调度 (LP)
    在SCUC确定的开机组合基础上求解经济调度，并提取LMP对偶变量。
    """

    def __init__(self, commitment_result: MarketResult, **kwargs):
        super().__init__(**kwargs)
        self.commitment_result = commitment_result

    def solve(self, include_commitment: bool = False) -> MarketResult:
        m = self.build_model(include_commitment=True)

        T = self.num_periods
        # Fix commitment from SCUC result and compute startup/shutdown
        for g in self._thermal_units:
            if g in self.commitment_result.unit_results:
                commit = self.commitment_result.unit_results[g].commitment
                for t in range(T):
                    val = int(commit[t])
                    m.u[g, t].fix(val)
                    if t == 0:
                        m.v[g, t].fix(max(val, 0))
                        m.w[g, t].fix(0)
                    else:
                        prev = int(commit[t-1])
                        m.v[g, t].fix(max(val - prev, 0))
                        m.w[g, t].fix(max(prev - val, 0))

        # Add dual suffix for LMP
        m.dual = Suffix(direction=Suffix.IMPORT)

        solver = SolverFactory(self.solver_name)
        results = solver.solve(m, tee=False)
        logger.info(f"SCED solver status: {results.solver.termination_condition}")

        market_result = MarketResult(num_periods=T, period_hours=self.period_hours)

        for g in self._thermal_units:
            power = np.array([pyo_value(m.p[g, t]) for t in range(T)])
            commit = np.array([round(pyo_value(m.u[g, t])) for t in range(T)])
            market_result.unit_results[g] = UnitResult(
                unit_id=g, commitment=commit, power=power
            )

        for re in self._renewable_units:
            power = np.array([pyo_value(m.p_re[re, t]) for t in range(T)])
            market_result.unit_results[re] = UnitResult(
                unit_id=re, commitment=np.ones(T), power=power
            )

        for es in self._storage_units:
            p_dis = np.array([pyo_value(m.p_dis[es, t]) for t in range(T)])
            p_ch = np.array([pyo_value(m.p_ch[es, t]) for t in range(T)])
            soc_arr = np.array([pyo_value(m.soc[es, t]) for t in range(T)])
            market_result.unit_results[es] = UnitResult(
                unit_id=es, commitment=np.ones(T), power=p_dis - p_ch,
                charge_power=p_ch, discharge_power=p_dis, soc=soc_arr,
            )

        for uid in self._price_taker_units:
            if uid in self.price_takers:
                sched = self.price_takers[uid].schedule_mw[:T]
                market_result.unit_results[uid] = UnitResult(
                    unit_id=uid, commitment=np.ones(T), power=sched.copy()
                )

        # Extract LMP from balance constraint duals
        lmp_default = np.zeros(T)
        dual_ok = False
        try:
            if hasattr(m, 'dual') and len(m.dual) > 0:
                for t in range(T):
                    dual_val = m.dual.get(m.balance[t], 0.0)
                    if dual_val != 0.0:
                        dual_ok = True
                    lmp_val = -dual_val / self.period_hours if dual_val else 0.0
                    lmp_val = max(PRICE_CLEAR_LOWER, min(PRICE_CLEAR_UPPER, lmp_val))
                    lmp_default[t] = lmp_val
        except Exception:
            pass

        if not dual_ok:
            logger.info("使用边际成本估算LMP (求解器未返回对偶值)")
            for t in range(T):
                costs = []
                for g in self._thermal_units:
                    ur = market_result.unit_results.get(g)
                    if ur and ur.commitment[t] > 0.5 and ur.power[t] > 0.01:
                        bid = self.bids.get(g)
                        if bid and hasattr(bid, 'energy_curve'):
                            mc = bid.energy_curve.marginal_cost_at(ur.power[t])
                            costs.append(mc)
                for re_id in self._renewable_units:
                    ur = market_result.unit_results.get(re_id)
                    if ur and ur.power[t] > 0.01:
                        bid = self.bids.get(re_id)
                        if bid and hasattr(bid, 'energy_curve') and bid.energy_curve.points:
                            costs.append(bid.energy_curve.marginal_cost_at(ur.power[t]))
                lmp_default[t] = max(costs) if costs else 0.0

        # Assign same LMP to all nodes (single-bus simplification)
        all_nodes = set(u.node for u in self.units.values())
        for node in all_nodes:
            market_result.lmp[node] = lmp_default.copy()

        # Compute generation cost (excluding slack penalty)
        gen_cost = 0.0
        dt = self.period_hours
        for g in self._thermal_units:
            ur = market_result.unit_results.get(g)
            bid = self.bids.get(g)
            if ur and bid and hasattr(bid, 'energy_curve'):
                for t in range(T):
                    if ur.power[t] > 0.01:
                        mc = bid.energy_curve.marginal_cost_at(ur.power[t])
                        gen_cost += mc * ur.power[t] * dt
                if hasattr(bid, 'noload_cost'):
                    gen_cost += bid.noload_cost * 10000 * ur.commitment.sum() * dt
        market_result.system_cost = gen_cost
        market_result.compute_unified_settlement_price(self.units)

        return market_result
