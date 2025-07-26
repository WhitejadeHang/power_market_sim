#!/usr/bin/env python3
"""
12时段演示版本 - 用于快速验证多时段功能
"""

import os
import sys
import time as timer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def create_12periods_demo():
    """创建12时段演示案例"""
    
    # 创建案例目录
    case_dir = 'simpower/tests/ieee_50_12periods_demo'
    os.makedirs(case_dir, exist_ok=True)
    
    # 复制基础文件
    import shutil
    base_dir = 'simpower/tests/ieee_50_single_period'
    
    for file in ['buses.csv', 'lines.csv', 'generators.csv']:
        src = os.path.join(base_dir, file)
        dst = os.path.join(case_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
    
    # 创建12时段时间序列（3小时）
    base_time = datetime(2025, 7, 26, 18, 0)  # 从晚上6点开始
    times = []
    load_factors = []
    
    for i in range(12):
        current_time = base_time + timedelta(minutes=15*i)
        times.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 晚高峰负荷曲线
        hour = current_time.hour + current_time.minute/60
        factor = 0.95 + 0.05 * np.sin((hour - 18) * np.pi / 3)
        factor += np.random.normal(0, 0.01)
        load_factors.append(max(0.85, min(1.05, factor)))
    
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    
    # 创建loads.csv
    loads_df = pd.read_csv(os.path.join(base_dir, 'loads.csv'))
    # 移除power列（多时段不需要）
    if 'power' in loads_df.columns:
        loads_df = loads_df.drop(columns=['power'])
    loads_df['schedule filename'] = 'timeseries.csv'
    loads_df = loads_df.drop_duplicates(subset=['name', 'bus'])
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    
    return case_dir


def run_12periods_demo():
    """运行12时段演示"""
    
    print("🚀 12时段演示版本（晚高峰3小时）")
    print("=" * 60)
    
    # 创建案例
    case_dir = create_12periods_demo()
    print(f"✅ 创建12时段案例: {case_dir}")
    
    # 运行求解
    print("\n🔧 开始12时段经济调度求解...")
    start_time = timer.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = timer.time() - start_time
        print(f"✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败")
            return False
        
        # 简单分析结果
        print("\n📊 12时段仿真结果概要:")
        
        if 'Status' in solution:
            status_df = solution['Status']
            print(f"\n机组运行状态:")
            print(f"  - 时段数: {len(status_df)}")
            print(f"  - 机组数: {len(status_df.columns)}")
            
            # 每个时段的运行机组数
            running_units = status_df.sum(axis=1)
            print(f"\n各时段运行机组数:")
            for idx, (time, count) in enumerate(running_units.items()):
                print(f"  时段{idx+1:2d}: {int(count)}台运行")
        
        if 'Power' in solution:
            power_df = solution['Power']
            total_gen = power_df.sum(axis=1)
            
            print(f"\n总发电量统计:")
            print(f"  - 平均: {total_gen.mean():.1f} MW")
            print(f"  - 最大: {total_gen.max():.1f} MW")
            print(f"  - 最小: {total_gen.min():.1f} MW")
            print(f"  - 峰谷差: {total_gen.max() - total_gen.min():.1f} MW")
        
        # 生成简单的可视化
        try:
            import matplotlib.pyplot as plt
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
            
            # 机组开停状态
            status_data = status_df.T.values
            im = ax1.imshow(status_data, aspect='auto', cmap='RdYlGn')
            ax1.set_ylabel('Generators')
            ax1.set_xlabel('Time Period')
            ax1.set_title('12-Period Unit Commitment Status')
            plt.colorbar(im, ax=ax1)
            
            # 总发电量
            periods = range(1, 13)
            ax2.plot(periods, total_gen.values, 'b-o', linewidth=2, markersize=8)
            ax2.fill_between(periods, 0, total_gen.values, alpha=0.3)
            ax2.set_xlabel('Time Period')
            ax2.set_ylabel('Total Generation (MW)')
            ax2.set_title('12-Period Total Generation')
            ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            output_dir = os.path.join(case_dir, 'results')
            os.makedirs(output_dir, exist_ok=True)
            output_path = os.path.join(output_dir, 'demo_12periods_results.png')
            plt.savefig(output_path, dpi=150, bbox_inches='tight')
            plt.close()
            
            print(f"\n📈 结果图表已保存: {output_path}")
            
        except Exception as e:
            print(f"⚠️ 绘图失败: {e}")
        
        print("\n✅ 12时段演示成功完成！")
        print("💡 这证明多时段功能正常工作")
        print("📌 下一步可以尝试更多时段（24、48、96）")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 求解失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = run_12periods_demo()
    
    if success:
        print("\n🎉 演示成功！多时段仿真功能验证通过")
    else:
        print("\n❌ 演示失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)