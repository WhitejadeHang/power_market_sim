#!/usr/bin/env python3
"""
创建平衡的预设机组组合案例
确保初始在线容量满足所有时段需求
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


def create_balanced_case():
    """创建平衡的24时段案例"""
    
    print("🔨 创建平衡的IEEE 14节点24时段案例\n")
    
    # 1. 设计发电机组
    generators_data = [
        # 1000MW级超大型机组（1台）
        {'name': 'G1', 'bus': 'Bus01', 'P min': 300, 'P max': 1000, 'type': 'ultra_large',
         'minuptime': 8, 'mindowntime': 8, 'startupcost': 50000, 'shutdowncost': 20000,
         'rampratemax': 300, 'rampratemin': -300, 'noloadcost': 5000},
        
        # 600MW级大型机组（3台）
        {'name': 'G2', 'bus': 'Bus02', 'P min': 150, 'P max': 600, 'type': 'large',
         'minuptime': 6, 'mindowntime': 6, 'startupcost': 20000, 'shutdowncost': 8000,
         'rampratemax': 240, 'rampratemin': -240, 'noloadcost': 2000},
        
        {'name': 'G3', 'bus': 'Bus03', 'P min': 150, 'P max': 600, 'type': 'large',
         'minuptime': 6, 'mindowntime': 6, 'startupcost': 20000, 'shutdowncost': 8000,
         'rampratemax': 240, 'rampratemin': -240, 'noloadcost': 2000},
        
        {'name': 'G4', 'bus': 'Bus06', 'P min': 150, 'P max': 600, 'type': 'large',
         'minuptime': 6, 'mindowntime': 6, 'startupcost': 20000, 'shutdowncost': 8000,
         'rampratemax': 240, 'rampratemin': -240, 'noloadcost': 2000},
        
        # 300MW级中型机组（5台）
        {'name': 'G5', 'bus': 'Bus06', 'P min': 50, 'P max': 300, 'type': 'medium',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 8000, 'shutdowncost': 3000,
         'rampratemax': 150, 'rampratemin': -150, 'noloadcost': 800},
        
        {'name': 'G6', 'bus': 'Bus08', 'P min': 50, 'P max': 300, 'type': 'medium',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 8000, 'shutdowncost': 3000,
         'rampratemax': 150, 'rampratemin': -150, 'noloadcost': 800},
        
        {'name': 'G7', 'bus': 'Bus08', 'P min': 50, 'P max': 300, 'type': 'medium',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 8000, 'shutdowncost': 3000,
         'rampratemax': 150, 'rampratemin': -150, 'noloadcost': 800},
        
        {'name': 'G8', 'bus': 'Bus13', 'P min': 50, 'P max': 300, 'type': 'medium',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 8000, 'shutdowncost': 3000,
         'rampratemax': 150, 'rampratemin': -150, 'noloadcost': 800},
        
        {'name': 'G9', 'bus': 'Bus14', 'P min': 50, 'P max': 300, 'type': 'medium',
         'minuptime': 4, 'mindowntime': 4, 'startupcost': 8000, 'shutdowncost': 3000,
         'rampratemax': 150, 'rampratemin': -150, 'noloadcost': 800}
    ]
    
    gen_df = pd.DataFrame(generators_data)
    
    # 2. 设计24时段负荷 - 基于初始在线容量
    # 初始开机: G1, G2, G3, G5 (确保Pmin > 最小负荷)
    initial_online = ['G1', 'G2', 'G3', 'G5']
    initial_pmin = sum(gen_df[gen_df['name'].isin(initial_online)]['P min'])
    initial_pmax = sum(gen_df[gen_df['name'].isin(initial_online)]['P max'])
    
    print(f"初始在线机组: {initial_online}")
    print(f"初始在线容量: Pmin={initial_pmin} MW, Pmax={initial_pmax} MW")
    
    # 设计负荷曲线 - 确保最小负荷 > 初始Pmin
    min_load = initial_pmin + 200  # 留200MW裕度
    max_load = initial_pmax - 200  # 留200MW裕度
    
    # 24小时负荷模式
    hourly_factors = [
        0.70, 0.68, 0.66, 0.65, 0.66, 0.68,  # 0-5时：夜间低谷
        0.72, 0.78, 0.84, 0.88, 0.92, 0.90,  # 6-11时：早高峰
        0.88, 0.86, 0.88, 0.90, 0.94, 0.96,  # 12-17时：午后高峰
        0.92, 0.86, 0.80, 0.75, 0.72, 0.71   # 18-23时：晚间下降
    ]
    
    # 转换为实际负荷
    load_range = max_load - min_load
    system_loads = []
    for factor in hourly_factors:
        load = min_load + load_range * (factor - min(hourly_factors)) / (max(hourly_factors) - min(hourly_factors))
        system_loads.append(load)
    
    print(f"\n负荷设计: {min(system_loads):.0f} - {max(system_loads):.0f} MW")
    
    # 3. 预设机组组合和出力
    unit_status = np.zeros((9, 24), dtype=int)
    unit_power = np.zeros((9, 24))
    
    # 机组索引
    gen_names = gen_df['name'].tolist()
    gen_pmin = gen_df['P min'].values
    gen_pmax = gen_df['P max'].values
    
    for t in range(24):
        load = system_loads[t]
        
        # 基本策略：优先使用大机组
        if load >= 1800:  # 高负荷
            # 开机: G1, G2, G3, G4, G5
            online_units = ['G1', 'G2', 'G3', 'G4', 'G5']
        elif load >= 1400:  # 中高负荷
            # 开机: G1, G2, G3, G5
            online_units = ['G1', 'G2', 'G3', 'G5']
        elif load >= 1000:  # 中负荷
            # 开机: G1, G2, G5
            online_units = ['G1', 'G2', 'G5']
        else:  # 低负荷
            # 开机: G1, G5, G6
            online_units = ['G1', 'G5', 'G6']
        
        # 设置状态
        for i, name in enumerate(gen_names):
            if name in online_units:
                unit_status[i, t] = 1
        
        # 经济分配出力
        online_indices = [i for i, name in enumerate(gen_names) if name in online_units]
        online_pmin_sum = sum(gen_pmin[i] for i in online_indices)
        online_pmax_sum = sum(gen_pmax[i] for i in online_indices)
        
        # 按容量比例分配
        remaining_load = load
        for i in online_indices:
            if remaining_load > 0:
                # 优先满足最小出力
                unit_power[i, t] = gen_pmin[i]
                remaining_load -= gen_pmin[i]
        
        # 剩余负荷按容量比例分配
        if remaining_load > 0:
            total_headroom = sum(gen_pmax[i] - gen_pmin[i] for i in online_indices)
            for i in online_indices:
                headroom = gen_pmax[i] - gen_pmin[i]
                additional = min(remaining_load * headroom / total_headroom, headroom)
                unit_power[i, t] += additional
    
    # 4. 确保满足最小开停机时间约束
    unit_status, unit_power = enforce_constraints(unit_status, unit_power, gen_df)
    
    return gen_df, unit_status, unit_power, system_loads


def enforce_constraints(unit_status, unit_power, gen_df):
    """确保满足最小开停机时间约束"""
    
    n_units, n_periods = unit_status.shape
    minuptime = gen_df['minuptime'].values
    mindowntime = gen_df['mindowntime'].values
    
    # 简化处理：延长状态持续时间
    for u in range(n_units):
        i = 0
        while i < n_periods - 1:
            if unit_status[u, i] != unit_status[u, i+1]:
                # 状态变化
                if unit_status[u, i+1] == 1:  # 启动
                    # 确保运行足够时间
                    end = min(i + 1 + minuptime[u], n_periods)
                    unit_status[u, i+1:end] = 1
                else:  # 停机
                    # 确保停机足够时间
                    end = min(i + 1 + mindowntime[u], n_periods)
                    unit_status[u, i+1:end] = 0
                    unit_power[u, i+1:end] = 0
                i = end - 1
            i += 1
    
    return unit_status, unit_power


def save_case(case_dir, gen_df, unit_status, unit_power, system_loads):
    """保存案例文件"""
    
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
    for _, gen in gen_df.iterrows():
        create_bid_file(case_dir, gen)
    
    # 3. 创建初始状态文件
    initial_states = []
    for i, gen in gen_df.iterrows():
        initial_states.append({
            'name': gen['name'],
            'status': int(unit_status[i, 0]),
            'power': float(unit_power[i, 0]) if unit_status[i, 0] == 1 else 0,
            'hoursinstatus': 10 if unit_status[i, 0] == 1 else -10
        })
    
    pd.DataFrame(initial_states).to_csv(f'{case_dir}/initial.csv', index=False)
    
    # 4. 创建负荷时序
    create_load_files(case_dir, system_loads)
    
    # 5. 保存预设方案
    preset = {
        'unit_status': unit_status.tolist(),
        'unit_power': unit_power.tolist(),
        'system_loads': system_loads,
        'generator_names': gen_df['name'].tolist()
    }
    
    with open(f'{case_dir}/preset_solution.json', 'w') as f:
        json.dump(preset, f, indent=2)
    
    print(f"\n✅ 案例保存到: {case_dir}")


def create_bid_file(case_dir, gen):
    """创建单个机组的报价文件"""
    
    base_prices = {'ultra_large': 30, 'large': 40, 'medium': 55}
    base_price = base_prices[gen['type']]
    
    # 4段报价
    pmin = gen['P min']
    pmax = gen['P max']
    
    power_points = [pmin]
    costs = [0.0]
    
    for i in range(1, 4):
        power_points.append(pmin + (pmax - pmin) * i / 3)
        power_increment = power_points[i] - power_points[i-1]
        marginal_cost = base_price * (1 + 0.2 * (i-1))
        costs.append(costs[-1] + power_increment * marginal_cost)
    
    bid_df = pd.DataFrame({'power': power_points, 'cost': costs})
    bid_df.to_csv(f'{case_dir}/{gen["name"]}_block_bid.csv', index=False)


def create_load_files(case_dir, system_loads):
    """创建负荷时序文件"""
    
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(24)]
    
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    loads_df = pd.read_csv(f'{case_dir}/loads.csv')
    
    total_base_demand = buses_df['real_power_demand'].sum()
    
    for _, load in loads_df.iterrows():
        bus_name = load['bus']
        bus_data = buses_df[buses_df['name'] == bus_name]
        
        if not bus_data.empty:
            base_power = bus_data['real_power_demand'].values[0]
            load_share = base_power / total_base_demand
            
            load_ts_df = pd.DataFrame({
                'time': times,
                'power': [load_share * total_load for total_load in system_loads]
            })
            
            load_ts_df.to_csv(f'{case_dir}/{load["name"]}_timeseries.csv', index=False)


def plot_preset(unit_status, unit_power, system_loads, case_dir):
    """绘制预设方案"""
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
    
    hours = list(range(24))
    
    # 1. 机组状态和负荷
    ax1_twin = ax1.twinx()
    
    # 负荷曲线
    ax1.plot(hours, system_loads, 'b-', linewidth=3, label='System Load')
    ax1.set_ylabel('Load (MW)', fontsize=12)
    ax1.set_ylim(0, max(system_loads) * 1.1)
    
    # 在线机组数
    units_online = np.sum(unit_status, axis=0)
    ax1_twin.bar(hours, units_online, alpha=0.3, color='green', label='Units Online')
    ax1_twin.set_ylabel('Units Online', fontsize=12)
    ax1_twin.set_ylim(0, 10)
    
    ax1.set_xlabel('Hour', fontsize=12)
    ax1.set_title('24-Hour Preset Schedule', fontsize=14)
    ax1.grid(True, alpha=0.3)
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    
    # 2. 机组出力堆叠图
    gen_names = [f'G{i+1}' for i in range(9)]
    colors = plt.cm.tab10(np.linspace(0, 1, 9))
    
    bottom = np.zeros(24)
    for i in range(9):
        if np.any(unit_power[i, :] > 0):
            ax2.fill_between(hours, bottom, bottom + unit_power[i, :],
                           label=gen_names[i], color=colors[i], alpha=0.7)
            bottom += unit_power[i, :]
    
    ax2.plot(hours, system_loads, 'k--', linewidth=2, label='Load')
    ax2.set_xlabel('Hour', fontsize=12)
    ax2.set_ylabel('Power (MW)', fontsize=12)
    ax2.set_title('Generation Dispatch', fontsize=14)
    ax2.legend(loc='upper left', bbox_to_anchor=(1.01, 1))
    ax2.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.savefig(f'{case_dir}/balanced_preset.png', dpi=150, bbox_inches='tight')
    plt.close()


def main():
    """主函数"""
    
    print("🚀 创建平衡的预设机组组合案例\n")
    
    # 创建案例
    gen_df, unit_status, unit_power, system_loads = create_balanced_case()
    
    # 保存案例
    case_dir = 'simpower/tests/ieee14_24periods_balanced'
    save_case(case_dir, gen_df, unit_status, unit_power, system_loads)
    
    # 绘图
    plot_preset(unit_status, unit_power, system_loads, case_dir)
    
    # 统计
    print("\n📊 预设方案统计:")
    print(f"  负荷范围: {min(system_loads):.0f} - {max(system_loads):.0f} MW")
    print(f"  初始在线机组: {int(np.sum(unit_status[:, 0]))}台")
    
    # 启停次数
    startups = 0
    for u in range(9):
        for t in range(1, 24):
            if unit_status[u, t] == 1 and unit_status[u, t-1] == 0:
                startups += 1
    print(f"  总启动次数: {startups}")


if __name__ == "__main__":
    main()