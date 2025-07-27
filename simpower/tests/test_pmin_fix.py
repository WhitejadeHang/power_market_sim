#!/usr/bin/env python3
"""
测试Pmin修复是否生效
"""

import os
import sys
import pandas as pd
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def test_simple_case():
    """创建最简单的测试案例"""
    
    # 使用原始demo
    source_dir = 'simpower/tests/ieee14_demo'
    test_dir = 'simpower/tests/test_pmin_fix'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 只保留前2个时段
    for file in os.listdir(test_dir):
        if file.endswith('_timeseries.csv'):
            ts_df = pd.read_csv(os.path.join(test_dir, file))
            ts_df = ts_df.iloc[:2]
            ts_df.to_csv(os.path.join(test_dir, file), index=False)
    
    # 读取发电机
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    
    # 设置Pmin为50%
    gen_df['P min'] = gen_df['P max'] * 0.5
    gen_df['minuptime'] = 1
    gen_df['mindowntime'] = 1
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    print("发电机参数:")
    print(gen_df[['name', 'P min', 'P max']])
    print(f"\n总Pmin: {gen_df['P min'].sum()} MW")
    
    # 创建初始状态 - 测试不同的初始功率值
    test_cases = [
        {"desc": "初始功率=0（应该被修正为Pmin）", "power": 0},
        {"desc": "初始功率=Pmin", "power": "pmin"},
        {"desc": "初始功率=Pmin*1.5", "power": 1.5},
    ]
    
    for test in test_cases:
        print(f"\n{'='*60}")
        print(f"测试: {test['desc']}")
        print(f"{'='*60}")
        
        initial_data = []
        for _, gen in gen_df.iterrows():
            if test['power'] == "pmin":
                power = gen['P min']
            elif isinstance(test['power'], (int, float)) and test['power'] < 1:
                power = test['power']
            else:
                power = gen['P min'] * test['power']
                
            initial_data.append({
                'name': gen['name'],
                'status': 1,  # 所有机组开机
                'power': power,
                'hoursinstatus': 1
            })
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        print("初始状态:")
        print(initial_df[['name', 'status', 'power']])
        
        # 尝试求解
        try:
            solution = solve_problem(test_dir)
            print("\n✅ 求解成功！")
            
            # 检查第一时段的出力
            if hasattr(solution, 'generators_power'):
                print(f"\n第一时段出力:")
                print(solution.generators_power[0])
                
        except Exception as e:
            print(f"\n❌ 求解失败: {e}")
    
    # 清理
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    print("🔍 测试Pmin修复\n")
    test_simple_case()