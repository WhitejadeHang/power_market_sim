#!/usr/bin/env python3
"""
修复120时段案例，确保能够求解
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

case_dir = 'simpower/tests/ieee14_120periods_coal'

print("🔧 修复IEEE 14节点120时段案例\n")

# 1. 读取并调整发电机参数
gen_df = pd.read_csv(f'{case_dir}/generators.csv')

# 降低所有机组的Pmin
print("📊 调整发电机参数:")
gen_df['P min'] = gen_df['P max'] * 0.2  # 降低到20%
gen_df.to_csv(f'{case_dir}/generators.csv', index=False)

print(gen_df[['name', 'P min', 'P max', 'minuptime', 'mindowntime']])
total_pmin = gen_df['P min'].sum()
total_pmax = gen_df['P max'].sum()
print(f"\n新的总容量: Pmin={total_pmin} MW, Pmax={total_pmax} MW")

# 2. 调整初始状态 - 让更多机组开机
print("\n\n⚡ 调整初始状态:")

# 新策略：前8台机组开机，只有G9停机
online_units = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8']  # 8台开机
offline_units = ['G9']  # 1台停机

initial_states = []
online_pmin = 0
online_pmax = 0

for _, gen in gen_df.iterrows():
    if gen['name'] in online_units:
        status = 1
        power = gen['P min'] * 1.5  # 初始出力为Pmin的150%
        if power > gen['P max']:
            power = gen['P max'] * 0.5
        hoursinstatus = gen['minuptime'] + 2
        
        online_pmin += gen['P min']
        online_pmax += gen['P max']
    else:
        status = 0
        power = 0
        hoursinstatus = -(gen['mindowntime'] + 2)
    
    initial_states.append({
        'name': gen['name'],
        'status': status,
        'power': power,
        'hoursinstatus': int(hoursinstatus)
    })

initial_df = pd.DataFrame(initial_states)
initial_df.to_csv(f'{case_dir}/initial.csv', index=False)

print("初始状态:")
print(initial_df)
print(f"\n在线机组: {len(online_units)}台")
print(f"在线Pmin: {online_pmin} MW")
print(f"在线Pmax: {online_pmax} MW")

# 3. 检查负荷范围
print("\n\n📈 检查负荷:")

# 读取所有负荷时序文件
loads_df = pd.read_csv(f'{case_dir}/loads.csv')
total_loads = np.zeros(120)

for _, load in loads_df.iterrows():
    load_name = load['name']
    ts_df = pd.read_csv(f'{case_dir}/{load_name}_timeseries.csv')
    total_loads += ts_df['power'].values[:120]

min_load = total_loads.min()
max_load = total_loads.max()

print(f"负荷范围: {min_load:.1f} - {max_load:.1f} MW")
print(f"在线容量裕度: 最小 {online_pmin - min_load:.1f} MW, 最大 {online_pmax - max_load:.1f} MW")

# 4. 重新生成报价文件（适应新的Pmin）
print("\n\n💰 更新报价文件:")

# 基础价格设置
base_prices = {
    'G1': 50, 'G2': 55, 'G3': 60,  # 大型基荷
    'G4': 80, 'G5': 85, 'G6': 90,  # 中型
    'G7': 120, 'G8': 130, 'G9': 140  # 小型调峰
}

for _, gen in gen_df.iterrows():
    gen_name = gen['name']
    pmin = gen['P min']
    pmax = gen['P max']
    
    # 基础价格
    base_price = base_prices.get(gen_name, 100)
    
    # 4段报价
    power_points = [
        pmin,
        pmin + (pmax - pmin) * 0.33,
        pmin + (pmax - pmin) * 0.67,
        pmax
    ]
    
    # 边际成本递增
    marginal_costs = [
        base_price,
        base_price * 1.2,
        base_price * 1.5,
        base_price * 2.0
    ]
    
    # 计算累积成本
    costs = [0.0]
    for i in range(1, len(power_points)):
        power_increment = power_points[i] - power_points[i-1]
        cost_increment = power_increment * marginal_costs[i-1]
        costs.append(costs[-1] + cost_increment)
    
    # 保存报价文件
    bid_df = pd.DataFrame({
        'power': power_points,
        'cost': costs
    })
    bid_df.to_csv(f'{case_dir}/{gen_name}_block_bid.csv', index=False)

print("✅ 所有报价文件已更新")

# 5. 验证可行性
print("\n\n✅ 可行性检查:")

if online_pmin > min_load:
    print(f"⚠️ 警告: 在线Pmin ({online_pmin:.1f}) > 最小负荷 ({min_load:.1f})")
    print("建议: 进一步降低Pmin或增加负荷")
else:
    print(f"✅ 通过: 在线Pmin ({online_pmin:.1f}) < 最小负荷 ({min_load:.1f})")

if online_pmax < max_load:
    print(f"❌ 错误: 在线Pmax ({online_pmax:.1f}) < 最大负荷 ({max_load:.1f})")
    print("需要: 增加在线机组或降低最大负荷")
else:
    print(f"✅ 通过: 在线Pmax ({online_pmax:.1f}) > 最大负荷 ({max_load:.1f})")

print("\n🎯 修复完成！")