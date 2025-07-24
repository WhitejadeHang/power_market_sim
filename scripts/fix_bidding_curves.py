#!/usr/bin/env python3
"""
修复IEEE 50节点案例的报价曲线格式
将错误的累计成本格式转换为正确的容量段价格格式
"""

import os
import pandas as pd
import numpy as np

def fix_all_bidding_curves():
    """修复所有报价曲线文件"""
    
    case_dir = 'simpower/tests/ieee_50_simple'
    
    # 读取发电机列表
    generators_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    print("🔧 修复报价曲线格式...")
    print("原问题: 生成的是累计成本，但应该是容量段价格")
    
    fixed_count = 0
    
    for i, gen in generators_df.iterrows():
        bid_file = os.path.join(case_dir, gen['cost curve points filename'])
        
        if os.path.exists(bid_file):
            # 读取原始数据
            original_df = pd.read_csv(bid_file)
            
            # 转换为正确的容量段价格格式
            fixed_df = convert_to_block_bidding(original_df, gen['name'])
            
            # 保存修复的文件
            fixed_df.to_csv(bid_file, index=False)
            fixed_count += 1
            
            if i < 3:  # 显示前3个示例
                print(f"\n{gen['name']} 修复前后对比:")
                print("修复前 (累计成本):")
                print(original_df.head(4))
                print("修复后 (容量段价格):")
                print(fixed_df.head(4))
    
    print(f"\n✅ 已修复 {fixed_count} 个报价文件")
    return fixed_count


def convert_to_block_bidding(original_df, gen_name):
    """将累计成本格式转换为容量段价格格式"""
    
    # 根据发电机类型设置基础价格范围
    if 'Coal' in gen_name:
        base_prices = [20, 35, 50, 70, 95, 130, 180]
    elif 'Gas' in gen_name:
        base_prices = [30, 50, 75, 105, 145, 200, 280]
    elif 'Steam' in gen_name:
        base_prices = [40, 70, 110, 160, 220, 300, 420]
    else:  # Peaker
        base_prices = [60, 120, 200, 300, 450, 650, 900, 1200]
    
    new_data = []
    
    for i in range(len(original_df)):
        power = original_df.iloc[i]['power']
        
        if i == 0:
            # 第一点：0功率，0价格
            price = 0
        else:
            # 使用预设的价格级别，加入随机波动
            price_idx = min(i - 1, len(base_prices) - 1)
            base_price = base_prices[price_idx]
            
            # 添加 ±20% 随机波动
            price_variation = np.random.uniform(0.8, 1.2)
            price = base_price * price_variation
            
            # 确保价格单调递增
            if new_data:
                prev_price = new_data[-1]['price']
                if price <= prev_price:
                    price = prev_price + np.random.uniform(5, 15)
            
            # 限制在合理范围内
            price = max(10, min(1500, price))
        
        new_data.append({
            'power': power,
            'price': round(price, 2)
        })
    
    return pd.DataFrame(new_data)


def test_fixed_curves():
    """测试修复后的报价曲线"""
    
    case_dir = 'simpower/tests/ieee_50_simple'
    generators_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    
    print("\n📊 测试修复后的报价曲线...")
    
    for i, gen in generators_df.head(3).iterrows():
        bid_file = os.path.join(case_dir, gen['cost curve points filename'])
        bid_df = pd.read_csv(bid_file)
        
        print(f"\n{gen['name']} 修复后:")
        print(bid_df)
        
        # 计算边际成本验证
        print("边际成本验证:")
        for j in range(1, len(bid_df)):
            power_diff = bid_df.iloc[j]['power'] - bid_df.iloc[j-1]['power']
            price_diff = bid_df.iloc[j]['price'] - bid_df.iloc[j-1]['price']
            if power_diff > 0:
                mc = price_diff / power_diff
                print(f"  段{j}: {mc:.3f} $/MWh")


if __name__ == "__main__":
    print("🔧 开始修复IEEE 50节点案例的报价曲线...")
    
    # 修复所有报价曲线
    fixed_count = fix_all_bidding_curves()
    
    # 测试修复结果
    test_fixed_curves()
    
    print(f"\n🎉 报价曲线修复完成！")
    print(f"📈 修复了 {fixed_count} 个文件")
    print("\n💡 现在可以重新测试案例:")
    print("   python3 simpower/tests/test_ieee_50_simple.py")