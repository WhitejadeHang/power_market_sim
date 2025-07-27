#!/usr/bin/env python3
"""
测试较短时段，找出最大可解时段数
"""

import os
import sys
import shutil
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
from simpower.solve import solve_problem

# 测试不同的时段数
test_periods = [24, 48, 72, 96, 120]

for periods in test_periods:
    print(f"\n{'='*60}")
    print(f"🧪 测试 {periods} 时段...")
    
    # 创建临时目录
    source_dir = 'simpower/tests/ieee14_120periods_coal'
    test_dir = f'simpower/tests/test_{periods}periods'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 截取负荷时序到指定时段
    loads_df = pd.read_csv(f'{test_dir}/loads.csv')
    for _, load in loads_df.iterrows():
        load_name = load['name']
        ts_df = pd.read_csv(f'{test_dir}/{load_name}_timeseries.csv')
        ts_df = ts_df.iloc[:periods]  # 只保留前N个时段
        ts_df.to_csv(f'{test_dir}/{load_name}_timeseries.csv', index=False)
    
    # 尝试求解
    try:
        print(f"开始求解...")
        solution = solve_problem(test_dir)
        print(f"✅ {periods} 时段求解成功！")
        
        # 统计启停
        if hasattr(solution, 'generators_status'):
            startups = 0
            shutdowns = 0
            n_gens = len(solution.generators_status[0])
            
            for g in range(n_gens):
                for t in range(1, periods):
                    if solution.generators_status[t-1][g] == 0 and solution.generators_status[t][g] == 1:
                        startups += 1
                    elif solution.generators_status[t-1][g] == 1 and solution.generators_status[t][g] == 0:
                        shutdowns += 1
            
            print(f"   启动次数: {startups}, 停机次数: {shutdowns}")
        
    except Exception as e:
        print(f"❌ {periods} 时段求解失败: {str(e)[:50]}...")
    
    finally:
        # 清理临时目录
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)

print(f"\n{'='*60}")
print("测试完成！")