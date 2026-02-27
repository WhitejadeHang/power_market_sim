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

### Python 3.12 compatibility notes

- `SafeConfigParser` was replaced with `ConfigParser` in `config.py`.
- pandas frequency alias `'H'` was changed to `'h'` (pandas 2.x deprecation).
- `setuptools<70` is pinned because newer versions removed `pkg_resources` which `standalone.py` imports.
- `nose-py3` is used instead of `nose` (the `imp` module was removed in Python 3.12).
