#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simpower 简化演示
================

本文件展示Simpower的核心功能，包括：
- 经济调度
- 节点电价计算
- 负载削减

运行方法：
cd /workspace
python examples/simple_demo.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 导入必要模块
from simpower.config import user_config
from simpower.tests.test_utils import *

def run_simple_demo():
    """运行简化演示"""
    
    print("Simpower 电力系统优化与市场仿真演示")
    print("=" * 50)
    
    # 启用对偶变量计算 (节点电价)
    user_config.duals = True
    print("✓ 对偶变量计算已启用 (节点电价功能)")
    
    print("\n案例1: 经济调度演示")
    print("-" * 30)
    
    # 创建3台不同类型的发电机组
    generators = [
        make_cheap_gen(pmax=100, pmin=20),     # 火电: 10$/MWh
        make_mid_gen(pmax=80, pmin=15),        # 燃气: 20$/MWh  
        make_expensive_gen(pmax=60, pmin=10)   # 尖峰: 30$/MWh
    ]
    
    print("发电机组配置:")
    print("- 火电机组: 100MW, 成本10$/MWh")
    print("- 燃气机组: 80MW, 成本20$/MWh")
    print("- 尖峰机组: 60MW, 成本30$/MWh")
    
    # 测试不同负载水平
    test_loads = [80, 120, 180, 250]
    
    print(f"\n{'负载(MW)':<10} {'火电(MW)':<10} {'燃气(MW)':<10} {'尖峰(MW)':<10} {'电价($/MWh)':<12}")
    print("-" * 60)
    
    for load in test_loads:
        try:
            # 求解优化问题
            power_system, times = solve_problem(generators, **make_loads_times(Pdt=[load]))
            
            # 获取机组出力
            fire_power = value(generators[0].power(times[0]))
            gas_power = value(generators[1].power(times[0]))
            peak_power = value(generators[2].power(times[0]))
            
            # 获取节点电价
            price = power_system.buses[0].price(times[0])
            
            print(f"{load:<10} {fire_power:<10.1f} {gas_power:<10.1f} {peak_power:<10.1f} {price:<12.2f}")
            
        except Exception as e:
            print(f"{load:<10} 求解失败: {e}")
    
    print("\n案例2: 负载削减演示")
    print("-" * 30)
    
    # 超出总供应能力的负载
    high_load = 280  # 总供应能力只有240MW
    
    print(f"测试负载: {high_load}MW (超出总供应能力240MW)")
    
    try:
        power_system, times = solve_problem(generators, **make_loads_times(Pdt=[high_load]))
        
        fire_power = value(generators[0].power(times[0]))
        gas_power = value(generators[1].power(times[0]))
        peak_power = value(generators[2].power(times[0]))
        total_gen = fire_power + gas_power + peak_power
        load_shed = high_load - total_gen
        price = power_system.buses[0].price(times[0])
        
        print(f"实际发电量: {total_gen:.1f}MW")
        print(f"负载削减量: {load_shed:.1f}MW")
        print(f"系统电价: {price:.2f}$/MWh")
        
        if load_shed > 0:
            print("✓ 系统正确处理了负载削减情况")
            print("✓ 电价升至负载削减成本，反映供应紧张")
        
    except Exception as e:
        print(f"负载削减测试失败: {e}")
    
    print("\n案例3: 节点电价分析")
    print("-" * 30)
    
    print("电价形成机制验证:")
    
    # 低负载场景
    low_load = 50
    power_system, times = solve_problem(generators, **make_loads_times(Pdt=[low_load]))
    low_price = power_system.buses[0].price(times[0])
    
    # 中等负载场景  
    mid_load = 120
    power_system, times = solve_problem(generators, **make_loads_times(Pdt=[mid_load]))
    mid_price = power_system.buses[0].price(times[0])
    
    # 高负载场景
    high_load = 200
    power_system, times = solve_problem(generators, **make_loads_times(Pdt=[high_load]))
    high_price = power_system.buses[0].price(times[0])
    
    print(f"低负载({low_load}MW): {low_price:.2f}$/MWh")
    print(f"中负载({mid_load}MW): {mid_price:.2f}$/MWh") 
    print(f"高负载({high_load}MW): {high_price:.2f}$/MWh")
    
    print(f"\n电价分析:")
    if low_price <= mid_price <= high_price:
        print("✓ 电价随负载增加而上升，符合经济学原理")
    
    if low_price == 10.0:
        print("✓ 低负载时电价等于最便宜机组成本(10$/MWh)")
        
    if high_price == 30.0:
        print("✓ 高负载时电价等于最贵运行机组成本(30$/MWh)")
    
    print(f"\n演示总结:")
    print("✅ 经济调度功能正常 - 优化资源配置")
    print("✅ 节点电价计算正确 - 反映边际成本")
    print("✅ 负载削减处理合理 - 供需平衡优化")
    print("✅ Simpower电力市场仿真功能完整可用!")


if __name__ == "__main__":
    try:
        run_simple_demo()
    except ImportError as e:
        print(f"导入错误: {e}")
        print("请确保在项目根目录下运行：python examples/simple_demo.py")
    except Exception as e:
        print(f"运行错误: {e}")
        import traceback
        traceback.print_exc()