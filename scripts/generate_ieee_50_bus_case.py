#!/usr/bin/env python3
"""
IEEE 50-Bus Economic Dispatch Case Generator
生成包含26台燃煤机组容量段报价和96时段负荷的标准测试案例
"""

import os
import sys
import numpy as np
import pandas as pd
import math

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def generate_bus_data():
    """生成50个节点的数据"""
    
    # 基于IEEE案例的50节点系统
    buses = []
    
    # 定义不同区域的负荷密度
    zones = {
        'urban_high': {'base_load': 200, 'buses': range(1, 11)},      # 都市高负荷区
        'urban_medium': {'base_load': 120, 'buses': range(11, 21)},   # 都市中负荷区  
        'suburban': {'base_load': 80, 'buses': range(21, 31)},        # 郊区
        'industrial': {'base_load': 150, 'buses': range(31, 41)},     # 工业区
        'rural': {'base_load': 40, 'buses': range(41, 51)}            # 农村区
    }
    
    bus_id = 1
    for zone_name, zone_info in zones.items():
        base_load = zone_info['base_load']
        
        for i, bus_num in enumerate(zone_info['buses']):
            # 添加随机变化
            load_factor = np.random.uniform(0.7, 1.3)
            bus_load = base_load * load_factor
            
            # 电压等级分配
            if zone_name in ['urban_high', 'industrial']:
                voltage = 345  # 高压
            elif zone_name == 'urban_medium':
                voltage = 230  # 中压
            else:
                voltage = 138  # 低压
            
            buses.append({
                'name': f'Bus_{bus_id:02d}_{zone_name}',
                'type': 'bus',
                'Vmax': voltage * 1.05 / 100,  # 标幺值
                'Vmin': voltage * 0.95 / 100,
                'zone': zone_name,
                'base_load_mw': round(bus_load, 1)
            })
            
            bus_id += 1
    
    return pd.DataFrame(buses)


def generate_transmission_lines():
    """生成传输线数据"""
    
    lines = []
    line_id = 1
    
    # 定义节点区域映射
    zone_names = []
    for i in range(1, 51):
        if 1 <= i <= 10:
            zone_names.append('urban_high')
        elif 11 <= i <= 20:
            zone_names.append('urban_medium')
        elif 21 <= i <= 30:
            zone_names.append('suburban')
        elif 31 <= i <= 40:
            zone_names.append('industrial')
        else:
            zone_names.append('rural')
    
    # 主干网连接 (高压backbone)
    backbone_connections = [
        (1, 11), (11, 21), (21, 31), (31, 41),  # 主要走廊
        (5, 15), (15, 25), (25, 35), (35, 45),  # 备用走廊
        (1, 5), (11, 15), (21, 25), (31, 35), (41, 45)  # 横向连接
    ]
    
    for from_bus, to_bus in backbone_connections:
        # 高压线路参数
        distance = np.random.uniform(50, 200)  # km
        lines.append({
            'from bus': f'Bus_{from_bus:02d}_{zone_names[from_bus-1]}',
            'to bus': f'Bus_{to_bus:02d}_{zone_names[to_bus-1]}',
            'Pmax': round(np.random.uniform(800, 1200))  # MW
        })
        line_id += 1
    
    # 区域内连接
    zones = [range(1, 11), range(11, 21), range(21, 31), range(31, 41), range(41, 51)]
    
    for zone in zones:
        zone_buses = list(zone)
        
        # 环形连接
        for i in range(len(zone_buses)):
            from_bus = zone_buses[i]
            to_bus = zone_buses[(i + 1) % len(zone_buses)]
            
            if from_bus < to_bus:  # 避免重复
                distance = np.random.uniform(20, 80)
                voltage = 230 if from_bus <= 30 else 138
                capacity = np.random.uniform(300, 600) if voltage == 230 else np.random.uniform(150, 400)
                
                lines.append({
                    'from bus': f'Bus_{from_bus:02d}_{zone_names[from_bus-1]}',
                    'to bus': f'Bus_{to_bus:02d}_{zone_names[to_bus-1]}',
                    'Pmax': round(capacity)
                })
                line_id += 1
        
        # 径向连接
        for i in range(len(zone_buses) - 2):
            from_bus = zone_buses[i]
            to_bus = zone_buses[i + 2]
            
            if np.random.random() < 0.4:  # 40%概率添加径向线路
                distance = np.random.uniform(30, 100)
                voltage = 138
                capacity = np.random.uniform(200, 400)
                
                lines.append({
                    'from bus': f'Bus_{from_bus:02d}_{zone_names[from_bus-1]}',
                    'to bus': f'Bus_{to_bus:02d}_{zone_names[to_bus-1]}',
                    'Pmax': round(capacity)
                })
                line_id += 1
    
    return pd.DataFrame(lines)


