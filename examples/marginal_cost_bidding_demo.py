#!/usr/bin/env python3
"""
Simpower 边际成本报价功能演示
展示边际成本申报格式的支持和转换功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from simpower.bidding_enhanced import (
    EnhancedBid, 
    create_bidding_from_marginal_costs, 
    create_bidding_from_total_costs,
    analyze_bidding_format,
    convert_marginal_to_total_csv
)


def demo_bidding_format_detection():
    """演示投标格式自动检测功能"""
    
    print("🔍 投标格式自动检测演示")
    print("=" * 50)
    
    # 分析现有的总成本格式文件
    print("\n📊 分析现有总成本格式:")
    analysis = analyze_bidding_format('simpower/tests/ed-custom-bidding-points/bid-points-cheap.csv')
    print(f"  文件: {analysis['file']}")
    print(f"  列名: {analysis['columns']}")
    print(f"  段数: {analysis['num_segments']}")
    print(f"  检测格式: {analysis['detected_format']}")
    
    if 'marginal_cost_stats' in analysis:
        stats = analysis['marginal_cost_stats']
        print(f"  边际成本统计:")
        print(f"    最小值: {stats['min']:.1f} $/MWh")
        print(f"    最大值: {stats['max']:.1f} $/MWh")
        print(f"    平均值: {stats['mean']:.1f} $/MWh")
    
    for rec in analysis['recommendations']:
        print(f"  建议: {rec}")


def demo_marginal_cost_creation():
    """演示从边际成本创建投标对象"""
    
    print("\n🏗️ 从边际成本创建投标对象演示")
    print("=" * 50)
    
    # 定义边际成本数据
    power_segments = [0, 50, 100, 150, 200]  # MW
    marginal_costs = [8.0, 12.0, 16.0, 20.0]  # $/MWh
    
    print("📊 边际成本输入数据:")
    print("  功率段: ", power_segments)
    print("  边际成本: ", marginal_costs)
    
    # 创建投标对象
    bid = create_bidding_from_marginal_costs(
        power_segments=power_segments,
        marginal_costs=marginal_costs
    )
    
    print("\n🔄 转换后的总成本格式:")
    if bid.bid_points is not None:
        for i, row in bid.bid_points.iterrows():
            power = row['power']
            total_cost = row['cost']
            print(f"  {power:6.0f}MW -> {total_cost:8.1f}$")
    
    # 获取边际成本时间表
    schedule = bid.get_marginal_cost_schedule()
    print("\n📈 边际成本时间表:")
    if schedule is not None:
        for i, row in schedule.iterrows():
            print(f"  段{row['segment']}: {row['power_from']:3.0f}-{row['power_to']:3.0f}MW "
                  f"(容量: {row['capacity']:3.0f}MW, 边际成本: {row['marginal_cost']:5.1f}$/MWh, "
                  f"段成本: {row['segment_cost']:6.1f}$)")


def demo_format_conversion():
    """演示格式转换功能"""
    
    print("\n🔄 格式转换功能演示")
    print("=" * 50)
    
    # 创建边际成本格式的示例数据
    marginal_data = pd.DataFrame({
        'power': [0, 100, 200, 300],
        'marginal_cost': [0, 10.0, 15.0, 25.0]
    })
    
    print("📊 边际成本格式输入:")
    print(marginal_data)
    
    # 使用EnhancedBid进行转换
    bid = EnhancedBid(bid_points=marginal_data, bid_format="marginal_cost")
    
    print("\n🔄 转换为总成本格式:")
    print(bid.bid_points)
    
    # 获取投标总结
    summary = bid.get_bid_summary()
    print(f"\n📋 投标总结:")
    for key, value in summary.items():
        if key != 'power_range':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value[0]}-{value[1]} MW")


def demo_csv_conversion():
    """演示CSV文件格式转换"""
    
    print("\n📁 CSV文件格式转换演示")
    print("=" * 50)
    
    # 创建边际成本格式的CSV文件
    marginal_csv_file = "marginal_cost_example.csv"
    total_csv_file = "total_cost_converted.csv"
    
    # 创建示例边际成本数据
    marginal_data = pd.DataFrame({
        'power': [0, 80, 160, 240, 300],
        'marginal_cost': [0, 12.0, 18.0, 24.0, 30.0]
    })
    
    # 保存边际成本CSV
    marginal_data.to_csv(marginal_csv_file, index=False)
    print(f"✅ 创建边际成本CSV: {marginal_csv_file}")
    
    # 分析文件格式
    analysis = analyze_bidding_format(marginal_csv_file)
    print(f"📊 检测格式: {analysis['detected_format']}")
    
    # 转换为总成本格式
    success = convert_marginal_to_total_csv(marginal_csv_file, total_csv_file)
    
    if success:
        print(f"✅ 转换成功: {total_csv_file}")
        
        # 显示转换结果
        converted_data = pd.read_csv(total_csv_file)
        print("\n🔄 转换结果:")
        print(converted_data)
        
        # 计算验证
        print("\n🧮 边际成本验证:")
        for i in range(1, len(converted_data)):
            power_diff = converted_data.iloc[i]['power'] - converted_data.iloc[i-1]['power']
            cost_diff = converted_data.iloc[i]['cost'] - converted_data.iloc[i-1]['cost']
            if power_diff > 0:
                calculated_marginal = cost_diff / power_diff
                original_marginal = marginal_data.iloc[i]['marginal_cost']
                print(f"  段{i}: 原始边际成本={original_marginal:.1f}, 计算边际成本={calculated_marginal:.1f}, "
                      f"匹配={'✅' if abs(calculated_marginal - original_marginal) < 0.1 else '❌'}")
    
    # 清理临时文件
    for file in [marginal_csv_file, total_csv_file]:
        if os.path.exists(file):
            os.remove(file)
            print(f"🗑️ 清理临时文件: {file}")


def demo_comparison():
    """演示两种格式的对比"""
    
    print("\n⚖️ 容量段总价格 vs 边际成本报价对比")
    print("=" * 60)
    
    # 相同的发电机，用两种格式表示
    print("📊 同一发电机的两种报价格式:")
    
    # 格式1: 容量段总价格 (当前标准)
    total_cost_data = pd.DataFrame({
        'power': [0, 100, 180, 250],
        'cost': [0, 1000, 2000, 3500]
    })
    
    # 格式2: 边际成本
    marginal_cost_data = pd.DataFrame({
        'power': [0, 100, 180, 250],
        'marginal_cost': [0, 10.0, 12.5, 21.4]  # 根据总成本计算得出
    })
    
    print("\n💰 容量段总价格格式:")
    print(total_cost_data)
    
    print("\n📈 边际成本格式:")
    print(marginal_cost_data)
    
    # 创建两种投标对象
    bid1 = EnhancedBid(bid_points=total_cost_data, bid_format="total_cost")
    bid2 = EnhancedBid(bid_points=marginal_cost_data, bid_format="marginal_cost")
    
    # 比较转换结果
    print("\n🔄 转换后的统一格式 (总成本):")
    print("格式1 (原始总成本):")
    print(bid1.bid_points)
    
    print("\n格式2 (边际成本转换):")
    print(bid2.bid_points)
    
    # 获取边际成本时间表进行比较
    schedule1 = bid1.get_marginal_cost_schedule()
    schedule2 = bid2.get_marginal_cost_schedule()
    
    print("\n📊 边际成本对比:")
    print("段号  总价格->边际  边际成本->边际  差异")
    print("-" * 45)
    for i in range(len(schedule1)):
        mc1 = schedule1.iloc[i]['marginal_cost']
        mc2 = schedule2.iloc[i]['marginal_cost']
        diff = abs(mc1 - mc2)
        print(f"{i+1:2d}    {mc1:8.2f}      {mc2:8.2f}      {diff:5.2f}")


def demo_use_cases():
    """演示实际应用场景"""
    
    print("\n🎯 实际应用场景演示")
    print("=" * 50)
    
    print("📋 应用场景:")
    print("1. 📊 传统发电商 - 提供总成本报价")
    print("2. 🔋 新能源 - 提供边际成本报价")
    print("3. 🏭 工业用户 - 需求响应边际成本")
    print("4. 🔄 数据转换 - 不同系统间的格式统一")
    
    print("\n💡 优势:")
    print("✅ 格式灵活性 - 支持多种报价习惯")
    print("✅ 自动转换 - 无需手动计算")
    print("✅ 数据验证 - 自动检查数据合理性")
    print("✅ 向后兼容 - 现有代码无需修改")
    
    print("\n🔧 使用建议:")
    print("📝 新项目: 根据用户习惯选择格式")
    print("🔄 迁移项目: 使用auto格式自动检测")
    print("📊 数据分析: 使用增强功能获取详细信息")
    print("🛠️ 调试: 利用格式转换验证数据正确性")


if __name__ == "__main__":
    print("🚀 Simpower 边际成本报价功能演示")
    print("=" * 60)
    
    # 演示各项功能
    demo_bidding_format_detection()
    demo_marginal_cost_creation()
    demo_format_conversion()
    demo_csv_conversion()
    demo_comparison()
    demo_use_cases()
    
    print("\n🎉 边际成本报价功能演示完成!")
    print("\n✅ 总结:")
    print("  🔧 Simpower 现在支持两种报价格式:")
    print("    - 容量段总价格 (当前标准，向后兼容)")
    print("    - 边际成本报价 (新增功能)")
    print("  🔄 提供格式自动检测和转换功能")
    print("  📊 增强的分析和验证工具")
    print("  🎯 满足不同用户的报价习惯和需求")