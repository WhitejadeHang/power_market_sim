#!/usr/bin/env python3
"""
精心设计9机组24时段系统，确保能够成功求解
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))


def analyze_system_capacity():
    """分析系统容量"""
    case_dir = 'simpower/tests/ieee14_24periods_coal'
    
    # 读取发电机数据
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    
    print("🔍 系统容量分析")
    print("="*60)
    print("\n发电机参数:")
    print(gen_df[['name', 'bus', 'P min', 'P max', 'minuptime', 'mindowntime']])
    
    total_pmin = gen_df['P min'].sum()
    total_pmax = gen_df['P max'].sum()
    
    print(f"\n总容量:")
    print(f"  总Pmin: {total_pmin:.1f} MW")
    print(f"  总Pmax: {total_pmax:.1f} MW")
    
    # 按容量大小分组
    large_gens = gen_df[gen_df['P max'] >= 80]
    medium_gens = gen_df[(gen_df['P max'] >= 50) & (gen_df['P max'] < 80)]
    small_gens = gen_df[gen_df['P max'] < 50]
    
    print(f"\n机组分组:")
    print(f"  大型机组 (≥80MW): {list(large_gens['name'])} - 总容量 {large_gens['P max'].sum()} MW")
    print(f"  中型机组 (50-80MW): {list(medium_gens['name'])} - 总容量 {medium_gens['P max'].sum()} MW")
    print(f"  小型机组 (<50MW): {list(small_gens['name'])} - 总容量 {small_gens['P max'].sum()} MW")
    
    return gen_df, total_pmin, total_pmax


def design_load_curve(total_pmin, total_pmax):
    """设计优化的负荷曲线"""
    
    print("\n\n📊 负荷曲线设计")
    print("="*60)
    
    # 设计原则：
    # 1. 最小负荷要高于初始在线机组的Pmin总和
    # 2. 最大负荷要低于总Pmax
    # 3. 变化要平滑，避免剧烈波动
    # 4. 创造适度的启停机会
    
    # 基准负荷设置为系统容量的60%
    base_load = total_pmax * 0.6
    
    # 24小时负荷模式 - 典型工作日
    hourly_factors = [
        0.75, 0.72, 0.70, 0.68, 0.70, 0.73,  # 0-5时：夜间低谷
        0.78, 0.85, 0.90, 0.92, 0.93, 0.91,  # 6-11时：早高峰
        0.89, 0.88, 0.89, 0.91, 0.93, 0.95,  # 12-17时：下午高峰
        0.92, 0.88, 0.82, 0.78, 0.76, 0.75   # 18-23时：晚间下降
    ]
    
    loads = [base_load * factor for factor in hourly_factors]
    
    print(f"负荷设计参数:")
    print(f"  基准负荷: {base_load:.1f} MW")
    print(f"  最小负荷: {min(loads):.1f} MW (发生在 {hourly_factors.index(min(hourly_factors))}时)")
    print(f"  最大负荷: {max(loads):.1f} MW (发生在 {hourly_factors.index(max(hourly_factors))}时)")
    print(f"  负荷范围: {min(loads):.1f} - {max(loads):.1f} MW")
    print(f"  平均负荷: {np.mean(loads):.1f} MW")
    
    # 检查负荷变化率
    max_ramp = 0
    for i in range(1, len(loads)):
        ramp = abs(loads[i] - loads[i-1])
        max_ramp = max(max_ramp, ramp)
    
    print(f"  最大小时变化: {max_ramp:.1f} MW")
    
    return loads, hourly_factors


def design_initial_state(gen_df, min_load, avg_load):
    """设计优化的初始状态"""
    
    print("\n\n⚙️ 初始状态设计")
    print("="*60)
    
    # 设计原则：
    # 1. 初始在线容量要能满足最小负荷
    # 2. 留有一定裕度应对负荷增长
    # 3. 保留一些机组停机以创造启动机会
    
    # 按效率排序（假设容量越大效率越高）
    gen_df_sorted = gen_df.sort_values('P max', ascending=False).copy()
    
    initial_states = []
    online_pmin = 0
    online_pmax = 0
    
    # 重要：确保初始在线Pmin > 最小负荷
    target_pmin = min_load * 1.05  # 留5%裕度
    
    print(f"目标初始Pmin: {target_pmin:.1f} MW (最小负荷的105%)")
    print(f"最小负荷: {min_load:.1f} MW")
    print("\n初始状态规划:")
    
    # 先选择必须开机的大机组
    for _, gen in gen_df_sorted.iterrows():
        if online_pmin < target_pmin:
            # 开机
            status = 1
            power = gen['P min']
            hours = gen['minuptime'] + 2  # 已运行时间超过最小运行时间
            online_pmin += gen['P min']
            online_pmax += gen['P max']
            print(f"  {gen['name']}: ON  - Pmin={gen['P min']:.0f}, Pmax={gen['P max']:.0f} MW (累计Pmin={online_pmin:.0f})")
        else:
            # 停机
            status = 0
            power = 0
            hours = -(gen['mindowntime'] + 2)  # 已停机时间超过最小停机时间
            print(f"  {gen['name']}: OFF")
        
        initial_states.append({
            'name': gen['name'],
            'status': status,
            'power': power,
            'hoursinstatus': int(hours)
        })
    
    print(f"\n初始状态汇总:")
    print(f"  在线机组数: {sum(s['status'] for s in initial_states)}")
    print(f"  初始在线Pmin: {online_pmin:.1f} MW")
    print(f"  初始在线Pmax: {online_pmax:.1f} MW")
    print(f"  对最小负荷的裕度: {online_pmin - min_load:.1f} MW")
    
    # 验证初始状态是否合理
    if online_pmin < min_load:
        print(f"\n⚠️ 警告：初始在线Pmin ({online_pmin:.1f}) < 最小负荷 ({min_load:.1f})")
        print("建议：增加初始开机机组或降低最小负荷")
    
    return initial_states


def update_case_files(case_dir, loads, initial_states):
    """更新案例文件"""
    
    print("\n\n📝 更新案例文件")
    print("="*60)
    
    # 1. 更新发电机参数 - 适度的约束
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    gen_df['minuptime'] = 2  # 2小时最小运行时间
    gen_df['mindowntime'] = 2  # 2小时最小停机时间
    gen_df['rampratemax'] = gen_df['P max'] * 0.8  # 80%爬坡率
    gen_df['rampratemin'] = -gen_df['P max'] * 0.8
    gen_df.to_csv(f'{case_dir}/generators.csv', index=False)
    print("✅ 更新发电机参数")
    
    # 2. 更新负荷时序
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
            
            filename = f'{case_dir}/{load["name"]}_timeseries.csv'
            load_ts_df.to_csv(filename, index=False)
    
    print("✅ 更新负荷时序文件")
    
    # 3. 更新初始状态
    initial_df = pd.DataFrame(initial_states)
    initial_df.to_csv(f'{case_dir}/initial.csv', index=False)
    print("✅ 更新初始状态文件")
    
    # 4. 绘制负荷曲线预览
    plt.figure(figsize=(12, 6))
    plt.plot(range(24), loads, 'b-', linewidth=2, marker='o')
    plt.xlabel('时间 (小时)')
    plt.ylabel('负荷 (MW)')
    plt.title('优化后的24小时负荷曲线')
    plt.grid(True, alpha=0.3)
    plt.xticks(range(0, 24, 2))
    
    # 标注关键点
    min_idx = loads.index(min(loads))
    max_idx = loads.index(max(loads))
    plt.annotate(f'最小: {min(loads):.0f} MW', 
                xy=(min_idx, min(loads)), 
                xytext=(min_idx, min(loads)-20),
                arrowprops=dict(arrowstyle='->', color='red'))
    plt.annotate(f'最大: {max(loads):.0f} MW', 
                xy=(max_idx, max(loads)), 
                xytext=(max_idx, max(loads)+20),
                arrowprops=dict(arrowstyle='->', color='green'))
    
    plt.tight_layout()
    plt.savefig(f'{case_dir}/optimized_load_curve.png', dpi=150)
    plt.close()
    print("✅ 保存负荷曲线图")


def verify_feasibility(gen_df, loads, initial_states):
    """验证可行性"""
    
    print("\n\n✅ 可行性验证")
    print("="*60)
    
    # 获取初始在线机组
    online_gens = [s['name'] for s in initial_states if s['status'] == 1]
    online_gen_data = gen_df[gen_df['name'].isin(online_gens)]
    
    online_pmin = online_gen_data['P min'].sum()
    online_pmax = online_gen_data['P max'].sum()
    total_pmax = gen_df['P max'].sum()
    
    print("时段可行性检查:")
    all_feasible = True
    
    for t, load in enumerate(loads):
        feasible = True
        issues = []
        
        # 第一时段只能用初始在线机组
        if t == 0:
            if load < online_pmin:
                feasible = False
                issues.append(f"负荷 {load:.0f} < 初始Pmin {online_pmin:.0f}")
            elif load > online_pmax:
                feasible = False
                issues.append(f"负荷 {load:.0f} > 初始Pmax {online_pmax:.0f}")
        else:
            # 后续时段可以启动新机组（简化假设）
            if load > total_pmax:
                feasible = False
                issues.append(f"负荷 {load:.0f} > 总Pmax {total_pmax:.0f}")
        
        status = "✅" if feasible else "❌"
        print(f"  t{t:02d} ({t}:00): {load:6.1f} MW {status} {' '.join(issues)}")
        
        if not feasible:
            all_feasible = False
    
    print(f"\n总体可行性: {'✅ 通过' if all_feasible else '❌ 存在问题'}")
    
    return all_feasible


def main():
    """主函数"""
    
    print("🎯 优化9机组24时段系统设计\n")
    
    case_dir = 'simpower/tests/ieee14_24periods_coal'
    
    # 1. 分析系统容量
    gen_df, total_pmin, total_pmax = analyze_system_capacity()
    
    # 2. 设计负荷曲线
    loads, hourly_factors = design_load_curve(total_pmin, total_pmax)
    
    # 3. 设计初始状态
    min_load = min(loads)
    avg_load = np.mean(loads)
    initial_states = design_initial_state(gen_df, min_load, avg_load)
    
    # 4. 验证可行性
    feasible = verify_feasibility(gen_df, loads, initial_states)
    
    if feasible:
        # 5. 更新案例文件
        update_case_files(case_dir, loads, initial_states)
        
        print("\n\n🎉 优化设计完成！")
        print("下一步：运行 run_ieee14_24periods_coal.py 进行仿真")
    else:
        print("\n\n⚠️ 设计存在可行性问题，请调整参数")


if __name__ == "__main__":
    main()