def generate_coal_generators():
    """生成26台燃煤机组数据"""
    
    generators = []
    
    # 机组类型定义
    plant_types = {
        'supercritical': {'capacity_range': (600, 800), 'count': 6, 'efficiency': 0.42},
        'subcritical': {'capacity_range': (400, 600), 'count': 8, 'efficiency': 0.38},
        'old_steam': {'capacity_range': (200, 400), 'count': 8, 'efficiency': 0.34},
        'small_unit': {'capacity_range': (100, 250), 'count': 4, 'efficiency': 0.32}
    }
    
    generator_id = 1
    bus_assignments = np.random.choice(range(1, 51), 26, replace=False)
    
    # 定义节点区域映射
    zones = []
    for i in range(1, 51):
        if 1 <= i <= 10:
            zones.append('urban_high')
        elif 11 <= i <= 20:
            zones.append('urban_medium')
        elif 21 <= i <= 30:
            zones.append('suburban')
        elif 31 <= i <= 40:
            zones.append('industrial')
        else:
            zones.append('rural')
    
    for plant_type, params in plant_types.items():
        count = params['count']
        min_cap, max_cap = params['capacity_range']
        efficiency = params['efficiency']
        
        for i in range(count):
            capacity = round(np.random.uniform(min_cap, max_cap))
            bus_id = bus_assignments[generator_id - 1]
            
            # 基础运行参数
            min_power = round(capacity * 0.4)  # 最小出力
            
            # 燃料成本和运维成本 (基于效率)
            heat_rate = 8500 / efficiency  # Btu/kWh
            fuel_cost = np.random.uniform(2.0, 3.5)  # $/MMBtu
            base_cost = heat_rate * fuel_cost / 1000  # $/MWh
            
            # 启停成本
            startup_cost = capacity * np.random.uniform(80, 150)  # $
            shutdown_cost = capacity * np.random.uniform(20, 40)
            
            # 爬坡率
            ramp_up = round(capacity * np.random.uniform(0.05, 0.15))  # MW/min
            ramp_down = round(capacity * np.random.uniform(0.05, 0.15))
            
            generators.append({
                'name': f'Coal_{generator_id:02d}_{plant_type}',
                'bus': f'Bus_{bus_id:02d}_{zones[bus_id-1]}',
                'type': 'coal',
                'P max': capacity,
                'no load cost': round(startup_cost / 10),  # 简化的空载成本
                'cost curve points filename': f'coal_{generator_id:02d}_block_bidding.csv'
            })
            
            generator_id += 1
    
    return pd.DataFrame(generators)


def generate_block_bidding_curves(generators_df, output_dir):
    """为每台机组生成容量段报价曲线"""
    
    for _, gen in generators_df.iterrows():
        filename = gen['cost curve points filename']
        capacity = gen['P max']
        min_power = round(capacity * 0.4)  # 40% 最小负荷
        base_cost = 50.0  # 基础成本
        # 从名称推断机组类型
        if 'supercritical' in gen['name']:
            plant_type = 'supercritical'
        elif 'subcritical' in gen['name']:
            plant_type = 'subcritical'
        elif 'old_steam' in gen['name']:
            plant_type = 'old_steam'
        else:
            plant_type = 'small_unit'
        
        # 根据机组类型确定容量段数量和价格特征 (4-10段，价格范围0-1500)
        if plant_type == 'supercritical':
            # 超临界机组：6段，低成本高效率
            segments = 6
            base_prices = [15, 25, 35, 50, 70, 100]  # $/MWh
        elif plant_type == 'subcritical':
            # 亚临界机组：7段，中等成本
            segments = 7
            base_prices = [20, 35, 50, 70, 95, 130, 180]  # $/MWh
        elif plant_type == 'old_steam':
            # 老式机组：8段，较高成本
            segments = 8
            base_prices = [30, 50, 75, 105, 145, 200, 280, 400]  # $/MWh
        else:  # small_unit
            # 小机组：10段，高成本，价格范围最大
            segments = 10
            base_prices = [40, 70, 110, 160, 220, 300, 420, 580, 800, 1200]  # $/MWh
        
        # 生成功率点
        power_points = [min_power]
        available_capacity = capacity - min_power
        
        for i in range(segments - 1):
            segment_end = min_power + available_capacity * (i + 1) / (segments - 1)
            power_points.append(round(segment_end))
        
        # 确保最后一点是最大容量
        power_points[-1] = capacity
        
        # 生成价格
        bid_data = []
        bid_data.append({'power': 0, 'price': 0})  # 起始点
        
        for i, power in enumerate(power_points):
            if i < len(base_prices):
                # 添加随机波动 ±15%
                price_variation = np.random.uniform(0.85, 1.15)
                price = base_prices[i] * price_variation
                
                # 确保价格递增且在合理范围内
                if bid_data and price <= bid_data[-1]['price']:
                    price = bid_data[-1]['price'] + np.random.uniform(5, 15)
                
                # 限制最高价格在1500$/MWh以内
                price = min(price, 1500)
                
                bid_data.append({
                    'power': power,
                    'price': round(price, 2)
                })
        
        # 保存文件
        bid_df = pd.DataFrame(bid_data)
        filepath = os.path.join(output_dir, filename)
        bid_df.to_csv(filepath, index=False)
        
        print(f"Generated {filename}: {segments} segments, capacity {capacity}MW, base cost {base_cost:.2f}$/MWh")


