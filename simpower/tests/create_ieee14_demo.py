#!/usr/bin/env python3
"""
创建IEEE 14节点12时段演示案例（符合simpower格式要求）
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def create_ieee14_demo():
    """创建演示案例"""
    
    case_dir = 'simpower/tests/ieee14_demo'
    os.makedirs(case_dir, exist_ok=True)
    print(f"📁 创建案例目录: {case_dir}")
    
    # 1. buses.csv
    buses_data = {
        'name': [f'Bus{i:02d}' for i in range(1, 15)],
        'bus_type': ['slack'] + ['PV']*4 + ['PQ']*9,
        'real_power_demand': [0, 21.7, 94.2, 47.8, 7.6, 11.2, 0, 0, 29.5, 9.0, 3.5, 6.1, 13.5, 14.9],
        'reactive_power_demand': [0, 12.7, 19.0, -3.9, 1.6, 7.5, 0, 0, 16.6, 5.8, 1.8, 1.6, 5.8, 5.0],
        'voltage_magnitude_setpoint': [1.06] + [1.045]*4 + [1.0]*9,
        'base_kv': [69.0]*14
    }
    buses_df = pd.DataFrame(buses_data)
    buses_df.to_csv(os.path.join(case_dir, 'buses.csv'), index=False)
    
    # 2. lines.csv
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
        'line_capacity': [130]*20,
        'emergency_capacity': [150]*20
    }
    lines_df = pd.DataFrame(lines_data)
    lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
    
    # 3. generators.csv - 简化版，使用多项式成本
    generators_data = {
        'name': ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7'],
        'bus': ['Bus01', 'Bus02', 'Bus03', 'Bus06', 'Bus06', 'Bus08', 'Bus08'],
        'P min': [10, 5, 10, 20, 50, 0, 0],
        'P max': [100, 40, 60, 80, 120, 30, 25],
        'rampratemax': [30, 20, 40, 25, 10, 30, 25],
        'rampratemin': [-30, -20, -40, -25, -10, -30, -25],
        'startupcost': [1000, 200, 800, 1500, 3000, 500, 0],
        'shutdowncost': [500, 100, 400, 800, 1500, 200, 0],
        'minuptime': [4, 2, 2, 6, 12, 1, 0],
        'mindowntime': [4, 1, 2, 6, 12, 1, 0],
        # 使用多项式成本：c0 + c1*P + c2*P^2，其中c0包含空载成本
        'costcurveequation': ['200 + 2.5 P + 0.01 P^2',
                             '50 + 1.0 P + 0.005 P^2',
                             '150 + 4.0 P + 0.02 P^2',
                             '250 + 2.2 P + 0.008 P^2',
                             '100 + 1.5 P + 0.003 P^2',
                             '80 + 8.0 P + 0.05 P^2',
                             '0 + 0.0 P + 0.0 P^2']  # 风电成本为0
    }
    generators_df = pd.DataFrame(generators_data)
    generators_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    
    # 4. loads.csv
    loads_data = {
        'name': [f'Load{i:02d}' for i in [2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]],
        'bus': [f'Bus{i:02d}' for i in [2, 3, 4, 5, 6, 9, 10, 11, 12, 13, 14]],
        'schedule filename': ['timeseries.csv']*11
    }
    loads_df = pd.DataFrame(loads_data)
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    
    # 5. timeseries.csv - 12小时
    base_time = datetime(2025, 1, 15, 0, 0)
    times = []
    load_factors = []
    
    hourly_factors = [0.75, 0.70, 0.68, 0.67, 0.68, 0.72, 
                     0.80, 0.88, 0.95, 0.98, 0.96, 0.94]
    
    for i in range(12):
        current_time = base_time + timedelta(hours=i)
        times.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        load_factors.append(hourly_factors[i])
    
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    
    print("✅ 所有文件创建完成")
    
    # 打印案例信息
    print("\n📊 IEEE 14节点演示案例:")
    print(f"  - 节点数: 14")
    print(f"  - 线路数: 20")
    print(f"  - 发电机数: 7")
    print(f"  - 负荷点数: 11")
    print(f"  - 时段数: 12")
    print(f"  - 使用多项式成本函数（包含空载成本）")
    
    return case_dir


if __name__ == "__main__":
    create_ieee14_demo()