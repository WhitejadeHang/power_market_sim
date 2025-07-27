#!/usr/bin/env python3
"""
创建IEEE 14节点5天120时段煤电案例
设计目标：实现机组启停
"""

import os
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def create_120periods_case():
    """创建120时段案例"""
    
    print("🔨 创建IEEE 14节点5天120时段煤电案例\n")
    
    # 源目录和目标目录
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    target_dir = 'simpower/tests/ieee14_120periods_coal'
    
    # 创建目标目录
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    shutil.copytree(source_dir, target_dir)
    
    print(f"✅ 复制基础案例到: {target_dir}")
    
    return target_dir


def design_generators(case_dir):
    """重新设计发电机组 - 调整容量等级"""
    
    print("\n⚡ 设计发电机组容量等级")
    print("="*60)
    
    # 重新设计9台煤电机组，分为三个等级
    generators_data = [
        # 大型基荷机组（高效率，低成本，高最小运行/停机时间）
        {'name': 'G1', 'bus': 'Bus01', 'P min': 60, 'P max': 200, 'type': 'large_baseload',
         'minuptime': 8, 'mindowntime': 8, 'startupcost': 5000, 'shutdowncost': 2000,
         'rampratemax': 60, 'rampratemin': -60, 'noloadcost': 1000},
        
        {'name': 'G2', 'bus': 'Bus02', 'P min': 50, 'P max': 150, 'type': 'large_baseload',
         'minuptime': 8, 'mindowntime': 8, 'startupcost': 4000, 'shutdowncost': 1500,
         'rampratemax': 45, 'rampratemin': -45, 'noloadcost': 800},
        
        {'name': 'G3', 'bus': 'Bus03', 'P min': 40, 'P max': 120, 'type': 'large_baseload',
         'minuptime': 6, 'mindowntime': 6, 'startupcost': 3000, 'shutdowncost': 1200,
         'rampratemax': 40, 'rampratemin': -40, 'noloadcost': 600},
        
        # 中型负荷跟踪机组（中等效率，适度灵活）
        {'name': 'G4', 'bus': 'Bus06', 'P min': 20, 'P max': 80, 'type': 'medium_cycling',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 2000, 'shutdowncost': 800,
         'rampratemax': 40, 'rampratemin': -40, 'noloadcost': 400},
        
        {'name': 'G5', 'bus': 'Bus06', 'P min': 15, 'P max': 60, 'type': 'medium_cycling',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 1500, 'shutdowncost': 600,
         'rampratemax': 30, 'rampratemin': -30, 'noloadcost': 300},
        
        {'name': 'G6', 'bus': 'Bus08', 'P min': 15, 'P max': 50, 'type': 'medium_cycling',
         'minuptime': 3, 'mindowntime': 3, 'startupcost': 1200, 'shutdowncost': 500,
         'rampratemax': 25, 'rampratemin': -25, 'noloadcost': 250},
        
        # 小型调峰机组（低效率，高成本，但灵活）
        {'name': 'G7', 'bus': 'Bus08', 'P min': 10, 'P max': 40, 'type': 'small_peaking',
         'minuptime': 2, 'mindowntime': 2, 'startupcost': 800, 'shutdowncost': 300,
         'rampratemax': 30, 'rampratemin': -30, 'noloadcost': 200},
        
        {'name': 'G8', 'bus': 'Bus13', 'P min': 5, 'P max': 30, 'type': 'small_peaking',
         'minuptime': 2, 'mindowntime': 2, 'startupcost': 600, 'shutdowncost': 200,
         'rampratemax': 25, 'rampratemin': -25, 'noloadcost': 150},
        
        {'name': 'G9', 'bus': 'Bus14', 'P min': 5, 'P max': 25, 'type': 'small_peaking',
         'minuptime': 1, 'mindowntime': 1, 'startupcost': 500, 'shutdowncost': 150,
         'rampratemax': 20, 'rampratemin': -20, 'noloadcost': 100},
    ]
    
    # 创建DataFrame
    gen_df = pd.DataFrame(generators_data)
    
    # 添加报价文件名列
    gen_df['costcurvepointsfilename'] = gen_df['name'].apply(lambda x: f'{x}_block_bid.csv')
    
    # 保存发电机文件
    gen_df[['name', 'bus', 'P min', 'P max', 'minuptime', 'mindowntime', 
            'rampratemax', 'rampratemin', 'startupcost', 'shutdowncost',
            'noloadcost', 'costcurvepointsfilename']].to_csv(
        f'{case_dir}/generators.csv', index=False)
    
    # 打印机组分类
    print("\n机组容量等级分类:")
    for gen_type in ['large_baseload', 'medium_cycling', 'small_peaking']:
        type_gens = gen_df[gen_df['type'] == gen_type]
        total_cap = type_gens['P max'].sum()
        print(f"\n{gen_type}:")
        for _, gen in type_gens.iterrows():
            print(f"  {gen['name']}: {gen['P min']}-{gen['P max']} MW, "
                  f"最小运行/停机: {gen['minuptime']}/{gen['mindowntime']}h")
        print(f"  小计: {len(type_gens)}台, 总容量 {total_cap} MW")
    
    # 系统总容量
    total_pmin = gen_df['P min'].sum()
    total_pmax = gen_df['P max'].sum()
    print(f"\n系统总容量: Pmin={total_pmin} MW, Pmax={total_pmax} MW")
    
    return gen_df


