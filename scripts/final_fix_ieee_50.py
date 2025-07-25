#!/usr/bin/env python3
"""
最终修正IEEE 50节点案例，确保所有格式都与simpower兼容
"""

import os
import pandas as pd
import shutil


def create_working_ieee_50_case():
    """创建一个可工作的IEEE 50节点案例"""
    
    # 源目录和目标目录
    src_dir = 'simpower/tests/ieee_50_bus_case'
    dst_dir = 'simpower/tests/ieee_50_bus_working'
    
    print(f"🔧 创建工作案例: {dst_dir}")
    
    # 创建目标目录
    os.makedirs(dst_dir, exist_ok=True)
    
    # 1. 处理buses.csv
    print("📝 处理buses.csv...")
    buses_df = pd.read_csv(os.path.join(src_dir, 'buses.csv'))
    # 只保留必要的列
    buses_df = buses_df[['name', 'type']]
    buses_df.to_csv(os.path.join(dst_dir, 'buses.csv'), index=False)
    
    # 2. 处理lines.csv - 修正列名
    print("📝 处理lines.csv...")
    lines_df = pd.read_csv(os.path.join(src_dir, 'lines.csv'))
    lines_df.columns = ['frombus', 'tobus', 'Pmax']  # 修正列名
    lines_df.to_csv(os.path.join(dst_dir, 'lines.csv'), index=False)
    
    # 3. 处理generators.csv
    print("📝 处理generators.csv...")
    gen_df = pd.read_csv(os.path.join(src_dir, 'generators.csv'))
    gen_df.to_csv(os.path.join(dst_dir, 'generators.csv'), index=False)
    
    # 4. 复制发电机报价文件
    print("📝 复制发电机报价文件...")
    for _, row in gen_df.iterrows():
        bid_file = row['cost curve points filename']
        src_file = os.path.join(src_dir, bid_file)
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_dir)
    
    # 5. 处理loads.csv - 确保有bus列
    print("📝 处理loads.csv...")
    loads_df = pd.read_csv(os.path.join(src_dir, 'loads.csv'))
    
    # 如果有调度文件，保留schedule filename列
    if 'schedule filename' in loads_df.columns:
        # 多时段案例
        loads_df = loads_df[['name', 'bus', 'schedule filename']]
        loads_df['schedulefilename'] = loads_df['schedule filename']  # 添加期望的列名
        loads_df = loads_df[['name', 'bus', 'schedulefilename']]
        
        # 复制负荷调度文件
        print("📝 复制负荷调度文件...")
        for _, row in loads_df.iterrows():
            schedule_file = row['schedulefilename']
            src_file = os.path.join(src_dir, schedule_file)
            if os.path.exists(src_file):
                shutil.copy2(src_file, dst_dir)
        
        # 创建timeseries.csv
        print("📝 创建timeseries.csv...")
        system_load_df = pd.read_csv(os.path.join(src_dir, 'system_load_curve.csv'))
        
        timeseries_data = []
        base_date = pd.to_datetime('2025-07-25')
        
        for idx, row in system_load_df.iterrows():
            time_str = row['time']
            hours, minutes = map(int, time_str.split(':'))
            timestamp = base_date + pd.Timedelta(hours=hours, minutes=minutes)
            
            timeseries_data.append({
                'time': timestamp.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        timeseries_df = pd.DataFrame(timeseries_data)
        timeseries_df.to_csv(os.path.join(dst_dir, 'timeseries.csv'), index=False)
        
    else:
        # 单时段案例
        if 'power' not in loads_df.columns:
            loads_df['power'] = 100  # 默认值
        loads_df = loads_df[['name', 'bus', 'power']]
    
    loads_df.to_csv(os.path.join(dst_dir, 'loads.csv'), index=False)
    
    print(f"\n✅ 工作案例创建完成: {dst_dir}")
    
    return dst_dir


def create_single_period_test():
    """创建单时段测试案例"""
    
    src_dir = 'simpower/tests/ieee_50_bus_case'
    dst_dir = 'simpower/tests/ieee_50_single_period'
    
    print(f"\n🔧 创建单时段测试案例: {dst_dir}")
    
    os.makedirs(dst_dir, exist_ok=True)
    
    # 复制基本文件
    shutil.copy2(os.path.join(src_dir, 'buses.csv'), dst_dir)
    shutil.copy2(os.path.join(src_dir, 'lines.csv'), dst_dir)
    shutil.copy2(os.path.join(src_dir, 'generators.csv'), dst_dir)
    
    # 修正buses.csv
    buses_df = pd.read_csv(os.path.join(dst_dir, 'buses.csv'))
    buses_df = buses_df[['name', 'type']]
    buses_df.to_csv(os.path.join(dst_dir, 'buses.csv'), index=False)
    
    # 修正lines.csv列名
    lines_df = pd.read_csv(os.path.join(dst_dir, 'lines.csv'))
    lines_df.columns = ['frombus', 'tobus', 'Pmax']
    lines_df.to_csv(os.path.join(dst_dir, 'lines.csv'), index=False)
    
    # 复制发电机报价文件
    gen_df = pd.read_csv(os.path.join(dst_dir, 'generators.csv'))
    for _, row in gen_df.iterrows():
        bid_file = row['cost curve points filename']
        src_file = os.path.join(src_dir, bid_file)
        if os.path.exists(src_file):
            shutil.copy2(src_file, dst_dir)
    
    # 创建单时段loads.csv
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
    
    print(f"✅ 单时段测试案例创建完成")
    
    return dst_dir


def main():
    """主函数"""
    
    print("🚀 最终修正IEEE 50节点案例")
    print("=" * 60)
    
    # 1. 创建工作案例（多时段）
    working_dir = create_working_ieee_50_case()
    
    # 2. 创建单时段测试案例
    single_period_dir = create_single_period_test()
    
    print(f"\n✅ 所有案例创建完成！")
    print(f"\n测试命令:")
    print(f"1. 单时段测试: python3 -m simpower.solve {single_period_dir}")
    print(f"2. 多时段测试: python3 -m simpower.solve {working_dir}")


if __name__ == "__main__":
    main()