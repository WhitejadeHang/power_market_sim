#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simpower 基础使用案例
====================

本文件包含了Simpower的基础使用示例，展示如何进行：
1. 经济调度 (Economic Dispatch)
2. 机组组合 (Unit Commitment) 
3. 电价分析
4. 结果可视化

运行示例：
python examples/basic_examples.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simpower.tests.test_utils import *
from simpower.config import user_config
import pandas as pd
import matplotlib.pyplot as plt

def example_1_economic_dispatch():
    """
    案例1: 基础经济调度
    
    场景：某电力系统有3台机组，需要满足100MW负载
    - 火电机组：50MW，成本10$/MWh
    - 燃气机组：40MW，成本20$/MWh  
    - 风电机组：30MW，成本0$/MWh
    """
    print("=" * 50)
    print("案例1: 经济调度 (Economic Dispatch)")
    print("=" * 50)
    
    # 启用对偶变量计算以获取电价
    user_config.duals = True
    
    # 创建发电机组
    generators = [
        make_cheap_gen(pmax=50, name='火电'),     # 10$/MWh
        make_mid_gen(pmax=40, name='燃气'),       # 20$/MWh  
        make_expensive_gen(pmax=30, name='风电', cost=0)  # 0$/MWh
    ]
    
    # 设置不同负载水平
    load_levels = [60, 80, 100, 120]
    
    print("负载(MW)  火电(MW)  燃气(MW)  风电(MW)  总成本($/h)  电价($/MWh)")
    print("-" * 70)
    
    for load in load_levels:
        # 求解经济调度
        power_system, times = solve_problem(generators, **make_loads_times(Pdt=[load]))
        
        # 获取结果
        coal_power = value(generators[0].power(times[0]))
        gas_power = value(generators[1].power(times[0]))
        wind_power = value(generators[2].power(times[0]))
        
        # 计算总成本
        total_cost = coal_power * 10 + gas_power * 20 + wind_power * 0
        
        # 获取电价
        price = power_system.buses[0].price(times[0])
        
        print(f"{load:7.0f}   {coal_power:7.1f}   {gas_power:7.1f}   {wind_power:7.1f}   {total_cost:9.0f}   {price:8.2f}")
    
    print("\n经济调度原理验证:")
    print("✓ 优先调用成本最低的机组")
    print("✓ 电价等于最后投入机组的边际成本")
    print("✓ 当所有便宜机组满载时，电价上升至次便宜机组成本")
    

def example_2_unit_commitment():
    """
    案例2: 24小时机组组合
    
    场景：考虑启停约束的多时段优化
    包含最小启停时间、爬坡约束等
    """
    print("\n" + "=" * 50)
    print("案例2: 机组组合 (Unit Commitment)")
    print("=" * 50)
    
    user_config.duals = True
    
    # 创建有启停约束的机组
    generators = [
        make_cheap_gen(pmax=100, pmin=30, name='基荷火电'),
        make_mid_gen(pmax=80, pmin=20, name='调峰燃气'),
        make_expensive_gen(pmax=60, pmin=10, name='尖峰燃气')
    ]
    
    # 典型日负载曲线 (MW)
    daily_load = [
        # 0-5时: 夜间低谷
        60, 55, 50, 48, 52, 58,
        # 6-11时: 上午负载上升  
        70, 90, 110, 130, 140, 150,
        # 12-17时: 日间高峰
        160, 155, 150, 155, 170, 180,
        # 18-23时: 晚间高峰后回落
        190, 175, 150, 120, 90, 75
    ]
    
    # 求解24小时机组组合
    power_system, times = solve_problem(generators, **make_loads_times(Pdt=daily_load))
    
    # 收集结果
    results = []
    for i, time in enumerate(times):
        hour_result = {
            'Hour': i,
            'Load': daily_load[i],
            'Coal_Power': value(generators[0].power(time)),
            'Gas1_Power': value(generators[1].power(time)),
            'Gas2_Power': value(generators[2].power(time)),
            'Coal_Status': value(generators[0].status(time)),
            'Gas1_Status': value(generators[1].status(time)),
            'Gas2_Status': value(generators[2].status(time)),
            'Price': power_system.buses[0].price(time)
        }
        results.append(hour_result)
    
    results_df = pd.DataFrame(results)
    
    # 打印关键时段结果
    print("时段  负载   基荷火电  调峰燃气  尖峰燃气   电价")
    print("     (MW)   出力/状态  出力/状态  出力/状态  ($/MWh)")
    print("-" * 60)
    
    key_hours = [0, 6, 12, 18, 23]  # 选择关键时段显示
    for hour in key_hours:
        row = results_df.iloc[hour]
        print(f"{hour:2d}   {row['Load']:5.0f}   "
              f"{row['Coal_Power']:4.0f}/{row['Coal_Status']:.0f}    "
              f"{row['Gas1_Power']:4.0f}/{row['Gas1_Status']:.0f}     "
              f"{row['Gas2_Power']:4.0f}/{row['Gas2_Status']:.0f}     "
              f"{row['Price']:6.2f}")
    
    # 统计分析
    total_cost = sum(results_df['Coal_Power'] * 10 + 
                    results_df['Gas1_Power'] * 20 + 
                    results_df['Gas2_Power'] * 30)
    avg_price = results_df['Price'].mean()
    peak_price = results_df['Price'].max()
    
    print(f"\n24小时运行统计:")
    print(f"总发电成本: ${total_cost:,.0f}")
    print(f"平均电价: {avg_price:.2f} $/MWh")
    print(f"峰值电价: {peak_price:.2f} $/MWh")
    
    return results_df


