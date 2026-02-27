# 重庆电力现货市场仿真系统

基于《重庆电力现货交易实施细则V2.0》与《重庆电力市场结算实施细则V2.0》实现的电力现货市场仿真平台。

## 技术栈

| 组件 | 技术 |
|------|------|
| 网络建模 | PyPSA (DC-OPF) |
| 优化建模 | Linopy (PyPSA 内置) |
| 求解器 | HiGHS (LP/MILP) / SCIP (LP/MILP) |
| 测试网络 | IEEE 6-bus / 14-bus |
| 语言 | Python 3.10+ |

## 建模框架

```
报价曲线 → 分段线性化 → PyPSA Network → Linopy Model → HiGHS/SCIP → LMP + 出力计划
```

- **PyPSA** 处理网络拓扑、KVL、功率平衡
- **Linopy** 自动生成变量和约束，支持通过 `extra_functionality` 注入自定义约束
- **HiGHS/SCIP** 作为底层 LP/MILP 求解器

## 安装

```bash
pip install -e .          # 基础安装 (HiGHS)
pip install -e ".[scip]"  # 含 SCIP 求解器
pip install -e ".[dev]"   # 含开发/测试依赖
```

## 快速开始

```bash
# 运行 IEEE 6-bus 96时段日前出清演示 (HiGHS)
python -m cq_market.demo highs

# 使用 SCIP 求解器
python -m cq_market.demo scip

# 运行测试
pytest
```

## 模块结构

```
cq_market/
├── models.py           # 数据模型 (机组/报价/市场结果/结算/常量)
├── bid_validator.py    # 报价校验 (2-10点, 单调递增, 0-1500限价)
├── ieee_network.py     # IEEE 6-bus / 14-bus 标准测试网络
├── pypsa_clearing.py   # PyPSA→Linopy→HiGHS/SCIP 出清引擎
├── clearing.py         # Pyomo SCUC/SCED (备用引擎)
├── rt_clearing.py      # 实时5min滚动SCED
├── settlement.py       # 结算引擎 (小时电价/统一结算点/成本补偿)
├── agents.py           # Agent框架 (BiddingAgent/PriceTakerAgent)
├── runner.py           # 市场编排器
├── demo.py             # IEEE 6-bus 96时段完整演示
└── tests/
    └── test_market.py  # 32个自动化测试
```

## 规则覆盖

- ✅ 96点(15min)日前出清 + 24×5min实时滚动
- ✅ 报量报价 / 报量不报价 / 价格接受者 三类主体
- ✅ 2-10点报价曲线 (单调递增/最小跨度/限价0-1500元/MWh)
- ✅ 报价曲线分段线性化 → segment generator merit order
- ✅ DC-OPF 网络约束 (线路潮流/KVL)
- ✅ LMP 节点电价 (含阻塞分量)
- ✅ 统一结算点电价 (发电侧加权平均)
- ✅ 小时结算电价 (DA: 4×15min均值)
- ✅ 机组运行成本补偿 (启动+空载+电能量损益)
- ✅ 必开机组/开停机过程/试验机组特殊处理 (模型层面)
- ✅ 储能充放电/SOC约束/套利优化
