#!/usr/bin/env python3
"""
96时段分析功能演示 - 使用模拟数据快速展示
"""

import os
import sys
import pandas as pd
import numpy as np
import json
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.results_analysis import get_chinese_font, apply_chinese_font_to_figure


def create_demo_96periods_data():
    """创建96时段的模拟数据"""
    
    print("📊 创建96时段模拟数据...")
    
    # 时间序列
    base_time = datetime(2025, 7, 26, 0, 0)
    times = []
    for i in range(96):
        times.append(base_time + timedelta(minutes=15*i))
    
    # 26台发电机
    gen_names = [f'g{i}' for i in range(26)]
    
    # 模拟机组状态和出力
    status_data = {}
    power_data = {}
    
    for gen in gen_names:
        status_data[gen] = []
        power_data[gen] = []
        
        # 根据机组编号确定类型
        gen_idx = int(gen[1:])
        
        for t_idx, time in enumerate(times):
            hour = time.hour + time.minute/60
            
            # 基荷机组 (0-5)
            if gen_idx < 6:
                status = 1  # 一直运行
                base_power = 600 + gen_idx * 50
                power = base_power * (0.9 + 0.1 * np.sin(hour * np.pi / 12))
            
            # 中间机组 (6-17)
            elif gen_idx < 18:
                # 负荷高于70%时运行
                load_factor = 0.6 + 0.4 * np.sin((hour - 6) * np.pi / 12)
                status = 1 if load_factor > 0.7 else 0
                base_power = 300 + gen_idx * 20
                power = base_power * load_factor * status
            
            # 调峰机组 (18-25)
            else:
                # 只在高峰时段运行
                if 7 <= hour <= 9 or 17 <= hour <= 21:
                    status = 1
                    base_power = 100 + gen_idx * 10
                    power = base_power * (0.8 + 0.2 * np.random.random())
                else:
                    status = 0
                    power = 0
            
            status_data[gen].append(status)
            power_data[gen].append(power)
    
    # 创建DataFrame
    status_df = pd.DataFrame(status_data, index=times)
    power_df = pd.DataFrame(power_data, index=times)
    
    # 模拟LMP数据
    lmp_data = {}
    for bus_idx in range(50):
        bus_name = f'Bus{bus_idx+1:02d}'
        lmp_data[bus_name] = []
        
        for t_idx, time in enumerate(times):
            hour = time.hour + time.minute/60
            # 基础电价
            base_lmp = 30 + 20 * np.sin((hour - 6) * np.pi / 12)
            # 节点差异
            node_factor = 1 + 0.2 * np.sin(bus_idx * np.pi / 25)
            # 随机扰动
            lmp = base_lmp * node_factor + np.random.normal(0, 5)
            lmp_data[bus_name].append(max(10, lmp))
    
    lmp_df = pd.DataFrame(lmp_data, index=times)
    
    return {
        'Status': status_df,
        'Power': power_df,
        'LMP': lmp_df
    }


