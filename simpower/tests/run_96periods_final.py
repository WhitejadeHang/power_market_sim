#!/usr/bin/env python3
"""
最终96时段仿真运行脚本
"""

import os
import sys
import time as timer
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.results_analysis_96periods import IEEE50Bus96PeriodsAnalysis


def run_96periods():
    """运行96时段仿真"""
    
    # 使用已创建的96时段案例
    case_dir = 'simpower/tests/ieee_50_96periods_final'
    
    print("🚀 IEEE 50节点96时段完整仿真")
    print("=" * 60)
    print(f"📁 案例目录: {case_dir}")
    
    # 验证文件
    required_files = ['buses.csv', 'lines.csv', 'generators.csv', 'loads.csv', 'timeseries.csv']
    for file in required_files:
        if os.path.exists(os.path.join(case_dir, file)):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} 缺失")
            return False
    
    # 检查并修正generators.csv的列名
    gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    # 重命名列以符合simpower的要求
    column_mapping = {
        'ramp rate': 'rampratemax',
        'start cost': 'startupcost',
        'no load cost': 'noloadcost',
        'type': 'planttype'  # 如果存在type列
    }
    
    for old_col, new_col in column_mapping.items():
        if old_col in gen_df.columns:
            gen_df = gen_df.rename(columns={old_col: new_col})
    
    # 添加缺失的列
    if 'rampratemin' not in gen_df.columns:
        gen_df['rampratemin'] = -gen_df.get('rampratemax', gen_df['P max'] * 0.2)
    
    # 保存修正后的文件
    gen_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    print("\n✅ 已修正generators.csv列名")
    
    # 开始求解
    print("\n🔧 开始96时段经济调度求解...")
    print("⏱️  这可能需要10-20分钟，请耐心等待...")
    
    start_time = timer.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = timer.time() - start_time
        print(f"\n✅ 求解完成！")
        print(f"⏱️  总用时: {solve_time:.2f} 秒 ({solve_time/60:.1f} 分钟)")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 生成分析报告
        print("\n📊 生成96时段分析报告...")
        
        analyzer = IEEE50Bus96PeriodsAnalysis(case_dir, solution)
        analyzer.generate_comprehensive_report()
        
        print("\n🎉 96时段仿真完成！")
        print("\n📋 已生成的内容：")
        print("  ✅ 96时段机组组合图")
        print("  ✅ 关键时段节点加权均价图")
        print("  ✅ 分机组类型发电量图")
        print("  ✅ 统计汇总报告")
        
        return True
        
    except Exception as e:
        solve_time = timer.time() - start_time
        print(f"\n❌ 仿真失败: {str(e)}")
        print(f"⏱️  失败时已用时: {solve_time:.2f} 秒")
        
        import traceback
        traceback.print_exc()
        
        return False


def main():
    """主函数"""
    print("📋 任务目标：")
    print("  1. 完成96时段（24小时）经济调度仿真")
    print("  2. 生成机组组合图")
    print("  3. 生成节点加权均价图")
    print("  4. 生成其他展示内容")
    print("")
    
    success = run_96periods()
    
    if success:
        print("\n✅ 所有任务完成！")
        print("📁 结果保存在: simpower/tests/ieee_50_96periods_final/results_96periods/")
    else:
        print("\n❌ 任务失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)