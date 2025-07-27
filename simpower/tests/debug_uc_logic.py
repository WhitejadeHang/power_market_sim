#!/usr/bin/env python3
"""
调试UC逻辑 - 理解为什么有约束时失败
"""

import os
import sys
import pandas as pd
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def create_debug_case(name, periods=3):
    """创建调试案例"""
    
    test_dir = f'simpower/tests/test_debug_{name}'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 3个节点，3台机组
    buses_data = [
        {'name': 'Bus1', 'is_generator': True, 'is_load': True, 'real_power_demand': 100},
        {'name': 'Bus2', 'is_generator': True, 'is_load': False, 'real_power_demand': 0},
        {'name': 'Bus3', 'is_generator': True, 'is_load': False, 'real_power_demand': 0},
    ]
    buses_df = pd.DataFrame(buses_data)
    buses_df.to_csv(f'{test_dir}/buses.csv', index=False)
    
    # 3台机组 - 不同容量
    gens_data = [
        {
            'name': 'G1',
            'bus': 'Bus1',
            'P min': 30,  # Pmin = 50% of Pmax
            'P max': 60,
            'minuptime': 1,
            'mindowntime': 1,
            'rampratemax': 60,
            'rampratemin': -60,
            'startupcost': 100,
            'shutdowncost': 50,
            'costcurvepointsfilename': 'G1_block_bid.csv',
            'noloadcost': 10
        },
        {
            'name': 'G2',
            'bus': 'Bus2',
            'P min': 40,  # Pmin = 50% of Pmax
            'P max': 80,
            'minuptime': 1,
            'mindowntime': 1,
            'rampratemax': 80,
            'rampratemin': -80,
            'startupcost': 150,
            'shutdowncost': 75,
            'costcurvepointsfilename': 'G2_block_bid.csv',
            'noloadcost': 15
        },
        {
            'name': 'G3',
            'bus': 'Bus3',
            'P min': 50,  # Pmin = 50% of Pmax
            'P max': 100,
            'minuptime': 1,
            'mindowntime': 1,
            'rampratemax': 100,
            'rampratemin': -100,
            'startupcost': 200,
            'shutdowncost': 100,
            'costcurvepointsfilename': 'G3_block_bid.csv',
            'noloadcost': 20
        },
    ]
    gens_df = pd.DataFrame(gens_data)
    gens_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    # 创建报价文件
    for gen in gens_data:
        bid_data = pd.DataFrame({
            'power': [gen['P min'], gen['P max']],
            'cost': [0, (gen['P max'] - gen['P min']) * 100]
        })
        bid_data.to_csv(f'{test_dir}/{gen["name"]}_block_bid.csv', index=False)
    
    # 线路
    lines_data = [
        {'name': 'Line1', 'frombus': 'Bus1', 'tobus': 'Bus2', 'pmax': 200, 'reactance': 0.1},
        {'name': 'Line2', 'frombus': 'Bus2', 'tobus': 'Bus3', 'pmax': 200, 'reactance': 0.1},
    ]
    lines_df = pd.DataFrame(lines_data)
    lines_df.to_csv(f'{test_dir}/lines.csv', index=False)
    
    # 负荷
    loads_data = [{
        'name': 'Load1',
        'bus': 'Bus1',
        'schedulefilename': 'Load1_timeseries.csv'
    }]
    loads_df = pd.DataFrame(loads_data)
    loads_df.to_csv(f'{test_dir}/loads.csv', index=False)
    
    return test_dir, gens_data


