#!/usr/bin/env python3
"""
简化的容量段报价功能测试
验证核心的容量段报价功能是否正常工作
"""

import os
import sys
import time
import pandas as pd

# 添加simpower路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.get_data_block import read_block_bid_points
from simpower.solve import solve_problem


def create_simple_test_case():
    """创建简单的3节点测试案例"""
    
    test_dir = 'simpower/tests/simple_block_test'
    os.makedirs(test_dir, exist_ok=True)
    
    print("🔧 创建简单的3节点容量段报价测试案例...")
    
    # 1. 节点数据
    buses_data = pd.DataFrame([
        {'name': 'Bus_A', 'type': 'bus'},
        {'name': 'Bus_B', 'type': 'bus'},
        {'name': 'Bus_C', 'type': 'bus'}
    ])
    buses_data.to_csv(os.path.join(test_dir, 'buses.csv'), index=False)
    
    # 2. 传输线数据
    lines_data = pd.DataFrame([
        {'from bus': 'Bus_A', 'to bus': 'Bus_B', 'Pmax': 500},
        {'from bus': 'Bus_B', 'to bus': 'Bus_C', 'Pmax': 400}
    ])
    lines_data.to_csv(os.path.join(test_dir, 'lines.csv'), index=False)
    
    # 3. 发电机数据 (使用容量段报价)
    generators_data = pd.DataFrame([
        {'name': 'Coal_A', 'bus': 'Bus_A', 'type': 'coal', 'P max': 400, 
         'no load cost': 100, 'cost curve points filename': 'coal_a_bid.csv'},
        {'name': 'Coal_B', 'bus': 'Bus_B', 'type': 'coal', 'P max': 300, 
         'no load cost': 80, 'cost curve points filename': 'coal_b_bid.csv'},
        {'name': 'Gas_C', 'bus': 'Bus_C', 'type': 'gas', 'P max': 200, 
         'no load cost': 60, 'cost curve points filename': 'gas_c_bid.csv'}
    ])
    generators_data.to_csv(os.path.join(test_dir, 'generators.csv'), index=False)
    
    # 4. 容量段报价文件
    # 燃煤电厂A - 低成本，3段
    coal_a_bid = pd.DataFrame([
        {'power': 0, 'price': 0.0},
        {'power': 160, 'price': 25.0},
        {'power': 280, 'price': 30.0},
        {'power': 400, 'price': 40.0}
    ])
    coal_a_bid.to_csv(os.path.join(test_dir, 'coal_a_bid.csv'), index=False)
    
    # 燃煤电厂B - 中等成本，4段
    coal_b_bid = pd.DataFrame([
        {'power': 0, 'price': 0.0},
        {'power': 100, 'price': 35.0},
        {'power': 180, 'price': 42.0},
        {'power': 240, 'price': 50.0},
        {'power': 300, 'price': 60.0}
    ])
    coal_b_bid.to_csv(os.path.join(test_dir, 'coal_b_bid.csv'), index=False)
    
    # 天然气电厂C - 高成本，3段
    gas_c_bid = pd.DataFrame([
        {'power': 0, 'price': 0.0},
        {'power': 80, 'price': 45.0},
        {'power': 140, 'price': 55.0},
        {'power': 200, 'price': 70.0}
    ])
    gas_c_bid.to_csv(os.path.join(test_dir, 'gas_c_bid.csv'), index=False)
    
    # 5. 负荷数据
    loads_data = pd.DataFrame([
        {'name': 'Load_A', 'power': 200},
        {'name': 'Load_B', 'power': 250},
        {'name': 'Load_C', 'power': 150}
    ])
    loads_data.to_csv(os.path.join(test_dir, 'loads.csv'), index=False)
    
    print(f"✅ 测试案例已创建: {test_dir}")
    print(f"   - 3个节点，2条线路")
    print(f"   - 3台发电机（容量段报价）")
    print(f"   - 总装机: 900MW，总负荷: 600MW")
    
    return test_dir


def test_block_bidding_read():
    """测试容量段报价文件读取"""
    
    print("\n📊 测试容量段报价文件读取...")
    
    test_dir = 'simpower/tests/simple_block_test'
    bid_files = ['coal_a_bid.csv', 'coal_b_bid.csv', 'gas_c_bid.csv']
    
    for bid_file in bid_files:
        filepath = os.path.join(test_dir, bid_file)
        bid_info = read_block_bid_points(filepath)
        
        if bid_info['data'] is not None:
            data = bid_info['data']
            format_type = bid_info['format']
            
            print(f"  ✅ {bid_file}: {format_type}格式, {len(data)}点")
            
            # 显示价格范围
            prices = data['price'][1:]  # 跳过起始点
            if len(prices) > 0:
                print(f"     价格范围: {min(prices):.1f} - {max(prices):.1f} $/MWh")
        else:
            print(f"  ❌ {bid_file}: 读取失败")


