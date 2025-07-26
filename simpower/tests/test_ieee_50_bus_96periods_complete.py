#!/usr/bin/env python3
"""
IEEE 50节点案例96时段完整仿真测试脚本
生成机组组合图、节点加权均价图等详细可视化结果
"""

import os
import sys
import time

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.results_analysis_96periods import analyze_ieee_50_bus_96periods_results


def run_96periods_simulation():
    """运行96时段完整仿真"""
    
    case_dir = 'simpower/tests/ieee_50_bus_working'
    
    print("🧪 IEEE 50节点96时段完整仿真")
    print("=" * 60)
    
    if not os.path.exists(case_dir):
        print(f"❌ 案例目录不存在: {case_dir}")
        return False
    
    # 1. 验证案例文件
    print("\n🔍 验证案例文件...")
    
    required_files = ['buses.csv', 'lines.csv', 'generators.csv', 'loads.csv', 
                     'timeseries.csv']
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(case_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        return False
    
    print("✅ 所有必要文件存在")
    
    # 2. 运行96时段经济调度求解
    print(f"\n🚀 开始96时段经济调度求解...")
    print("⏱️  这可能需要几分钟时间，请耐心等待...")
    
    start_time = time.time()
    
    try:
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"✅ 求解完成，用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 3. 生成96时段的详细分析和可视化
        print("\n📈 生成96时段详细分析和可视化...")
        
        results_dir = analyze_ieee_50_bus_96periods_results(case_dir, solution)
        
        print(f"\n✅ 96时段仿真完成！")
        print(f"📁 结果保存在: {results_dir}")
        
        # 列出生成的文件
        print("\n📊 生成的可视化文件:")
        expected_files = [
            'unit_commitment_96periods.png',  # 机组组合图
            'weighted_lmp_key_periods.png',   # 关键时段节点加权均价图
            'lmp_heatmap_96periods.png',      # LMP热力图
            'generation_by_type_96periods.png', # 分机组类型发电量图
            'summary_statistics.json'          # 汇总统计报告
        ]
        
        for file in expected_files:
            file_path = os.path.join(results_dir, file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"   ✅ {file} ({file_size:.1f} KB)")
            else:
                print(f"   ❌ {file}")
        
        return True
        
    except Exception as e:
        print(f"❌ 仿真过程失败: {str(e)}")
        print(f"💻 用时: {time.time() - start_time:.2f} 秒")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主函数"""
    
    print("🚀 开始IEEE 50节点96时段完整仿真任务")
    print("📋 任务内容:")
    print("   1. 运行96时段经济调度优化")
    print("   2. 生成机组组合图")
    print("   3. 生成各时段节点加权均价图")
    print("   4. 生成其他相关可视化结果")
    print("")
    
    success = run_96periods_simulation()
    
    if success:
        print("\n🎉 任务完成！")
        print("✅ 已生成以下内容:")
        print("   - 96时段机组组合图 (显示每个时段各机组的开停状态)")
        print("   - 关键时段节点加权均价图 (显示不同时段的电价分布)")
        print("   - LMP时序热力图 (显示所有节点在96时段的电价变化)")
        print("   - 分机组类型发电量图 (显示不同类型机组的发电贡献)")
        print("   - 详细统计报告 (JSON格式)")
    else:
        print("\n❌ 任务失败，请检查错误信息")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)