# Simpower 快速入门指南 ⚡

## 🚀 5分钟快速体验

### 1. 环境准备

```bash
# 确保Python 3.8+
python3 --version

# 安装求解器 (Ubuntu/Debian)
sudo apt-get install coinor-cbc glpk-utils

# 或者通过conda安装
conda install -c conda-forge coincbc glpk
```

### 2. 运行演示

```bash
# 克隆项目
git clone https://github.com/WhitejadeHang/power_market_sim
cd power_market_sim

# 安装依赖
pip install -r requirements.txt

# 运行简化演示
python examples/simple_demo.py
```

### 3. 预期输出

```
Simpower 电力系统优化与市场仿真演示
==================================================
✓ 对偶变量计算已启用 (节点电价功能)

案例1: 经济调度演示
------------------------------
发电机组配置:
- 火电机组: 100MW, 成本10$/MWh
- 燃气机组: 80MW, 成本20$/MWh
- 尖峰机组: 60MW, 成本30$/MWh

负载(MW)   火电(MW)   燃气(MW)   尖峰(MW)   电价($/MWh)
------------------------------------------------------------
80         60.0       15.0       10.0       10.00
120        95.0       15.0       10.0       10.00
180        100.0      65.0       15.0       20.00
250        100.0      80.0       60.0       30.00

案例2: 负载削减演示
------------------------------
测试负载: 280MW (超出总供应能力240MW)
实际发电量: 240.0MW
负载削减量: 40.0MW
系统电价: 10000.00$/MWh
✓ 系统正确处理了负载削减情况
✓ 电价升至负载削减成本，反映供应紧张

案例3: 节点电价分析
------------------------------
电价形成机制验证:
低负载(50MW): 10.00$/MWh
中负载(120MW): 10.00$/MWh
高负载(200MW): 30.00$/MWh

电价分析:
✓ 电价随负载增加而上升，符合经济学原理
✓ 低负载时电价等于最便宜机组成本(10$/MWh)
✓ 高负载时电价等于最贵运行机组成本(30$/MWh)

演示总结:
✅ 经济调度功能正常 - 优化资源配置
✅ 节点电价计算正确 - 反映边际成本
✅ 负载削减处理合理 - 供需平衡优化
✅ Simpower电力市场仿真功能完整可用!
```

## 📖 基础概念

### 什么是经济调度？
经济调度是在满足负载需求的前提下，以最小成本安排发电机组出力的优化问题。

**数学模型：**
```
目标函数: min Σ C_i(P_i)        # 最小化总发电成本
约束条件: Σ P_i = Load         # 功率平衡约束
         P_min_i ≤ P_i ≤ P_max_i  # 机组出力限制
```

### 什么是节点边际电价(LMP)？
节点边际电价是增加单位负载所增加的系统总成本，等于最后投入机组的边际成本。

**经济学含义：**
- 反映电力的真实价值
- 引导资源优化配置
- 支持市场化定价机制

### 什么是机组组合？
机组组合在经济调度基础上，增加了机组启停决策，考虑启停成本、最小运行时间等约束。

**关键约束：**
- 最小启动/停机时间
- 爬坡速率限制
- 启停成本

## 🔧 基础API使用

### 创建发电机组

```python
from simpower.tests.test_utils import *

# 火电机组 - 成本低但灵活性差
coal_gen = make_cheap_gen(
    pmax=200,      # 最大出力 200MW
    pmin=50,       # 最小出力 50MW
    cost=25        # 边际成本 25$/MWh
)

# 燃气机组 - 成本中等但灵活性好
gas_gen = make_mid_gen(
    pmax=150,
    pmin=30,
    cost=40
)

# 可再生能源 - 零边际成本
wind_gen = make_expensive_gen(
    pmax=100,
    pmin=0,
    cost=0         # 风电边际成本为0
)
```

### 求解优化问题

```python
from simpower.config import user_config

# 启用电价计算
user_config.duals = True

# 创建负载
generators = [coal_gen, gas_gen, wind_gen]
load_mw = 250

# 求解
power_system, times = solve_problem(
    generators, 
    **make_loads_times(Pdt=[load_mw])
)

# 获取结果
for i, gen in enumerate(generators):
    power = value(gen.power(times[0]))
    print(f"机组{i+1}出力: {power:.1f} MW")

# 获取电价
price = power_system.buses[0].price(times[0])
print(f"系统电价: {price:.2f} $/MWh")
```

### 多时段优化

```python
# 24小时负载曲线
hourly_load = [
    120, 110, 100, 95, 100, 120,    # 0-5时
    140, 160, 180, 200, 220, 240,   # 6-11时
    250, 245, 240, 245, 260, 280,   # 12-17时
    300, 280, 250, 200, 160, 140    # 18-23时
]

# 求解24小时机组组合
power_system, times = solve_problem(
    generators,
    **make_loads_times(Pdt=hourly_load)
)

# 分析每小时结果
for hour, time in enumerate(times):
    load = hourly_load[hour]
    price = power_system.buses[0].price(time)
    print(f"第{hour:2d}时: 负载={load:3d}MW, 电价={price:6.2f}$/MWh")
```