def generate_load_profile():
    """生成96个时段的负荷曲线"""
    
    times = []
    system_loads = []
    
    # 24小时，每15分钟一个时段
    for hour in range(24):
        for quarter in range(4):
            minute = quarter * 15
            time_str = f"{hour:02d}:{minute:02d}"
            times.append(time_str)
            
            # 典型日负荷曲线 (基于IEEE标准)
            # 基础负荷：6000 MW，峰值：8500 MW
            base_load = 6000
            peak_load = 8500
            
            # 双峰负荷曲线 (上午峰和晚上峰)
            time_decimal = hour + minute / 60
            
            # 夜间低谷 (0-6点)
            if 0 <= time_decimal < 6:
                load_factor = 0.70 + 0.05 * np.sin(np.pi * time_decimal / 6)
            
            # 晨间上升 (6-9点)
            elif 6 <= time_decimal < 9:
                load_factor = 0.75 + 0.20 * (time_decimal - 6) / 3
            
            # 上午峰 (9-12点)
            elif 9 <= time_decimal < 12:
                load_factor = 0.95 + 0.05 * np.sin(np.pi * (time_decimal - 9) / 3)
            
            # 下午稳定 (12-17点)
            elif 12 <= time_decimal < 17:
                load_factor = 0.85 + 0.10 * np.sin(np.pi * (time_decimal - 12) / 5)
            
            # 晚峰 (17-22点)
            elif 17 <= time_decimal < 22:
                peak_factor = 1.0 + 0.15 * np.sin(np.pi * (time_decimal - 17) / 5)
                load_factor = min(peak_factor, 1.0)
            
            # 夜间下降 (22-24点)
            else:
                load_factor = 1.0 - 0.30 * (time_decimal - 22) / 2
            
            # 添加随机波动
            load_factor *= np.random.uniform(0.98, 1.02)
            
            # 计算系统总负荷
            system_load = base_load + (peak_load - base_load) * load_factor
            system_loads.append(round(system_load, 1))
    
    return times, system_loads


def distribute_load_to_buses(bus_data, system_loads, times, output_dir):
    """将系统负荷分配到各个节点"""
    
    # 计算各节点的负荷分配比例
    total_base_load = bus_data['base_load_mw'].sum()
    bus_data['load_ratio'] = bus_data['base_load_mw'] / total_base_load
    
    # 生成负荷文件数据
    load_data = []
    
    for _, bus in bus_data.iterrows():
        load_ratio = bus['load_ratio']
        bus_name = bus['name']
        
        # 创建该节点的时间序列负荷文件
        schedule_filename = f"{bus_name}_load_schedule.csv"
        schedule_data = []
        
        for i, (time_str, system_load) in enumerate(zip(times, system_loads)):
            bus_load = system_load * load_ratio
            
            # 添加节点特定的随机变化
            variation = np.random.uniform(0.98, 1.02)
            bus_load *= variation
            
            # 创建时间戳 (2024-01-01为基准日期)
            hour = i // 4
            minute = (i % 4) * 15
            timestamp = f"2024-01-01 {hour:02d}:{minute:02d}"
            
            schedule_data.append({
                'time': timestamp,
                'power': round(bus_load, 2)
            })
        
        # 保存时间序列文件
        schedule_df = pd.DataFrame(schedule_data)
        schedule_path = os.path.join(output_dir, schedule_filename)
        schedule_df.to_csv(schedule_path, index=False)
        
        # 添加到主负荷文件
        load_data.append({
            'name': bus_name,
            'power': '',  # 空值表示使用schedule文件
            'schedule filename': schedule_filename
        })
    
    return pd.DataFrame(load_data)


