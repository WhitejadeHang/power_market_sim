#!/usr/bin/env python3
"""
创建一个简单的3节点演示案例
"""

import os
import pandas as pd
from datetime import datetime, timedelta

def create_simple_demo():
    """创建简单案例"""
    
    case_dir = 'simpower/tests/simple_demo'
    os.makedirs(case_dir, exist_ok=True)
    
    # 1. buses.csv - 3个节点
    buses_df = pd.DataFrame({
        'name': ['Bus1', 'Bus2', 'Bus3'],
        'bus_type': ['slack', 'PV', 'PQ'],
        'real_power_demand': [0, 50, 100],
        'reactive_power_demand': [0, 10, 20]
    })
    buses_df.to_csv(os.path.join(case_dir, 'buses.csv'), index=False)
    
    # 2. lines.csv - 3条线路
    lines_df = pd.DataFrame({
        'name': ['Line1', 'Line2', 'Line3'],
        'frombus': ['Bus1', 'Bus1', 'Bus2'],
        'tobus': ['Bus2', 'Bus3', 'Bus3'],
        'reactance': [0.1, 0.15, 0.12],
        'pmax': [100, 100, 100]
    })
    lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
    
    # 3. generators.csv - 2台机组
    generators_df = pd.DataFrame({
        'name': ['G1', 'G2'],
        'bus': ['Bus1', 'Bus2'],
        'P min': [20, 10],
        'P max': [100, 80],
        'rampratemax': [50, 40],
        'rampratemin': [-50, -40],
        'startupcost': [500, 300],
        'shutdowncost': [200, 150],
        'minuptime': [2, 1],
        'mindowntime': [2, 1],
        'costcurveequation': [
            '100 + 20 P + 0.02 P^2',  # G1: 空载100, 边际20, 二次0.02
            '50 + 25 P + 0.03 P^2'     # G2: 空载50, 边际25, 二次0.03
        ]
    })
    generators_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    
    # 4. loads.csv
    loads_df = pd.DataFrame({
        'name': ['Load2', 'Load3'],
        'bus': ['Bus2', 'Bus3'],
        'schedule filename': ['timeseries.csv', 'timeseries.csv']
    })
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    
    # 5. timeseries.csv - 12小时
    base_time = datetime(2025, 1, 15, 0, 0)
    times = []
    load_factors = []
    
    # 简单的负荷曲线
    hourly_factors = [0.7, 0.65, 0.6, 0.6, 0.65, 0.7,
                     0.8, 0.9, 0.95, 1.0, 0.95, 0.9]
    
    for i in range(12):
        times.append((base_time + timedelta(hours=i)).strftime("%Y-%m-%d %H:%M:%S"))
        load_factors.append(hourly_factors[i])
    
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(case_dir, 'timeseries.csv'), index=False)
    
    print("✅ 简单3节点案例创建完成")
    print(f"📁 案例目录: {case_dir}")
    print("  - 3个节点, 3条线路, 2台发电机")
    print("  - 12个时段仿真")
    
    return case_dir


if __name__ == "__main__":
    create_simple_demo()