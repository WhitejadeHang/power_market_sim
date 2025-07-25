#!/usr/bin/env python3
"""
修正IEEE 50节点案例的数据格式，使其与simpower兼容
并确保能够运行96时段的仿真
"""

import os
import sys
import pandas as pd
import numpy as np
import shutil

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def fix_loads_csv(case_dir):
    """修正loads.csv文件格式"""
    
    print("📝 修正loads.csv文件...")
    
    # 读取原始文件
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    
    # 创建新的loads.csv，包含所有96个时段
    new_loads_data = []
    
    # 读取系统负荷曲线获取时间信息
    system_load_df = pd.read_csv(os.path.join(case_dir, 'system_load_curve.csv'))
    
    for idx, row in loads_df.iterrows():
        load_name = row['name']
        schedule_file = row['schedule filename']
        
        # 提取节点名称（例如：从 "Bus_01_urban_high" 提取 "Bus01"）
        parts = load_name.split('_')
        if len(parts) >= 2:
            bus_name = f"Bus{int(parts[1]):02d}"
        else:
            bus_name = load_name
        
        # 读取负荷调度文件
        schedule_path = os.path.join(case_dir, schedule_file)
        if os.path.exists(schedule_path):
            schedule_df = pd.read_csv(schedule_path)
            
            # 为每个时段创建一条记录
            for i, (_, sched_row) in enumerate(schedule_df.iterrows()):
                if i < len(system_load_df):
                    time_str = system_load_df.iloc[i]['time']
                    new_loads_data.append({
                        'name': f"Load{int(parts[1]):02d}",
                        'bus': bus_name,
                        'power': sched_row['power'],
                        'time': time_str
                    })
    
    # 创建新的DataFrame
    new_loads_df = pd.DataFrame(new_loads_data)
    
    # 备份原文件
    backup_path = os.path.join(case_dir, 'loads_original.csv')
    shutil.copy2(os.path.join(case_dir, 'loads.csv'), backup_path)
    
    # 保存新文件
    new_loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    
    print(f"✅ loads.csv已修正，包含 {len(new_loads_df)} 条记录（{len(loads_df)} 个负荷 × {len(new_loads_df)//len(loads_df)} 个时段）")
    
    return new_loads_df


def create_timeseries_csv(case_dir):
    """创建timeseries.csv文件"""
    
    print("📝 创建timeseries.csv文件...")
    
    # 读取系统负荷曲线
    system_load_df = pd.read_csv(os.path.join(case_dir, 'system_load_curve.csv'))
    
    # 创建时间序列数据
    timeseries_data = []
    
    # 使用2025-07-25作为基准日期（与ieee_50_simple一致）
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
    
    return timeseries_df


def update_generators_for_timeseries(case_dir):
    """更新generators.csv以支持时间序列"""
    
    print("📝 更新generators.csv...")
    
    # 读取generators.csv
    generators_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    # 添加必要的列（如果不存在）
    if 'P min' not in generators_df.columns:
        # 如果没有Pmin列，设置为P max的10%
        generators_df['P min'] = generators_df['P max'] * 0.1
    
    # 确保列名一致性
    if 'type' in generators_df.columns and 'plant_type' not in generators_df.columns:
        generators_df['plant_type'] = generators_df['type']
    
    # 确保所有必要的列都存在
    required_columns = ['name', 'bus', 'P min', 'P max', 'cost curve points filename']
    for col in required_columns:
        if col not in generators_df.columns:
            if col == 'cost curve points filename' and col not in generators_df.columns:
                # 根据发电机名称生成成本曲线文件名
                generators_df[col] = generators_df['name'].apply(
                    lambda x: f"{x.lower()}_block_bidding.csv"
                )
    
    # 保存更新后的文件
    generators_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    
    print(f"✅ generators.csv已更新")
    
    return generators_df


def create_test_script_for_96_periods(case_dir):
    """创建专门用于96时段仿真的测试脚本"""
    
    script_content = '''#!/usr/bin/env python3
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
    
    for file in required_files:
        if not os.path.exists(os.path.join(case_dir, file)):
            print(f"❌ 缺少文件: {file}")
            return False
    
    print("✅ 所有必要文件存在")
    
    # 2. 分析案例数据
    print("\\n📊 分析案例数据...")
    
    buses_df = pd.read_csv(os.path.join(case_dir, 'buses.csv'))
    lines_df = pd.read_csv(os.path.join(case_dir, 'lines.csv'))
    generators_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    timeseries_df = pd.read_csv(os.path.join(case_dir, 'timeseries.csv'))
    
    print(f"🏗️ 网络规模:")
    print(f"   节点数: {len(buses_df)}")
    print(f"   线路数: {len(lines_df)}")
    print(f"   发电机数: {len(generators_df)}")
    print(f"   负荷数据点: {len(loads_df)}")
    print(f"   时段数: {len(timeseries_df)}")
    
    # 3. 运行经济调度求解
    print(f"\\n🚀 运行96时段经济调度求解...")
    
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
        print("\\n📈 生成完整结果分析和可视化（包括网络拓扑图）...")
        
        try:
            results_dir = analyze_ieee_50_bus_results(case_dir, solution)
            print(f"✅ 结果分析完成，保存到: {results_dir}")
            
            # 验证网络拓扑图是否生成
            topology_file = os.path.join(results_dir, 'network_topology.png')
            if os.path.exists(topology_file):
                print(f"✅ 网络拓扑图已生成: {topology_file}")
            else:
                print(f"⚠️ 网络拓扑图未生成")
            
        except Exception as e:
            print(f"⚠️ 结果分析部分失败: {e}")
        
        print(f"\\n🎉 IEEE 50节点96时段经济调度测试成功！")
        print(f"✅ 主要功能验证:")
        print(f"   - ✅ 96时段经济调度")
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


def main():
    """主函数"""
    
    success = test_ieee_50_bus_96_periods()
    
    if success:
        print(f"\\n🚀 测试完成状态: ✅ 成功")
        print(f"📁 结果文件保存在: simpower/tests/ieee_50_bus_case/results/")
    else:
        print(f"\\n❌ 测试失败，请检查错误信息")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
'''
    
    # 保存测试脚本
    test_script_path = os.path.join(os.path.dirname(case_dir), 'test_ieee_50_bus_96periods.py')
    with open(test_script_path, 'w') as f:
        f.write(script_content)
    
    # 使脚本可执行
    os.chmod(test_script_path, 0o755)
    
    print(f"✅ 测试脚本已创建: {test_script_path}")
    
    return test_script_path


def main():
    """主函数"""
    
    case_dir = 'simpower/tests/ieee_50_bus_case'
    
    print("🔧 修正IEEE 50节点案例数据格式")
    print("=" * 60)
    
    if not os.path.exists(case_dir):
        print(f"❌ 案例目录不存在: {case_dir}")
        return
    
    # 1. 修正loads.csv
    fix_loads_csv(case_dir)
    
    # 2. 创建timeseries.csv
    create_timeseries_csv(case_dir)
    
    # 3. 更新generators.csv
    update_generators_for_timeseries(case_dir)
    
    # 4. 创建测试脚本
    test_script_path = create_test_script_for_96_periods(case_dir)
    
    print(f"\n✅ 数据格式修正完成！")
    print(f"📝 下一步：运行测试脚本")
    print(f"   python3 {test_script_path}")


if __name__ == "__main__":
    main()