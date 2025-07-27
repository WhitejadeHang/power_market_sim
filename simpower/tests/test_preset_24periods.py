#!/usr/bin/env python3
"""
测试预设案例的24时段版本
"""

import os
import sys
import shutil
import pandas as pd
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem

# 创建24时段版本
source_dir = 'simpower/tests/ieee14_120periods_preset'
test_dir = 'simpower/tests/ieee14_24periods_preset'

if os.path.exists(test_dir):
    shutil.rmtree(test_dir)
shutil.copytree(source_dir, test_dir)

# 截取前24时段
loads_df = pd.read_csv(f'{test_dir}/loads.csv')
for _, load in loads_df.iterrows():
    load_name = load['name']
    ts_df = pd.read_csv(f'{test_dir}/{load_name}_timeseries.csv')
    ts_df = ts_df.iloc[:24]  # 只保留前24时段
    ts_df.to_csv(f'{test_dir}/{load_name}_timeseries.csv', index=False)

# 更新预设方案
with open(f'{test_dir}/preset_solution.json', 'r') as f:
    preset = json.load(f)

preset['unit_status'] = [row[:24] for row in preset['unit_status']]
preset['unit_power'] = [row[:24] for row in preset['unit_power']]
preset['system_loads'] = preset['system_loads'][:24]

with open(f'{test_dir}/preset_solution.json', 'w') as f:
    json.dump(preset, f, indent=2)

print("🧪 测试24时段预设案例...")
print(f"案例目录: {test_dir}")

# 放松最小开停机时间约束
gen_df = pd.read_csv(f'{test_dir}/generators.csv')
gen_df['minuptime'] = gen_df['minuptime'].apply(lambda x: min(x, 6))
gen_df['mindowntime'] = gen_df['mindowntime'].apply(lambda x: min(x, 6))
gen_df.to_csv(f'{test_dir}/generators.csv', index=False)

print("\n调整后的机组参数:")
print(gen_df[['name', 'P min', 'P max', 'minuptime', 'mindowntime']])

# 尝试求解
try:
    print("\n开始求解...")
    solution = solve_problem(test_dir)
    print("✅ 24时段求解成功！")
    
    if hasattr(solution, 'objective'):
        print(f"总成本: ${solution.objective:,.2f}")
    
except Exception as e:
    print(f"❌ 求解失败: {e}")

# 清理
if os.path.exists(test_dir):
    shutil.rmtree(test_dir)