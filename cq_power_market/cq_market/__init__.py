"""
重庆电力现货市场仿真系统
Chongqing Electricity Spot Market Simulation System

基于《重庆电力现货交易实施细则V2.0》与《重庆电力市场结算实施细则V2.0》

核心模块:
- models: 数据模型（机组、报价、市场结果、结算）
- bid_validator: 报价校验（煤机/新能源/储能）
- clearing: 出清引擎（SCUC/SCED/RT_SCED）
- pricing: LMP 节点电价计算
- settlement: 结算模块
- agents: 市场主体Agent框架
- runner: 市场运行主流程编排
"""

__version__ = "1.0.0"
