#!/usr/bin/env python3
"""
运行IEEE 14节点24时段（1天）煤电机组仿真
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.ieee14_72periods_analysis import IEEE14MultiPeriodAnalysis


def run_simulation():
    """运行24时段仿真"""
    
    case_dir = 'simpower/tests/ieee14_24periods_coal'
    
    print("🚀 IEEE 14节点24时段（1天）煤电机组仿真")
    print("=" * 60)
    print("📅 仿真周期: 1天，24时段")
    print("⚡ 发电机组: 7台煤电机组")
    print("=" * 60)
    
    # 运行求解
    print("\n⚙️ 开始24时段机组组合优化求解...")
    start_time = time.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"\n✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 生成分析报告
        print("\n📊 生成24时段完整分析报告...")
        analyzer = IEEE14MultiPeriodAnalysis(case_dir, solution)
        analyzer.generate_full_report()
        
        print("\n🎉 仿真完成！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 仿真失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_simulation()
    sys.exit(0 if success else 1)