#!/usr/bin/env python3
"""
基于预设机组组合创建IEEE 14节点5天120时段案例
确保有可行解
"""

import os
import shutil
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import json

# 设置中文字体
plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
plt.rcParams['axes.unicode_minus'] = False


def design_generators():
    """设计大型机组（300MW、600MW、1000MW级）"""
    
    generators_data = [
        # 1000MW级超大型机组（1台）
        {
            'name': 'G1',
            'bus': 'Bus01',
            'P min': 400,  # 40%最小技术出力
            'P max': 1000,
            'type': 'ultra_large',
            'minuptime': 24,  # 24小时最小运行时间
            'mindowntime': 24,  # 24小时最小停机时间
            'startupcost': 50000,
            'shutdowncost': 20000,
            'rampratemax': 200,  # 20%/小时爬坡率
            'rampratemin': -200,
            'noloadcost': 5000,
            'efficiency': 0.45  # 效率45%
        },
        
        # 600MW级大型机组（3台）
        {
            'name': 'G2',
            'bus': 'Bus02',
            'P min': 180,  # 30%最小技术出力
            'P max': 600,
            'type': 'large',
            'minuptime': 12,
            'mindowntime': 12,
            'startupcost': 20000,
            'shutdowncost': 8000,
            'rampratemax': 180,  # 30%/小时爬坡率
            'rampratemin': -180,
            'noloadcost': 2000,
            'efficiency': 0.42
        },
        {
            'name': 'G3',
            'bus': 'Bus03',
            'P min': 180,
            'P max': 600,
            'type': 'large',
            'minuptime': 12,
            'mindowntime': 12,
            'startupcost': 20000,
            'shutdowncost': 8000,
            'rampratemax': 180,
            'rampratemin': -180,
            'noloadcost': 2000,
            'efficiency': 0.42
        },
        {
            'name': 'G4',
            'bus': 'Bus06',
            'P min': 180,
            'P max': 600,
            'type': 'large',
            'minuptime': 12,
            'mindowntime': 12,
            'startupcost': 20000,
            'shutdowncost': 8000,
            'rampratemax': 180,
            'rampratemin': -180,
            'noloadcost': 2000,
            'efficiency': 0.42
        },
        
        # 300MW级中型机组（5台）
        {
            'name': 'G5',
            'bus': 'Bus06',
            'P min': 60,  # 20%最小技术出力
            'P max': 300,
            'type': 'medium',
            'minuptime': 6,
            'mindowntime': 6,
            'startupcost': 8000,
            'shutdowncost': 3000,
            'rampratemax': 120,  # 40%/小时爬坡率
            'rampratemin': -120,
            'noloadcost': 800,
            'efficiency': 0.38
        },
        {
            'name': 'G6',
            'bus': 'Bus08',
            'P min': 60,
            'P max': 300,
            'type': 'medium',
            'minuptime': 6,
            'mindowntime': 6,
            'startupcost': 8000,
            'shutdowncost': 3000,
            'rampratemax': 120,
            'rampratemin': -120,
            'noloadcost': 800,
            'efficiency': 0.38
        },
        {
            'name': 'G7',
            'bus': 'Bus08',
            'P min': 60,
            'P max': 300,
            'type': 'medium',
            'minuptime': 6,
            'mindowntime': 6,
            'startupcost': 8000,
            'shutdowncost': 3000,
            'rampratemax': 120,
            'rampratemin': -120,
            'noloadcost': 800,
            'efficiency': 0.38
        },
        {
            'name': 'G8',
            'bus': 'Bus13',
            'P min': 60,
            'P max': 300,
            'type': 'medium',
            'minuptime': 6,
            'mindowntime': 6,
            'startupcost': 8000,
            'shutdowncost': 3000,
            'rampratemax': 120,
            'rampratemin': -120,
            'noloadcost': 800,
            'efficiency': 0.38
        },
        {
            'name': 'G9',
            'bus': 'Bus14',
            'P min': 60,
            'P max': 300,
            'type': 'medium',
            'minuptime': 6,
            'mindowntime': 6,
            'startupcost': 8000,
            'shutdowncost': 3000,
            'rampratemax': 120,
            'rampratemin': -120,
            'noloadcost': 800,
            'efficiency': 0.38
        }
    ]
    
    gen_df = pd.DataFrame(generators_data)
    
    # 系统总容量
    total_pmin = gen_df['P min'].sum()
    total_pmax = gen_df['P max'].sum()
    
    print("⚡ 发电机组设计:")
    print("="*60)
    print("\n机组容量分类:")
    
    for gen_type in ['ultra_large', 'large', 'medium']:
        type_gens = gen_df[gen_df['type'] == gen_type]
        print(f"\n{gen_type}:")
        for _, gen in type_gens.iterrows():
            print(f"  {gen['name']}: {gen['P min']}-{gen['P max']} MW")
        print(f"  小计: {len(type_gens)}台, 总容量 {type_gens['P max'].sum()} MW")
    
    print(f"\n系统总容量: Pmin={total_pmin} MW, Pmax={total_pmax} MW")
    
    return gen_df