def create_bid_curves(case_dir, gen_df):
    """创建容量段报价曲线"""
    
    print("\n💰 创建容量段报价曲线")
    print("="*60)
    
    # 基础价格设置（按机组类型）
    base_prices = {
        'large_baseload': 50,    # 大型基荷机组成本最低
        'medium_cycling': 80,    # 中型机组成本中等
        'small_peaking': 120     # 小型调峰机组成本最高
    }
    
    for _, gen in gen_df.iterrows():
        gen_name = gen['name']
        pmin = gen['P min']
        pmax = gen['P max']
        gen_type = gen['type']
        
        # 基础价格
        base_price = base_prices[gen_type]
        
        # 4段报价，边际成本递增
        power_points = [
            pmin,
            pmin + (pmax - pmin) * 0.33,
            pmin + (pmax - pmin) * 0.67,
            pmax
        ]
        
        # 边际成本系数
        marginal_factors = [1.0, 1.2, 1.5, 2.0]
        marginal_costs = [base_price * factor for factor in marginal_factors]
        
        # 计算累积成本
        costs = [0.0]
        for i in range(1, len(power_points)):
            power_increment = power_points[i] - power_points[i-1]
            cost_increment = power_increment * marginal_costs[i-1]
            costs.append(costs[-1] + cost_increment)
        
        # 保存报价文件
        bid_df = pd.DataFrame({
            'power': power_points,
            'cost': costs
        })
        bid_df.to_csv(f'{case_dir}/{gen_name}_block_bid.csv', index=False)
    
    print("✅ 所有机组报价文件已创建")


def design_load_pattern():
    """设计5天负荷模式"""
    
    print("\n📈 设计5天负荷模式")
    print("="*60)
    
    # 设计5天不同的负荷模式
    daily_patterns = {
        'workday_normal': {  # 正常工作日
            'name': '正常工作日',
            'base_factor': 0.75,
            'hourly': [
                0.65, 0.62, 0.60, 0.58, 0.60, 0.63,  # 0-5时
                0.68, 0.75, 0.85, 0.90, 0.92, 0.90,  # 6-11时
                0.88, 0.86, 0.87, 0.89, 0.91, 0.93,  # 12-17时
                0.90, 0.85, 0.78, 0.72, 0.68, 0.66   # 18-23时
            ]
        },
        'workday_high': {  # 高负荷工作日
            'name': '高负荷工作日',
            'base_factor': 0.85,
            'hourly': [
                0.70, 0.68, 0.66, 0.65, 0.67, 0.70,  # 0-5时
                0.75, 0.82, 0.90, 0.95, 0.97, 0.95,  # 6-11时
                0.93, 0.92, 0.93, 0.95, 0.97, 0.98,  # 12-17时
                0.95, 0.90, 0.83, 0.77, 0.73, 0.71   # 18-23时
            ]
        },
        'weekend': {  # 周末
            'name': '周末',
            'base_factor': 0.65,
            'hourly': [
                0.60, 0.58, 0.56, 0.55, 0.56, 0.58,  # 0-5时
                0.60, 0.65, 0.70, 0.75, 0.78, 0.80,  # 6-11时
                0.82, 0.83, 0.82, 0.80, 0.78, 0.75,  # 12-17时
                0.72, 0.70, 0.68, 0.65, 0.62, 0.60   # 18-23时
            ]
        },
        'workday_low': {  # 低负荷工作日
            'name': '低负荷工作日',
            'base_factor': 0.70,
            'hourly': [
                0.58, 0.55, 0.53, 0.52, 0.53, 0.55,  # 0-5时
                0.60, 0.68, 0.75, 0.80, 0.82, 0.80,  # 6-11时
                0.78, 0.76, 0.77, 0.79, 0.81, 0.83,  # 12-17时
                0.80, 0.75, 0.68, 0.62, 0.58, 0.56   # 18-23时
            ]
        },
        'transition': {  # 过渡日（周一）
            'name': '过渡日',
            'base_factor': 0.72,
            'hourly': [
                0.62, 0.60, 0.58, 0.57, 0.58, 0.60,  # 0-5时
                0.65, 0.72, 0.80, 0.85, 0.87, 0.85,  # 6-11时
                0.83, 0.81, 0.82, 0.84, 0.86, 0.88,  # 12-17时
                0.85, 0.80, 0.73, 0.67, 0.63, 0.61   # 18-23时
            ]
        }
    }
    
    # 5天的模式安排
    five_day_sequence = [
        'workday_normal',   # 第1天：正常工作日
        'workday_high',     # 第2天：高负荷工作日
        'weekend',          # 第3天：周末（低负荷）
        'workday_low',      # 第4天：低负荷工作日
        'transition'        # 第5天：过渡日
    ]
    
    print("\n5天负荷模式安排:")
    for i, pattern_name in enumerate(five_day_sequence):
        pattern = daily_patterns[pattern_name]
        print(f"  第{i+1}天: {pattern['name']} (基准因子: {pattern['base_factor']})")
    
    return daily_patterns, five_day_sequence


