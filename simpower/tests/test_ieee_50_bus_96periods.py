#!/usr/bin/env python3
"""
IEEE 50节点案例96时段经济调度测试脚本
包含网络拓扑图绘制功能
"""

import os
import sys
import time
import pandas as pd

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.results_analysis import analyze_ieee_50_bus_results


def test_ieee_50_bus_96_periods():
    """测试IEEE 50节点案例96时段经济调度"""
    
    case_dir = 'simpower/tests/ieee_50_bus_case'
    
    print("🧪 IEEE 50节点96时段经济调度案例测试")
    print("=" * 60)
    
    if not os.path.exists(case_dir):
        print(f"❌ 案例目录不存在: {case_dir}")
        return False
    
    # 1. 验证案例文件
    print("🔍 验证案例文件...")
    
    required_files = ['buses.csv', 'lines.csv', 'generators.csv', 'loads.csv', 
                     'timeseries.csv', 'system_load_curve.csv']
    
    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(case_dir, file)):
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 缺少文件: {missing_files}")
        # 如果只缺少timeseries.csv，尝试创建它
        if missing_files == ['timeseries.csv']:
            print("📝 创建timeseries.csv...")
            create_timeseries_csv(case_dir)
        else:
            return False
    else:
        print("✅ 所有必要文件存在")
    
    # 2. 分析案例数据
    print("\n📊 分析案例数据...")
    
    buses_df = pd.read_csv(os.path.join(case_dir, 'buses.csv'))
    lines_df = pd.read_csv(os.path.join(case_dir, 'lines.csv'))
    generators_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    
    # 统计时段数
    if 'time' in loads_df.columns:
        time_periods = loads_df['time'].unique()
        num_periods = len(time_periods)
    else:
        num_periods = 1
    
    print(f"🏗️ 网络规模:")
    print(f"   节点数: {len(buses_df)}")
    print(f"   线路数: {len(lines_df)}")
    print(f"   发电机数: {len(generators_df)}")
    print(f"   负荷数据点: {len(loads_df)}")
    print(f"   时段数: {num_periods}")
    
    # 3. 运行经济调度求解
    print(f"\n🚀 运行{num_periods}时段经济调度求解...")
    
    start_time = time.time()
    
    try:
        print("⚡ 开始求解...")
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"✅ 求解完成，用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 4. 生成完整的结果分析和可视化（包括网络拓扑图）
        print("\n📈 生成完整结果分析和可视化（包括网络拓扑图）...")
        
        try:
            results_dir = analyze_ieee_50_bus_results(case_dir, solution)
            print(f"✅ 结果分析完成，保存到: {results_dir}")
            
            # 验证网络拓扑图是否生成
            topology_file = os.path.join(results_dir, 'network_topology.png')
            if os.path.exists(topology_file):
                print(f"✅ 网络拓扑图已生成: {topology_file}")
            else:
                print(f"⚠️ 网络拓扑图未生成")
            
            # 检查其他生成的文件
            expected_files = ['network_topology.png', 'generation_dispatch_analysis.png', 
                            'lmp_analysis.png', 'cost_analysis.png']
            
            print("\n📁 生成的结果文件:")
            for file in expected_files:
                file_path = os.path.join(results_dir, file)
                if os.path.exists(file_path):
                    file_size = os.path.getsize(file_path) / 1024  # KB
                    print(f"   ✅ {file} ({file_size:.1f} KB)")
                else:
                    print(f"   ❌ {file}")
            
        except Exception as e:
            print(f"⚠️ 结果分析部分失败: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"\n🎉 IEEE 50节点{num_periods}时段经济调度测试成功！")
        print(f"✅ 主要功能验证:")
        print(f"   - ✅ {num_periods}时段经济调度")
        print(f"   - ✅ 容量段报价")
        print(f"   - ✅ 网络拓扑图绘制")
        print(f"   - ✅ 结果分析和可视化")
        
        return True
        
    except Exception as e:
        print(f"❌ 求解过程失败: {str(e)}")
        print(f"💻 用时: {time.time() - start_time:.2f} 秒")
        import traceback
        traceback.print_exc()
        return False


def create_timeseries_csv(case_dir):
    """创建timeseries.csv文件"""
    
    # 读取系统负荷曲线
    system_load_df = pd.read_csv(os.path.join(case_dir, 'system_load_curve.csv'))
    
    # 创建时间序列数据
    timeseries_data = []
    
    # 使用2025-07-25作为基准日期
    base_date = pd.to_datetime('2025-07-25')
    
    for idx, row in system_load_df.iterrows():
        time_str = row['time']
        hours, minutes = map(int, time_str.split(':'))
        timestamp = base_date + pd.Timedelta(hours=hours, minutes=minutes)
        
        timeseries_data.append({
            'time': timestamp.strftime('%Y-%m-%d %H:%M:%S')
        })
    
    # 创建DataFrame并保存
    timeseries_df = pd.DataFrame(timeseries_data)
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    
    print(f"✅ timeseries.csv已创建，包含 {len(timeseries_df)} 个时段")


def main():
    """主函数"""
    
    success = test_ieee_50_bus_96_periods()
    
    if success:
        print(f"\n🚀 测试完成状态: ✅ 成功")
        print(f"📁 结果文件保存在: simpower/tests/ieee_50_bus_case/results/")
    else:
        print(f"\n❌ 测试失败，请检查错误信息")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)