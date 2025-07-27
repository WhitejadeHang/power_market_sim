#!/usr/bin/env python3
"""
简化的minuptime/mindowntime测试
"""

import os
import sys
import pandas as pd
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def test_constraint_boundary():
    """测试约束边界"""
    
    print("🔍 测试minuptime/mindowntime约束边界\n")
    
    # 基础案例目录
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    
    # 测试配置 - 从简单到复杂
    test_configs = [
        # (描述, 时段数, minuptime, mindowntime, 初始开机台数)
        ("无约束_6时段", 6, 0, 0, 6),
        ("无约束_12时段", 12, 0, 0, 6),
        ("无约束_24时段", 24, 0, 0, 6),
        
        ("约束1_6时段", 6, 1, 1, 6),
        ("约束1_12时段", 12, 1, 1, 6),
        ("约束1_24时段", 24, 1, 1, 6),
        
        # 测试不同初始状态
        ("约束1_12时段_全开", 12, 1, 1, 9),
        ("约束1_12时段_部分开", 12, 1, 1, 4),
        
        # 测试只有mindowntime
        ("仅停机约束_12时段", 12, 0, 1, 6),
        ("仅停机约束_12时段_全开", 12, 0, 1, 9),
    ]
    
    results = []
    
    for desc, periods, minuptime, mindowntime, init_online in test_configs:
        print(f"\n{'='*60}")
        print(f"测试: {desc}")
        print(f"  时段: {periods}, minup: {minuptime}, mindown: {mindowntime}, 初始开机: {init_online}")
        
        # 创建测试目录
        test_dir = f'simpower/tests/test_{desc.replace(" ", "_").replace("/", "_")}'
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        shutil.copytree(source_dir, test_dir)
        
        try:
            # 修改发电机参数
            gen_df = pd.read_csv(f'{test_dir}/generators.csv')
            gen_df['minuptime'] = minuptime
            gen_df['mindowntime'] = mindowntime
            gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
            
            # 调整初始状态
            initial_data = []
            sorted_gens = gen_df.sort_values('P max', ascending=False)
            
            for idx, (_, gen) in enumerate(sorted_gens.iterrows()):
                if idx < init_online:
                    status = 1
                    power = gen['P min']
                    hoursinstatus = max(minuptime, 1)
                else:
                    status = 0
                    power = 0
                    hoursinstatus = -max(mindowntime, 1)
                
                initial_data.append({
                    'name': gen['name'],
                    'status': status,
                    'power': power,
                    'hoursinstatus': int(hoursinstatus)
                })
            
            initial_df = pd.DataFrame(initial_data)
            initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
            
            # 如果需要调整时段
            if periods < 24:
                for file in os.listdir(test_dir):
                    if file.endswith('_timeseries.csv'):
                        ts_df = pd.read_csv(os.path.join(test_dir, file))
                        ts_df = ts_df.iloc[:periods]
                        ts_df.to_csv(os.path.join(test_dir, file), index=False)
            
            # 计算初始状态的总Pmin
            online_gens = initial_df[initial_df['status'] == 1]
            init_pmin = 0
            for _, irow in online_gens.iterrows():
                gen_data = gen_df[gen_df['name'] == irow['name']]
                if not gen_data.empty:
                    init_pmin += gen_data['P min'].values[0]
            
            print(f"  初始在线Pmin: {init_pmin:.1f} MW")
            
            # 读取负荷
            loads_df = pd.read_csv(f'{test_dir}/loads.csv')
            min_load = float('inf')
            max_load = 0
            
            for _, load in loads_df.iterrows():
                ts_file = f'{test_dir}/{load["name"]}_timeseries.csv'
                if os.path.exists(ts_file):
                    ts_df = pd.read_csv(ts_file)
                    min_load = min(min_load, ts_df['power'].min())
                    max_load = max(max_load, ts_df['power'].max())
            
            print(f"  负荷范围: {min_load:.1f} - {max_load:.1f} MW")
            
            # 求解
            solution = solve_problem(test_dir)
            
            print(f"  ✅ 求解成功!")
            
            results.append({
                'test': desc,
                'periods': periods,
                'minuptime': minuptime,
                'mindowntime': mindowntime,
                'init_online': init_online,
                'status': 'Success',
                'init_pmin': init_pmin,
                'min_load': min_load
            })
            
        except Exception as e:
            error_msg = str(e)
            if "failed to solve with shedding" in error_msg:
                print(f"  ❌ 机组组合不可行")
            else:
                print(f"  ❌ 错误: {error_msg[:100]}")
            
            results.append({
                'test': desc,
                'periods': periods,
                'minuptime': minuptime,
                'mindowntime': mindowntime,
                'init_online': init_online,
                'status': 'Failed',
                'error': error_msg[:100]
            })
        
        finally:
            # 清理
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
    
    # 汇总
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    for r in results:
        status = "✅" if r['status'] == 'Success' else "❌"
        print(f"{status} {r['test']:30} minup={r['minuptime']} mindown={r['mindowntime']} init={r['init_online']}")
    
    # 分析成功边界
    success_results = [r for r in results if r['status'] == 'Success']
    if success_results:
        print(f"\n✅ 成功案例数: {len(success_results)}")
        max_minup = max(r['minuptime'] for r in success_results)
        max_mindown = max(r['mindowntime'] for r in success_results)
        print(f"   最大成功minuptime: {max_minup}")
        print(f"   最大成功mindowntime: {max_mindown}")


