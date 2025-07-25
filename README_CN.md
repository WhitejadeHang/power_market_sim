# Simpower - 电力系统优化与市场仿真平台

[English](README.textile) | 中文

Simpower是一个强大的电力系统优化和电力市场仿真平台，专为研究人员、工程师和学生设计。它提供了完整的电力系统建模、优化求解和市场仿真功能，支持多种电力市场机制的分析和研究。

## 🌟 核心特性

### 📊 电力系统建模
- **发电机组建模**: 支持火电、水电、燃气、风电、光伏等多种机组类型
- **负载建模**: 灵活的负载模式，支持时变负载和不确定性建模
- **网络建模**: 电力传输线路和变电站建模
- **约束建模**: 全面的运行约束，包括功率平衡、爬坡约束、最小启停时间等

### ⚡ 优化问题类型
- **经济调度 (ED)**: 最小成本发电调度
- **机组组合 (UC)**: 考虑启停约束的优化调度  
- **最优潮流 (OPF)**: 网络约束下的优化调度
- **随机机组组合 (SCUC)**: 考虑不确定性的鲁棒优化

### 💰 电力市场仿真
- **节点边际电价 (LMP)**: 实时电价计算
- **阻塞管理**: 输电阻塞的经济分析
- **备用市场**: 备用容量的定价和调度
- **负载削减**: 供需不平衡时的优化决策

### 🔧 求解器支持
- **开源求解器**: CBC, GLPK (免费使用)
- **商业求解器**: CPLEX, Gurobi (如已安装)
- **双变量支持**: 完整的对偶变量计算，支持边际价格分析

## 🚀 快速开始

### 安装要求
```bash
# Python环境要求
Python >= 3.8

# 安装依赖
pip install -r requirements.txt

# 安装开源求解器 (Ubuntu/Debian)
sudo apt-get install coinor-cbc glpk-utils

# 安装项目
python setup.py install
```

### 基础使用示例

```python
import simpower

# 创建发电机组
generators = [
    simpower.Generator(name='Coal1', pmax=100, pmin=20, cost_curve=[[0, 25], [100, 35]]),
    simpower.Generator(name='Gas1', pmax=80, pmin=10, cost_curve=[[0, 40], [80, 50]]),
    simpower.Generator(name='Wind1', pmax=50, pmin=0, cost_curve=[[0, 0], [50, 0]])
]

# 创建负载
loads = [simpower.Load(name='Load1', schedule=[120, 150, 180])]

# 创建电力系统
power_system = simpower.PowerSystem(generators=generators, loads=loads)

# 求解优化问题
power_system.solve()

# 获取结果
for gen in generators:
    print(f'{gen.name}: {gen.power_output} MW')
    
# 获取电价
price = power_system.get_lmp()
print(f'电价: {price} $/MWh')
```

## 📖 详细功能介绍

### 1. 电力系统建模

#### 1.1 发电机组建模

Simpower支持多种类型的发电机组建模：

```python
# 火电机组 - 具有最小出力约束和启停成本
coal_unit = simpower.Generator(
    name='Coal_Unit_1',
    pmax=300,           # 最大出力 (MW)
    pmin=100,           # 最小出力 (MW)
    cost_curve=[        # 成本曲线 [[出力, 成本], ...]
        [100, 2500],    # 100MW时成本2500$/h
        [200, 4800],    # 200MW时成本4800$/h
        [300, 7500]     # 300MW时成本7500$/h
    ],
    startup_cost=10000, # 启动成本 ($)
    shutdown_cost=2000, # 停机成本 ($)
    min_up_time=8,      # 最小运行时间 (小时)
    min_down_time=6,    # 最小停机时间 (小时)
    ramp_up_rate=50,    # 上爬坡率 (MW/h)
    ramp_down_rate=60   # 下爬坡率 (MW/h)
)

# 燃气机组 - 灵活性更高
gas_unit = simpower.Generator(
    name='Gas_Turbine_1',
    pmax=150,
    pmin=30,
    cost_curve=[[30, 1200], [100, 3800], [150, 6000]],
    startup_cost=3000,
    min_up_time=2,
    min_down_time=1,
    ramp_up_rate=100,
    ramp_down_rate=100
)

# 可再生能源 - 零边际成本
wind_unit = simpower.Generator(
    name='Wind_Farm_1',
    pmax=100,
    pmin=0,
    cost_curve=[[0, 0], [100, 0]],  # 零边际成本
    availability=[0.8, 0.9, 0.7],   # 不同时段的可用率
    startup_cost=0
)
```

