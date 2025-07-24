#!/usr/bin/env python3
"""
简化的IEEE 50节点案例生成器
使用简单的节点命名以确保兼容性
"""

import os
import sys
import numpy as np
import pandas as pd

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

def create_simplified_ieee_50_case():
    """创建简化的IEEE 50节点案例"""
    
    output_dir = 'simpower/tests/ieee_50_simple'
    os.makedirs(output_dir, exist_ok=True)
    
    print("🏗️ 生成简化的IEEE 50节点案例...")
    
    # 1. 生成节点数据 - 使用简单命名
    buses_data = []
    for i in range(1, 51):
        buses_data.append({
            'name': f'Bus{i:02d}',
            'type': 'bus'
        })
    
    buses_df = pd.DataFrame(buses_data)
    buses_df.to_csv(os.path.join(output_dir, 'buses.csv'), index=False)
    print(f"✅ 生成 {len(buses_df)} 个节点")
    
    # 2. 生成传输线数据
    lines_data = []
    
    # 主干网连接
    backbone_pairs = [
        (1, 11), (11, 21), (21, 31), (31, 41),
        (5, 15), (15, 25), (25, 35), (35, 45),
        (1, 5), (11, 15), (21, 25), (31, 35), (41, 45)
    ]
    
    for from_bus, to_bus in backbone_pairs:
        lines_data.append({
            'from bus': f'Bus{from_bus:02d}',
            'to bus': f'Bus{to_bus:02d}',
            'Pmax': round(np.random.uniform(800, 1200))
        })
    
    # 区域内连接
    zones = [range(1, 11), range(11, 21), range(21, 31), range(31, 41), range(41, 51)]
    
    for zone in zones:
        zone_buses = list(zone)
        
        # 环形连接
        for i in range(len(zone_buses)):
            from_bus = zone_buses[i]
            to_bus = zone_buses[(i + 1) % len(zone_buses)]
            
            if from_bus < to_bus:
                lines_data.append({
                    'from bus': f'Bus{from_bus:02d}',
                    'to bus': f'Bus{to_bus:02d}',
                    'Pmax': round(np.random.uniform(300, 600))
                })
        
        # 部分径向连接
        for i in range(len(zone_buses) - 2):
            from_bus = zone_buses[i]
            to_bus = zone_buses[i + 2]
            
            if np.random.random() < 0.3:
                lines_data.append({
                    'from bus': f'Bus{from_bus:02d}',
                    'to bus': f'Bus{to_bus:02d}',
                    'Pmax': round(np.random.uniform(200, 400))
                })
    
    lines_df = pd.DataFrame(lines_data)
    lines_df.to_csv(os.path.join(output_dir, 'lines.csv'), index=False)
    print(f"✅ 生成 {len(lines_df)} 条传输线")
    
    # 3. 生成发电机数据
    generators_data = []
    
    # 发电机类型和对应的报价段数
    plant_configs = [
        {'name': 'Coal', 'count': 6, 'capacity_range': (600, 800), 'segments': 6, 'base_prices': [15, 25, 35, 50, 70, 100]},
        {'name': 'Gas', 'count': 8, 'capacity_range': (400, 600), 'segments': 7, 'base_prices': [20, 35, 50, 70, 95, 130, 180]},
        {'name': 'Steam', 'count': 8, 'capacity_range': (200, 400), 'segments': 8, 'base_prices': [30, 50, 75, 105, 145, 200, 280, 400]},
        {'name': 'Peaker', 'count': 4, 'capacity_range': (100, 250), 'segments': 10, 'base_prices': [40, 70, 110, 160, 220, 300, 420, 580, 800, 1200]}
    ]
    
    generator_id = 1
    available_buses = list(range(1, 51))
    np.random.shuffle(available_buses)
    
    for config in plant_configs:
        for i in range(config['count']):
            capacity = round(np.random.uniform(*config['capacity_range']))
            bus_id = available_buses[generator_id - 1]
            
            generators_data.append({
                'name': f"{config['name']}{generator_id:02d}",
                'bus': f'Bus{bus_id:02d}',
                'type': config['name'].lower(),
                'P max': capacity,
                'no load cost': round(capacity * np.random.uniform(0.5, 1.5)),
                'cost curve points filename': f"{config['name'].lower()}_{generator_id:02d}_bid.csv"
            })
            
            # 生成对应的容量段报价文件
            create_bidding_curve(
                output_dir, 
                f"{config['name'].lower()}_{generator_id:02d}_bid.csv",
                capacity,
                config['segments'],
                config['base_prices']
            )
            
            generator_id += 1
    
    generators_df = pd.DataFrame(generators_data)
    generators_df.to_csv(os.path.join(output_dir, 'generators.csv'), index=False)
    print(f"✅ 生成 {len(generators_df)} 台发电机和报价文件")
    
    # 4. 生成负荷数据
    loads_data = []
    
    # 为每个节点分配不同的负荷
    base_loads = np.random.uniform(100, 300, 50)  # 每个节点100-300MW基础负荷
    
    for i, base_load in enumerate(base_loads, 1):
        loads_data.append({
            'name': f'Load{i:02d}',
            'bus': f'Bus{i:02d}',
            'power': round(base_load),
        })
    
    loads_df = pd.DataFrame(loads_data)
    loads_df.to_csv(os.path.join(output_dir, 'loads.csv'), index=False)
    print(f"✅ 生成 {len(loads_df)} 个负荷点")
    
    # 5. 生成案例统计
    total_capacity = generators_df['P max'].sum()
    total_load = loads_df['power'].sum()
    
    stats_report = f"""
简化IEEE 50节点案例统计
======================

网络配置:
- 节点数: {len(buses_df)}
- 传输线数: {len(lines_df)}
- 发电机数: {len(generators_df)}
- 负荷点数: {len(loads_df)}

容量配置:
- 总装机容量: {total_capacity:,} MW
- 总负荷: {total_load:,} MW
- 备用率: {(total_capacity - total_load) / total_load * 100:.1f}%

发电机类型分布:
- Coal: 6台, 容量600-800MW, 6段报价
- Gas: 8台, 容量400-600MW, 7段报价  
- Steam: 8台, 容量200-400MW, 8段报价
- Peaker: 4台, 容量100-250MW, 10段报价

报价特征:
- 价格范围: 15-1200 $/MWh
- 总报价段数: {6*6 + 8*7 + 8*8 + 4*10}
- 支持标准容量段报价格式
"""
    
    with open(os.path.join(output_dir, 'case_info.txt'), 'w') as f:
        f.write(stats_report)
    
    print("✅ 案例统计报告已生成")
    print(f"\n🎉 简化IEEE 50节点案例生成完成！")
    print(f"📁 输出目录: {output_dir}")
    print(f"📊 总容量: {total_capacity:,} MW")
    print(f"📈 总负荷: {total_load:,} MW")
    print(f"🔋 备用率: {(total_capacity - total_load) / total_load * 100:.1f}%")
    
    return output_dir


def create_bidding_curve(output_dir, filename, capacity, segments, base_prices):
    """创建容量段报价曲线"""
    
    min_power = round(capacity * 0.4)  # 40%最小出力
    
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
            
            # 确保价格递增
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


if __name__ == "__main__":
    case_dir = create_simplified_ieee_50_case()
    print(f"\n🚀 案例已保存到: {case_dir}")
    print("💡 使用以下命令测试案例:")
    print(f"   python3 -c \"from simpower.solve import solve_problem; solve_problem('{case_dir}')\"")