def create_load_timeseries(case_dir, gen_df, daily_patterns, five_day_sequence):
    """创建120小时负荷时序"""
    
    print("\n⏰ 创建120小时负荷时序")
    print("="*60)
    
    # 系统总容量
    total_pmax = gen_df['P max'].sum()
    base_load = total_pmax  # 基准负荷设为总容量
    
    # 生成120小时负荷
    all_loads = []
    for day_idx, pattern_name in enumerate(five_day_sequence):
        pattern = daily_patterns[pattern_name]
        daily_base = base_load * pattern['base_factor']
        
        for hour_factor in pattern['hourly']:
            all_loads.append(daily_base * hour_factor)
    
    # 统计负荷信息
    min_load = min(all_loads)
    max_load = max(all_loads)
    avg_load = np.mean(all_loads)
    
    print(f"\n负荷统计:")
    print(f"  最小负荷: {min_load:.1f} MW")
    print(f"  最大负荷: {max_load:.1f} MW")
    print(f"  平均负荷: {avg_load:.1f} MW")
    print(f"  负荷率: {avg_load/total_pmax*100:.1f}%")
    
    # 创建时间序列
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(120)]
    
    # 读取负荷分配
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    loads_df = pd.read_csv(f'{case_dir}/loads.csv')
    total_base_demand = buses_df['real_power_demand'].sum()
    
    # 为每个负荷创建时序文件
    for _, load in loads_df.iterrows():
        bus_name = load['bus']
        bus_data = buses_df[buses_df['name'] == bus_name]
        if not bus_data.empty:
            base_power = bus_data['real_power_demand'].values[0]
            load_share = base_power / total_base_demand
            
            load_ts_df = pd.DataFrame({
                'time': times,
                'power': [load_share * total_load for total_load in all_loads]
            })
            
            filename = f'{case_dir}/{load["name"]}_timeseries.csv'
            load_ts_df.to_csv(filename, index=False)
    
    print("✅ 负荷时序文件已创建")
    
    # 绘制负荷曲线预览
    plt.figure(figsize=(15, 8))
    hours = list(range(120))
    plt.plot(hours, all_loads, 'b-', linewidth=1.5)
    
    # 标注每天的分界线
    for day in range(1, 5):
        plt.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
        plt.text(day*24-12, max_load*0.95, f'Day {day}', ha='center', fontsize=10)
    plt.text(108, max_load*0.95, 'Day 5', ha='center', fontsize=10)
    
    # 添加标签
    plt.xlabel('Hour', fontsize=12)
    plt.ylabel('Load (MW)', fontsize=12)
    plt.title('5-Day (120-Hour) Load Profile', fontsize=14)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 119)
    
    # 标注最小和最大负荷
    min_idx = all_loads.index(min_load)
    max_idx = all_loads.index(max_load)
    plt.plot(min_idx, min_load, 'ro', markersize=8)
    plt.plot(max_idx, max_load, 'go', markersize=8)
    plt.text(min_idx, min_load-20, f'Min: {min_load:.0f} MW', ha='center', fontsize=10)
    plt.text(max_idx, max_load+20, f'Max: {max_load:.0f} MW', ha='center', fontsize=10)
    
    plt.tight_layout()
    plt.savefig(f'{case_dir}/load_profile_120h.png', dpi=150)
    plt.close()
    
    print("✅ 负荷曲线图已保存")
    
    return all_loads


