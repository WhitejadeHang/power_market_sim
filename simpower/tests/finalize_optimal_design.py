#!/usr/bin/env python3
"""
最终优化设计 - 确保9机组24时段系统能够成功求解
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem


def optimize_system():
    """优化系统参数和设计"""
    
    print("🎯 最终优化9机组24时段系统设计\n")
    
    case_dir = 'simpower/tests/ieee14_24periods_coal'
    
    # 1. 更新发电机参数 - 降低Pmin以增加灵活性
    print("📊 优化发电机参数")
    print("="*60)
    
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    
    # 降低Pmin到30%的Pmax
    gen_df['P min'] = gen_df['P max'] * 0.3
    
    # 适度的约束
    gen_df['minuptime'] = 2
    gen_df['mindowntime'] = 2
    gen_df['rampratemax'] = gen_df['P max'] * 0.8
    gen_df['rampratemin'] = -gen_df['P max'] * 0.8
    
    gen_df.to_csv(f'{case_dir}/generators.csv', index=False)
    
    print("发电机参数（优化后）:")
    print(gen_df[['name', 'bus', 'P min', 'P max', 'minuptime']])
    
    total_pmin = gen_df['P min'].sum()
    total_pmax = gen_df['P max'].sum()
    print(f"\n总容量: Pmin={total_pmin:.1f} MW, Pmax={total_pmax:.1f} MW")
    
    # 2. 设计负荷曲线
    print("\n\n📈 设计负荷曲线")
    print("="*60)
    
    # 基准负荷：系统容量的65%
    base_load = total_pmax * 0.65
    
    # 更平滑的负荷曲线
    hourly_factors = [
        0.70, 0.68, 0.66, 0.65, 0.66, 0.68,  # 0-5时：夜间低谷
        0.72, 0.78, 0.84, 0.88, 0.90, 0.89,  # 6-11时：早高峰
        0.87, 0.86, 0.87, 0.88, 0.90, 0.92,  # 12-17时：下午高峰
        0.90, 0.86, 0.80, 0.75, 0.72, 0.71   # 18-23时：晚间下降
    ]
    
    loads = [base_load * factor for factor in hourly_factors]
    
    print(f"负荷参数:")
    print(f"  基准负荷: {base_load:.1f} MW")
    print(f"  负荷范围: {min(loads):.1f} - {max(loads):.1f} MW")
    print(f"  平均负荷: {np.mean(loads):.1f} MW")
    
    # 3. 设计初始状态
    print("\n\n⚙️ 设计初始状态")
    print("="*60)
    
    # 排序：大机组优先
    gen_df_sorted = gen_df.sort_values('P max', ascending=False)
    
    # 确保初始开机容量充足
    min_load = min(loads)
    target_pmin = min_load * 0.95  # Pmin略低于最小负荷，允许经济调度
    
    initial_states = []
    online_pmin = 0
    online_pmax = 0
    
    print(f"最小负荷: {min_load:.1f} MW")
    print(f"目标Pmin: {target_pmin:.1f} MW")
    print("\n机组状态规划:")
    
    for _, gen in gen_df_sorted.iterrows():
        if online_pmin < target_pmin:
            # 开机
            status = 1
            power = gen['P min'] * 1.2  # 初始功率略高于Pmin
            hours = 4  # 已运行4小时
            online_pmin += gen['P min']
            online_pmax += gen['P max']
            state = "ON"
        else:
            # 停机
            status = 0
            power = 0
            hours = -4  # 已停机4小时
            state = "OFF"
        
        initial_states.append({
            'name': gen['name'],
            'status': status,
            'power': power if power <= gen['P max'] else gen['P max'],
            'hoursinstatus': int(hours)
        })
        
        print(f"  {gen['name']}: {state:3} - Pmin={gen['P min']:.0f}, Pmax={gen['P max']:.0f} MW")
    
    print(f"\n初始状态汇总:")
    online_count = sum(s['status'] for s in initial_states)
    print(f"  在线机组: {online_count}台")
    print(f"  在线Pmin: {online_pmin:.1f} MW")
    print(f"  在线Pmax: {online_pmax:.1f} MW")
    
    # 4. 更新所有文件
    print("\n\n📝 更新案例文件")
    print("="*60)
    
    # 更新负荷时序
    start_time = datetime(2025, 1, 15, 0, 0, 0)
    times = [start_time + timedelta(hours=h) for h in range(24)]
    
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    loads_df = pd.read_csv(f'{case_dir}/loads.csv')
    total_base_demand = buses_df['real_power_demand'].sum()
    
    for _, load in loads_df.iterrows():
        bus_name = load['bus']
        bus_data = buses_df[buses_df['name'] == bus_name]
        if not bus_data.empty:
            base_power = bus_data['real_power_demand'].values[0]
            load_share = base_power / total_base_demand
            
            load_ts_df = pd.DataFrame({
                'time': times,
                'power': [load_share * total_load for total_load in loads]
            })
            
            load_ts_df.to_csv(f'{case_dir}/{load["name"]}_timeseries.csv', index=False)
    
    print("✅ 负荷时序文件已更新")
    
    # 更新初始状态
    initial_df = pd.DataFrame(initial_states)
    initial_df.to_csv(f'{case_dir}/initial.csv', index=False)
    print("✅ 初始状态文件已更新")
    
    # 更新报价文件（适应新的Pmin）
    for _, gen in gen_df.iterrows():
        gen_name = gen['name']
        pmin = gen['P min']
        pmax = gen['P max']
        
        # 4段报价
        power_points = [
            pmin,
            pmin + (pmax - pmin) * 0.33,
            pmin + (pmax - pmin) * 0.67,
            pmax
        ]
        
        # 边际成本递增
        base_price = 150 + (ord(gen_name[-1]) - ord('1')) * 10
        marginal_costs = [
            base_price,
            base_price * 1.15,
            base_price * 1.35,
            base_price * 1.60
        ]
        
        # 计算累积成本
        costs = [0.0]
        for i in range(1, len(power_points)):
            power_increment = power_points[i] - power_points[i-1]
            cost_increment = power_increment * marginal_costs[i-1]
            costs.append(costs[-1] + cost_increment)
        
        bid_df = pd.DataFrame({
            'power': power_points,
            'cost': costs
        })
        
        bid_df.to_csv(f'{case_dir}/{gen_name}_block_bid.csv', index=False)
    
    print("✅ 报价文件已更新")
    
    # 5. 验证设计
    print("\n\n✅ 最终验证")
    print("="*60)
    
    print("\n时段负荷与容量检查:")
    issues = 0
    
    for t, load in enumerate(loads):
        # 检查第一时段
        if t == 0:
            if load < online_pmin:
                print(f"  t{t:02d}: {load:6.1f} MW ⚠️ 负荷 < 在线Pmin ({online_pmin:.1f})")
                issues += 1
            elif load > online_pmax:
                print(f"  t{t:02d}: {load:6.1f} MW ❌ 负荷 > 在线Pmax ({online_pmax:.1f})")
                issues += 1
            else:
                print(f"  t{t:02d}: {load:6.1f} MW ✅")
        else:
            if load > total_pmax:
                print(f"  t{t:02d}: {load:6.1f} MW ❌ 负荷 > 总Pmax ({total_pmax:.1f})")
                issues += 1
            else:
                print(f"  t{t:02d}: {load:6.1f} MW ✅")
    
    if issues == 0:
        print("\n🎉 设计验证通过！系统应该能够成功求解。")
        return True
    else:
        print(f"\n⚠️ 发现 {issues} 个潜在问题，可能需要进一步调整。")
        return False


def test_solution():
    """测试求解"""
    
    print("\n\n🔧 测试求解")
    print("="*60)
    
    case_dir = 'simpower/tests/ieee14_24periods_coal'
    
    try:
        print("开始求解...")
        solution = solve_problem(case_dir)
        print("✅ 求解成功！")
        
        # 打印一些结果
        if hasattr(solution, 'objective'):
            print(f"\n总成本: ${solution.objective:,.2f}")
        
        # 检查是否有机组启停
        if hasattr(solution, 'generators_status'):
            startups = 0
            shutdowns = 0
            gen_status = solution.generators_status
            
            for g in range(len(gen_status[0])):
                for t in range(1, len(gen_status)):
                    if gen_status[t][g] > gen_status[t-1][g]:
                        startups += 1
                    elif gen_status[t][g] < gen_status[t-1][g]:
                        shutdowns += 1
            
            print(f"机组启动次数: {startups}")
            print(f"机组停机次数: {shutdowns}")
        
        return True
        
    except Exception as e:
        print(f"❌ 求解失败: {e}")
        return False


def main():
    """主函数"""
    
    # 1. 优化系统设计
    success = optimize_system()
    
    if success:
        # 2. 尝试求解
        print("\n" + "="*60)
        solved = test_solution()
        
        if solved:
            print("\n\n🎊 恭喜！系统优化成功并通过求解测试！")
            print("您可以运行 run_ieee14_24periods_coal.py 查看完整结果。")
        else:
            print("\n\n⚠️ 系统设计通过验证但求解失败，请检查具体错误。")
    else:
        print("\n\n❌ 系统设计存在问题，请调整参数。")


if __name__ == "__main__":
    main()