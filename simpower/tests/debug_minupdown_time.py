#!/usr/bin/env python3
"""
逐步调试minuptime和mindowntime约束
"""

import os
import sys
import pandas as pd
import numpy as np
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def create_test_case(test_name, periods=24, minuptime=0, mindowntime=0):
    """创建测试案例"""
    
    # 复制基础案例
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    test_dir = f'simpower/tests/test_{test_name}'
    
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 修改发电机参数
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    gen_df['minuptime'] = minuptime
    gen_df['mindowntime'] = mindowntime
    gen_df['rampratemax'] = gen_df['P max'] * 0.8  # 80%爬坡率
    gen_df['rampratemin'] = -gen_df['P max'] * 0.8
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    # 如果需要调整时段数
    if periods < 24:
        start_time = datetime(2025, 1, 15, 0, 0, 0)
        times = [start_time + timedelta(hours=h) for h in range(periods)]
        
        # 截断负荷时序
        for file in os.listdir(test_dir):
            if file.endswith('_timeseries.csv'):
                ts_df = pd.read_csv(os.path.join(test_dir, file))
                ts_df = ts_df.iloc[:periods]
                ts_df.to_csv(os.path.join(test_dir, file), index=False)
    
    return test_dir


def test_minupdown_combinations():
    """测试不同的minuptime/mindowntime组合"""
    
    print("🔍 逐步调试minuptime和mindowntime约束\n")
    print("="*80)
    
    # 测试组合
    test_configs = [
        # (名称, 时段数, minuptime, mindowntime)
        ("baseline_24h", 24, 0, 0),      # 基准测试
        ("minup1_24h", 24, 1, 0),        # 只有最小运行时间
        ("mindown1_24h", 24, 0, 1),      # 只有最小停机时间
        ("both1_24h", 24, 1, 1),         # 两者都是1
        ("both2_24h", 24, 2, 2),         # 两者都是2
        ("both3_24h", 24, 3, 3),         # 两者都是3
        ("both4_24h", 24, 4, 4),         # 两者都是4
        
        # 缩短时段测试
        ("baseline_12h", 12, 0, 0),      # 12时段基准
        ("both1_12h", 12, 1, 1),         # 12时段，约束1
        ("both2_12h", 12, 2, 2),         # 12时段，约束2
        
        # 更短时段
        ("baseline_6h", 6, 0, 0),        # 6时段基准
        ("both1_6h", 6, 1, 1),           # 6时段，约束1
    ]
    
    results = []
    
    for test_name, periods, minuptime, mindowntime in test_configs:
        print(f"\n测试: {test_name}")
        print(f"  时段数: {periods}")
        print(f"  minuptime: {minuptime}, mindowntime: {mindowntime}")
        print("-" * 40)
        
        try:
            test_dir = create_test_case(test_name, periods, minuptime, mindowntime)
            
            # 打印初始状态
            initial_df = pd.read_csv(f'{test_dir}/initial.csv')
            online_count = len(initial_df[initial_df['status'] == 1])
            print(f"  初始开机: {online_count}台")
            
            # 求解
            solution = solve_problem(test_dir)
            
            # 统计启停次数
            startup_count = 0
            shutdown_count = 0
            
            if hasattr(solution, 'generators_status'):
                gen_status = solution.generators_status
                n_gens = len(gen_status[0]) if gen_status else 0
                
                for g in range(n_gens):
                    for t in range(1, len(gen_status)):
                        if gen_status[t][g] > gen_status[t-1][g]:
                            startup_count += 1
                        elif gen_status[t][g] < gen_status[t-1][g]:
                            shutdown_count += 1
            
            # 计算成本
            total_cost = solution.objective if hasattr(solution, 'objective') else 0
            
            print(f"  ✅ 求解成功!")
            print(f"  总成本: ${total_cost:,.2f}")
            print(f"  启动次数: {startup_count}, 停机次数: {shutdown_count}")
            
            results.append({
                'test_name': test_name,
                'periods': periods,
                'minuptime': minuptime,
                'mindowntime': mindowntime,
                'status': 'Success',
                'total_cost': total_cost,
                'startups': startup_count,
                'shutdowns': shutdown_count
            })
            
        except Exception as e:
            error_msg = str(e)
            print(f"  ❌ 求解失败: {error_msg}")
            
            # 尝试提取更多信息
            if "failed to solve with shedding" in error_msg:
                print(f"  注: 机组组合不可行")
            
            results.append({
                'test_name': test_name,
                'periods': periods,
                'minuptime': minuptime,
                'mindowntime': mindowntime,
                'status': 'Failed',
                'error': error_msg,
                'startups': 0,
                'shutdowns': 0
            })
        
        finally:
            # 清理测试目录
            if os.path.exists(test_dir):
                shutil.rmtree(test_dir)
    
    # 汇总结果
    print("\n" + "="*80)
    print("📊 测试结果汇总")
    print("="*80)
    
    results_df = pd.DataFrame(results)
    print(results_df.to_string(index=False))
    
    # 分析边界
    print("\n🔍 约束边界分析:")
    success_cases = results_df[results_df['status'] == 'Success']
    failed_cases = results_df[results_df['status'] == 'Failed']
    
    if not success_cases.empty:
        max_success_minup = success_cases['minuptime'].max()
        max_success_mindown = success_cases['mindowntime'].max()
        print(f"  成功的最大minuptime: {max_success_minup}")
        print(f"  成功的最大mindowntime: {max_success_mindown}")
    
    if not failed_cases.empty:
        min_fail_minup = failed_cases['minuptime'].min()
        min_fail_mindown = failed_cases['mindowntime'].min()
        print(f"  失败的最小minuptime: {min_fail_minup}")
        print(f"  失败的最小mindowntime: {min_fail_mindown}")
    
    return results_df


