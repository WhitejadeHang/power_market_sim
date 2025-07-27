#!/usr/bin/env python3
"""
逐步添加发电机测试
"""

import os
import sys
import pandas as pd
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def test_with_generators(include_g8=False, include_g9=False):
    """测试不同的发电机组合"""
    
    # 复制原始demo
    source_dir = 'simpower/tests/ieee14_demo'
    test_dir = 'simpower/tests/test_gen_combination'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 读取发电机
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    
    # 可选添加G8
    if include_g8:
        new_gen = pd.DataFrame([{
            'name': 'G8',
            'bus': 'Bus13',
            'P min': 0,
            'P max': 70,
            'rampratemax': 70,
            'rampratemin': -70,
            'startupcost': 1400,
            'shutdowncost': 700,
            'minuptime': 0,
            'mindowntime': 0,
            'costcurvepointsfilename': 'G8_block_bid.csv'
        }])
        gen_df = pd.concat([gen_df, new_gen], ignore_index=True)
        
        # 创建G8报价文件
        bid_df = pd.DataFrame({
            'power': [0, 21, 42, 70],
            'cost': [0, 2100, 6300, 14000]
        })
        bid_df.to_csv(f'{test_dir}/G8_block_bid.csv', index=False)
    
    # 可选添加G9
    if include_g9:
        new_gen = pd.DataFrame([{
            'name': 'G9',
            'bus': 'Bus14',
            'P min': 0,
            'P max': 90,
            'rampratemax': 90,
            'rampratemin': -90,
            'startupcost': 1800,
            'shutdowncost': 900,
            'minuptime': 0,
            'mindowntime': 0,
            'costcurvepointsfilename': 'G9_block_bid.csv'
        }])
        gen_df = pd.concat([gen_df, new_gen], ignore_index=True)
        
        # 创建G9报价文件
        bid_df = pd.DataFrame({
            'power': [0, 27, 54, 90],
            'cost': [0, 2700, 8100, 18000]
        })
        bid_df.to_csv(f'{test_dir}/G9_block_bid.csv', index=False)
    
    # 保存发电机文件
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    # 只保留2时段
    for file in os.listdir(test_dir):
        if file.endswith('_timeseries.csv'):
            ts_df = pd.read_csv(os.path.join(test_dir, file))
            ts_df = ts_df.iloc[:2]
            ts_df.to_csv(os.path.join(test_dir, file), index=False)
    
    # 创建初始状态
    initial_data = []
    for _, gen in gen_df.iterrows():
        initial_data.append({
            'name': gen['name'],
            'status': 1,
            'power': 0,
            'hoursinstatus': 1
        })
    
    initial_df = pd.DataFrame(initial_data)
    initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
    
    # 描述测试
    desc = f"7台机组"
    if include_g8:
        desc += "+G8"
    if include_g9:
        desc += "+G9"
    
    print(f"\n{'='*60}")
    print(f"测试: {desc}")
    print(f"{'='*60}")
    
    # 尝试求解
    try:
        solution = solve_problem(test_dir)
        print(f"✅ {desc} 求解成功！")
        return True
    except Exception as e:
        print(f"❌ {desc} 求解失败: {e}")
        return False


def main():
    """主函数"""
    
    print("🔍 逐步添加发电机测试\n")
    
    # 测试不同组合
    test_with_generators(False, False)  # 原始7台
    test_with_generators(True, False)   # 7+G8
    test_with_generators(False, True)   # 7+G9
    test_with_generators(True, True)    # 7+G8+G9


if __name__ == "__main__":
    main()