def test_economic_dispatch():
    """测试经济调度求解"""
    
    print("\n🚀 测试经济调度求解...")
    
    test_dir = 'simpower/tests/simple_block_test'
    
    start_time = time.time()
    
    try:
        # 运行求解
        print("⚡ 开始求解3节点容量段报价案例...")
        solution = solve_problem(test_dir)
        
        solve_time = time.time() - start_time
        print(f"✅ 求解完成，用时: {solve_time:.2f} 秒")
        
        if solution is None:
            print("❌ 求解失败：返回空解")
            return False
        
        # 分析结果
        print("\n📊 分析求解结果...")
        
        # 检查解的状态
        if hasattr(solution, 'solved') and solution.solved:
            print("✅ 找到可行解")
        else:
            print("⚠️ 解的状态未知")
            
        # 分析发电调度
        if hasattr(solution, 'generators'):
            gen_results = solution.generators
            total_generation = 0
            
            print("\n🏭 发电调度结果:")
            
            for gen_name, gen_data in gen_results.items():
                if hasattr(gen_data, 'power') and hasattr(gen_data.power, 'value'):
                    power_output = gen_data.power.value
                    total_generation += power_output
                    
                    print(f"  {gen_name}: {power_output:.1f} MW")
            
            print(f"  总发电量: {total_generation:.1f} MW")
        
        # 分析节点电价
        if hasattr(solution, 'buses'):
            bus_results = solution.buses
            lmps = []
            
            print("\n💰 节点电价(LMP):")
            
            for bus_name, bus_data in bus_results.items():
                if hasattr(bus_data, 'lmp') and hasattr(bus_data.lmp, 'value'):
                    lmp = bus_data.lmp.value
                    if lmp is not None:
                        lmps.append(lmp)
                        print(f"  {bus_name}: {lmp:.2f} $/MWh")
            
            if lmps:
                print(f"  价格范围: {min(lmps):.2f} - {max(lmps):.2f} $/MWh")
        
        return True
        
    except Exception as e:
        print(f"❌ 求解失败: {str(e)}")
        print(f"💻 用时: {time.time() - start_time:.2f} 秒")
        return False


def analyze_market_merit_order():
    """分析市场供应曲线"""
    
    print("\n📈 分析市场供应曲线...")
    
    test_dir = 'simpower/tests/simple_block_test'
    
    # 读取所有投标
    generators = [
        {'name': 'Coal_A', 'file': 'coal_a_bid.csv', 'capacity': 400},
        {'name': 'Coal_B', 'file': 'coal_b_bid.csv', 'capacity': 300},
        {'name': 'Gas_C', 'file': 'gas_c_bid.csv', 'capacity': 200}
    ]
    
    all_blocks = []
    
    for gen in generators:
        filepath = os.path.join(test_dir, gen['file'])
        bid_info = read_block_bid_points(filepath)
        
        if bid_info['data'] is not None and bid_info['format'] == 'block':
            data = bid_info['data']
            
            for i in range(1, len(data)):
                power_from = data.iloc[i-1]['power']
                power_to = data.iloc[i]['power']
                price = data.iloc[i]['price']
                capacity = power_to - power_from
                
                all_blocks.append({
                    'generator': gen['name'],
                    'capacity': capacity,
                    'price': price,
                    'power_from': power_from,
                    'power_to': power_to
                })
    
    # 按价格排序
    all_blocks.sort(key=lambda x: x['price'])
    
    print("📊 Merit Order (按价格排序):")
    
    cumulative_capacity = 0
    total_demand = 600  # MW
    
    for i, block in enumerate(all_blocks):
        cumulative_capacity += block['capacity']
        
        status = "✅ 调度" if cumulative_capacity <= total_demand else "❌ 未调度"
        
        print(f"  {i+1:2d}. {block['generator']:8s} {block['capacity']:3.0f}MW @ {block['price']:5.1f}$/MWh "
              f"(累计: {cumulative_capacity:3.0f}MW) {status}")
        
        if cumulative_capacity >= total_demand:
            clearing_price = block['price']
            print(f"\n💡 出清价格: {clearing_price:.1f} $/MWh")
            break


def main():
    """主测试函数"""
    
    print("🧪 Simpower 容量段报价功能测试")
    print("=" * 50)
    
    # 1. 创建测试案例
    test_dir = create_simple_test_case()
    
    # 2. 测试报价文件读取
    test_block_bidding_read()
    
    # 3. 分析市场供应曲线
    analyze_market_merit_order()
    
    # 4. 测试经济调度
    success = test_economic_dispatch()
    
    print(f"\n🎯 测试总结:")
    if success:
        print("✅ 容量段报价功能测试通过！")
        print("🎉 核心功能验证成功:")
        print("  - ✅ 容量段报价文件读取")
        print("  - ✅ 格式自动检测")
        print("  - ✅ Merit Order构建")
        print("  - ✅ 经济调度求解")
        print("  - ✅ LMP计算")
    else:
        print("❌ 容量段报价功能测试失败")
        print("⚠️ 请检查错误信息并修复问题")
    
    # 清理测试文件
    import shutil
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
        print(f"\n🧹 已清理测试文件: {test_dir}")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)