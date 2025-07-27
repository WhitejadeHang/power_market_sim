#!/usr/bin/env python3
"""
多时段仿真工作版本
"""

import os
import sys
import time as timer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def create_multiperiod_case(num_periods=12):
    """创建多时段测试案例"""
    
    # 源目录（使用已验证可工作的案例）
    src_dir = 'simpower/tests/ieee_50_simple'
    dst_dir = f'simpower/tests/ieee_50_{num_periods}periods_work'
    
    # 删除旧目录
    if os.path.exists(dst_dir):
        shutil.rmtree(dst_dir)
    
    # 复制整个目录
    shutil.copytree(src_dir, dst_dir)
    print(f"✅ 复制基础案例到: {dst_dir}")
    
    # 创建时间序列
    base_time = datetime(2025, 7, 26, 0, 0)
    times = []
    load_factors = []
    
    for i in range(num_periods):
        current_time = base_time + timedelta(minutes=15*i)
        times.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 简单的负荷曲线
        hour = current_time.hour + current_time.minute/60
        if 0 <= hour < 6:
            factor = 0.7
        elif 6 <= hour < 9:
            factor = 0.9
        elif 9 <= hour < 18:
            factor = 0.95
        elif 18 <= hour < 21:
            factor = 1.0
        else:
            factor = 0.8
        
        load_factors.append(factor)
    
    # 保存时间序列
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(dst_dir, 'timeseries.csv'), index=False)
    
    # 修改loads.csv
    loads_df = pd.read_csv(os.path.join(dst_dir, 'loads.csv'))
    loads_df['schedule filename'] = 'timeseries.csv'
    # 确保只有必要的列
    loads_df = loads_df[['name', 'bus', 'schedule filename']]
    loads_df.to_csv(os.path.join(dst_dir, 'loads.csv'), index=False)
    
    # 确保generators.csv有必要的列
    gen_df = pd.read_csv(os.path.join(dst_dir, 'generators.csv'))
    if 'ramp rate' not in gen_df.columns:
        gen_df['ramp rate'] = gen_df['P max'] * 0.2  # 20%爬坡率
    if 'start cost' not in gen_df.columns:
        gen_df['start cost'] = gen_df['P max'] * 100
    gen_df.to_csv(os.path.join(dst_dir, 'generators.csv'), index=False)
    
    return dst_dir


def run_multiperiod_simulation(num_periods=12):
    """运行多时段仿真"""
    
    print(f"\n🚀 {num_periods}时段仿真测试")
    print("=" * 60)
    
    # 创建案例
    case_dir = create_multiperiod_case(num_periods)
    
    # 运行求解
    print(f"\n⚙️ 开始{num_periods}时段经济调度求解...")
    start_time = timer.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = timer.time() - start_time
        print(f"✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解返回空解")
            return False
        
        # 分析结果
        print(f"\n📊 {num_periods}时段仿真结果:")
        
        if 'Status' in solution:
            status_df = solution['Status']
            print(f"  - 实际时段数: {len(status_df)}")
            print(f"  - 机组数: {len(status_df.columns)}")
            
            running_units = status_df.sum(axis=1)
            print(f"  - 平均运行机组数: {running_units.mean():.1f}")
        
        if 'Power' in solution:
            power_df = solution['Power']
            total_gen = power_df.sum(axis=1)
            print(f"  - 平均总发电量: {total_gen.mean():.1f} MW")
            print(f"  - 峰值发电量: {total_gen.max():.1f} MW")
            print(f"  - 谷值发电量: {total_gen.min():.1f} MW")
        
        # 生成简单图表
        try:
            import matplotlib.pyplot as plt
            
            plt.figure(figsize=(12, 4))
            periods = range(1, len(total_gen)+1)
            plt.plot(periods, total_gen.values, 'b-o', linewidth=2)
            plt.fill_between(periods, 0, total_gen.values, alpha=0.3)
            plt.xlabel('Time Period')
            plt.ylabel('Total Generation (MW)')
            plt.title(f'{num_periods}-Period Total Generation')
            plt.grid(True, alpha=0.3)
            
            output_path = os.path.join(case_dir, 'multiperiod_generation.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            print(f"\n📈 生成图表: {output_path}")
        except:
            pass
        
        print(f"\n✅ {num_periods}时段仿真成功！")
        return True
        
    except Exception as e:
        print(f"\n❌ 求解失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数 - 逐步测试不同时段数"""
    
    print("🧪 多时段仿真功能测试")
    print("逐步测试不同的时段数...")
    
    # 测试不同的时段数
    test_periods = [4, 12, 24]  # 先测试较少的时段
    
    for num_periods in test_periods:
        print(f"\n{'='*60}")
        print(f"测试 {num_periods} 时段...")
        
        success = run_multiperiod_simulation(num_periods)
        
        if not success:
            print(f"❌ {num_periods}时段测试失败，停止测试")
            return False
        
        print(f"✅ {num_periods}时段测试通过")
    
    print("\n🎉 所有测试通过！")
    print("\n💡 下一步建议：")
    print("  1. 可以尝试运行48或96时段")
    print("  2. 使用results_analysis_96periods模块生成详细报告")
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)