#### 1.2 负载建模

```python
# 工业负载 - 相对稳定
industrial_load = simpower.Load(
    name='Industrial_Zone',
    schedule=[
        150, 155, 148, 152, 160, 165,  # 0-5时
        170, 180, 200, 210, 215, 220,  # 6-11时
        225, 230, 225, 220, 215, 210,  # 12-17时
        200, 185, 170, 165, 158, 152   # 18-23时
    ],
    priority=1          # 高优先级负载
)

# 居民负载 - 峰谷明显
residential_load = simpower.Load(
    name='Residential_Area',
    schedule=[
        80, 75, 70, 68, 70, 85,        # 深夜到清晨
        100, 120, 110, 95, 90, 95,     # 上午
        100, 95, 90, 95, 110, 140,     # 下午
        160, 150, 130, 110, 95, 85     # 晚间高峰
    ],
    priority=2
)

# 可中断负载 - 可以削减
interruptible_load = simpower.Load(
    name='Pumping_Station',
    schedule=[50] * 24,
    interruptible=True,
    interruption_cost=200  # 中断成本 ($/MWh)
)
```

#### 1.3 电网建模

```python
# 创建节点
bus1 = simpower.Bus(name='Bus_A', voltage_level=345)
bus2 = simpower.Bus(name='Bus_B', voltage_level=345)
bus3 = simpower.Bus(name='Bus_C', voltage_level=138)

# 创建输电线路
line1 = simpower.Line(
    name='Line_A_B',
    from_bus=bus1,
    to_bus=bus2,
    capacity=200,      # 传输容量 (MW)
    reactance=0.05,    # 电抗
    resistance=0.01    # 电阻
)

line2 = simpower.Line(
    name='Line_B_C',
    from_bus=bus2,
    to_bus=bus3,
    capacity=150,
    reactance=0.08,
    resistance=0.015
)

# 关联发电机和负载到节点
bus1.add_generator(coal_unit)
bus2.add_generator(gas_unit)
bus3.add_load(industrial_load)
```

### 2. 优化问题求解

#### 2.1 经济调度 (Economic Dispatch)

最基本的优化问题，在给定的负载下找到成本最小的发电方案：

```python
# 创建经济调度问题
ed_problem = simpower.EconomicDispatch()

# 添加发电机组
ed_problem.add_generators([coal_unit, gas_unit, wind_unit])

# 设置负载需求
ed_problem.set_load_demand(250)  # 250 MW

# 求解
ed_problem.solve()

# 查看结果
print("=== 经济调度结果 ===")
for gen in ed_problem.generators:
    power = gen.get_power_output()
    cost = gen.get_operating_cost()
    print(f"{gen.name}: {power:.1f} MW, 成本: {cost:.0f} $/h")

total_cost = ed_problem.get_total_cost()
print(f"系统总成本: {total_cost:.0f} $/h")

# 获取边际电价
lmp = ed_problem.get_marginal_price()
print(f"系统边际电价: {lmp:.2f} $/MWh")
```

#### 2.2 机组组合 (Unit Commitment)

考虑机组启停约束的多时段优化：

```python
# 创建24小时负载曲线
load_profile = [
    180, 170, 160, 155, 160, 175,  # 0-5时: 夜间低谷
    190, 220, 260, 280, 290, 300,  # 6-11时: 上午负载上升
    310, 305, 295, 300, 320, 350,  # 12-17时: 日间高峰
    380, 360, 320, 280, 240, 210   # 18-23时: 晚间高峰后回落
]

# 创建机组组合问题
uc_problem = simpower.UnitCommitment(horizon=24)

# 添加机组
uc_problem.add_generators([coal_unit, gas_unit, wind_unit])

# 设置负载曲线
uc_problem.set_load_profile(load_profile)

# 设置初始状态
initial_status = {
    'Coal_Unit_1': {'status': 1, 'hours_on': 5},  # 已运行5小时
    'Gas_Turbine_1': {'status': 0, 'hours_off': 2}, # 已停机2小时
    'Wind_Farm_1': {'status': 1, 'hours_on': 10}
}
uc_problem.set_initial_status(initial_status)

# 求解
uc_problem.solve()

# 分析结果
print("=== 24小时机组组合结果 ===")
print("时段  负载   Coal1  Gas1  Wind1  总成本   电价")
print("-" * 55)

for hour in range(24):
    load = load_profile[hour]
    coal_power = uc_problem.get_power(coal_unit, hour)
    gas_power = uc_problem.get_power(gas_unit, hour)
    wind_power = uc_problem.get_power(wind_unit, hour)
    cost = uc_problem.get_hourly_cost(hour)
    price = uc_problem.get_hourly_price(hour)
    
    print(f"{hour:2d}   {load:3.0f}   {coal_power:5.1f}  {gas_power:5.1f}  {wind_power:5.1f}  {cost:6.0f}  {price:6.2f}")
```