def demo_96periods_analysis():
    """演示96时段分析功能"""
    
    print("🚀 96时段分析功能演示")
    print("=" * 60)
    
    # 创建模拟数据
    solution = create_demo_96periods_data()
    
    # 创建结果目录
    results_dir = 'simpower/tests/demo_96periods_results'
    os.makedirs(results_dir, exist_ok=True)
    
    chinese_font = get_chinese_font()
    
    # 1. 机组组合图
    print("\n📊 生成机组组合图...")
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
    
    # 机组开停状态热力图
    status_data = solution['Status'].T.values
    im1 = ax1.imshow(status_data, aspect='auto', cmap='RdYlGn', 
                     interpolation='nearest', vmin=0, vmax=1)
    
    ax1.set_yticks(range(0, 26, 5))
    ax1.set_yticklabels([f'Gen {i}' for i in range(0, 26, 5)])
    ax1.set_title('96时段机组开停状态 (24小时)', fontproperties=chinese_font, fontsize=14)
    ax1.set_ylabel('发电机组', fontproperties=chinese_font)
    
    # 时间轴标签
    time_labels = []
    time_positions = []
    for i in range(0, 96, 8):  # 每2小时一个标签
        hour = i * 0.25
        time_labels.append(f'{int(hour):02d}:00')
        time_positions.append(i)
    
    ax1.set_xticks(time_positions)
    ax1.set_xticklabels(time_labels)
    
    # 颜色条
    cbar1 = plt.colorbar(im1, ax=ax1, orientation='vertical', pad=0.02)
    cbar1.set_label('状态 (0=停机, 1=运行)', fontproperties=chinese_font)
    
    # 总发电量曲线
    total_gen = solution['Power'].sum(axis=1)
    hours = np.arange(96) * 0.25
    
    ax2.plot(hours, total_gen, 'b-', linewidth=2)
    ax2.fill_between(hours, 0, total_gen, alpha=0.3)
    ax2.set_xlabel('时间 (小时)', fontproperties=chinese_font)
    ax2.set_ylabel('总发电量 (MW)', fontproperties=chinese_font)
    ax2.set_title('96时段总发电量曲线', fontproperties=chinese_font, fontsize=14)
    ax2.grid(True, alpha=0.3)
    ax2.set_xlim(0, 24)
    ax2.set_xticks(range(0, 25, 3))
    
    # 标注峰谷
    peak_idx = total_gen.idxmax()
    valley_idx = total_gen.idxmin()
    peak_hour = hours[total_gen.index.get_loc(peak_idx)]
    valley_hour = hours[total_gen.index.get_loc(valley_idx)]
    
    ax2.annotate(f'峰值: {total_gen.max():.0f} MW', 
                xy=(peak_hour, total_gen.max()),
                xytext=(peak_hour+2, total_gen.max()+500),
                arrowprops=dict(arrowstyle='->', color='red'),
                fontproperties=chinese_font)
    
    ax2.annotate(f'谷值: {total_gen.min():.0f} MW', 
                xy=(valley_hour, total_gen.min()),
                xytext=(valley_hour+2, total_gen.min()-500),
                arrowprops=dict(arrowstyle='->', color='blue'),
                fontproperties=chinese_font)
    
    plt.tight_layout()
    apply_chinese_font_to_figure(fig, chinese_font)
    
    output_path = os.path.join(results_dir, 'unit_commitment_96periods_demo.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 保存到: {output_path}")
    
    # 2. 关键时段LMP分布
    print("\n💰 生成节点加权均价图...")
    
    key_periods = {
        '深夜低谷 (03:00)': 12,
        '早高峰 (08:00)': 32,
        '午间 (12:00)': 48,
        '晚高峰 (19:00)': 76
    }
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    axes = axes.flatten()
    
    for idx, (period_name, period_idx) in enumerate(key_periods.items()):
        ax = axes[idx]
        
        lmp_data = solution['LMP'].iloc[period_idx]
        
        ax.hist(lmp_data, bins=20, alpha=0.7, color='blue', edgecolor='black')
        ax.axvline(lmp_data.mean(), color='red', linestyle='--', linewidth=2,
                  label=f'平均值: {lmp_data.mean():.2f} $/MWh')
        
        ax.set_xlabel('节点电价 ($/MWh)', fontproperties=chinese_font)
        ax.set_ylabel('节点数量', fontproperties=chinese_font)
        ax.set_title(f'{period_name} LMP分布', fontproperties=chinese_font)
        ax.legend(prop={'family': chinese_font.get_name()})
        ax.grid(True, alpha=0.3)
    
    plt.suptitle('96时段关键时刻节点电价分布', fontproperties=chinese_font, fontsize=16)
    plt.tight_layout()
    apply_chinese_font_to_figure(fig, chinese_font)
    
    output_path = os.path.join(results_dir, 'weighted_lmp_key_periods_demo.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    print(f"✅ 保存到: {output_path}")
    
    # 3. 统计汇总
    print("\n📊 生成统计汇总...")
    
    summary = {
        '仿真概况': {
            '总时段数': 96,
            '时间间隔': '15分钟',
            '总时长': '24小时'
        },
        '发电统计': {
            '平均总发电量': f"{total_gen.mean():.2f} MW",
            '峰值发电量': f"{total_gen.max():.2f} MW",
            '谷值发电量': f"{total_gen.min():.2f} MW",
            '峰谷差': f"{total_gen.max() - total_gen.min():.2f} MW",
            '峰谷差率': f"{(total_gen.max() - total_gen.min()) / total_gen.max() * 100:.1f}%"
        },
        '机组运行统计': {
            '平均运行机组数': f"{solution['Status'].sum(axis=1).mean():.1f}",
            '最多运行机组数': int(solution['Status'].sum(axis=1).max()),
            '最少运行机组数': int(solution['Status'].sum(axis=1).min())
        },
        '电价统计': {
            '日平均电价': f"{solution['LMP'].mean().mean():.2f} $/MWh",
            '最高节点电价': f"{solution['LMP'].max().max():.2f} $/MWh",
            '最低节点电价': f"{solution['LMP'].min().min():.2f} $/MWh"
        }
    }
    
    output_path = os.path.join(results_dir, 'summary_statistics_demo.json')
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"✅ 保存到: {output_path}")
    
    # 打印汇总
    print("\n📋 96时段仿真汇总:")
    for category, stats in summary.items():
        print(f"\n{category}:")
        for key, value in stats.items():
            print(f"  {key}: {value}")
    
    print("\n✅ 演示完成！")
    print(f"📁 所有结果保存在: {results_dir}")
    
    return True


def main():
    """主函数"""
    print("📋 96时段分析功能演示")
    print("  - 使用模拟数据快速展示分析功能")
    print("  - 生成机组组合图")
    print("  - 生成节点加权均价图")
    print("  - 生成统计汇总")
    print("")
    
    success = demo_96periods_analysis()
    
    if success:
        print("\n🎉 演示成功！")
        print("💡 这展示了96时段分析的主要功能")
    
    return success


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)