def preset_unit_commitment_schedule():
    """预设5天120时段的机组组合方案"""
    
    print("\n\n📋 预设机组组合方案:")
    print("="*60)
    
    # 120时段的机组状态矩阵 (9机组 x 120时段)
    # 1 = 开机, 0 = 停机
    unit_status = np.zeros((9, 120), dtype=int)
    unit_power = np.zeros((9, 120))
    
    # 机组索引: G1(0), G2(1), G3(2), G4(3), G5(4), G6(5), G7(6), G8(7), G9(8)
    # 容量: G1=1000MW, G2-G4=600MW, G5-G9=300MW
    
    # 定义典型日负荷模式
    daily_patterns = {
        'high_workday': {  # 高负荷工作日
            'peak_load': 3200,  # MW
            'valley_load': 1800,
            'pattern': [
                # 0-5时：夜间低谷
                0.60, 0.58, 0.56, 0.55, 0.56, 0.58,
                # 6-11时：早高峰爬升
                0.65, 0.72, 0.80, 0.88, 0.95, 0.93,
                # 12-17时：午后高峰
                0.90, 0.88, 0.90, 0.93, 0.97, 1.00,
                # 18-23时：晚间下降
                0.95, 0.88, 0.80, 0.72, 0.65, 0.62
            ]
        },
        'normal_workday': {  # 正常工作日
            'peak_load': 2800,
            'valley_load': 1500,
            'pattern': [
                0.55, 0.53, 0.52, 0.50, 0.52, 0.55,
                0.60, 0.68, 0.75, 0.83, 0.88, 0.86,
                0.84, 0.82, 0.84, 0.86, 0.90, 0.92,
                0.88, 0.82, 0.75, 0.68, 0.60, 0.57
            ]
        },
        'weekend': {  # 周末
            'peak_load': 2200,
            'valley_load': 1200,
            'pattern': [
                0.50, 0.48, 0.47, 0.46, 0.47, 0.48,
                0.52, 0.58, 0.65, 0.72, 0.78, 0.80,
                0.82, 0.83, 0.82, 0.80, 0.78, 0.75,
                0.72, 0.68, 0.62, 0.58, 0.54, 0.52
            ]
        }
    }
    
    # 5天的负荷模式安排
    day_types = ['normal_workday', 'high_workday', 'weekend', 'weekend', 'normal_workday']
    
    # 根据负荷预设机组组合
    system_loads = []
    
    for day_idx, day_type in enumerate(day_types):
        pattern = daily_patterns[day_type]
        peak = pattern['peak_load']
        valley = pattern['valley_load']
        
        print(f"\n第{day_idx+1}天 ({day_type}):")
        print(f"  负荷范围: {valley} - {peak} MW")
        
        for hour in range(24):
            t = day_idx * 24 + hour
            load_factor = pattern['pattern'][hour]
            load = valley + (peak - valley) * (load_factor - min(pattern['pattern'])) / (max(pattern['pattern']) - min(pattern['pattern']))
            system_loads.append(load)
            
            # 根据负荷水平决定机组组合
            if load >= 2800:  # 高负荷：需要大部分机组
                # G1(1000MW) + G2,G3,G4(600MW x3) + G5,G6(300MW x2) = 3100MW
                unit_status[0, t] = 1  # G1 开
                unit_status[1:4, t] = 1  # G2-G4 开
                unit_status[4:6, t] = 1  # G5-G6 开
                unit_status[6:9, t] = 0  # G7-G9 停
                
                # 分配出力
                unit_power[0, t] = min(800, load * 0.30)  # G1承担30%
                unit_power[1, t] = min(500, load * 0.17)  # G2承担17%
                unit_power[2, t] = min(500, load * 0.17)  # G3承担17%
                unit_power[3, t] = min(500, load * 0.17)  # G4承担17%
                unit_power[4, t] = min(250, load * 0.10)  # G5承担10%
                unit_power[5, t] = min(250, load * 0.09)  # G6承担9%
                
            elif load >= 2000:  # 中高负荷
                # G1(1000MW) + G2,G3(600MW x2) + G5(300MW) = 2500MW
                unit_status[0, t] = 1  # G1 开
                unit_status[1:3, t] = 1  # G2-G3 开
                unit_status[3, t] = 0  # G4 停
                unit_status[4, t] = 1  # G5 开
                unit_status[5:9, t] = 0  # G6-G9 停
                
                # 分配出力
                unit_power[0, t] = min(700, load * 0.35)  # G1承担35%
                unit_power[1, t] = min(450, load * 0.23)  # G2承担23%
                unit_power[2, t] = min(450, load * 0.23)  # G3承担23%
                unit_power[4, t] = min(200, load * 0.19)  # G5承担19%
                
            elif load >= 1400:  # 中负荷
                # G1(1000MW) + G2(600MW) = 1600MW
                unit_status[0, t] = 1  # G1 开
                unit_status[1, t] = 1  # G2 开
                unit_status[2:9, t] = 0  # G3-G9 停
                
                # 分配出力
                unit_power[0, t] = min(600, load * 0.60)  # G1承担60%
                unit_power[1, t] = min(400, load * 0.40)  # G2承担40%
                
            else:  # 低负荷 < 1400MW
                # 仅G1(1000MW)
                unit_status[0, t] = 1  # G1 开
                unit_status[1:9, t] = 0  # G2-G9 停
                
                # 分配出力
                unit_power[0, t] = max(400, load)  # G1承担全部（但不低于最小出力）
    
    # 检查并修正机组启停约束
    print("\n\n🔧 检查并修正启停约束...")
    unit_status, unit_power = enforce_minupdown_constraints(unit_status, unit_power, system_loads)
    
    return unit_status, unit_power, system_loads