def create_ieee_50_bus_case():
    """创建完整的IEEE 50节点案例"""
    
    output_dir = 'simpower/tests/ieee_50_bus_case'
    os.makedirs(output_dir, exist_ok=True)
    
    print("🏗️ 生成IEEE 50节点经济调度案例...")
    
    # 1. 生成网络数据
    print("📊 生成50个节点数据...")
    bus_data = generate_bus_data()
    bus_data.to_csv(os.path.join(output_dir, 'buses.csv'), index=False)
    print(f"✅ 生成 {len(bus_data)} 个节点")
    
    # 2. 生成传输线数据
    print("🔌 生成传输线数据...")
    line_data = generate_transmission_lines()
    line_data.to_csv(os.path.join(output_dir, 'lines.csv'), index=False)
    print(f"✅ 生成 {len(line_data)} 条传输线")
    
    # 3. 生成发电机数据
    print("⚡ 生成26台燃煤机组数据...")
    generator_data = generate_coal_generators()
    generator_data.to_csv(os.path.join(output_dir, 'generators.csv'), index=False)
    print(f"✅ 生成 {len(generator_data)} 台发电机")
    
    # 4. 生成容量段报价曲线
    print("💰 生成容量段报价曲线...")
    generate_block_bidding_curves(generator_data, output_dir)
    print(f"✅ 生成 {len(generator_data)} 个报价文件")
    
    # 5. 生成负荷曲线
    print("📈 生成96时段负荷曲线...")
    times, system_loads = generate_load_profile()
    
    # 保存系统负荷曲线
    load_curve = pd.DataFrame({
        'time_period': range(1, 97),
        'time': times,
        'system_load_mw': system_loads
    })
    load_curve.to_csv(os.path.join(output_dir, 'system_load_curve.csv'), index=False)
    
    # 6. 分配负荷到各节点
    print("🏢 分配负荷到各节点...")
    load_data = distribute_load_to_buses(bus_data, system_loads, times, output_dir)
    load_data.to_csv(os.path.join(output_dir, 'loads.csv'), index=False)
    print(f"✅ 生成 {len(load_data)} 个负荷节点，每个包含96时段")
    
    # 7. 生成案例统计信息
    print("📋 生成案例统计...")
    
    # 发电机统计 - 简化统计信息
    total_capacity = generator_data['P max'].sum()
    gen_count = len(generator_data)
    min_load = min(system_loads)
    max_load = max(system_loads)
    avg_load = sum(system_loads) / len(system_loads)
    
    stats_report = f"""
IEEE 50-Bus Economic Dispatch Case Statistics
=============================================

Network Configuration:
- Buses: {len(bus_data)}
- Transmission Lines: {len(line_data)}
- Generators: {len(generator_data)} coal plants
- Time Periods: 96 (15-min intervals, 24 hours)

Generator Summary:
- Total Generators: {gen_count}
- Total Generation Capacity: {total_capacity:,} MW
System Load Range: {min_load:.1f} - {max_load:.1f} MW
Average System Load: {avg_load:.1f} MW
Reserve Margin: {(total_capacity - max_load) / max_load * 100:.1f}%

Load Profile:
- Peak Load Time: {times[system_loads.index(max_load)]}
- Min Load Time: {times[system_loads.index(min_load)]}
- Load Factor: {avg_load / max_load:.3f}

File Structure:
- buses.csv: Network bus data
- lines.csv: Transmission line data  
- generators.csv: Generator specifications
- coal_XX_block_bidding.csv: Block bidding curves (26 files)
- loads.csv: Load data for all buses and time periods
- system_load_curve.csv: System-wide load curve
"""
    
    with open(os.path.join(output_dir, 'case_statistics.txt'), 'w') as f:
        f.write(stats_report)
    
    print("✅ 案例统计报告已生成")
    print(f"\n🎉 IEEE 50节点案例生成完成！")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 总容量: {total_capacity:,} MW")
    print(f"📈 峰值负荷: {max_load:.1f} MW")
    print(f"🔋 备用率: {(total_capacity - max_load) / max_load * 100:.1f}%")
    
    return output_dir


if __name__ == "__main__":
    case_dir = create_ieee_50_bus_case()
    print(f"\n🚀 案例已保存到: {case_dir}")
    print("💡 使用以下命令测试案例:")
    print(f"   python3 -c \"from simpower.solve import solve_problem; solve_problem('{case_dir}')\"")