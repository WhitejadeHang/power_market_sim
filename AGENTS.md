## Cursor Cloud specific instructions

**simpower** is a Python power systems optimization toolkit (ED, OPF, UC, SCUC). It is a CLI tool, not a web application.

### Environment setup

- **Python 3.11** is required. Python 3.12+ breaks `SafeConfigParser` imports in `simpower/config.py`.
- A virtual environment lives at `/workspace/.venv` — activate with `source /workspace/.venv/bin/activate`.
- **GLPK** (`glpsol`) is the default open-source LP/MIP solver. It must be installed system-wide (`apt install glpk-utils`).
- The solver config defaults to `cplex` in `simpower/configuration/minpower.cfg`. Override to `glpk` via `~/.minpowerrc` (already configured).
- A symlink `minpower -> simpower` at the repo root is needed because tests import from `minpower.*` while the package directory is `simpower/`.

### Running

- **Lint:** `flake8 simpower/ --max-line-length=120` (config in `setup.cfg`)
- **Tests:** `python -m pytest simpower/tests/ -v` (use pytest, not nose — nose is broken on Python 3.10+)
- **Run a problem:** `python -m simpower.solve <problem_directory> --solver glpk`
  - Example: `python -m simpower.solve simpower/tests/ed --solver glpk`

### Known test failures

4 tests fail when using GLPK because it does not return dual values (LMPs/prices) for MIP problems:
- `test_opf::line_limit_high`, `test_opf::line_limit_low`, `test_opf::three_buses` — need duals for OPF pricing
- `test_uc::load_shedding` — needs duals for shedding price assertion

These pass with commercial solvers (CPLEX/Gurobi) that support MIP duals.