#### 2.3 最优潮流 (Optimal Power Flow)

考虑网络约束的优化调度：

```python
# 创建多节点系统
network = simpower.PowerNetwork()

# 添加节点和设备
network.add_bus(bus1, generators=[coal_unit])
network.add_bus(bus2, generators=[gas_unit])  
network.add_bus(bus3, loads=[industrial_load])

# 添加线路
network.add_line(line1)
network.add_line(line2)

# 创建OPF问题
opf_problem = simpower.OptimalPowerFlow(network)

# 求解
opf_problem.solve()

# 分析网络结果
print("=== 最优潮流结果 ===")
print("\n节点信息:")
for bus in network.buses:
    voltage = opf_problem.get_voltage(bus)
    angle = opf_problem.get_angle(bus)
    lmp = opf_problem.get_lmp(bus)
    print(f"{bus.name}: 电压={voltage:.3f}pu, 相角={angle:.2f}°, LMP={lmp:.2f}$/MWh")

print("\n线路潮流:")
for line in network.lines:
    power_flow = opf_problem.get_power_flow(line)
    loading = abs(power_flow) / line.capacity * 100
    print(f"{line.name}: {power_flow:+6.1f}MW ({loading:4.1f}%)")
    
print("\n阻塞分析:")
congested_lines = opf_problem.get_congested_lines()
if congested_lines:
    for line in congested_lines:
        shadow_price = opf_problem.get_line_shadow_price(line)
        print(f"{line.name}: 阻塞影子价格 = {shadow_price:.2f} $/MW")
else:
    print("系统无阻塞")
```

### 3. 电力市场仿真

#### 3.1 现货市场仿真

```python
# 创建现货市场
spot_market = simpower.SpotMarket()

# 发电商投标
coal_bid = simpower.Bid(
    generator=coal_unit,
    quantity_price_pairs=[
        (50, 25.0),   # 50MW @ 25$/MWh
        (100, 28.0),  # 额外50MW @ 28$/MWh  
        (150, 32.0)   # 额外50MW @ 32$/MWh
    ]
)

gas_bid = simpower.Bid(
    generator=gas_unit,
    quantity_price_pairs=[
        (30, 40.0),
        (80, 45.0),
        (120, 52.0)
    ]
)

spot_market.submit_bids([coal_bid, gas_bid])

# 需求方投标
demand_bid = simpower.DemandBid(
    load=industrial_load,
    quantity_price_pairs=[
        (100, 80.0),  # 愿意为100MW支付80$/MWh
        (150, 60.0),  # 额外50MW愿支付60$/MWh
        (200, 40.0)   # 额外50MW愿支付40$/MWh
    ]
)

spot_market.submit_demand_bid(demand_bid)

# 市场出清
market_results = spot_market.clear_market()

print("=== 现货市场出清结果 ===")
print(f"出清电价: {market_results.clearing_price:.2f} $/MWh")
print(f"出清电量: {market_results.clearing_quantity:.0f} MW")

print("\n中标情况:")
for bid_result in market_results.accepted_bids:
    print(f"{bid_result.bidder}: {bid_result.quantity:.0f}MW @ {bid_result.price:.2f}$/MWh")

print(f"\n总交易金额: ${market_results.total_payment:,.0f}")
```

#### 3.2 备用市场