def enforce_minupdown_constraints(unit_status, unit_power, system_loads):
    """强制执行最小开停机时间约束"""
    
    # 机组最小开停机时间
    minuptime = [24, 12, 12, 12, 6, 6, 6, 6, 6]  # 小时
    mindowntime = [24, 12, 12, 12, 6, 6, 6, 6, 6]  # 小时
    
    n_units, n_periods = unit_status.shape
    
    for u in range(n_units):
        # 检查每个状态转换
        i = 0
        while i < n_periods:
            if i == 0:
                i += 1
                continue
                
            # 检测启动
            if unit_status[u, i] == 1 and unit_status[u, i-1] == 0:
                # 确保机组运行足够长时间
                run_end = min(i + minuptime[u], n_periods)
                unit_status[u, i:run_end] = 1
                i = run_end
                
            # 检测停机
            elif unit_status[u, i] == 0 and unit_status[u, i-1] == 1:
                # 确保机组停机足够长时间
                stop_end = min(i + mindowntime[u], n_periods)
                unit_status[u, i:stop_end] = 0
                # 清除出力
                unit_power[u, i:stop_end] = 0
                i = stop_end
            else:
                i += 1
    
    # 重新计算负荷以确保平衡
    for t in range(n_periods):
        total_gen = np.sum(unit_power[:, t])
        if abs(total_gen - system_loads[t]) > 1:  # 如果不平衡
            # 按比例调整在线机组出力
            online_units = np.where(unit_status[:, t] == 1)[0]
            if len(online_units) > 0:
                scale = system_loads[t] / total_gen if total_gen > 0 else 1
                for u in online_units:
                    unit_power[u, t] *= scale
    
    return unit_status, unit_power


def create_case_files(case_dir, gen_df, unit_status, unit_power, system_loads):
    """创建案例文件"""
    
    print("\n\n📁 创建案例文件...")
    print("="*60)
    
    # 创建目录
    if os.path.exists(case_dir):
        shutil.rmtree(case_dir)
    
    # 复制基础文件
    source_dir = 'simpower/tests/ieee14_24periods_coal'
    shutil.copytree(source_dir, case_dir)
    
    # 1. 更新发电机文件
    gen_df['costcurvepointsfilename'] = gen_df['name'].apply(lambda x: f'{x}_block_bid.csv')
    gen_df[['name', 'bus', 'P min', 'P max', 'minuptime', 'mindowntime',
            'rampratemax', 'rampratemin', 'startupcost', 'shutdowncost',
            'noloadcost', 'costcurvepointsfilename']].to_csv(
        f'{case_dir}/generators.csv', index=False)
    
    # 2. 创建报价文件
    create_bid_files(case_dir, gen_df)
    
    # 3. 创建初始状态文件
    initial_states = []
    for i, gen in gen_df.iterrows():
        initial_states.append({
            'name': gen['name'],
            'status': int(unit_status[i, 0]),
            'power': float(unit_power[i, 0]) if unit_status[i, 0] == 1 else 0,
            'hoursinstatus': 10 if unit_status[i, 0] == 1 else -10
        })
    
    initial_df = pd.DataFrame(initial_states)
    initial_df.to_csv(f'{case_dir}/initial.csv', index=False)
    
    # 4. 创建负荷时序文件
    create_load_timeseries(case_dir, system_loads)
    
    # 5. 保存预设方案供对比
    preset_solution = {
        'unit_status': unit_status.tolist(),
        'unit_power': unit_power.tolist(),
        'system_loads': system_loads,
        'generator_names': gen_df['name'].tolist()
    }
    
    with open(f'{case_dir}/preset_solution.json', 'w') as f:
        json.dump(preset_solution, f, indent=2)
    
    print("✅ 案例文件创建完成")
    
    return case_dir


