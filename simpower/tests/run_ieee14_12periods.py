#!/usr/bin/env python3
"""
运行IEEE 14节点12时段仿真
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.ieee14_12periods_analysis import IEEE14Analysis


def run_ieee14_12periods():
    """运行IEEE 14节点12时段仿真"""
    
    case_dir = 'simpower/tests/ieee14_12periods'
    
    print("🚀 IEEE 14节点12时段仿真")
    print("=" * 60)
    print("📋 任务内容:")
    print("  - 7台机组容量段报价")
    print("  - 12个连续时段（12小时）")
    print("  - 生成完整分析报告")
    print("")
    
    # 验证案例文件
    print("🔍 验证案例文件...")
    required_files = ['buses.csv', 'lines.csv', 'generators.csv', 'loads.csv', 'timeseries.csv']
    
    for file in required_files:
        if os.path.exists(os.path.join(case_dir, file)):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} 缺失")
            return False
    
    # 验证报价文件
    print("\n💰 验证容量段报价文件...")
    bid_files = [
        'G1_Steam_block_bid.csv',
        'G2_Hydro_block_bid.csv', 
        'G3_Gas_block_bid.csv',
        'G4_Coal_block_bid.csv',
        'G5_Nuclear_block_bid.csv',
        'G6_Peaker_block_bid.csv',
        'G7_Wind_linear_bid.csv'
    ]
    
    for file in bid_files:
        if os.path.exists(os.path.join(case_dir, file)):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} 缺失")
    
    # 运行求解
    print("\n⚙️ 开始12时段经济调度求解...")
    start_time = time.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"\n✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 生成分析报告
        print("\n📊 生成完整分析报告...")
        analyzer = IEEE14Analysis(case_dir, solution)
        analyzer.generate_full_report()
        
        print("\n🎉 仿真完成！")
        print("\n📋 已生成的内容:")
        print("  1️⃣ 网络拓扑图")
        print("  2️⃣ 12时段负荷曲线")
        print("  3️⃣ 机组组合状态图")
        print("  4️⃣ 机组出力详情")
        print("  5️⃣ 节点电价分析")
        print("  6️⃣ 系统费用报告")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 仿真失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    success = run_ieee14_12periods()
    
    if success:
        print("\n✅ 所有任务完成！")
        print("📁 结果保存在: simpower/tests/ieee14_12periods/results/")
    else:
        print("\n❌ 任务失败")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)