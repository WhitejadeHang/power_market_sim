#!/usr/bin/env python3
"""
修正lines.csv列名
"""

import pandas as pd
import os

case_dir = 'simpower/tests/ieee14_demo'

# 修正lines.csv
lines_df = pd.read_csv(os.path.join(case_dir, 'lines.csv'))

# 重命名列
column_mapping = {
    'from bus': 'frombus',
    'to bus': 'tobus',
    'line_capacity': 'pmax',
    'resistance': 'r',  # 可能不需要
    'emergency_capacity': 'emergency'  # 可能不需要
}

for old_col, new_col in column_mapping.items():
    if old_col in lines_df.columns:
        lines_df = lines_df.rename(columns={old_col: new_col})

# 只保留必要的列
required_cols = ['name', 'frombus', 'tobus', 'reactance', 'pmax']
lines_df = lines_df[required_cols]

lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
print("✅ 修正 lines.csv")
print(f"列名: {list(lines_df.columns)}")