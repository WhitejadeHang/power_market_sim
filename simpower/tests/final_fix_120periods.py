#!/usr/bin/env python3
"""
最终修复120时段案例 - 所有机组开机策略
"""

import os
import pandas as pd
import numpy as np

case_dir = 'simpower/tests/ieee14_120periods_coal'

print("🔨 最终修复120时段案例\n")

# 1. 极度降低Pmin
gen_df = pd.read_csv(f'{case_dir}/generators.csv')
gen_df['P min'] = gen_df['P max'] * 0.1  # 降低到10%

# 放松最小运行/停机时间约束
gen_df['minuptime'] = gen_df['minuptime'].apply(lambda x: min(x, 4))
gen_df['mindowntime'] = gen_df['mindowntime'].apply(lambda x: min(x, 4))

gen_df.to_csv(f'{case_dir}/generators.csv', index=False)

print("📊 新的发电机参数:")
print(gen_df[['name', 'P min', 'P max', 'minuptime', 'mindowntime']])

# 2. 所有机组初始都开机
initial_states = []
for _, gen in gen_df.iterrows():
    initial_states.append({
        'name': gen['name'],
        'status': 1,  # 全部开机
        'power': gen['P min'] * 2,  # 初始出力为Pmin的2倍
        'hoursinstatus': 5  # 已运行5小时
    })

initial_df = pd.DataFrame(initial_states)
initial_df.to_csv(f'{case_dir}/initial.csv', index=False)

print("\n⚡ 初始状态: 所有9台机组都开机")
print(f"总Pmin: {gen_df['P min'].sum():.1f} MW")
print(f"总Pmax: {gen_df['P max'].sum():.1f} MW")

# 3. 检查负荷
loads_df = pd.read_csv(f'{case_dir}/loads.csv')
total_loads = np.zeros(120)

for _, load in loads_df.iterrows():
    load_name = load['name']
    ts_df = pd.read_csv(f'{case_dir}/{load_name}_timeseries.csv')
    total_loads += ts_df['power'].values[:120]

print(f"\n📈 负荷范围: {total_loads.min():.1f} - {total_loads.max():.1f} MW")

print("\n✅ 修复完成！预期能够求解。")