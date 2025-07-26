#!/usr/bin/env python3
"""
创建IEEE 14节点12时段（12小时）仿真案例
7台机组，容量段报价
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import shutil


def create_ieee14_12periods_case():
    """创建IEEE 14节点12时段案例"""
    
    case_dir = 'simpower/tests/ieee14_12periods'
    os.makedirs(case_dir, exist_ok=True)
    print(f"📁 创建案例目录: {case_dir}")
    
    # 1. 创建buses.csv - 14个节点
    buses_data = {
        'name': [f'Bus{i:02d}' for i in range(1, 15)],
        'bus_type': ['slack'] + ['PV']*4 + ['PQ']*9,  # 1个平衡节点，4个PV节点，9个PQ节点
        'real_power_demand': [0, 21.7, 94.2, 47.8, 7.6, 11.2, 0, 0, 29.5, 9.0, 3.5, 6.1, 13.5, 14.9],
        'reactive_power_demand': [0, 12.7, 19.0, -3.9, 1.6, 7.5, 0, 0, 16.6, 5.8, 1.8, 1.6, 5.8, 5.0],
        'voltage_magnitude_setpoint': [1.06] + [1.045]*4 + [1.0]*9,
        'base_kv': [69.0]*14
    }
    buses_df = pd.DataFrame(buses_data)
    buses_df.to_csv(os.path.join(case_dir, 'buses.csv'), index=False)
    print("✅ 创建 buses.csv")
    
    # 2. 创建lines.csv - 20条线路
    lines_data = {
        'name': [f'Line{i:02d}' for i in range(1, 21)],
        'from bus': ['Bus01', 'Bus01', 'Bus02', 'Bus02', 'Bus02', 'Bus03', 'Bus04', 
                     'Bus04', 'Bus05', 'Bus06', 'Bus06', 'Bus06', 'Bus07', 'Bus07',
                     'Bus09', 'Bus09', 'Bus10', 'Bus12', 'Bus13', 'Bus04'],
        'to bus': ['Bus02', 'Bus05', 'Bus03', 'Bus04', 'Bus05', 'Bus04', 'Bus05',
                   'Bus07', 'Bus06', 'Bus11', 'Bus12', 'Bus13', 'Bus08', 'Bus09',
                   'Bus10', 'Bus14', 'Bus11', 'Bus13', 'Bus14', 'Bus09'],
        'resistance': [0.01938, 0.05403, 0.04699, 0.05811, 0.05695, 0.06701, 0.01335,
                      0.0, 0.0, 0.09498, 0.12291, 0.06615, 0.0, 0.0,
                      0.03181, 0.12711, 0.08205, 0.22092, 0.17093, 0.0],
        'reactance': [0.05917, 0.22304, 0.19797, 0.17632, 0.17388, 0.17103, 0.04211,
                     0.20912, 0.55618, 0.19890, 0.25581, 0.13027, 0.17615, 0.11001,
                     0.08450, 0.27038, 0.19207, 0.19988, 0.34802, 0.25202],
        'line_capacity': [130]*20,  # MW
        'emergency_capacity': [150]*20
    }
    lines_df = pd.DataFrame(lines_data)
    lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
    print("✅ 创建 lines.csv")
    
    # 3. 创建generators.csv - 7台机组
    generators_data = {
        'name': ['G1_Steam', 'G2_Hydro', 'G3_Gas', 'G4_Coal', 'G5_Nuclear', 'G6_Peaker', 'G7_Wind'],
        'bus': ['Bus01', 'Bus02', 'Bus03', 'Bus06', 'Bus06', 'Bus08', 'Bus08'],
        'fuel': ['Steam', 'Hydro', 'Gas', 'Coal', 'Nuclear', 'Gas', 'Wind'],
        'P min': [10, 5, 10, 20, 50, 0, 0],
        'P max': [100, 40, 60, 80, 120, 30, 25],
        'ramp rate': [30, 20, 40, 25, 10, 30, 25],  # MW/hour
        'start cost': [1000, 200, 800, 1500, 3000, 500, 0],
        'shut cost': [500, 100, 400, 800, 1500, 200, 0],
        'min run time': [4, 2, 2, 6, 12, 1, 0],
        'min stop time': [4, 1, 2, 6, 12, 1, 0],
        'no load cost': [200, 50, 150, 250, 100, 80, 0],
        'bid_type': ['block_bid']*6 + ['linear'],  # 前6台容量段报价，风电线性报价
        'min_bid_quantity': [10, 5, 10, 20, 50, 0, 0]
    }
    generators_df = pd.DataFrame(generators_data)
    generators_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    print("✅ 创建 generators.csv")
    
    # 4. 创建容量段报价文件（前6台机组）
    # G1_Steam - 3段报价
    g1_bids = pd.DataFrame({
        'hour': [1]*3,
        'block': [1, 2, 3],
        'power': [30, 40, 30],  # MW per block
        'price': [25, 35, 45]   # $/MWh
    })
    g1_bids.to_csv(os.path.join(case_dir, 'G1_Steam_block_bid.csv'), index=False)
    
    # G2_Hydro - 2段报价
    g2_bids = pd.DataFrame({
        'hour': [1]*2,
        'block': [1, 2],
        'power': [20, 15],
        'price': [10, 20]
    })
    g2_bids.to_csv(os.path.join(case_dir, 'G2_Hydro_block_bid.csv'), index=False)
    
    # G3_Gas - 3段报价
    g3_bids = pd.DataFrame({
        'hour': [1]*3,
        'block': [1, 2, 3],
        'power': [20, 20, 20],
        'price': [40, 50, 65]
    })
    g3_bids.to_csv(os.path.join(case_dir, 'G3_Gas_block_bid.csv'), index=False)
    
    # G4_Coal - 3段报价
    g4_bids = pd.DataFrame({
        'hour': [1]*3,
        'block': [1, 2, 3],
        'power': [30, 30, 20],
        'price': [22, 28, 38]
    })
    g4_bids.to_csv(os.path.join(case_dir, 'G4_Coal_block_bid.csv'), index=False)
    
    # G5_Nuclear - 2段报价（基荷）
    g5_bids = pd.DataFrame({
        'hour': [1]*2,
        'block': [1, 2],
        'power': [70, 50],
        'price': [15, 18]
    })
    g5_bids.to_csv(os.path.join(case_dir, 'G5_Nuclear_block_bid.csv'), index=False)
    
    # G6_Peaker - 2段报价（调峰）
    g6_bids = pd.DataFrame({
        'hour': [1]*2,
        'block': [1, 2],
        'power': [15, 15],
        'price': [80, 100]
    })
    g6_bids.to_csv(os.path.join(case_dir, 'G6_Peaker_block_bid.csv'), index=False)
    
    # G7_Wind - 线性报价
    g7_bids = pd.DataFrame({
        'hour': [1],
        'power': [25],
        'price': [0]  # 风电边际成本为0
    })
    g7_bids.to_csv(os.path.join(case_dir, 'G7_Wind_linear_bid.csv'), index=False)
    
    print("✅ 创建容量段报价文件")
    
    # 5. 创建loads.csv - 多时段负荷
    loads_data = {
        'name': [f'Load{i:02d}' for i in [2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]],
        'bus': [f'Bus{i:02d}' for i in [2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]],
        'schedule filename': ['timeseries.csv']*11
    }
    loads_df = pd.DataFrame(loads_data)
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    print("✅ 创建 loads.csv")
    
    # 6. 创建timeseries.csv - 12小时负荷曲线
    base_time = datetime(2025, 1, 15, 0, 0)
    times = []
    load_factors = []
    
    # 典型日负荷曲线（12小时，从0点到11点）
    hourly_factors = [
        0.75,  # 00:00 - 深夜低谷
        0.70,  # 01:00
        0.68,  # 02:00
        0.67,  # 03:00 - 最低点
        0.68,  # 04:00
        0.72,  # 05:00 - 开始上升
        0.80,  # 06:00 - 早晨
        0.88,  # 07:00
        0.95,  # 08:00 - 早高峰
        0.98,  # 09:00 - 高峰
        0.96,  # 10:00
        0.94   # 11:00 - 午间
    ]
    
    for i in range(12):
        current_time = base_time + timedelta(hours=i)
        times.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        load_factors.append(hourly_factors[i])
    
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    print("✅ 创建 timeseries.csv")
    
    # 7. 打印案例信息
    print("\n📊 IEEE 14节点12时段案例信息:")
    print(f"  - 节点数: 14")
    print(f"  - 线路数: 20")
    print(f"  - 发电机数: 7")
    print(f"  - 负荷点数: 11")
    print(f"  - 时段数: 12 (12小时)")
    print(f"  - 总装机容量: {sum(generators_data['P max'])} MW")
    print(f"  - 基础负荷: {sum(buses_data['real_power_demand'])} MW")
    print(f"  - 负荷变化范围: {min(load_factors)*100:.0f}% - {max(load_factors)*100:.0f}%")
    
    return case_dir


if __name__ == "__main__":
    print("🚀 创建IEEE 14节点12时段仿真案例")
    print("=" * 60)
    
    case_dir = create_ieee14_12periods_case()
    
    print(f"\n✅ 案例创建完成！")
    print(f"📁 案例目录: {case_dir}")