```python
# 创建备用市场
reserve_market = simpower.ReserveMarket()

# 系统备用需求 (通常为负载的10-15%)
reserve_requirement = 0.12 * sum(load_profile)

# 备用服务投标
coal_reserve_bid = simpower.ReserveBid(
    generator=coal_unit,
    available_capacity=50,  # 可提供50MW备用
    price=8.0              # 8$/MW的备用价格
)

gas_reserve_bid = simpower.ReserveBid(
    generator=gas_unit,
    available_capacity=40,
    price=12.0
)

reserve_market.submit_bids([coal_reserve_bid, gas_reserve_bid])
reserve_market.set_requirement(reserve_requirement)

# 备用市场出清
reserve_results = reserve_market.clear_market()

print("=== 备用市场结果 ===")
print(f"备用需求: {reserve_requirement:.0f} MW")
print(f"备用价格: {reserve_results.reserve_price:.2f} $/MW")

for provider in reserve_results.providers:
    revenue = provider.capacity * reserve_results.reserve_price
    print(f"{provider.generator.name}: {provider.capacity:.0f}MW, 收入: ${revenue:.0f}")
```

### 4. 高级功能和案例

#### 4.1 随机优化 - 风电不确定性

```python
# 风电出力预测和不确定性建模
wind_scenarios = [
    {'probability': 0.3, 'output': [30, 35, 40, 45, 50]},  # 高风力场景
    {'probability': 0.5, 'output': [20, 25, 28, 30, 32]},  # 中等风力场景  
    {'probability': 0.2, 'output': [5, 8, 10, 12, 15]}     # 低风力场景
]

# 创建随机机组组合
stochastic_uc = simpower.StochasticUnitCommitment()

# 设置场景
for scenario in wind_scenarios:
    stochastic_uc.add_scenario(
        probability=scenario['probability'],
        wind_output=scenario['output']
    )

# 求解鲁棒优化
stochastic_uc.solve()

print("=== 随机机组组合结果 ===")
print("考虑风电不确定性的鲁棒调度方案:")

for hour in range(5):
    print(f"\n时段 {hour+1}:")
    coal_commitment = stochastic_uc.get_first_stage_decision(coal_unit, hour)
    gas_commitment = stochastic_uc.get_first_stage_decision(gas_unit, hour)
    
    print(f"  第一阶段决策 - Coal: {coal_commitment}, Gas: {gas_commitment}")
    
    for i, scenario in enumerate(wind_scenarios):
        coal_power = stochastic_uc.get_second_stage_power(coal_unit, hour, i)
        gas_power = stochastic_uc.get_second_stage_power(gas_unit, hour, i)
        wind_power = scenario['output'][hour]
        
        print(f"  场景{i+1} (概率{scenario['probability']:.1f}): "
              f"Coal={coal_power:.1f}MW, Gas={gas_power:.1f}MW, Wind={wind_power}MW")
```

#### 4.2 多区域市场仿真

```python
# 创建多区域电力系统
region_north = simpower.Region(name='North')
region_south = simpower.Region(name='South')

# 北部区域 - 以火电为主
region_north.add_generators([
    simpower.Generator(name='Coal_N1', pmax=200, cost_curve=[[0, 20], [200, 30]]),
    simpower.Generator(name='Coal_N2', pmax=180, cost_curve=[[0, 22], [180, 32]])
])
region_north.add_load(simpower.Load(name='Load_N', schedule=[300]))

# 南部区域 - 以天然气和可再生能源为主
region_south.add_generators([
    simpower.Generator(name='Gas_S1', pmax=150, cost_curve=[[0, 35], [150, 45]]),
    simpower.Generator(name='Hydro_S1', pmax=100, cost_curve=[[0, 5], [100, 8]]),
    simpower.Generator(name='Solar_S1', pmax=80, cost_curve=[[0, 0], [80, 0]])
])
region_south.add_load(simpower.Load(name='Load_S', schedule=[250]))

# 区域间联络线
tie_line = simpower.TieLine(
    from_region=region_north,
    to_region=region_south,
    capacity=100,           # 传输容量
    loss_factor=0.03        # 线损率3%
)

# 创建多区域市场
multi_region_market = simpower.MultiRegionMarket([region_north, region_south])
multi_region_market.add_tie_line(tie_line)

# 求解
multi_region_market.solve()

print("=== 多区域市场结果 ===")
for region in [region_north, region_south]:
    print(f"\n{region.name}区域:")
    print(f"  本地发电: {region.get_local_generation():.0f} MW")
    print(f"  本地负载: {region.get_local_load():.0f} MW")
    print(f"  净流出: {region.get_net_export():.0f} MW")
    print(f"  区域电价: {region.get_lmp():.2f} $/MWh")

tie_flow = multi_region_market.get_tie_flow(tie_line)
print(f"\n联络线潮流: {tie_flow:+.0f} MW (North→South)")

# 阻塞收入分析
congestion_rent = multi_region_market.get_congestion_rent(tie_line)
print(f"阻塞收入: ${congestion_rent:.0f}")
```

