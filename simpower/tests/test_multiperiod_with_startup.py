#!/usr/bin/env python3
"""
多时段测试 - 处理初始状态和机组启停
"""

import os
import sys
import pandas as pd
import shutil
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def setup_multiperiod_case(periods):
    """设置多时段案例"""
    
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    test_dir = f'simpower/tests/ieee14_{periods}periods_test'
    
    # 清理并创建测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 读取发电机数据
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    
    # 确保初始状态文件存在并正确
    if not os.path.exists(f'{test_dir}/initial.csv'):
        # 创建初始状态
        initial_data = []
        for _, gen in gen_df.iterrows():
            # 部分机组初始停机以允许启停
            if gen['name'] in ['G2', 'G6', 'G7', 'G8']:
                status = 0
                power = 0
                hoursinstatus = -2
            else:
                status = 1
                power = 10
                hoursinstatus = 2
            
            initial_data.append({
                'name': gen['name'],
                'status': status,
                'power': power,
                'hoursinstatus': int(hoursinstatus)
            })
        
        initial_df = pd.DataFrame(initial_data)
        initial_df.to_csv(f'{test_dir}/initial.csv', index=False)
    
    # 截取时序数据到指定时段数
    for file in os.listdir(test_dir):
        if '_timeseries.csv' in file:
            ts_df = pd.read_csv(os.path.join(test_dir, file))
            ts_df = ts_df.iloc[:periods]
            ts_df.to_csv(os.path.join(test_dir, file), index=False)
    
    return test_dir


def analyze_solution(solution, periods):
    """分析求解结果"""
    
    if solution is None:
        return
    
    print("\n📊 求解结果分析:")
    
    # 检查机组状态
    try:
        status_df = solution.gen_time_df('status')
        
        # 统计启停次数
        print("\n机组启停统计:")
        for col in status_df.columns:
            status = status_df[col].values
            starts = sum(1 for i in range(1, len(status)) if status[i] > status[i-1])
            stops = sum(1 for i in range(1, len(status)) if status[i] < status[i-1])
            
            if starts > 0 or stops > 0:
                print(f"{col}: 启动{starts}次, 停机{stops}次")
        
        # 显示状态变化
        print("\n机组状态时序:")
        print(status_df.to_string())
        
    except Exception as e:
        print(f"无法分析机组状态: {e}")


def test_with_relaxed_constraints(periods):
    """使用放松的约束测试"""
    
    test_dir = setup_multiperiod_case(periods)
    
    # 进一步放松约束
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    
    # 极度放松的参数
    gen_df['P min'] = 0
    gen_df['minuptime'] = 0
    gen_df['mindowntime'] = 0
    gen_df['rampratemax'] = gen_df['P max'] * 2  # 200%爬坡率
    gen_df['rampratemin'] = -gen_df['P max'] * 2
    
    gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
    
    print(f"\n{'='*60}")
    print(f"测试 {periods} 时段（极度放松约束）")
    print(f"{'='*60}")
    
    try:
        solution = solve_problem(test_dir)
        print(f"✅ {periods}时段求解成功！")
        
        analyze_solution(solution, periods)
        
        # 保留成功案例
        success_dir = f'simpower/tests/ieee14_{periods}periods_success'
        shutil.copytree(test_dir, success_dir)
        print(f"\n成功案例保存在: {success_dir}")
        
        return True
        
    except Exception as e:
        print(f"❌ {periods}时段求解失败: {e}")
        return False
    finally:
        # 清理临时目录
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)


def main():
    """主函数"""
    
    print("🔍 多时段逐步测试（处理初始状态）\n")
    
    # 逐步测试
    for periods in [1, 2, 4, 8, 12, 24]:
        success = test_with_relaxed_constraints(periods)
        
        if not success and periods > 1:
            print("\n⚠️ 在此时段数遇到问题，停止测试")
            break
    
    # 如果所有测试都成功，尝试带约束的版本
    if success:
        print("\n" + "="*60)
        print("尝试带机组组合约束的24时段")
        print("="*60)
        
        test_dir = setup_multiperiod_case(24)
        
        # 适度的约束
        gen_df = pd.read_csv(f'{test_dir}/generators.csv')
        gen_df['minuptime'] = 2
        gen_df['mindowntime'] = 2
        gen_df['startupcost'] = gen_df['P max'] * 50
        gen_df['shutdowncost'] = gen_df['P max'] * 25
        gen_df.to_csv(f'{test_dir}/generators.csv', index=False)
        
        try:
            solution = solve_problem(test_dir)
            print("✅ 24时段机组组合求解成功！")
            analyze_solution(solution, 24)
            
        except Exception as e:
            print(f"❌ 24时段机组组合求解失败: {e}")


if __name__ == "__main__":
    main()