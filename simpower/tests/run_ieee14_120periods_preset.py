#!/usr/bin/env python3
"""
运行基于预设机组组合的IEEE 14节点120时段仿真
"""

import os
import sys
import time
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.solve import solve_problem
from simpower.ieee14_120periods_analysis import IEEE14_120PeriodsAnalysis
from simpower.ieee14_analysis import get_chinese_font


def compare_with_preset(case_dir, solution):
    """对比优化结果与预设方案"""
    
    print("\n\n📊 对比优化结果与预设方案")
    print("="*60)
    
    # 加载预设方案
    with open(f'{case_dir}/preset_solution.json', 'r') as f:
        preset = json.load(f)
    
    preset_status = np.array(preset['unit_status'])
    preset_power = np.array(preset['unit_power'])
    gen_names = preset['generator_names']
    
    # 获取优化结果
    n_periods = len(solution.generators_status)
    n_units = len(solution.generators_status[0])
    
    opt_status = np.zeros((n_units, n_periods))
    opt_power = np.zeros((n_units, n_periods))
    
    for t in range(n_periods):
        for g in range(n_units):
            opt_status[g, t] = solution.generators_status[t][g]
            opt_power[g, t] = solution.generators_power[t][g] if solution.generators_status[t][g] > 0 else 0
    
    # 1. 启停次数对比
    print("\n机组启停次数对比:")
    print(f"{'机组':<6} {'预设启动':<10} {'优化启动':<10} {'预设停机':<10} {'优化停机':<10}")
    print("-" * 50)
    
    total_preset_starts = 0
    total_opt_starts = 0
    total_preset_stops = 0
    total_opt_stops = 0
    
    for g in range(n_units):
        preset_starts = 0
        opt_starts = 0
        preset_stops = 0
        opt_stops = 0
        
        for t in range(1, n_periods):
            # 预设方案
            if preset_status[g, t] == 1 and preset_status[g, t-1] == 0:
                preset_starts += 1
            elif preset_status[g, t] == 0 and preset_status[g, t-1] == 1:
                preset_stops += 1
            
            # 优化结果
            if opt_status[g, t] == 1 and opt_status[g, t-1] == 0:
                opt_starts += 1
            elif opt_status[g, t] == 0 and opt_status[g, t-1] == 1:
                opt_stops += 1
        
        print(f"{gen_names[g]:<6} {preset_starts:<10} {opt_starts:<10} {preset_stops:<10} {opt_stops:<10}")
        
        total_preset_starts += preset_starts
        total_opt_starts += opt_starts
        total_preset_stops += preset_stops
        total_opt_stops += opt_stops
    
    print("-" * 50)
    print(f"{'总计':<6} {total_preset_starts:<10} {total_opt_starts:<10} {total_preset_stops:<10} {total_opt_stops:<10}")
    
    # 2. 运行时间对比
    print("\n\n机组运行时间对比:")
    print(f"{'机组':<6} {'预设(小时)':<12} {'优化(小时)':<12} {'差异':<10}")
    print("-" * 40)
    
    for g in range(n_units):
        preset_hours = np.sum(preset_status[g, :])
        opt_hours = np.sum(opt_status[g, :])
        diff = opt_hours - preset_hours
        print(f"{gen_names[g]:<6} {preset_hours:<12} {opt_hours:<12} {diff:+10}")
    
    # 3. 总发电量对比
    print("\n\n机组总发电量对比:")
    print(f"{'机组':<6} {'预设(MWh)':<12} {'优化(MWh)':<12} {'差异(%)':<10}")
    print("-" * 40)
    
    for g in range(n_units):
        preset_gen = np.sum(preset_power[g, :])
        opt_gen = np.sum(opt_power[g, :])
        if preset_gen > 0:
            diff_pct = (opt_gen - preset_gen) / preset_gen * 100
        else:
            diff_pct = 100 if opt_gen > 0 else 0
        print(f"{gen_names[g]:<6} {preset_gen:>10.0f}  {opt_gen:>10.0f}  {diff_pct:>8.1f}%")
    
    # 4. 成本对比
    if hasattr(solution, 'objective'):
        print(f"\n\n成本对比:")
        print(f"  优化总成本: ${solution.objective:,.2f}")
        print(f"  预设估算成本: $10,159,473 (简化计算)")
        print(f"  节省: ${10159473 - solution.objective:,.2f} ({(10159473 - solution.objective)/10159473*100:.1f}%)")
    
    # 5. 绘制对比图
    plot_comparison(preset_status, opt_status, preset_power, opt_power, gen_names, case_dir)