def design_initial_state(case_dir, gen_df, min_load):
    """设计初始状态 - 7台开机，2台停机"""
    
    print("\n🔧 设计初始状态")
    print("="*60)
    
    # 初始状态策略：
    # - 所有大型基荷机组开机（G1, G2, G3）
    # - 中型机组部分开机（G4, G5开机，G6停机）
    # - 小型调峰机组：G7开机，G8、G9停机
    
    initial_states = []
    online_units = ['G1', 'G2', 'G3', 'G4', 'G5', 'G7']  # 7台开机
    offline_units = ['G6', 'G8', 'G9']  # 2台停机
    
    online_pmin = 0
    online_pmax = 0
    
    print("初始机组状态:")
    print("\n开机机组 (7台):")
    
    for _, gen in gen_df.iterrows():
        if gen['name'] in online_units:
            status = 1
            power = gen['P min'] * 1.2  # 初始出力为Pmin的120%
            if power > gen['P max']:
                power = gen['P max'] * 0.8
            hoursinstatus = gen['minuptime'] + 2  # 已运行时间
            
            online_pmin += gen['P min']
            online_pmax += gen['P max']
            
            print(f"  {gen['name']}: ON, 初始出力 {power:.1f} MW, "
                  f"容量 {gen['P min']}-{gen['P max']} MW")
        else:
            status = 0
            power = 0
            hoursinstatus = -(gen['mindowntime'] + 2)  # 已停机时间
        
        initial_states.append({
            'name': gen['name'],
            'status': status,
            'power': power,
            'hoursinstatus': int(hoursinstatus)
        })
    
    print(f"\n停机机组 (2台):")
    for unit in offline_units:
        gen_info = gen_df[gen_df['name'] == unit].iloc[0]
        print(f"  {unit}: OFF, 容量 {gen_info['P min']}-{gen_info['P max']} MW")
    
    print(f"\n初始状态汇总:")
    print(f"  在线机组数: 7台")
    print(f"  停机机组数: 2台")
    print(f"  在线Pmin: {online_pmin} MW")
    print(f"  在线Pmax: {online_pmax} MW")
    print(f"  最小负荷: {min_load:.1f} MW")
    print(f"  初始容量裕度: {online_pmax - min_load:.1f} MW")
    
    # 保存初始状态
    initial_df = pd.DataFrame(initial_states)
    initial_df.to_csv(f'{case_dir}/initial.csv', index=False)
    
    print("\n✅ 初始状态文件已创建")
    
    return initial_df, online_pmin, online_pmax


def analyze_uc_opportunities(all_loads, online_pmin, online_pmax, gen_df):
    """分析机组启停机会"""
    
    print("\n📊 分析机组启停机会")
    print("="*60)
    
    # 找出需要启动额外机组的时段
    startup_hours = []
    shutdown_hours = []
    
    # 考虑备用需求，负荷需要额外10%的备用
    reserve_factor = 1.1
    
    for hour, load in enumerate(all_loads):
        load_with_reserve = load * reserve_factor
        
        # 如果负荷超过当前在线容量，需要启动机组
        if load_with_reserve > online_pmax * 0.95:  # 留5%裕度
            startup_hours.append(hour)
        
        # 如果负荷很低，可以停机
        # 考虑停掉一台中型机组(G6: 50MW)后是否还能满足
        if load_with_reserve < (online_pmax - 50) * 0.8:
            shutdown_hours.append(hour)
    
    print(f"\n潜在启动时机: {len(startup_hours)}个小时")
    if startup_hours:
        print(f"  主要在: 第{startup_hours[0]//24 + 1}天开始")
    
    print(f"\n潜在停机时机: {len(shutdown_hours)}个小时")
    if shutdown_hours:
        print(f"  主要在: 第{shutdown_hours[0]//24 + 1}天开始")
    
    # 检查各天的负荷范围
    print("\n各天负荷范围:")
    for day in range(5):
        day_loads = all_loads[day*24:(day+1)*24]
        print(f"  第{day+1}天: {min(day_loads):.1f} - {max(day_loads):.1f} MW")


def main():
    """主函数"""
    
    print("🚀 IEEE 14节点5天120时段煤电案例设计\n")
    
    # 1. 创建案例目录
    case_dir = create_120periods_case()
    
    # 2. 设计发电机组
    gen_df = design_generators(case_dir)
    
    # 3. 创建报价曲线
    create_bid_curves(case_dir, gen_df)
    
    # 4. 设计负荷模式
    daily_patterns, five_day_sequence = design_load_pattern()
    
    # 5. 创建负荷时序
    all_loads = create_load_timeseries(case_dir, gen_df, daily_patterns, five_day_sequence)
    
    # 6. 设计初始状态
    min_load = min(all_loads)
    initial_df, online_pmin, online_pmax = design_initial_state(case_dir, gen_df, min_load)
    
    # 7. 分析启停机会
    analyze_uc_opportunities(all_loads, online_pmin, online_pmax, gen_df)
    
    print("\n\n✅ 5天120时段案例创建完成！")
    print(f"📁 案例目录: {case_dir}")
    print("\n下一步:")
    print("1. 创建运行脚本: run_ieee14_120periods_coal.py")
    print("2. 创建分析模块: ieee14_120periods_analysis.py")
    print("3. 运行仿真并查看结果")


if __name__ == "__main__":
    main()