#### 4.3 排放约束与碳市场

```python
# 添加排放特性
coal_unit_with_emission = simpower.Generator(
    name='Coal_Emission',
    pmax=300,
    cost_curve=[[0, 25], [300, 35]],
    emission_rate=0.9,      # 0.9 tCO2/MWh
    emission_type='CO2'
)

gas_unit_with_emission = simpower.Generator(
    name='Gas_Clean',
    pmax=200, 
    cost_curve=[[0, 40], [200, 50]],
    emission_rate=0.4,      # 0.4 tCO2/MWh
    emission_type='CO2'
)

# 创建带排放约束的优化
emission_constrained_uc = simpower.EmissionConstrainedUC()

# 设置排放限额
daily_emission_cap = 5000  # 5000 tCO2/day

emission_constrained_uc.add_generators([coal_unit_with_emission, gas_unit_with_emission])
emission_constrained_uc.set_emission_cap(daily_emission_cap)
emission_constrained_uc.set_load_profile(load_profile)

# 求解
emission_constrained_uc.solve()

print("=== 排放约束机组组合结果 ===")
total_emission = 0
total_cost = 0

for hour in range(24):
    coal_power = emission_constrained_uc.get_power(coal_unit_with_emission, hour)
    gas_power = emission_constrained_uc.get_power(gas_unit_with_emission, hour)
    
    hour_emission = coal_power * 0.9 + gas_power * 0.4
    total_emission += hour_emission
    
    hour_cost = emission_constrained_uc.get_hourly_cost(hour)
    total_cost += hour_cost
    
    if hour % 6 == 0:  # 每6小时打印一次
        print(f"时段{hour:2d}: Coal={coal_power:5.1f}MW, Gas={gas_power:5.1f}MW, "
              f"排放={hour_emission:5.1f}tCO2")

print(f"\n每日总排放: {total_emission:.0f} tCO2 (限额: {daily_emission_cap} tCO2)")
print(f"每日总成本: ${total_cost:,.0f}")

# 获取碳价格 (排放约束的影子价格)
carbon_price = emission_constrained_uc.get_emission_shadow_price()
print(f"隐含碳价格: ${carbon_price:.2f}/tCO2")
```

## 📊 结果分析和可视化

### 数据导出和分析

```python
import pandas as pd
import matplotlib.pyplot as plt

# 导出结果到DataFrame
results_df = simpower.export_results_to_dataframe(uc_problem)

# 基本统计分析
print("=== 系统运行统计 ===")
print(f"平均负载: {results_df['Load'].mean():.1f} MW")
print(f"峰值负载: {results_df['Load'].max():.1f} MW")
print(f"谷值负载: {results_df['Load'].min():.1f} MW")
print(f"平均电价: {results_df['LMP'].mean():.2f} $/MWh")
print(f"最高电价: {results_df['LMP'].max():.2f} $/MWh")

# 机组利用率分析
for gen_name in ['Coal_Unit_1', 'Gas_Turbine_1']:
    utilization = (results_df[f'{gen_name}_Power'].sum() / 
                  (results_df[f'{gen_name}_Status'].sum() * generators[0].pmax)) * 100
    capacity_factor = results_df[f'{gen_name}_Power'].sum() / (24 * generators[0].pmax) * 100
    print(f"{gen_name} 利用率: {utilization:.1f}%, 容量因子: {capacity_factor:.1f}%")
```

### 可视化图表

