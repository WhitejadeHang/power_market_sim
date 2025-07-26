#!/usr/bin/env python3
"""
修正IEEE 14节点案例的列名格式
"""

import pandas as pd
import os

case_dir = 'simpower/tests/ieee14_12periods'

# 修正generators.csv
gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))

# 重命名列
column_mapping = {
    'ramp rate': 'rampratemax',
    'start cost': 'startupcost', 
    'shut cost': 'shutdowncost',
    'min run time': 'minuptime',
    'min stop time': 'mindowntime',
    'no load cost': 'noloadcost',
    'bid_type': 'bidtype',
    'min_bid_quantity': 'min bid quantity'
}

for old_col, new_col in column_mapping.items():
    if old_col in gen_df.columns:
        gen_df = gen_df.rename(columns={old_col: new_col})

# 添加必要的列
if 'rampratemin' not in gen_df.columns:
    gen_df['rampratemin'] = -gen_df['rampratemax']

# 移除不支持的列
cols_to_remove = ['fuel', 'bidtype', 'min bid quantity']
for col in cols_to_remove:
    if col in gen_df.columns:
        gen_df = gen_df.drop(columns=[col])

gen_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
print("✅ 修正 generators.csv")

# 验证修正后的列名
print("\n修正后的列名:")
print(list(gen_df.columns))