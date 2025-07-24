#!/usr/bin/env python3
"""
简化的边际成本报价功能测试
验证Simpower当前使用的是容量段总价格，并演示如何支持边际成本报价
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np


def analyze_current_bidding_format():
    """分析当前Simpower的投标格式"""
    
    print("🔍 当前Simpower投标格式分析")
    print("=" * 50)
    
    # 读取现有投标数据
    cheap_bids = pd.read_csv('simpower/tests/ed-custom-bidding-points/bid-points-cheap.csv')
    expensive_bids = pd.read_csv('simpower/tests/ed-custom-bidding-points/bid-points-expensive.csv')
    
    # 标准化列名
    cheap_bids.columns = cheap_bids.columns.str.strip()
    expensive_bids.columns = expensive_bids.columns.str.strip()
    
    print("📊 Cheap机组投标数据分析:")
    print(cheap_bids)
    print()
    
    print("🔍 成本类型确认:")
    print("Cheap机组边际成本计算:")
    
    total_costs = []
    marginal_costs = []
    
    for i in range(len(cheap_bids)):
        power = cheap_bids.iloc[i]['power']
        cost = cheap_bids.iloc[i]['cost']
        
        if i == 0:
            print(f"  段{i+1}: {power:6.0f}MW -> {cost:8.0f}$ (起始点)")
            marginal_cost = 0
        else:
            prev_power = cheap_bids.iloc[i-1]['power']
            prev_cost = cheap_bids.iloc[i-1]['cost']
            power_diff = power - prev_power
            cost_diff = cost - prev_cost
            marginal_cost = cost_diff / power_diff if power_diff > 0 else 0
            
            print(f"  段{i+1}: {power:6.0f}MW -> {cost:8.0f}$ (增量: {power_diff}MW, {cost_diff}$, 边际: {marginal_cost:.1f}$/MWh)")
        
        total_costs.append(cost)
        marginal_costs.append(marginal_cost)
    
    print()
    print("💡 结论:")
    print("✅ 当前系统使用: 容量段总价格 (Capacity Block Total Price)")
    print("  - cost字段表示从0MW到该功率的累计总成本")
    print("  - 边际成本通过相邻段的差值计算")
    print("  - 这是电力市场中的标准容量段报价格式")
    
    return cheap_bids, total_costs, marginal_costs


def demonstrate_marginal_cost_conversion():
    """演示边际成本到总成本的转换"""
    
    print("\n🔄 边际成本报价转换演示")
    print("=" * 50)
    
    # 假设我们有边际成本报价
    print("📊 假设的边际成本报价:")
    marginal_bid_data = pd.DataFrame({
        'power_from': [0, 80, 150, 220],
        'power_to': [80, 150, 220, 300],
        'marginal_cost': [9.0, 13.0, 18.0, 25.0]
    })
    
    print(marginal_bid_data)
    
    # 转换为总成本格式
    print("\n🔄 转换为总成本格式:")
    total_cost_data = []
    cumulative_cost = 0
    
    # 起始点
    total_cost_data.append({'power': 0, 'cost': 0})
    
    for i, row in marginal_bid_data.iterrows():
        power_to = row['power_to']
        power_from = row['power_from']
        marginal_cost = row['marginal_cost']
        
        # 计算该段的成本
        segment_capacity = power_to - power_from
        segment_cost = segment_capacity * marginal_cost
        cumulative_cost += segment_cost
        
        total_cost_data.append({
            'power': power_to,
            'cost': cumulative_cost
        })
        
        print(f"  段{i+1}: {power_from:3.0f}-{power_to:3.0f}MW, "
              f"边际成本: {marginal_cost:5.1f}$/MWh, "
              f"段成本: {segment_cost:6.0f}$, "
              f"累计成本: {cumulative_cost:8.0f}$")
    
    # 转换结果
    converted_df = pd.DataFrame(total_cost_data)
    print("\n📋 转换后的总成本格式 (Simpower标准格式):")
    print(converted_df)
    
    return converted_df


def demonstrate_reverse_conversion():
    """演示总成本到边际成本的反向转换"""
    
    print("\n↩️ 总成本到边际成本的反向转换")
    print("=" * 50)
    
    # 使用之前分析的Cheap机组数据
    cheap_bids = pd.read_csv('simpower/tests/ed-custom-bidding-points/bid-points-cheap.csv')
    cheap_bids.columns = cheap_bids.columns.str.strip()
    
    print("📊 原始总成本数据:")
    print(cheap_bids)
    
    print("\n🔄 提取边际成本信息:")
    marginal_schedule = []
    
    for i in range(1, len(cheap_bids)):
        power_from = cheap_bids.iloc[i-1]['power']
        power_to = cheap_bids.iloc[i]['power']
        cost_from = cheap_bids.iloc[i-1]['cost']
        cost_to = cheap_bids.iloc[i]['cost']
        
        capacity = power_to - power_from
        segment_cost = cost_to - cost_from
        marginal_cost = segment_cost / capacity if capacity > 0 else 0
        
        marginal_schedule.append({
            'segment': i,
            'power_from': power_from,
            'power_to': power_to,
            'capacity_mw': capacity,
            'marginal_cost_mwh': marginal_cost,
            'segment_cost': segment_cost
        })
        
        print(f"  段{i}: {power_from:3.0f}-{power_to:3.0f}MW, "
              f"容量: {capacity:3.0f}MW, "
              f"边际成本: {marginal_cost:5.1f}$/MWh, "
              f"段成本: {segment_cost:6.0f}$")
    
    marginal_df = pd.DataFrame(marginal_schedule)
    print("\n📋 边际成本时间表:")
    print(marginal_df[['segment', 'power_from', 'power_to', 'marginal_cost_mwh']])


def create_marginal_cost_csv_example():
    """创建边际成本CSV格式示例"""
    
    print("\n📁 边际成本CSV格式示例")
    print("=" * 50)
    
    # 创建边际成本格式的数据
    marginal_csv_data = pd.DataFrame({
        'power': [0, 100, 200, 300, 400],
        'marginal_cost': [0, 12.0, 16.0, 22.0, 30.0]
    })
    
    print("📊 边际成本CSV格式:")
    print(marginal_csv_data)
    
    # 转换为总成本格式
    total_csv_data = marginal_csv_data.copy()
    total_csv_data['cost'] = 0.0
    
    for i in range(1, len(total_csv_data)):
        power_diff = total_csv_data.iloc[i]['power'] - total_csv_data.iloc[i-1]['power']
        marginal_cost = total_csv_data.iloc[i]['marginal_cost']
        segment_cost = power_diff * marginal_cost
        total_csv_data.iloc[i, total_csv_data.columns.get_loc('cost')] = \
            total_csv_data.iloc[i-1]['cost'] + segment_cost
    
    print("\n🔄 转换为总成本CSV格式:")
    print(total_csv_data[['power', 'cost']])
    
    # 保存示例文件
    marginal_file = "marginal_cost_example.csv"
    total_file = "total_cost_example.csv"
    
    marginal_csv_data.to_csv(marginal_file, index=False)
    total_csv_data[['power', 'cost']].to_csv(total_file, index=False)
    
    print(f"\n✅ 已保存示例文件:")
    print(f"  边际成本格式: {marginal_file}")
    print(f"  总成本格式: {total_file}")
    
    return marginal_file, total_file


def usage_recommendations():
    """使用建议"""
    
    print("\n💡 使用建议和最佳实践")
    print("=" * 50)
    
    print("🎯 当前Simpower投标格式确认:")
    print("  ✅ 使用容量段总价格 (power, cost)")
    print("  ✅ cost字段表示累计总成本")
    print("  ✅ 系统自动计算边际成本")
    print("  ✅ 符合电力市场标准实践")
    
    print("\n📋 新增边际成本报价支持建议:")
    print("  1. 🔄 格式转换: 边际成本 -> 总成本")
    print("  2. 📊 自动检测: 智能识别输入格式")
    print("  3. ✅ 数据验证: 检查数据合理性")
    print("  4. 🔧 向后兼容: 保持现有功能不变")
    
    print("\n🚀 实现方案:")
    print("  📝 方案1: 扩展现有Generator类，支持marginal_cost_filename")
    print("  📝 方案2: 在数据读取阶段进行格式转换")
    print("  📝 方案3: 创建增强的Bid类，支持多种格式")
    print("  📝 方案4: 添加格式转换工具函数")
    
    print("\n📊 应用场景:")
    print("  🏭 传统发电商: 继续使用总成本格式")
    print("  🔋 新能源发电: 可使用边际成本格式")
    print("  📈 电力交易: 支持多种报价习惯")
    print("  🔄 数据迁移: 不同系统间格式转换")


if __name__ == "__main__":
    print("🚀 Simpower 投标格式分析和边际成本支持方案")
    print("=" * 60)
    
    # 分析当前格式
    current_data, total_costs, marginal_costs = analyze_current_bidding_format()
    
    # 演示转换功能
    demonstrate_marginal_cost_conversion()
    demonstrate_reverse_conversion()
    
    # 创建示例文件
    marginal_file, total_file = create_marginal_cost_csv_example()
    
    # 使用建议
    usage_recommendations()
    
    # 清理示例文件
    for file in [marginal_file, total_file]:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n🎉 分析完成!")
    print("\n✅ 核心结论:")
    print("  📊 Simpower当前使用容量段总价格格式")
    print("  🔄 可以通过格式转换支持边际成本报价")
    print("  ✅ 建议创建增强模块，支持两种格式")
    print("  🎯 保持向后兼容性，满足不同用户需求")