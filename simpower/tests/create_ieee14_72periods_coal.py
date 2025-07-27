#!/usr/bin/env python3
"""
创建IEEE 14节点3天72时段煤电案例
"""

import os
import shutil
import pandas as pd
import numpy as np

print("🔨 创建IEEE 14节点3天72时段煤电案例\n")

# 复制120时段案例
source_dir = 'simpower/tests/ieee14_120periods_coal'
target_dir = 'simpower/tests/ieee14_72periods_coal'

if os.path.exists(target_dir):
    shutil.rmtree(target_dir)
shutil.copytree(source_dir, target_dir)

# 截取前72时段的负荷
loads_df = pd.read_csv(f'{target_dir}/loads.csv')

for _, load in loads_df.iterrows():
    load_name = load['name']
    ts_df = pd.read_csv(f'{target_dir}/{load_name}_timeseries.csv')
    ts_df = ts_df.iloc[:72]  # 只保留前72个时段
    ts_df.to_csv(f'{target_dir}/{load_name}_timeseries.csv', index=False)

# 分析负荷范围
total_loads = np.zeros(72)
for _, load in loads_df.iterrows():
    load_name = load['name']
    ts_df = pd.read_csv(f'{target_dir}/{load_name}_timeseries.csv')
    total_loads += ts_df['power'].values

print("📊 3天72时段负荷统计:")
print(f"  最小负荷: {total_loads.min():.1f} MW")
print(f"  最大负荷: {total_loads.max():.1f} MW")
print(f"  平均负荷: {total_loads.mean():.1f} MW")

# 读取发电机信息
gen_df = pd.read_csv(f'{target_dir}/generators.csv')
print(f"\n⚡ 发电机总容量:")
print(f"  Pmin: {gen_df['P min'].sum():.1f} MW")
print(f"  Pmax: {gen_df['P max'].sum():.1f} MW")

print(f"\n✅ 3天72时段案例创建完成！")
print(f"📁 案例目录: {target_dir}")