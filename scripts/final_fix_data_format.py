#!/usr/bin/env python3
"""
最终修正数据格式，确保与results_analysis.py兼容
"""

import os
import pandas as pd
import shutil


def fix_single_period_case():
    """修正单时段案例的数据格式"""
    
    case_dir = 'simpower/tests/ieee_50_single_period'
    
    print(f"🔧 修正单时段案例: {case_dir}")
    
    # 1. 修正generators.csv - 添加缺失的列
    print("📝 修正generators.csv...")
    gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    # 从原始案例获取no load cost数据
    orig_gen_df = pd.read_csv('simpower/tests/ieee_50_bus_case/generators.csv')
    
    if 'no load cost' not in gen_df.columns and 'no load cost' in orig_gen_df.columns:
        # 合并no load cost数据
        gen_df = gen_df.merge(orig_gen_df[['name', 'no load cost']], on='name', how='left')
    
    # 确保有plant_type列
    if 'plant_type' not in gen_df.columns:
        gen_df['plant_type'] = 'coal'
    
    gen_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    print(f"✅ generators.csv已修正")
    
    # 2. 修正lines.csv的列名
    print("📝 修正lines.csv列名...")
    lines_df = pd.read_csv(os.path.join(case_dir, 'lines.csv'))
    
    # 检查当前列名
    if 'frombus' in lines_df.columns and 'from bus' not in lines_df.columns:
        lines_df.rename(columns={'frombus': 'from bus', 'tobus': 'to bus'}, inplace=True)
    
    lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
    print(f"✅ lines.csv列名已修正")
    
    return case_dir


def create_complete_single_period_case():
    """创建完整的单时段测试案例"""
    
    src_dir = 'simpower/tests/ieee_50_bus_case'
    dst_dir = 'simpower/tests/ieee_50_complete'
    
    print(f"\n🔧 创建完整的单时段案例: {dst_dir}")
    
    # 创建目录
    os.makedirs(dst_dir, exist_ok=True)
    
    # 1. 复制buses.csv（只保留必要列）
    print("📝 处理buses.csv...")
    buses_df = pd.read_csv(os.path.join(src_dir, 'buses.csv'))
    buses_df = buses_df[['name', 'type']]
    buses_df.to_csv(os.path.join(dst_dir, 'buses.csv'), index=False)
    
    # 2. 复制lines.csv（保持列名为"from bus"和"to bus"）
    print("📝 处理lines.csv...")
    lines_df = pd.read_csv(os.path.join(src_dir, 'lines.csv'))
    lines_df.to_csv(os.path.join(dst_dir, 'lines.csv'), index=False)
    
    # 3. 复制generators.csv（包含所有必要列）
    print("📝 处理generators.csv...")
    gen_df = pd.read_csv(os.path.join(src_dir, 'generators.csv'))
    
    # 确保有plant_type列
    if 'plant_type' not in gen_df.columns and 'type' in gen_df.columns:
        gen_df['plant_type'] = gen_df['type']
    elif 'plant_type' not in gen_df.columns:
        gen_df['plant_type'] = 'coal'
    
    gen_df.to_csv(os.path.join(dst_dir, 'generators.csv'), index=False)
    
    # 4. 复制发电机报价文件
    print("📝 复制发电机报价文件...")
    for _, row in gen_df.iterrows():
        bid_file = row['cost curve points filename']
        src_file = os.path.join(src_dir, bid_file)
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_dir)
    
    # 5. 创建单时段loads.csv
    print("📝 创建loads.csv...")
    loads_df = pd.read_csv(os.path.join(src_dir, 'loads.csv'))
    
    # 计算平均负荷
    simple_loads_data = []
    for idx, row in loads_df.iterrows():
        load_name = row['name']
        bus_name = row['bus'] if 'bus' in row else f"Bus{int(load_name.replace('Load', '')):02d}"
        
        # 读取调度文件计算平均负荷
        if 'schedule filename' in row:
            schedule_path = os.path.join(src_dir, row['schedule filename'])
            if os.path.exists(schedule_path):
                schedule_df = pd.read_csv(schedule_path)
                avg_power = schedule_df['power'].mean()
            else:
                avg_power = 150
        else:
            avg_power = 150
        
        simple_loads_data.append({
            'name': load_name,
            'bus': bus_name,
            'power': avg_power
        })
    
    simple_loads_df = pd.DataFrame(simple_loads_data)
    simple_loads_df.to_csv(os.path.join(dst_dir, 'loads.csv'), index=False)
    
    print(f"✅ 完整案例创建完成")
    
    return dst_dir


def main():
    """主函数"""
    
    print("🚀 最终数据格式修正")
    print("=" * 60)
    
    # 1. 修正现有单时段案例
    fix_single_period_case()
    
    # 2. 创建完整的单时段案例
    complete_case_dir = create_complete_single_period_case()
    
    print(f"\n✅ 所有修正完成！")
    print(f"\n测试命令:")
    print(f"1. 修正后的案例: python3 simpower/tests/test_single_period_only.py")
    print(f"2. 完整案例: python3 -m simpower.solve {complete_case_dir}")


if __name__ == "__main__":
    main()