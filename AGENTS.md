# AGENTS.md

## Cursor Cloud specific instructions

### Project overview

**simpower** is a Python library and CLI tool for power systems optimization (Economic Dispatch, OPF, Unit Commitment, Stochastic UC). It uses Pyomo for algebraic modeling and GLPK as the default open-source solver.

### Virtual environment

The project uses a Python 3.12 venv at `.venv/`. Always activate it before running commands:

```bash
source .venv/bin/activate
```

### Package alias: minpower → simpower

The test files import from `minpower` (legacy package name), but the package directory is `simpower`. A symlink in site-packages (`minpower` → `/workspace/simpower`) provides the alias. If dependencies are reinstalled, recreate it:

```bash
SITE_PKGS=$(python3 -c "import site; print(site.getsitepackages()[0])")
ln -sf /workspace/simpower "$SITE_PKGS/minpower"
```

### Key commands

| Action | Command |
|--------|---------|
| Lint | `flake8 simpower/ --max-line-length=120` |
| Tests | `python3 -m pytest simpower/tests/ -v` |
| CLI (ED) | `simpower simpower/tests/ed --solver glpk` |
| CLI (UC) | `simpower simpower/tests/uc --solver glpk` |

### Known test limitations

- 4 tests fail due to GLPK not supporting dual/price extraction for MIP problems (`line_limit_high`, `line_limit_low`, `three_buses`, `load_shedding`). These require CPLEX or Gurobi to pass.
- 1 stochastic test is skipped (requires PySP which is not installed).
- FutureWarnings from pandas 2.1.x about `Series.__getitem__` and `pd.unique()` are expected and harmless.

### 新市场仿真系统 (simpower.market)

新系统在 `simpower/market/` 子包中，按照《重庆电力现货交易实施细则V2.0》实现。
核心出清引擎使用 **PyPSA DC-OPF + HiGHS** 求解器，支持网络约束下的 LMP 计算。

| Action | Command |
|--------|---------|
| 运行 IEEE 6-bus 96时段演示 | `python -m simpower.market.demo` |
| 市场模块测试 (26个) | `python -m pytest simpower/market/tests/ -v` |

模块结构:
- `models.py`: 数据模型（机组/报价/市场结果/结算/常量）
- `bid_validator.py`: 报价校验（煤机/新能源/储能，2-10点，0-1500限价）
- `ieee_network.py`: IEEE 6-bus / 14-bus 标准测试网络
- `pypsa_clearing.py`: PyPSA DC-OPF 出清引擎（含LMP提取）
- `clearing.py`: Pyomo SCUC/SCED 引擎（备用）
- `rt_clearing.py`: 实时5min滚动 SCED
- `settlement.py`: 结算引擎
- `agents.py`: Agent 框架（BiddingAgent / PriceTakerAgent）
- `runner.py`: 市场编排器
- `demo.py`: IEEE 6-bus 96时段完整演示

依赖: PyPSA 1.1+, linopy, HiGHS (highspy), Pyomo, GLPK。

### Python 3.12 compatibility notes

- `SafeConfigParser` was replaced with `ConfigParser` in `config.py`.
- pandas frequency alias `'H'` was changed to `'h'` (pandas 2.x deprecation).
- `setuptools<70` is pinned because newer versions removed `pkg_resources` which `standalone.py` imports.
- `nose-py3` is used instead of `nose` (the `imp` module was removed in Python 3.12).