def test_specific_case():
    """测试特定案例以理解失败原因"""
    
    print("\n\n🔍 深入分析特定失败案例")
    print("="*60)
    
    # 创建一个最小负荷很低的案例
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    test_dir = 'simpower/tests/test_specific_case'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 只测试6时段
    periods = 6
    
    # 读取发电机
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    gen_df['minuptime'] = 1
    gen_df['mindowntime'] = 1
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    print(f"发电机总Pmin: {gen_df['P min'].sum():.1f} MW")
    print(f"发电机总Pmax: {gen_df['P max'].sum():.1f} MW")
    
    # 创建特殊负荷曲线 - 前3时段低负荷，后3时段高负荷
    load_pattern = [0.55, 0.53, 0.52, 0.85, 0.90, 0.88]  # 负荷因子
    base_load = gen_df['P max'].sum() * 0.6  # 基准负荷
    
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(periods)]
    
    buses_df = pd.read_csv(f'{test_dir}/buses.csv')
    loads_df = pd.read_csv(f'{test_dir}/loads.csv')
    total_base_demand = buses_df['real_power_demand'].sum()
    
    actual_loads = []
    for factor in load_pattern:
        actual_loads.append(base_load * factor)
    
    print(f"\n设计负荷: {[f'{l:.1f}' for l in actual_loads]}")
    print(f"负荷范围: {min(actual_loads):.1f} - {max(actual_loads):.1f} MW")
    
    for _, load in loads_df.iterrows():
        bus_name = load['bus']
        bus_data = buses_df[buses_df['name'] == bus_name]
        if not bus_data.empty:
            base_power = bus_data['real_power_demand'].values[0]
            load_share = base_power / total_base_demand
            
            load_ts_df = pd.DataFrame({
                'time': times,
                'power': [load_share * actual_load for actual_load in actual_loads]
            })
            
            load_ts_df.to_csv(f'{test_dir}/{load["name"]}_timeseries.csv', index=False)
    
    # 测试不同的初始状态
    init_configs = [
        ("全部开机", 9),
        ("大机组开机", 5),
        ("最少开机", 3),
    ]
    
    for config_name, init_online in init_configs:
        print(f"\n测试初始状态: {config_name} ({init_online}台)")
        
        # 设置初始状态
        initial_data = []
        sorted_gens = gen_df.sort_values('P max', ascending=False)
        
        for idx, (_, gen) in enumerate(sorted_gens.iterrows()):
            if idx < init_online:
                status = 1
                power = gen['P min']
                hoursinstatus = 2
            else:
                status = 0
                power = 0
                hoursinstatus = -2
            
            initial_data.append({
                'name': gen['name'],
                'status': status,
                'power': power,
                'hoursinstatus': int(hoursinstatus)
            })
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        online_pmin = sum(gen_df[gen_df['name'].isin(
            initial_df[initial_df['status'] == 1]['name'])]['P min'])
        
        print(f"  初始在线Pmin: {online_pmin:.1f} MW")
        print(f"  最小负荷: {min(actual_loads):.1f} MW")
        print(f"  裕度: {min(actual_loads) - online_pmin:.1f} MW")
        
        try:
            solution = solve_problem(test_dir)
            print(f"  ✅ 求解成功!")
        except Exception as e:
            print(f"  ❌ 求解失败: {str(e)[:100]}")
    
    # 清理
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_constraint_boundary()
    test_specific_case()