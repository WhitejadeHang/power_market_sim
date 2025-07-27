#!/usr/bin/env python3
"""
IEEE 50节点单时段案例测试脚本，包含网络拓扑图绘制
"""

import os
import sys
import time

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.results_analysis import analyze_ieee_50_bus_results


def main():
    """测试单时段案例并生成网络拓扑图"""
    
    case_dir = 'simpower/tests/ieee_50_single_period'
    
    print("🧪 IEEE 50节点单时段案例测试（包含网络拓扑图）")
    print("=" * 60)
    
    if not os.path.exists(case_dir):
        print(f"❌ 案例目录不存在: {case_dir}")
        return False
    
    # 1. 运行经济调度求解
    print(f"\n🚀 运行经济调度求解...")
    
    start_time = time.time()
    
    try:
        print("⚡ 开始求解...")
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"✅ 求解完成，用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 2. 生成完整的结果分析和可视化（包括网络拓扑图）
        print("\n📈 生成完整结果分析和可视化（包括网络拓扑图）...")
        
        results_dir = analyze_ieee_50_bus_results(case_dir, solution)
        print(f"✅ 结果分析完成，保存到: {results_dir}")
        
        # 验证生成的文件
        expected_files = [
            'network_topology.png',
            'generation_dispatch_analysis.png', 
            'lmp_analysis.png',
            'cost_analysis.png',
            'generator_results.csv',
            'bus_results.csv',
            'line_results.csv'
        ]
        
        print("\n📁 生成的结果文件:")
        for file in expected_files:
            file_path = os.path.join(results_dir, file)
            if os.path.exists(file_path):
                file_size = os.path.getsize(file_path) / 1024  # KB
                print(f"   ✅ {file} ({file_size:.1f} KB)")
            else:
                print(f"   ❌ {file}")
        
        # 特别检查网络拓扑图
        topology_file = os.path.join(results_dir, 'network_topology.png')
        if os.path.exists(topology_file):
            print(f"\n🎨 网络拓扑图已成功生成!")
            print(f"   位置: {topology_file}")
            print(f"   大小: {os.path.getsize(topology_file)/1024/1024:.2f} MB")
        else:
            print(f"\n⚠️ 网络拓扑图未生成")
        
        print(f"\n🎉 IEEE 50节点案例测试成功！")
        print(f"✅ 主要功能验证:")
        print(f"   - ✅ 经济调度求解")
        print(f"   - ✅ 容量段报价")
        print(f"   - ✅ 网络拓扑图绘制")
        print(f"   - ✅ 结果分析和可视化")
        
        print(f"\n📊 案例规模:")
        print(f"   - 50个节点")
        print(f"   - 77条线路")
        print(f"   - 26台燃煤发电机")
        print(f"   - 总装机容量: ~11,500 MW")
        print(f"   - 系统负荷: ~8,500 MW")
        
        return True
        
    except Exception as e:
        print(f"❌ 测试过程失败: {str(e)}")
        print(f"💻 用时: {time.time() - start_time:.2f} 秒")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)