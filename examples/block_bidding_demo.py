#!/usr/bin/env python3
"""
Simpower 容量段报价功能演示
展示标准电力市场容量段报价格式的支持
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pandas as pd
import numpy as np
from simpower.bidding_block import BlockBid, create_block_bid_from_prices, create_block_bid_from_segments
from simpower.get_data_block import read_block_bid_points, convert_csv_format


def demo_basic_block_bidding():
    """演示基本的容量段报价功能"""
    
    print("🏭 基本容量段报价演示")
    print("=" * 50)
    
    # 创建标准容量段报价数据
    block_data = pd.DataFrame({
        'power': [0, 100, 200, 300],      # MW
        'price': [0, 12.0, 18.0, 25.0]   # $/MWh
    })
    
    print("📊 容量段报价输入数据:")
    print(block_data)
    print()
    
    # 创建BlockBid对象
    bid = BlockBid(bid_points=block_data, block_format=True)
    
    # 显示转换后的内部格式
    cumulative_data = bid.get_cumulative_cost_data()
    print("🔄 内部累计总成本格式:")
    print(cumulative_data)
    print()
    
    # 显示容量段时间表
    block_schedule = bid.get_block_schedule()
    print("📋 容量段报价时间表:")
    print(block_schedule)
    print()
    
    # 计算指定功率水平的价格
    test_powers = [50, 150, 250]
    print("💰 指定功率水平的容量段价格:")
    for power in test_powers:
        price = bid.output_block_price(power)
        print(f"  {power}MW: {price:.1f}$/MWh")
    
    return bid


def demo_create_from_prices():
    """演示从价格列表创建容量段报价"""
    
    print("\n🔧 从价格列表创建容量段报价")
    print("=" * 50)
    
    # 定义功率端点和价格
    power_points = [0, 80, 160, 240, 320]  # MW
    prices = [10.0, 15.0, 20.0, 28.0]      # $/MWh
    
    print("📊 输入数据:")
    print(f"  功率端点: {power_points} MW")
    print(f"  容量段价格: {prices} $/MWh")
    print()
    
    # 创建投标对象
    bid = create_block_bid_from_prices(power_points, prices)
    
    # 显示结果
    block_schedule = bid.get_block_schedule()
    print("📋 生成的容量段报价:")
    for i, row in block_schedule.iterrows():
        print(f"  段{row['block']}: {row['power_from']:3.0f}-{row['power_to']:3.0f}MW @ {row['price_mwh']:5.1f}$/MWh "
              f"(容量: {row['capacity_mw']:3.0f}MW)")
    
    return bid


def demo_create_from_segments():
    """演示从容量段列表创建投标"""
    
    print("\n🏗️ 从容量段列表创建投标")
    print("=" * 50)
    
    # 定义容量段
    segments = [
        {'from': 0, 'to': 100, 'price': 8.0},
        {'from': 100, 'to': 180, 'price': 14.0},
        {'from': 180, 'to': 250, 'price': 22.0},
        {'from': 250, 'to': 300, 'price': 30.0}
    ]
    
    print("📊 容量段定义:")
    for i, seg in enumerate(segments, 1):
        print(f"  段{i}: {seg['from']:3d}-{seg['to']:3d}MW @ {seg['price']:5.1f}$/MWh")
    print()
    
    # 创建投标对象
    bid = create_block_bid_from_segments(segments)
    
    # 显示结果
    original_data = bid.original_bid_points
    print("🔄 生成的投标数据:")
    print(original_data)
    
    return bid


def demo_format_detection():
    """演示格式自动检测功能"""
    
    print("\n🔍 格式自动检测演示")
    print("=" * 50)
    
    # 创建不同格式的示例文件
    print("📁 创建测试文件:")
    
    # 1. 容量段报价格式
    block_data = pd.DataFrame({
        'power': [0, 120, 240, 360],
        'price': [0, 11.0, 16.0, 24.0]
    })
    block_file = "test_block_bidding.csv"
    block_data.to_csv(block_file, index=False)
    print(f"  ✅ {block_file} (容量段报价格式)")
    
    # 2. 累计总成本格式
    cumulative_data = pd.DataFrame({
        'power': [0, 120, 240, 360],
        'cost': [0, 1320, 3240, 6120]
    })
    cumulative_file = "test_cumulative_cost.csv"
    cumulative_data.to_csv(cumulative_file, index=False)
    print(f"  ✅ {cumulative_file} (累计总成本格式)")
    print()
    
    # 检测格式
    print("🔍 格式检测结果:")
    files = [block_file, cumulative_file]
    
    for file in files:
        bid_info = read_block_bid_points(file)
        format_type = bid_info['format']
        data = bid_info['data']
        
        print(f"\n📄 {file}:")
        print(f"  检测格式: {format_type}")
        print(f"  数据预览:")
        print(f"    {data.iloc[0].to_dict()}")
        print(f"    {data.iloc[1].to_dict()}")
        print(f"    ...")
    
    # 清理文件
    for file in files:
        if os.path.exists(file):
            os.remove(file)
    
    return files


def demo_format_conversion():
    """演示格式转换功能"""
    
    print("\n🔄 格式转换演示")
    print("=" * 50)
    
    # 创建源文件
    source_data = pd.DataFrame({
        'power': [0, 100, 200, 300, 400],
        'price': [0, 12.0, 18.0, 26.0, 35.0]
    })
    source_file = "source_block.csv"
    target_file = "target_cumulative.csv"
    
    source_data.to_csv(source_file, index=False)
    
    print("📊 源文件 (容量段报价格式):")
    print(source_data)
    print()
    
    # 执行转换
    success = convert_csv_format(
        input_file=source_file,
        output_file=target_file,
        source_format='block',
        target_format='cumulative'
    )
    
    if success:
        # 显示转换结果
        converted_data = pd.read_csv(target_file)
        print("🔄 转换结果 (累计总成本格式):")
        print(converted_data)
        
        print("\n✅ 转换验证:")
        # 验证转换正确性
        for i in range(1, len(source_data)):
            source_power = source_data.iloc[i]['power']
            source_price = source_data.iloc[i]['price']
            prev_power = source_data.iloc[i-1]['power']
            
            converted_cost = converted_data.iloc[i]['cost']
            prev_cost = converted_data.iloc[i-1]['cost']
            
            segment_capacity = source_power - prev_power
            expected_cost = prev_cost + segment_capacity * source_price
            
            print(f"  段{i}: {prev_power}-{source_power}MW @ {source_price}$/MWh")
            print(f"       预期成本: {expected_cost:.0f}$, 实际成本: {converted_cost:.0f}$, "
                  f"匹配: {'✅' if abs(expected_cost - converted_cost) < 1 else '❌'}")
    
    # 清理文件
    for file in [source_file, target_file]:
        if os.path.exists(file):
            os.remove(file)


def demo_bid_summary():
    """演示投标总结功能"""
    
    print("\n📋 投标总结功能演示")
    print("=" * 50)
    
    # 创建复杂的容量段报价
    complex_data = pd.DataFrame({
        'power': [0, 50, 120, 200, 280, 350],
        'price': [0, 9.0, 13.0, 19.0, 27.0, 38.0]
    })
    
    bid = BlockBid(bid_points=complex_data, block_format=True)
    
    # 获取投标总结
    summary = bid.get_bid_summary()
    
    print("📊 投标总结信息:")
    for key, value in summary.items():
        if key != 'power_range':
            print(f"  {key}: {value}")
        else:
            print(f"  {key}: {value[0]}-{value[1]} MW")
    
    print("\n📈 详细容量段信息:")
    block_schedule = bid.get_block_schedule()
    for i, row in block_schedule.iterrows():
        capacity_utilization = row['capacity_mw'] / summary['total_capacity'] * 100
        print(f"  段{row['block']}: {row['capacity_mw']:3.0f}MW ({capacity_utilization:4.1f}%) @ {row['price_mwh']:5.1f}$/MWh")


def demo_real_world_example():
    """演示实际应用场景"""
    
    print("\n🌍 实际应用场景演示")
    print("=" * 50)
    
    print("🏭 场景: 燃煤发电厂的容量段报价")
    print()
    
    # 模拟真实的燃煤电厂报价
    coal_plant_segments = [
        {'from': 0, 'to': 150, 'price': 25.0},      # 基荷段，较低成本
        {'from': 150, 'to': 300, 'price': 32.0},    # 中等负荷段
        {'from': 300, 'to': 400, 'price': 45.0},    # 高负荷段，效率下降
        {'from': 400, 'to': 450, 'price': 65.0}     # 峰荷段，成本很高
    ]
    
    print("⚡ 容量段报价策略:")
    for i, seg in enumerate(coal_plant_segments, 1):
        capacity = seg['to'] - seg['from']
        print(f"  段{i}: {seg['from']:3d}-{seg['to']:3d}MW ({capacity:3d}MW) @ {seg['price']:5.1f}$/MWh")
    
    # 创建投标
    coal_bid = create_block_bid_from_segments(coal_plant_segments)
    
    # 计算不同负荷水平的成本
    print("\n💰 不同负荷水平的发电成本分析:")
    load_levels = [100, 200, 350, 430]
    
    for load in load_levels:
        price = coal_bid.output_block_price(load)
        cumulative_data = coal_bid.get_cumulative_cost_data()
        
        # 计算该负荷水平的总成本
        total_cost = 0
        for i, row in cumulative_data.iterrows():
            if row['power'] >= load:
                if i == 0:
                    total_cost = 0
                else:
                    prev_power = cumulative_data.iloc[i-1]['power']
                    prev_cost = cumulative_data.iloc[i-1]['cost']
                    ratio = (load - prev_power) / (row['power'] - prev_power)
                    total_cost = prev_cost + ratio * (row['cost'] - prev_cost)
                break
        
        avg_cost = total_cost / load if load > 0 else 0
        
        print(f"  {load:3d}MW: 边际成本={price:5.1f}$/MWh, 总成本={total_cost:8.0f}$, 平均成本={avg_cost:5.1f}$/MWh")


if __name__ == "__main__":
    print("🚀 Simpower 容量段报价功能完整演示")
    print("=" * 60)
    
    # 执行所有演示
    demo_basic_block_bidding()
    demo_create_from_prices()
    demo_create_from_segments()
    demo_format_detection()
    demo_format_conversion()
    demo_bid_summary()
    demo_real_world_example()
    
    print("\n🎉 容量段报价功能演示完成!")
    print("\n✅ 功能总结:")
    print("  🔧 支持标准容量段报价格式 (power, price)")
    print("  🔄 自动格式检测和转换")
    print("  📊 丰富的分析和总结功能")
    print("  🏭 适用于实际电力市场应用")
    print("  ✅ 完全向后兼容现有系统")
    
    print("\n📋 使用方式:")
    print("  1. 直接使用容量段报价数据创建投标")
    print("  2. 从现有累计成本格式自动转换")
    print("  3. 通过工具函数快速构建投标")
    print("  4. 利用分析功能进行市场研究")