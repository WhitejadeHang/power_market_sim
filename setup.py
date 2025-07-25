# simpower's setup script

# make a new release by using
# seed release --dry-run
# and then
# seed release

from setuptools import setup, find_packages

version_number = open("simpower/__init__.py").read().split('"')[1].rstrip('"')

setup(
    name="simpower",
    version=version_number,
    download_url="https://github.com/WhitejadeHang/power_market_sim"
    + "/zipball/v{v}".format(v=version_number),
    entry_points="""
    [console_scripts]
    simpower = simpower.solve:main
    standalone_simpower = simpower.solve:standaloneUC
    scheduler_simpower = simpower.experiments.scheduler_simpower:main
    initial_dispatch = simpower.experiments.get_initial_dispatch:main
    """,
    package_data={
        "simpower.configuration": ["simpower.cfg"],
        "simpower.tests": ["*.csv", "*/*.csv", "*/*/*.csv"],
    },
    install_requires=[
        "pandas>=1.3,<3.0",
        "pyomo>=6.0,<7.0",
        "matplotlib>=3.4,<4.0",
        "xarray>=0.18,<3.0",
        "numpy>=1.20,<2.0",
    ],
    tests_require=["nose", "coverage", "objgraph"],
    # it helps to have seed if you are going to make releases
    # but it is not required for setup
    description="power systems optimization made beautiful",
    author="Adam Greenhall",
    author_email="simpower@adamgreenhall.com",
    url="https://github.com/WhitejadeHang/power_market_sim",
    packages=find_packages(),
    keywords=["power systems", "optimization"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Other Environment",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Natural Language :: English",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Topic :: Scientific/Engineering",
        "Topic :: Scientific/Engineering :: Mathematics",
    ],
    long_description="""
power systems tools made beautiful
-----------------------------------------

* Solves ED, OPF, and UC problems.
* Problems can be defined in simple spreadsheets.
* Visualizations are created for the answers.
* Many solvers are supported.


* `Full documentation and tutorials <https://github.com/WhitejadeHang/power_market_sim>`_
* `Code base <https://github.com/WhitejadeHang/power_market_sim>`_

""",
)
