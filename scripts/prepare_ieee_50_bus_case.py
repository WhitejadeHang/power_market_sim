#!/usr/bin/env python3
"""
准备IEEE 50节点案例的数据，确保格式正确
"""

import os
import sys
import pandas as pd

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


def fix_generators_csv(case_dir):
    """修正generators.csv的格式"""
    
    print("📝 修正generators.csv...")
    
    # 读取现有文件
    gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    # 添加必要的列
    if 'P min' not in gen_df.columns:
        gen_df['P min'] = gen_df['P max'] * 0.1  # 最小出力设为最大出力的10%
    
    # 确保列名正确
    if 'type' in gen_df.columns and 'plant_type' not in gen_df.columns:
        gen_df['plant_type'] = gen_df['type']
    
    # 重新排列列顺序，匹配ieee_50_simple案例
    column_order = ['name', 'bus', 'P min', 'P max', 'cost curve points filename']
    
    # 只保留需要的列
    gen_df = gen_df[column_order]
    
    # 保存
    gen_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    
    print(f"✅ generators.csv已修正，包含 {len(gen_df)} 台发电机")
    
    return gen_df


def verify_load_schedules(case_dir):
    """验证负荷调度文件"""
    
    print("\n📝 验证负荷调度文件...")
    
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    
    verified_count = 0
    for idx, row in loads_df.iterrows():
        schedule_file = row['schedule filename']
        file_path = os.path.join(case_dir, schedule_file)
        
        if os.path.exists(file_path):
            # 检查文件格式
            schedule_df = pd.read_csv(file_path)
            if 'time' in schedule_df.columns and 'power' in schedule_df.columns:
                verified_count += 1
            else:
                print(f"⚠️ {schedule_file} 格式不正确")
        else:
            print(f"❌ {schedule_file} 不存在")
    
    print(f"✅ 验证完成: {verified_count}/{len(loads_df)} 个调度文件有效")
    
    return verified_count == len(loads_df)


def create_simple_case_for_testing(case_dir):
    """创建一个简化的单时段案例用于初步测试"""
    
    print("\n📝 创建简化的单时段测试案例...")
    
    # 创建新目录
    simple_case_dir = os.path.join(os.path.dirname(case_dir), 'ieee_50_bus_simple_test')
    os.makedirs(simple_case_dir, exist_ok=True)
    
    # 复制基础文件
    import shutil
    for file in ['buses.csv', 'lines.csv']:
        shutil.copy2(os.path.join(case_dir, file), simple_case_dir)
    
    # 创建简化的generators.csv
    gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    if 'P min' not in gen_df.columns:
        gen_df['P min'] = gen_df['P max'] * 0.1
    
    # 修正节点名称格式
    gen_df['bus'] = gen_df['bus'].apply(lambda x: x.split('_')[0] if '_' in x else x)
    
    gen_df[['name', 'bus', 'P min', 'P max', 'cost curve points filename']].to_csv(
        os.path.join(simple_case_dir, 'generators.csv'), index=False
    )
    
    # 复制发电机报价文件
    for _, row in gen_df.iterrows():
        bid_file = row['cost curve points filename']
        src = os.path.join(case_dir, bid_file)
        if os.path.exists(src):
            shutil.copy2(src, simple_case_dir)
    
    # 创建简化的loads.csv（单时段）
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    
    # 计算每个负荷的平均值
    simple_loads_data = []
    for idx, row in loads_df.iterrows():
        load_name = row['name']
        bus_name = load_name.split('_')[0] if '_' in load_name else load_name
        
        # 读取调度文件计算平均负荷
        schedule_file = row['schedule filename']
        schedule_path = os.path.join(case_dir, schedule_file)
        
        if os.path.exists(schedule_path):
            schedule_df = pd.read_csv(schedule_path)
            avg_power = schedule_df['power'].mean()
        else:
            avg_power = 100  # 默认值
        
        simple_loads_data.append({
            'name': f"Load{int(load_name.split('_')[1]):02d}" if '_' in load_name else load_name,
            'bus': bus_name,
            'power': avg_power
        })
    
    simple_loads_df = pd.DataFrame(simple_loads_data)
    simple_loads_df.to_csv(os.path.join(simple_case_dir, 'loads.csv'), index=False)
    
    print(f"✅ 简化案例已创建: {simple_case_dir}")
    
    return simple_case_dir


def main():
    """主函数"""
    
    case_dir = 'simpower/tests/ieee_50_bus_case'
    
    print("🔧 准备IEEE 50节点案例数据")
    print("=" * 60)
    
    if not os.path.exists(case_dir):
        print(f"❌ 案例目录不存在: {case_dir}")
        return
    
    # 1. 修正generators.csv
    fix_generators_csv(case_dir)
    
    # 2. 验证负荷调度文件
    schedules_ok = verify_load_schedules(case_dir)
    
    if not schedules_ok:
        print("\n⚠️ 负荷调度文件存在问题")
    
    # 3. 创建简化测试案例
    simple_case_dir = create_simple_case_for_testing(case_dir)
    
    print(f"\n✅ 数据准备完成！")
    print(f"\n下一步:")
    print(f"1. 测试简化案例: python3 -m simpower.solve {simple_case_dir}")
    print(f"2. 测试完整案例: python3 simpower/tests/test_ieee_50_bus_96periods.py")


if __name__ == "__main__":
    main()