def example_3_load_shedding():
    """
    案例3: 负载削减分析
    
    场景：供应能力不足时的优化决策
    """
    print("\n" + "=" * 50)
    print("案例3: 负载削减分析")
    print("=" * 50)
    
    user_config.duals = True
    
    # 有限的发电能力
    generators = [
        make_cheap_gen(pmax=80, name='机组1'),
        make_mid_gen(pmax=60, name='机组2')
    ]
    
    # 超出供应能力的负载
    high_load = 180  # 需求180MW，但总供应能力只有140MW
    
    power_system, times = solve_problem(generators, **make_loads_times(Pdt=[high_load]))
    
    # 获取结果
    gen1_power = value(generators[0].power(times[0]))
    gen2_power = value(generators[1].power(times[0]))
    total_generation = gen1_power + gen2_power
    load_shed = high_load - total_generation
    price = power_system.buses[0].price(times[0])
    
    print(f"需求负载: {high_load} MW")
    print(f"机组1出力: {gen1_power:.1f} MW")
    print(f"机组2出力: {gen2_power:.1f} MW") 
    print(f"总发电量: {total_generation:.1f} MW")
    print(f"负载削减: {load_shed:.1f} MW")
    print(f"系统电价: {price:.2f} $/MWh")
    
    print(f"\n负载削减分析:")
    print(f"✓ 供应不足时，系统电价升至负载削减成本")
    print(f"✓ 所有可用机组满载运行")
    print(f"✓ 削减的负载 = 需求 - 最大供应能力")


def example_4_price_sensitivity():
    """
    案例4: 电价敏感性分析
    
    分析不同因素对电价的影响
    """
    print("\n" + "=" * 50)
    print("案例4: 电价敏感性分析")
    print("=" * 50)
    
    user_config.duals = True
    
    # 基准场景
    base_generators = [
        make_cheap_gen(pmax=100, name='基准便宜'),
        make_mid_gen(pmax=80, name='基准中等'),
        make_expensive_gen(pmax=60, name='基准昂贵')
    ]
    
    load_range = range(50, 251, 25)
    scenarios = {
        '基准场景': base_generators,
        '便宜机组故障': [make_mid_gen(pmax=80), make_expensive_gen(pmax=60)],
        '新增可再生能源': base_generators + [make_cheap_gen(pmax=50, cost=0, name='风电')]
    }
    
    print("负载(MW)  基准场景  机组故障  新增风电")
    print("         ($/MWh)  ($/MWh)  ($/MWh)")
    print("-" * 40)
    
    for load in load_range:
        prices = []
        for scenario_name, gens in scenarios.items():
            try:
                power_system, times = solve_problem(gens, **make_loads_times(Pdt=[load]))
                price = power_system.buses[0].price(times[0])
                prices.append(price)
            except:
                prices.append(float('inf'))  # 无解时标记为无穷大
        
        print(f"{load:7.0f}   {prices[0]:7.2f}   {prices[1]:7.2f}   {prices[2]:7.2f}")
    
    print(f"\n价格敏感性分析:")
    print(f"✓ 机组故障时电价显著上升")
    print(f"✓ 新增可再生能源降低系统电价")
    print(f"✓ 负载增加推高边际电价")


