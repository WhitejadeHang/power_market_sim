#!/usr/bin/env python3
"""
调试不可行性问题
"""

import os
import sys
import pandas as pd
import numpy as np
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def analyze_case(case_dir):
    """分析案例的基本信息"""
    
    print(f"\n分析案例: {case_dir}")
    print("=" * 60)
    
    # 读取数据
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    lines_df = pd.read_csv(f'{case_dir}/lines.csv')
    
    # 读取初始状态
    if os.path.exists(f'{case_dir}/initial.csv'):
        initial_df = pd.read_csv(f'{case_dir}/initial.csv')
        
        # 初始开机机组
        online_gens = initial_df[initial_df['status'] == 1]['name'].tolist()
        offline_gens = initial_df[initial_df['status'] == 0]['name'].tolist()
        
        print(f"\n初始状态:")
        print(f"开机机组: {online_gens}")
        print(f"停机机组: {offline_gens}")
        
        # 计算容量
        online_cap = gen_df[gen_df['name'].isin(online_gens)]['P max'].sum()
        online_min = gen_df[gen_df['name'].isin(online_gens)]['P min'].sum()
        
        print(f"\n初始开机容量: {online_cap} MW")
        print(f"初始最小出力: {online_min} MW")
    
    # 分析负荷
    print(f"\n负荷分析:")
    
    # 单时段负荷
    if 'power' in pd.read_csv(f'{case_dir}/loads.csv').columns:
        loads_df = pd.read_csv(f'{case_dir}/loads.csv')
        total_load = loads_df['power'].sum()
        print(f"单时段总负荷: {total_load} MW")
    else:
        # 多时段负荷
        total_loads = []
        for file in os.listdir(case_dir):
            if file.startswith('Load') and file.endswith('_timeseries.csv'):
                ts_df = pd.read_csv(os.path.join(case_dir, file))
                total_loads.append(ts_df['power'].values)
        
        if total_loads:
            total_loads = np.sum(total_loads, axis=0)
            print(f"时段数: {len(total_loads)}")
            print(f"负荷范围: {min(total_loads):.1f} - {max(total_loads):.1f} MW")
            print(f"前5时段负荷: {total_loads[:5]}")
    
    # 检查线路容量
    print(f"\n线路容量:")
    print(f"容量范围: {lines_df['pmax'].min()} - {lines_df['pmax'].max()} MW")
    
    # 检查发电机参数
    print(f"\n发电机参数:")
    print(f"总容量: {gen_df['P max'].sum()} MW")
    print(f"总最小出力: {gen_df['P min'].sum()} MW")
    print(f"最小开停机时间: {gen_df['minuptime'].max()}/{gen_df['mindowntime'].max()} 小时")


def create_minimal_test():
    """创建最小测试案例"""
    
    print("\n创建最小2时段测试案例...")
    
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    test_dir = 'simpower/tests/minimal_2period_test'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 修改发电机 - 完全放松
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    gen_df['P min'] = 0
    gen_df['minuptime'] = 0
    gen_df['mindowntime'] = 0
    gen_df['rampratemax'] = 1000
    gen_df['rampratemin'] = -1000
    gen_df['startupcost'] = 0
    gen_df['shutdowncost'] = 0
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    # 创建非常低的负荷
    for file in os.listdir(test_dir):
        if file.endswith('_timeseries.csv'):
            # 创建2时段低负荷
            ts_df = pd.DataFrame({
                'time': ['2025-01-15 00:00:00', '2025-01-15 01:00:00'],
                'power': [5.0, 5.0]  # 每个负荷只有5MW
            })
            ts_df.to_csv(os.path.join(test_dir, file), index=False)
    
    # 初始状态 - 全部开机
    initial_data = []
    for _, gen in gen_df.iterrows():
        initial_data.append({
            'name': gen['name'],
            'status': 1,
            'power': 0,
            'hoursinstatus': 0
        })
    
    initial_df = pd.DataFrame(initial_data)
    initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
    
    print("最小测试案例创建完成")
    
    # 分析案例
    analyze_case(test_dir)
    
    # 尝试求解
    print("\n尝试求解最小案例...")
    try:
        from simpower.solve import solve_problem
        solution = solve_problem(test_dir)
        print("✅ 最小案例求解成功！")
        return True
    except Exception as e:
        print(f"❌ 最小案例求解失败: {e}")
        return False


def main():
    # 分析原始案例
    analyze_case('simpower/tests/ieee14_24periods_coal')
    
    # 创建最小测试
    if create_minimal_test():
        print("\n✅ 找到了可行解！现在可以逐步增加复杂度")
    else:
        print("\n❌ 即使最小案例也无法求解，可能存在其他问题")


if __name__ == "__main__":
    main()