## 🎯 应用场景

### 1. 学术研究
- **电力市场设计研究**: 比较不同市场机制的效率
- **政策影响评估**: 分析碳税、可再生能源补贴等政策效果
- **算法开发**: 测试新的优化算法和启发式方法

### 2. 工程实践
- **电网规划**: 评估新建发电厂的经济效益
- **运行分析**: 制定最优的机组调度策略
- **投资决策**: 分析不同技术路线的投资回报

### 3. 教学应用
- **理论验证**: 让学生直观理解电力系统经济学原理
- **案例分析**: 创建真实的电力市场仿真案例
- **实验设计**: 支持各种假设情况的实验

## 🔍 故障排除

### 常见问题

**Q: 运行时出现"Solver not found"错误**
```bash
# 解决方案：安装求解器
sudo apt-get install coinor-cbc glpk-utils

# 或检查求解器是否在PATH中
which cbc
which glpsol
```

**Q: 导入模块失败**
```bash
# 解决方案：确保在项目根目录运行
cd power_market_sim
python examples/simple_demo.py

# 或设置PYTHONPATH
export PYTHONPATH=$PWD:$PYTHONPATH
```

**Q: 求解失败或无解**
```python
# 检查问题规模是否合理
total_capacity = sum(gen.pmax for gen in generators)
max_load = max(hourly_load)
print(f"总供应能力: {total_capacity}MW")
print(f"最大负载: {max_load}MW")

# 如果供应不足，系统会自动进行负载削减
```

**Q: 电价为0或异常值**
```python
# 确保启用了对偶变量计算
from simpower.config import user_config
user_config.duals = True
print(f"对偶变量状态: {user_config.duals}")
```

### 调试技巧

```python
# 启用详细日志
import logging
logging.basicConfig(level=logging.INFO)

# 保存问题文件用于分析
user_config.keep_lp_files = True

# 检查优化结果
print(f"问题是否求解成功: {power_system.solved}")
print(f"求解时间: {power_system.solution_time:.2f}秒")
```

## 📚 进阶学习

### 推荐资源
1. **理论基础**
   - 《电力系统分析》- 何仰赞
   - 《电力市场理论与实践》- 言茂松
   - 《Power System Economics》- Steven Stoft

2. **编程技能**
   - Python数值计算：NumPy, Pandas
   - 优化建模：Pyomo, CVXPY
   - 数据可视化：Matplotlib, Plotly

3. **实际应用**
   - 查看更多例子：`examples/` 目录
   - 阅读测试用例：`simpower/tests/` 目录
   - 研究源代码：理解实现细节

## 🚀 高级功能 (v5.0新增)

### 大规模多时段优化

#### 120时段机组组合案例
```python
# 运行IEEE 14节点120时段案例
import os
os.chdir('simpower/tests')
exec(open('run_ieee14_120periods_preset.py').read())

# 特点：
# - 5天120时段连续优化
# - 大型机组建模 (300-1000MW)
# - 预设调度验证方法
# - 完整的可视化分析
```

#### 预设机组组合方法
```python
# 创建预设调度案例
exec(open('create_preset_uc_case.py').read())

# 解决问题：
# - 多时段UC优化可行性
# - 大规模问题求解稳定性
# - 最小启停时间约束处理
```

### 增强可视化分析

新版本提供10+种专业图表：
- 机组组合甘特图
- 多日负荷曲线对比
- 节点电价热力图  
- 成本结构分析
- 网络拓扑可视化
- 发电机利用率分析

### 案例库扩展

```bash
# 完整的IEEE 14节点案例系列
simpower/tests/ieee14_24periods_balanced/    # 24时段平衡调度
simpower/tests/ieee14_72periods_coal/        # 72时段燃煤案例
simpower/tests/ieee14_120periods_coal/       # 120时段燃煤案例
simpower/tests/ieee14_120periods_preset/     # 120时段预设调度
```

### 下一步
- 尝试修改机组参数，观察对电价的影响
- 添加可再生能源，分析对系统的影响
- 实现多区域电力系统建模
- 考虑输电约束和网络潮流
- **探索120时段长周期优化** 🆕
- **分析大型机组调度策略** 🆕
- **使用预设方法验证复杂调度** 🆕

---

**开始您的电力系统优化之旅吧！** 🌟

📖 更多资源：
- [最新更新总结](LATEST_UPDATES_SUMMARY.md)
- [项目状态报告](PROJECT_STATUS.md)
- [全面测试报告](COMPREHENSIVE_TEST_REPORT.md)

有问题请访问：https://github.com/WhitejadeHang/power_market_sim/issues