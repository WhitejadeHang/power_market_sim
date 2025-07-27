#!/usr/bin/env python3
"""
单时段调试脚本 - 逐步找出不可行约束
"""

import os
import sys
import pandas as pd
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def test_single_period():
    """测试单时段求解"""
    
    # 创建单时段案例
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    test_dir = 'simpower/tests/ieee14_single_period_test'
    
    # 清理并创建测试目录
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    shutil.copytree(source_dir, test_dir)
    
    # 修改为单时段
    loads_df = pd.read_csv(f'{test_dir}/loads.csv')
    
    # 移除时序文件引用，直接设置功率
    loads_df['power'] = [10, 15, 20, 25, 15, 20, 25, 10, 15, 20, 10]  # 总和 = 190 MW
    if 'schedulefilename' in loads_df.columns:
        loads_df = loads_df.drop('schedulefilename', axis=1)
    
    loads_df.to_csv(f'{test_dir}/loads.csv', index=False)
    
    # 删除时序文件
    for file in os.listdir(test_dir):
        if '_timeseries.csv' in file:
            os.remove(os.path.join(test_dir, file))
    
    print("=" * 60)
    print("单时段测试")
    print("=" * 60)
    print(f"总负荷: {loads_df['power'].sum()} MW")
    
    # 检查发电机参数
    gen_df = pd.read_csv(f'{test_dir}/generators.csv')
    print(f"\n发电机总容量: {gen_df['P max'].sum()} MW")
    print(f"发电机总最小出力: {gen_df['P min'].sum()} MW")
    
    # 尝试求解
    try:
        solution = solve_problem(test_dir)
        print("\n✅ 单时段求解成功！")
        return True
    except Exception as e:
        print(f"\n❌ 单时段求解失败: {e}")
        return False


def test_network_constraints():
    """分析网络约束"""
    
    test_dir = 'simpower/tests/ieee14_single_period_test'
    
    # 读取线路数据
    lines_df = pd.read_csv(f'{test_dir}/lines.csv')
    
    print("\n" + "=" * 60)
    print("线路容量分析")
    print("=" * 60)
    
    # 显示所有线路容量
    print("\n线路容量详情:")
    print(lines_df[['name', 'frombus', 'tobus', 'pmax']].to_string())
    
    # 统计容量
    print(f"\n线路容量统计:")
    print(f"最小容量: {lines_df['pmax'].min()} MW")
    print(f"最大容量: {lines_df['pmax'].max()} MW")
    print(f"平均容量: {lines_df['pmax'].mean():.1f} MW")
    
    # 识别可能的瓶颈
    bottleneck_threshold = lines_df['pmax'].quantile(0.25)
    bottlenecks = lines_df[lines_df['pmax'] <= bottleneck_threshold]
    
    if not bottlenecks.empty:
        print(f"\n潜在瓶颈线路 (容量 <= {bottleneck_threshold} MW):")
        print(bottlenecks[['name', 'frombus', 'tobus', 'pmax']].to_string())


def progressive_test():
    """逐步增加时段数测试"""
    
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    
    for periods in [1, 2, 4, 8, 12, 24]:
        print(f"\n{'='*60}")
        print(f"测试 {periods} 时段")
        print(f"{'='*60}")
        
        test_dir = f'simpower/tests/ieee14_{periods}periods_test'
        
        # 清理并创建测试目录
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir)
        shutil.copytree(source_dir, test_dir)
        
        # 截取时序数据到指定时段数
        for file in os.listdir(test_dir):
            if '_timeseries.csv' in file:
                ts_df = pd.read_csv(os.path.join(test_dir, file))
                ts_df = ts_df.iloc[:periods]
                ts_df.to_csv(os.path.join(test_dir, file), index=False)
        
        # 尝试求解
        try:
            solution = solve_problem(test_dir)
            print(f"✅ {periods}时段求解成功！")
            
            # 清理临时目录
            shutil.rmtree(test_dir)
            
        except Exception as e:
            print(f"❌ {periods}时段求解失败: {e}")
            print(f"   问题案例保存在: {test_dir}")
            break


if __name__ == "__main__":
    print("🔍 开始逐步调试...\n")
    
    # 1. 单时段测试
    if test_single_period():
        # 2. 网络约束分析
        test_network_constraints()
        
        # 3. 逐步增加时段
        progressive_test()
    else:
        print("\n单时段测试失败，需要先解决基本可行性问题")