```python
# 创建多子图分析
fig, axes = plt.subplots(2, 2, figsize=(15, 10))

# 1. 负载和发电曲线
axes[0,0].plot(results_df.index, results_df['Load'], label='负载', linewidth=2)
axes[0,0].plot(results_df.index, results_df['Coal_Unit_1_Power'], label='火电')
axes[0,0].plot(results_df.index, results_df['Gas_Turbine_1_Power'], label='燃气')
axes[0,0].plot(results_df.index, results_df['Wind_Farm_1_Power'], label='风电')
axes[0,0].set_title('24小时负载与发电曲线')
axes[0,0].set_xlabel('时间 (小时)')
axes[0,0].set_ylabel('功率 (MW)')
axes[0,0].legend()
axes[0,0].grid(True)

# 2. 电价曲线
axes[0,1].plot(results_df.index, results_df['LMP'], color='red', linewidth=2)
axes[0,1].set_title('节点边际电价')
axes[0,1].set_xlabel('时间 (小时)')
axes[0,1].set_ylabel('电价 ($/MWh)')
axes[0,1].grid(True)

# 3. 机组状态
status_data = results_df[['Coal_Unit_1_Status', 'Gas_Turbine_1_Status']].T
axes[1,0].imshow(status_data, cmap='RdYlGn', aspect='auto')
axes[1,0].set_title('机组启停状态')
axes[1,0].set_xlabel('时间 (小时)')
axes[1,0].set_ylabel('机组')
axes[1,0].set_yticks([0, 1])
axes[1,0].set_yticklabels(['火电', '燃气'])

# 4. 成本分析
hourly_cost = results_df['Total_Cost'].diff().fillna(results_df['Total_Cost'].iloc[0])
axes[1,1].bar(results_df.index, hourly_cost)
axes[1,1].set_title('小时发电成本')
axes[1,1].set_xlabel('时间 (小时)')
axes[1,1].set_ylabel('成本 ($/h)')
axes[1,1].grid(True)

plt.tight_layout()
plt.savefig('simpower_analysis.png', dpi=300)
plt.show()
```

## 🔧 配置和自定义

### 求解器配置

```python
# 配置求解器选项
simpower.config.solver = 'cbc'              # 使用CBC求解器
simpower.config.solver_options = {
    'seconds': 300,                          # 求解时间限制
    'gap': 0.01,                            # MIP gap容差
    'threads': 4                            # 并行线程数
}

# 启用对偶变量计算
simpower.config.duals = True

# 启用详细日志
simpower.config.logging_level = 'INFO'

# 保存问题文件用于调试
simpower.config.keep_lp_files = True
```

### 自定义约束

```python
# 添加自定义约束
def ramp_constraint(model, gen, t):
    """自定义爬坡约束"""
    if t > 0:
        return model.power[gen, t] - model.power[gen, t-1] <= gen.ramp_up_rate
    else:
        return pyo.Constraint.Skip

# 注册约束
uc_problem.add_custom_constraint('ramp_up', ramp_constraint)

# 添加自定义目标函数项
def emission_penalty(model):
    """排放惩罚项"""
    return sum(gen.emission_rate * model.power[gen, t] 
               for gen in model.generators for t in model.time_periods) * carbon_price

uc_problem.add_objective_term('emission_cost', emission_penalty)
```

## 📚 学习资源

### 理论基础
- 电力系统经济学
- 电力市场理论
- 优化理论和方法
- 电力系统运行与控制

### 推荐阅读
1. "Power System Economics" - Steven Stoft
2. "Electricity Markets: Pricing, Structures and Economics" - Chris Harris  
3. "Power Generation, Operation, and Control" - Wood & Wollenberg
4. "Convex Optimization" - Boyd & Vandenberghe

### 在线资源
- [项目文档](https://github.com/WhitejadeHang/power_market_sim)
- [API参考](https://github.com/WhitejadeHang/power_market_sim/wiki)
- [示例代码](https://github.com/WhitejadeHang/power_market_sim/examples)

## 🤝 贡献指南

我们欢迎社区贡献！请参考以下步骤：

1. Fork 项目仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交Pull Request

### 代码规范
- 遵循PEP 8 Python代码规范
- 添加适当的文档字符串
- 编写单元测试
- 更新相关文档

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

感谢所有为本项目贡献代码、文档和建议的开发者和研究人员。

## 📞 联系方式

- **项目主页**: https://github.com/WhitejadeHang/power_market_sim
- **问题反馈**: https://github.com/WhitejadeHang/power_market_sim/issues
- **讨论**: https://github.com/WhitejadeHang/power_market_sim/discussions

---

**Simpower - 让电力系统优化和市场仿真变得简单而强大！** ⚡