def create_bid_files(case_dir, gen_df):
    """创建容量段报价文件"""
    
    # 基础价格（$/MWh）- 根据机组类型和效率
    base_prices = {
        'ultra_large': 30,  # 超大型机组效率最高，成本最低
        'large': 40,        # 大型机组
        'medium': 55        # 中型机组
    }
    
    for _, gen in gen_df.iterrows():
        gen_name = gen['name']
        pmin = gen['P min']
        pmax = gen['P max']
        gen_type = gen['type']
        
        # 基础价格
        base_price = base_prices[gen_type]
        
        # 5段报价，边际成本递增
        segments = 5
        power_points = []
        costs = [0.0]
        
        for i in range(segments):
            if i == 0:
                power_points.append(pmin)
            else:
                power_points.append(pmin + (pmax - pmin) * i / (segments - 1))
        
        # 边际成本递增
        marginal_costs = [base_price * (1 + 0.2 * i) for i in range(segments)]
        
        # 计算累积成本
        for i in range(1, segments):
            power_increment = power_points[i] - power_points[i-1]
            cost_increment = power_increment * marginal_costs[i-1]
            costs.append(costs[-1] + cost_increment)
        
        # 保存报价文件
        bid_df = pd.DataFrame({
            'power': power_points,
            'cost': costs
        })
        bid_df.to_csv(f'{case_dir}/{gen_name}_block_bid.csv', index=False)


def create_load_timeseries(case_dir, system_loads):
    """创建负荷时序文件"""
    
    # 创建时间序列
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(120)]
    
    # 读取节点和负荷数据
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    loads_df = pd.read_csv(f'{case_dir}/loads.csv')
    
    # 计算负荷分配比例
    total_base_demand = buses_df['real_power_demand'].sum()
    
    # 为每个负荷创建时序
    for _, load in loads_df.iterrows():
        bus_name = load['bus']
        bus_data = buses_df[buses_df['name'] == bus_name]
        
        if not bus_data.empty:
            base_power = bus_data['real_power_demand'].values[0]
            load_share = base_power / total_base_demand
            
            # 创建该负荷的时序
            load_ts_df = pd.DataFrame({
                'time': times,
                'power': [load_share * total_load for total_load in system_loads]
            })
            
            filename = f'{case_dir}/{load["name"]}_timeseries.csv'
            load_ts_df.to_csv(filename, index=False)