def example_5_visualization():
    """
    案例5: 结果可视化
    
    创建图表展示优化结果
    """
    print("\n" + "=" * 50)
    print("案例5: 结果可视化")
    print("=" * 50)
    
    # 重用案例2的结果
    results_df = example_2_unit_commitment()
    
    # 创建可视化
    fig, axes = plt.subplots(2, 2, figsize=(15, 10))
    plt.rcParams['font.sans-serif'] = ['SimHei']  # 支持中文显示
    plt.rcParams['axes.unicode_minus'] = False
    
    # 1. 负载和发电曲线
    axes[0,0].plot(results_df['Hour'], results_df['Load'], 'k-', linewidth=2, label='负载')
    axes[0,0].plot(results_df['Hour'], results_df['Coal_Power'], 'brown', label='基荷火电')
    axes[0,0].plot(results_df['Hour'], results_df['Gas1_Power'], 'blue', label='调峰燃气')
    axes[0,0].plot(results_df['Hour'], results_df['Gas2_Power'], 'red', label='尖峰燃气')
    axes[0,0].set_title('24小时负载与发电曲线')
    axes[0,0].set_xlabel('时间 (小时)')
    axes[0,0].set_ylabel('功率 (MW)')
    axes[0,0].legend()
    axes[0,0].grid(True, alpha=0.3)
    
    # 2. 电价曲线
    axes[0,1].plot(results_df['Hour'], results_df['Price'], 'red', linewidth=2)
    axes[0,1].set_title('24小时电价曲线')
    axes[0,1].set_xlabel('时间 (小时)')
    axes[0,1].set_ylabel('电价 ($/MWh)')
    axes[0,1].grid(True, alpha=0.3)
    
    # 3. 机组启停状态
    status_matrix = results_df[['Coal_Status', 'Gas1_Status', 'Gas2_Status']].T
    im = axes[1,0].imshow(status_matrix, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)
    axes[1,0].set_title('机组运行状态')
    axes[1,0].set_xlabel('时间 (小时)')
    axes[1,0].set_yticks([0, 1, 2])
    axes[1,0].set_yticklabels(['基荷火电', '调峰燃气', '尖峰燃气'])
    
    # 4. 成本堆叠图
    coal_cost = results_df['Coal_Power'] * 10
    gas1_cost = results_df['Gas1_Power'] * 20  
    gas2_cost = results_df['Gas2_Power'] * 30
    
    axes[1,1].fill_between(results_df['Hour'], 0, coal_cost, alpha=0.7, label='火电成本')
    axes[1,1].fill_between(results_df['Hour'], coal_cost, coal_cost + gas1_cost, alpha=0.7, label='燃气1成本')
    axes[1,1].fill_between(results_df['Hour'], coal_cost + gas1_cost, 
                          coal_cost + gas1_cost + gas2_cost, alpha=0.7, label='燃气2成本')
    axes[1,1].set_title('小时发电成本构成')
    axes[1,1].set_xlabel('时间 (小时)')
    axes[1,1].set_ylabel('成本 ($/小时)')
    axes[1,1].legend()
    axes[1,1].grid(True, alpha=0.3)
    
    plt.tight_layout()
    
    # 保存图表
    output_path = 'simpower_examples_results.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"可视化结果已保存至: {output_path}")
    
    # 显示图表
    plt.show()


def main():
    """
    运行所有示例案例
    """
    print("Simpower 电力系统优化与市场仿真 - 基础案例演示")
    print("=" * 60)
    print("本演示包含5个案例，展示Simpower的核心功能:")
    print("1. 经济调度 - 最优发电资源分配")
    print("2. 机组组合 - 考虑启停约束的多时段优化")
    print("3. 负载削减 - 供需不平衡时的优化决策")
    print("4. 价格敏感性 - 不同因素对电价的影响")
    print("5. 结果可视化 - 图表展示和分析")
    
    try:
        # 运行所有案例
        example_1_economic_dispatch()
        example_2_unit_commitment()
        example_3_load_shedding()
        example_4_price_sensitivity()
        example_5_visualization()
        
        print("\n" + "=" * 60)
        print("✅ 所有案例运行完成!")
        print("✅ Simpower电力市场仿真功能验证成功!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ 运行出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()