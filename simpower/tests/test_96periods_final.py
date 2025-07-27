#!/usr/bin/env python3
"""
IEEE 50节点96时段最终测试脚本
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.results_analysis_96periods import IEEE50Bus96PeriodsAnalysis


def run_96periods_final():
    """运行96时段仿真并生成分析报告"""
    
    case_dir = 'simpower/tests/ieee_50_96periods_final'
    
    print("🚀 IEEE 50节点96时段经济调度仿真")
    print("=" * 60)
    
    # 验证案例文件
    print("\n🔍 验证案例文件...")
    required_files = ['buses.csv', 'lines.csv', 'generators.csv', 'loads.csv', 'timeseries.csv']
    
    all_exist = True
    for file in required_files:
        path = os.path.join(case_dir, file)
        if os.path.exists(path):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} 缺失")
            all_exist = False
    
    if not all_exist:
        print("\n❌ 案例文件不完整")
        return False
    
    # 运行求解
    print(f"\n🚀 开始96时段经济调度求解...")
    print("⏱️  预计需要5-10分钟，请耐心等待...")
    
    start_time = time.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"\n✅ 求解完成！用时: {solve_time:.2f} 秒 ({solve_time/60:.1f} 分钟)")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 分析结果
        print("\n📊 开始生成96时段分析报告...")
        
        analyzer = IEEE50Bus96PeriodsAnalysis(case_dir, solution)
        analyzer.generate_comprehensive_report()
        
        print("\n🎉 96时段仿真和分析完成！")
        
        # 列出生成的文件
        results_dir = analyzer.results_dir
        if os.path.exists(results_dir):
            print(f"\n📁 生成的文件列表:")
            for file in os.listdir(results_dir):
                file_path = os.path.join(results_dir, file)
                if os.path.isfile(file_path):
                    size_kb = os.path.getsize(file_path) / 1024
                    print(f"  - {file} ({size_kb:.1f} KB)")
        
        return True
        
    except Exception as e:
        solve_time = time.time() - start_time
        print(f"\n❌ 仿真失败: {str(e)}")
        print(f"⏱️  用时: {solve_time:.2f} 秒")
        
        import traceback
        traceback.print_exc()
        
        # 如果是内存或时间问题，建议减少时段数
        if "memory" in str(e).lower() or solve_time > 600:
            print("\n💡 建议：")
            print("  - 尝试减少时段数（如48或24时段）")
            print("  - 增加系统内存")
            print("  - 使用更强大的求解器")
        
        return False


def main():
    """主函数"""
    print("📋 任务：96时段完整仿真")
    print("  - 96个时段（24小时，每15分钟一个时段）")
    print("  - 生成机组组合图")
    print("  - 生成节点加权均价图")
    print("  - 生成其他分析图表")
    print("")
    
    success = run_96periods_final()
    
    if success:
        print("\n✅ 所有任务完成！")
    else:
        print("\n❌ 任务未完成")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)