def test_scenarios():
    """测试不同场景"""
    
    print("🔍 调试UC逻辑 - 3时段3机组系统\n")
    
    test_cases = [
        # (名称, 负荷序列, 初始状态)
        ("低负荷递增", [60, 90, 120], [(1, 30), (0, 0), (0, 0)]),  # G1开，G2/G3停
        ("高负荷递减", [180, 150, 120], [(1, 30), (1, 40), (1, 50)]),  # 全开
        ("波动负荷", [80, 160, 100], [(1, 30), (0, 0), (0, 0)]),  # 需要启停
        ("极低起始", [50, 150, 200], [(0, 0), (0, 0), (0, 0)]),  # 全停（预期失败）
    ]
    
    test_dir, gens_data = create_debug_case("base", 3)
    
    # 计算系统容量
    total_pmin = sum(g['P min'] for g in gens_data)
    total_pmax = sum(g['P max'] for g in gens_data)
    print(f"系统容量: Pmin={total_pmin} MW, Pmax={total_pmax} MW\n")
    
    for test_name, loads, init_states in test_cases:
        print(f"\n{'='*60}")
        print(f"场景: {test_name}")
        print(f"负荷: {loads} MW")
        
        # 创建负荷时序
        start_time = datetime(2025, 1, 15, 0, 0, 0)
        times = [start_time + timedelta(hours=h) for h in range(3)]
        
        load_ts_df = pd.DataFrame({
            'time': times,
            'power': loads
        })
        load_ts_df.to_csv(f'{test_dir}/Load1_timeseries.csv', index=False)
        
        # 设置初始状态
        initial_data = []
        init_pmin_total = 0
        for i, (status, power) in enumerate(init_states):
            gen = gens_data[i]
            initial_data.append({
                'name': gen['name'],
                'status': status,
                'power': power,
                'hoursinstatus': 2 if status else -2
            })
            if status:
                init_pmin_total += gen['P min']
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        print(f"初始状态: {[f'{d["name"]}={d["status"]}' for d in initial_data]}")
        print(f"初始在线Pmin: {init_pmin_total} MW")
        
        # 分析可行性
        print(f"\n可行性分析:")
        for t, load in enumerate(loads):
            print(f"  t{t}: 负荷={load} MW", end="")
            if t == 0:
                available_pmin = init_pmin_total
                available_pmax = sum(g['P max'] for i, g in enumerate(gens_data) if init_states[i][0] == 1)
            else:
                # 考虑可能启动的机组（简化分析）
                available_pmin = total_pmin  # 假设所有机组都可以运行
                available_pmax = total_pmax
            
            if load < available_pmin:
                print(f" ⚠️ 负荷 < 在线Pmin ({available_pmin} MW)")
            elif load > available_pmax:
                print(f" ⚠️ 负荷 > 在线Pmax ({available_pmax} MW)")
            else:
                print(f" ✓ 可行区间内")
        
        # 求解
        try:
            solution = solve_problem(test_dir)
            print(f"\n✅ 求解成功!")
            
            # 打印结果
            if hasattr(solution, 'generators_status') and hasattr(solution, 'generators_power'):
                print("\n机组状态和出力:")
                for t in range(3):
                    status = solution.generators_status[t]
                    power = solution.generators_power[t]
                    print(f"  t{t}: ", end="")
                    for g in range(3):
                        print(f"G{g+1}={status[g]}/{power[g]:.0f}MW ", end="")
                    print()
                    
        except Exception as e:
            print(f"\n❌ 求解失败: {str(e)}")
            if "total committed" in str(e):
                print("注: 可能是初始承诺容量不足")
    
    # 清理
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


def test_minupdown_relaxation():
    """测试逐步放松minuptime/mindowntime"""
    
    print("\n\n🔍 测试minuptime/mindowntime逐步放松")
    print("="*60)
    
    test_dir, gens_data = create_debug_case("relax", 3)
    
    # 固定负荷和初始状态
    loads = [80, 160, 100]  # 需要启停的负荷
    
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(3)]
    
    load_ts_df = pd.DataFrame({
        'time': times,
        'power': loads
    })
    load_ts_df.to_csv(f'{test_dir}/Load1_timeseries.csv', index=False)
    
    # G1开，其他停
    initial_df = pd.DataFrame([
        {'name': 'G1', 'status': 1, 'power': 30, 'hoursinstatus': 2},
        {'name': 'G2', 'status': 0, 'power': 0, 'hoursinstatus': -2},
        {'name': 'G3', 'status': 0, 'power': 0, 'hoursinstatus': -2},
    ])
    initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
    
    # 测试不同的约束值
    constraint_values = [0, 1, 2, 3]
    
    for mintime in constraint_values:
        print(f"\nminuptime = mindowntime = {mintime}")
        
        # 更新发电机参数
        gen_df = pd.read_csv(f'{test_dir}/generators.csv')
        gen_df['minuptime'] = mintime
        gen_df['mindowntime'] = mintime
        gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
        
        try:
            solution = solve_problem(test_dir)
            print(f"  ✅ 成功")
        except Exception as e:
            print(f"  ❌ 失败: {str(e)[:50]}...")
    
    # 清理
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_scenarios()
    test_minupdown_relaxation()