def test_specific_boundary(minuptime, mindowntime):
    """测试特定的边界条件"""
    
    print(f"\n🎯 测试特定边界: minuptime={minuptime}, mindowntime={mindowntime}")
    print("="*60)
    
    # 测试不同的初始状态
    test_configs = [
        ("all_on", True),    # 所有机组初始开机
        ("partial", False),  # 部分机组开机
    ]
    
    for config_name, all_on in test_configs:
        print(f"\n测试配置: {config_name}")
        
        test_dir = create_test_case(f"boundary_{config_name}", 24, minuptime, mindowntime)
        
        # 修改初始状态
        gen_df = pd.read_csv(f'{test_dir}/generators.csv')
        initial_data = []
        
        for _, gen in gen_df.iterrows():
            if all_on:
                status = 1
                power = gen['P min']
                hoursinstatus = minuptime + 1
            else:
                # 部分开机策略
                if gen['P max'] >= 80:  # 大机组开机
                    status = 1
                    power = gen['P min']
                    hoursinstatus = minuptime + 1
                else:
                    status = 0
                    power = 0
                    hoursinstatus = -(mindowntime + 1)
            
            initial_data.append({
                'name': gen['name'],
                'status': status,
                'power': power,
                'hoursinstatus': int(hoursinstatus)
            })
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
        
        print(f"初始开机: {len(initial_df[initial_df['status'] == 1])}台")
        
        try:
            solution = solve_problem(test_dir)
            print("✅ 求解成功!")
        except Exception as e:
            print(f"❌ 求解失败: {e}")
        
        # 清理
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


if __name__ == "__main__":
    # 1. 测试不同组合
    results = test_minupdown_combinations()
    
    # 2. 基于结果测试边界
    # 如果发现边界，进一步测试
    if len(results) > 0:
        success_results = results[results['status'] == 'Success']
        if not success_results.empty and success_results['minuptime'].max() > 0:
            # 测试边界附近
            boundary_mintime = success_results['minuptime'].max()
            test_specific_boundary(boundary_mintime + 1, boundary_mintime + 1)