def plot_preset_schedule(unit_status, unit_power, system_loads, case_dir):
    """绘制预设的机组组合方案"""
    
    print("\n\n📊 绘制预设方案...")
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(20, 15))
    
    # 1. 负荷曲线
    hours = list(range(120))
    ax1.plot(hours, system_loads, 'b-', linewidth=2)
    ax1.fill_between(hours, 0, system_loads, alpha=0.3)
    ax1.set_ylabel('Load (MW)', fontsize=12)
    ax1.set_title('5-Day System Load Profile (Preset)', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.set_xlim(0, 119)
    
    # 添加日分界线
    for day in range(1, 5):
        ax1.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
    
    # 2. 机组状态
    im = ax2.imshow(unit_status, aspect='auto', cmap='RdYlGn', interpolation='nearest')
    ax2.set_yticks(range(9))
    ax2.set_yticklabels([f'G{i+1}' for i in range(9)])
    ax2.set_ylabel('Units', fontsize=12)
    ax2.set_title('Unit Commitment Status (Green=ON, Red=OFF)', fontsize=14)
    
    # 3. 堆叠面积图显示各机组出力
    bottom = np.zeros(120)
    colors = plt.cm.tab10(np.linspace(0, 1, 9))
    
    for i in range(9):
        ax3.fill_between(hours, bottom, bottom + unit_power[i, :], 
                        label=f'G{i+1}', color=colors[i], alpha=0.7)
        bottom += unit_power[i, :]
    
    ax3.plot(hours, system_loads, 'k--', linewidth=2, label='Load')
    ax3.set_xlabel('Hour', fontsize=12)
    ax3.set_ylabel('Power (MW)', fontsize=12)
    ax3.set_title('Generation Dispatch (Stacked)', fontsize=14)
    ax3.legend(loc='upper left', bbox_to_anchor=(1.01, 1), ncol=1)
    ax3.grid(True, alpha=0.3)
    ax3.set_xlim(0, 119)
    
    plt.tight_layout()
    plt.savefig(f'{case_dir}/preset_schedule.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("✅ 预设方案图已保存")


def analyze_preset_solution(unit_status, unit_power, system_loads, gen_df):
    """分析预设方案"""
    
    print("\n\n📈 预设方案分析:")
    print("="*60)
    
    # 1. 启停统计
    startups = 0
    shutdowns = 0
    
    for u in range(9):
        for t in range(1, 120):
            if unit_status[u, t] == 1 and unit_status[u, t-1] == 0:
                startups += 1
            elif unit_status[u, t] == 0 and unit_status[u, t-1] == 1:
                shutdowns += 1
    
    print(f"\n启停统计:")
    print(f"  总启动次数: {startups}")
    print(f"  总停机次数: {shutdowns}")
    
    # 2. 机组利用率
    print("\n机组利用率:")
    for i in range(9):
        online_hours = np.sum(unit_status[i, :])
        if online_hours > 0:
            avg_power = np.sum(unit_power[i, :]) / online_hours
            capacity_factor = np.sum(unit_power[i, :]) / (120 * gen_df.iloc[i]['P max']) * 100
            print(f"  G{i+1}: 运行{online_hours}小时, 平均出力{avg_power:.0f}MW, 容量因子{capacity_factor:.1f}%")
        else:
            print(f"  G{i+1}: 全程停机")
    
    # 3. 负荷统计
    print(f"\n负荷统计:")
    print(f"  最小负荷: {min(system_loads):.0f} MW")
    print(f"  最大负荷: {max(system_loads):.0f} MW")
    print(f"  平均负荷: {np.mean(system_loads):.0f} MW")
    print(f"  峰谷差: {max(system_loads) - min(system_loads):.0f} MW")
    
    # 4. 成本估算（简化）
    total_startup_cost = 0
    total_noload_cost = 0
    total_generation_cost = 0
    
    for u in range(9):
        # 启动成本
        for t in range(1, 120):
            if unit_status[u, t] == 1 and unit_status[u, t-1] == 0:
                total_startup_cost += gen_df.iloc[u]['startupcost']
        
        # 空载成本
        online_hours = np.sum(unit_status[u, :])
        total_noload_cost += online_hours * gen_df.iloc[u]['noloadcost']
        
        # 发电成本（简化计算）
        total_generation = np.sum(unit_power[u, :])
        avg_cost = 30 if gen_df.iloc[u]['type'] == 'ultra_large' else (40 if gen_df.iloc[u]['type'] == 'large' else 55)
        total_generation_cost += total_generation * avg_cost
    
    total_cost = total_startup_cost + total_noload_cost + total_generation_cost
    
    print(f"\n预估成本:")
    print(f"  启动成本: ${total_startup_cost:,.0f}")
    print(f"  空载成本: ${total_noload_cost:,.0f}")
    print(f"  发电成本: ${total_generation_cost:,.0f}")
    print(f"  总成本: ${total_cost:,.0f}")


def main():
    """主函数"""
    
    print("🚀 基于预设机组组合的IEEE 14节点5天120时段案例设计\n")
    
    # 1. 设计发电机组
    gen_df = design_generators()
    
    # 2. 预设机组组合方案
    unit_status, unit_power, system_loads = preset_unit_commitment_schedule()
    
    # 3. 分析预设方案
    analyze_preset_solution(unit_status, unit_power, system_loads, gen_df)
    
    # 4. 创建案例文件
    case_dir = 'simpower/tests/ieee14_120periods_preset'
    case_dir = create_case_files(case_dir, gen_df, unit_status, unit_power, system_loads)
    
    # 5. 绘制预设方案
    plot_preset_schedule(unit_status, unit_power, system_loads, case_dir)
    
    print("\n\n✅ 案例设计完成！")
    print(f"📁 案例目录: {case_dir}")
    print("\n下一步:")
    print("1. 运行仿真: python3 run_ieee14_120periods_preset.py")
    print("2. 对比预设方案和优化结果")


if __name__ == "__main__":
    main()