def plot_comparison(preset_status, opt_status, preset_power, opt_power, gen_names, case_dir):
    """绘制对比图"""
    
    print("\n📊 生成对比图...")
    
    fig, axes = plt.subplots(3, 2, figsize=(20, 15))
    
    n_units, n_periods = preset_status.shape
    hours = list(range(n_periods))
    
    # 1. 机组状态对比
    ax1, ax2 = axes[0]
    
    im1 = ax1.imshow(preset_status, aspect='auto', cmap='RdYlGn', interpolation='nearest')
    ax1.set_title('Preset Unit Commitment', fontsize=14)
    ax1.set_ylabel('Units', fontsize=12)
    ax1.set_yticks(range(n_units))
    ax1.set_yticklabels(gen_names)
    
    im2 = ax2.imshow(opt_status, aspect='auto', cmap='RdYlGn', interpolation='nearest')
    ax2.set_title('Optimized Unit Commitment', fontsize=14)
    ax2.set_ylabel('Units', fontsize=12)
    ax2.set_yticks(range(n_units))
    ax2.set_yticklabels(gen_names)
    
    # 2. 在线机组数对比
    ax3, ax4 = axes[1]
    
    preset_online = np.sum(preset_status, axis=0)
    opt_online = np.sum(opt_status, axis=0)
    
    ax3.plot(hours, preset_online, 'b-', linewidth=2, label='Preset')
    ax3.plot(hours, opt_online, 'r--', linewidth=2, label='Optimized')
    ax3.set_xlabel('Hour', fontsize=12)
    ax3.set_ylabel('Units Online', fontsize=12)
    ax3.set_title('Number of Units Online', fontsize=14)
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    # 3. 总发电量对比
    preset_total_gen = np.sum(preset_power, axis=0)
    opt_total_gen = np.sum(opt_power, axis=0)
    
    ax4.plot(hours, preset_total_gen, 'b-', linewidth=2, label='Preset')
    ax4.plot(hours, opt_total_gen, 'r--', linewidth=2, label='Optimized')
    ax4.set_xlabel('Hour', fontsize=12)
    ax4.set_ylabel('Total Generation (MW)', fontsize=12)
    ax4.set_title('Total Generation', fontsize=14)
    ax4.legend()
    ax4.grid(True, alpha=0.3)
    
    # 4. 机组利用率对比
    ax5, ax6 = axes[2]
    
    preset_cf = [np.sum(preset_power[g, :]) / (n_periods * 1000) * 100 if g == 0 else
                 np.sum(preset_power[g, :]) / (n_periods * 600) * 100 if g < 4 else
                 np.sum(preset_power[g, :]) / (n_periods * 300) * 100 for g in range(n_units)]
    
    opt_cf = [np.sum(opt_power[g, :]) / (n_periods * 1000) * 100 if g == 0 else
              np.sum(opt_power[g, :]) / (n_periods * 600) * 100 if g < 4 else
              np.sum(opt_power[g, :]) / (n_periods * 300) * 100 for g in range(n_units)]
    
    x = np.arange(n_units)
    width = 0.35
    
    ax5.bar(x - width/2, preset_cf, width, label='Preset', alpha=0.8)
    ax5.bar(x + width/2, opt_cf, width, label='Optimized', alpha=0.8)
    ax5.set_xlabel('Units', fontsize=12)
    ax5.set_ylabel('Capacity Factor (%)', fontsize=12)
    ax5.set_title('Unit Capacity Factors', fontsize=14)
    ax5.set_xticks(x)
    ax5.set_xticklabels(gen_names)
    ax5.legend()
    ax5.grid(True, alpha=0.3, axis='y')
    
    # 删除最后一个子图
    fig.delaxes(ax6)
    
    plt.tight_layout()
    plt.savefig(f'{case_dir}/results/preset_vs_optimized.png', dpi=150, bbox_inches='tight')
    plt.close()
    
    print("✅ 对比图已保存")


def run_simulation():
    """运行仿真"""
    
    print("🚀 基于预设机组组合的IEEE 14节点120时段仿真")
    print("="*60)
    print("📅 仿真周期: 5天，120时段")
    print("⚡ 发电机组: 9台（1x1000MW + 3x600MW + 5x300MW）")
    print("🎯 目标: 验证预设方案的可行性并优化")
    print("="*60)
    
    case_dir = 'simpower/tests/ieee14_120periods_preset'
    
    print("\n⚙️ 开始120时段机组组合优化求解...")
    
    start_time = time.time()
    
    try:
        # 求解问题
        solution = solve_problem(case_dir)
        
        solve_time = time.time() - start_time
        print(f"\n✅ 求解完成！用时: {solve_time:.2f} 秒")
        
        # 分析结果
        print("\n📊 生成120时段完整分析报告...")
        
        # 确保结果目录存在
        results_dir = os.path.join(case_dir, 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # 使用120时段分析模块
        analysis = IEEE14_120PeriodsAnalysis(case_dir, solution)
        analysis.generate_full_report()
        
        # 对比预设方案
        compare_with_preset(case_dir, solution)
        
        print("\n🎉 仿真完成！")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 仿真失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    # 加载中文字体
    chinese_font = get_chinese_font()
    if chinese_font:
        font_name = chinese_font.get_name()
        print(f"✅ 成功加载中文字体: {font_name}")
    
    run_simulation()