#!/usr/bin/env python3
"""
极简机组组合测试 - 定位问题
"""

import os
import sys
import pandas as pd
import numpy as np
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def create_minimal_case(test_name, periods=2, minuptime=1, mindowntime=1):
    """创建最小测试案例"""
    
    test_dir = f'simpower/tests/test_{test_name}'
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # 创建最简单的系统 - 2台机组，2个节点
    buses_data = [
        {'name': 'Bus1', 'is_generator': True, 'is_load': True, 'real_power_demand': 100},
        {'name': 'Bus2', 'is_generator': True, 'is_load': False, 'real_power_demand': 0},
    ]
    buses_df = pd.DataFrame(buses_data)
    buses_df.to_csv(f'{test_dir}/buses.csv', index=False)
    
    # 2台发电机
    gens_data = [
        {
            'name': 'G1',
            'bus': 'Bus1',
            'P min': 50,  # Pmin = 50% of Pmax
            'P max': 100,
            'minuptime': minuptime,
            'mindowntime': mindowntime,
            'rampratemax': 100,
            'rampratemin': -100,
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
            'minuptime': minuptime,
            'mindowntime': mindowntime,
            'rampratemax': 80,
            'rampratemin': -80,
            'startupcost': 80,
            'shutdowncost': 40,
            'costcurvepointsfilename': 'G2_block_bid.csv',
            'noloadcost': 8
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
    
    # 1条线路
    lines_data = [{
        'name': 'Line1',
        'frombus': 'Bus1',
        'tobus': 'Bus2',
        'pmax': 200,
        'reactance': 0.1
    }]
    lines_df = pd.DataFrame(lines_data)
    lines_df.to_csv(f'{test_dir}/lines.csv', index=False)
    
    # 1个负荷
    loads_data = [{
        'name': 'Load1',
        'bus': 'Bus1',
        'schedulefilename': 'Load1_timeseries.csv'
    }]
    loads_df = pd.DataFrame(loads_data)
    loads_df.to_csv(f'{test_dir}/loads.csv', index=False)
    
    # 负荷时序 - 设计为需要启停的模式
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(periods)]
    
    # 负荷设计：第1时段100MW（1台机可满足），第2时段150MW（需要2台机）
    if periods == 2:
        load_values = [100, 150]
    else:
        # 更多时段的负荷模式
        load_values = [100 + 50 * (i % 2) for i in range(periods)]
    
    load_ts_df = pd.DataFrame({
        'time': times[:len(load_values)],
        'power': load_values[:periods]
    })
    load_ts_df.to_csv(f'{test_dir}/Load1_timeseries.csv', index=False)
    
    return test_dir


def test_progressive():
    """逐步测试以找出问题"""
    
    print("🔍 极简机组组合测试\n")
    
    test_configs = [
        # (名称, 时段, minuptime, mindowntime, G1初始状态, G2初始状态)
        ("2p_no_constraint", 2, 0, 0, 1, 0),
        ("2p_constraint_1", 2, 1, 1, 1, 0),
        ("2p_constraint_1_both_on", 2, 1, 1, 1, 1),
        ("2p_constraint_1_both_off", 2, 1, 1, 0, 0),
        
        # 测试初始小时数的影响
        ("2p_constraint_1_hours", 2, 1, 1, 1, 0),  # 需要特殊处理hoursinstatus
    ]
    
    for test_name, periods, minuptime, mindowntime, g1_status, g2_status in test_configs:
        print(f"\n{'='*60}")
        print(f"测试: {test_name}")
        print(f"  时段: {periods}, minup: {minuptime}, mindown: {mindowntime}")
        print(f"  初始状态: G1={g1_status}, G2={g2_status}")
        
        test_dir = create_minimal_case(test_name, periods, minuptime, mindowntime)
        
        # 设置初始状态
        initial_data = [
            {
                'name': 'G1',
                'status': g1_status,
                'power': 50 if g1_status else 0,
                'hoursinstatus': 2 if g1_status else -2
            },
            {
                'name': 'G2',
                'status': g2_status,
                'power': 40 if g2_status else 0,
                'hoursinstatus': 2 if g2_status else -2
            }
        ]
        
        # 特殊处理hoursinstatus测试
        if "hours" in test_name:
            initial_data[0]['hoursinstatus'] = 0 if g1_status else 0  # 恰好满足约束
            initial_data[1]['hoursinstatus'] = 0 if g2_status else 0
            print(f"  特殊hoursinstatus: G1={initial_data[0]['hoursinstatus']}, G2={initial_data[1]['hoursinstatus']}")
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        # 计算初始在线容量
        online_pmin = sum(d['power'] for d in initial_data if d['status'] == 1)
        print(f"  初始在线Pmin: {online_pmin} MW")
        
        # 读取负荷
        load_ts = pd.read_csv(f'{test_dir}/Load1_timeseries.csv')
        print(f"  负荷: {list(load_ts['power'])}")
        
        try:
            solution = solve_problem(test_dir)
            print(f"  ✅ 求解成功!")
            
            # 打印结果
            if hasattr(solution, 'generators_power'):
                print(f"  发电出力:")
                for t in range(len(solution.generators_power)):
                    powers = solution.generators_power[t]
                    print(f"    t{t}: G1={powers[0]:.1f}, G2={powers[1]:.1f}")
            
            if hasattr(solution, 'generators_status'):
                print(f"  机组状态:")
                for t in range(len(solution.generators_status)):
                    status = solution.generators_status[t]
                    print(f"    t{t}: G1={status[0]}, G2={status[1]}")
                    
        except Exception as e:
            print(f"  ❌ 求解失败: {str(e)}")
            # 如果是UC失败，尝试提取更多信息
            if "failed to solve with shedding" in str(e):
                print(f"  注: 检查约束冲突")
        
        finally:
            # 清理
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)


def test_initial_hours_impact():
    """专门测试initial_status_hours的影响"""
    
    print("\n\n🔍 测试initial_status_hours的影响")
    print("="*60)
    
    test_dir = create_minimal_case("hours_test", 2, 1, 1)
    
    # 测试不同的hoursinstatus值
    hours_configs = [
        ("已运行2小时", 2, -2),
        ("已运行1小时", 1, -1),
        ("刚好满足", 1, -1),  # minuptime=1, hoursinstatus=1
        ("刚启动", 0, 0),
        ("负值测试", -1, 1),
    ]
    
    for config_name, g1_hours, g2_hours in hours_configs:
        print(f"\n配置: {config_name}")
        print(f"  G1 hoursinstatus: {g1_hours}, G2 hoursinstatus: {g2_hours}")
        
        initial_data = [
            {
                'name': 'G1',
                'status': 1,
                'power': 50,
                'hoursinstatus': g1_hours
            },
            {
                'name': 'G2',
                'status': 0,
                'power': 0,
                'hoursinstatus': g2_hours
            }
        ]
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        try:
            solution = solve_problem(test_dir)
            print(f"  ✅ 求解成功!")
        except Exception as e:
            print(f"  ❌ 求解失败: {str(e)[:100]}")
    
    # 清理
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)


if __name__ == "__main__":
    test_progressive()
    test_initial_hours_impact()