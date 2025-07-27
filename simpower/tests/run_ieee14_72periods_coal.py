#!/usr/bin/env python3
"""
运行IEEE 14节点3天72时段煤电仿真
"""

import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.ieee14_72periods_analysis import IEEE14MultiPeriodAnalysis
from simpower.ieee14_analysis import get_chinese_font


def run_simulation():
    """运行仿真"""
    
    print("🚀 IEEE 14节点3天72时段煤电机组仿真")
    print("="*60)
    print("📅 仿真周期: 3天，72时段")
    print("⚡ 发电机组: 9台煤电机组")
    print("🎯 目标: 实现机组启停优化")
    print("="*60)
    
    case_dir = 'simpower/tests/ieee14_72periods_coal'
    
    print("\n⚙️ 开始72时段机组组合优化求解...")
    
    start_time = time.time()
    
    try:
        # 求解问题
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"\n✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        # 分析结果
        print("\n📊 生成72时段完整分析报告...")
        analysis = IEEE14MultiPeriodAnalysis(case_dir, solution)
        analysis.generate_full_report()
        
        print("\n🎉 仿真完成！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 仿真失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 加载中文字体
    chinese_font = get_chinese_font()
    if chinese_font:
        font_name = chinese_font.get_name()
        print(f"✅ 成功加载中文字体: {font_name}")
    
    run_simulation()