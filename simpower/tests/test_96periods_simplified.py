#!/usr/bin/env python3
"""
简化版96时段仿真测试 - 先测试24个时段（6小时）
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def test_simplified_96periods():
    """测试简化版多时段仿真"""
    
    # 先创建一个24时段的测试案例
    case_dir = 'simpower/tests/ieee_50_24periods'
    os.makedirs(case_dir, exist_ok=True)
    
    print("🧪 创建24时段测试案例...")
    
    # 复制基础文件
    import shutil
    base_dir = 'simpower/tests/ieee_50_bus_working'
    
    for file in ['buses.csv', 'lines.csv', 'generators.csv']:
        src = os.path.join(base_dir, file)
        dst = os.path.join(case_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
    
    # 创建24时段的负荷数据
    import pandas as pd
    
    # 读取原始负荷数据
    loads_df = pd.read_csv(os.path.join(base_dir, 'loads.csv'))
    loads_df['schedule filename'] = 'timeseries.csv'
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    
    # 创建24时段的时间序列（6小时，每15分钟一个点）
    time_periods = []
    load_factors = []
    
    for hour in range(6):
        for quarter in range(4):
            time_str = f"2025-07-26 {hour:02d}:{quarter*15:02d}:00"
            time_periods.append(time_str)
            # 简单的负荷曲线
            factor = 0.8 + 0.2 * (hour / 6)
            load_factors.append(factor)
    
    timeseries_df = pd.DataFrame({
        'time': time_periods,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    
    print(f"✅ 创建24时段测试案例完成")
    print(f"📁 案例目录: {case_dir}")
    
    # 运行求解
    print("\n🚀 开始24时段经济调度求解...")
    start_time = time.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"✅ 求解完成，用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 简单分析结果
        print("\n📊 求解结果概要:")
        
        if hasattr(solution, 'Status'):
            status_df = solution['Status']
            print(f"  - 时段数: {len(status_df)}")
            print(f"  - 机组数: {len(status_df.columns)}")
            
            # 统计每个时段的运行机组数
            running_units = status_df.sum(axis=1)
            print(f"  - 平均运行机组数: {running_units.mean():.1f}")
            print(f"  - 最大运行机组数: {running_units.max()}")
            print(f"  - 最小运行机组数: {running_units.min()}")
        
        if hasattr(solution, 'Power'):
            power_df = solution['Power']
            total_gen = power_df.sum(axis=1)
            print(f"  - 平均总发电量: {total_gen.mean():.1f} MW")
            print(f"  - 最大总发电量: {total_gen.max():.1f} MW")
            print(f"  - 最小总发电量: {total_gen.min():.1f} MW")
        
        return True
        
    except Exception as e:
        print(f"❌ 求解失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    print("🚀 简化版多时段仿真测试")
    print("=" * 60)
    
    success = test_simplified_96periods()
    
    if success:
        print("\n✅ 简化版多时段仿真成功！")
        print("💡 建议：可以逐步增加时段数进行测试")
    else:
        print("\n❌ 简化版多时段仿真失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)