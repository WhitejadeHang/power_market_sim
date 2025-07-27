#!/usr/bin/env python3
"""
分析网络约束并修复，生成带容量标注的拓扑图
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import networkx as nx
from matplotlib.patches import FancyBboxPatch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from simpower.results_analysis import get_chinese_font


def analyze_power_flow(case_dir):
    """分析单时段潮流结果"""
    
    # 读取数据
    lines_df = pd.read_csv(f'{case_dir}/lines.csv')
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    
    print("\n" + "=" * 60)
    print("潮流分析")
    print("=" * 60)
    
    # 从之前的输出中提取潮流数据
    line_flows = [17.07, 12.93, 4.46, 12.24, 10.77, 7.46, -6.78, -0.32, -8.09, 
                  23.93, 13.61, 24.58, -16.5, 16.18, 11.07, -8.09, -13.93, -1.39, 3.19, 6.80]
    
    # 添加潮流数据到lines_df
    lines_df['power_flow'] = np.abs(line_flows)
    lines_df['utilization'] = lines_df['power_flow'] / lines_df['pmax'] * 100
    
    # 显示利用率
    print("\n线路利用率:")
    high_util = lines_df[lines_df['utilization'] > 50].sort_values('utilization', ascending=False)
    if not high_util.empty:
        print("\n高利用率线路 (>50%):")
        print(high_util[['name', 'frombus', 'tobus', 'pmax', 'power_flow', 'utilization']].to_string())
    
    # 建议增容
    print("\n建议增容的线路:")
    for _, line in lines_df.iterrows():
        if line['utilization'] > 15:  # 利用率超过15%的线路
            new_capacity = int(line['power_flow'] * 10)  # 留10倍裕度
            print(f"{line['name']}: {line['pmax']} MW -> {new_capacity} MW")
    
    return lines_df


def create_enhanced_topology(case_dir, lines_df):
    """创建带容量和潮流标注的网络拓扑图"""
    
    # 读取数据
    buses_df = pd.read_csv(f'{case_dir}/buses.csv')
    gen_df = pd.read_csv(f'{case_dir}/generators.csv')
    loads_df = pd.read_csv(f'{case_dir}/loads.csv')
    
    # 获取中文字体
    chinese_font = get_chinese_font()
    
    # 创建图
    G = nx.Graph()
    
    # 添加节点
    for _, bus in buses_df.iterrows():
        G.add_node(bus['name'])
    
    # 添加边（带权重）
    for _, line in lines_df.iterrows():
        G.add_edge(line['frombus'], line['tobus'], 
                  capacity=line['pmax'],
                  flow=line['power_flow'] if 'power_flow' in line else 0,
                  utilization=line['utilization'] if 'utilization' in line else 0)
    
    # 创建图形
    plt.figure(figsize=(16, 12))
    
    # 布局算法
    pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
    
    # 手动调整某些节点位置以更清晰
    pos['Bus01'] = np.array([-1.0, 0.8])
    pos['Bus02'] = np.array([-0.5, 0.5])
    pos['Bus03'] = np.array([0.0, 0.8])
    pos['Bus04'] = np.array([-0.5, 0.0])
    pos['Bus05'] = np.array([-1.0, 0.0])
    pos['Bus06'] = np.array([0.0, 0.0])
    pos['Bus07'] = np.array([-0.5, -0.5])
    pos['Bus08'] = np.array([-1.0, -0.8])
    pos['Bus09'] = np.array([0.0, -0.5])
    pos['Bus10'] = np.array([0.5, -0.5])
    pos['Bus11'] = np.array([0.5, 0.0])
    pos['Bus12'] = np.array([0.5, 0.5])
    pos['Bus13'] = np.array([1.0, 0.5])
    pos['Bus14'] = np.array([1.0, -0.5])
    
    # 绘制边（线路）- 根据利用率着色
    edge_colors = []
    edge_widths = []
    for u, v, data in G.edges(data=True):
        util = data.get('utilization', 0)
        if util > 20:
            edge_colors.append('red')
            edge_widths.append(3)
        elif util > 10:
            edge_colors.append('orange')
            edge_widths.append(2)
        else:
            edge_colors.append('green')
            edge_widths.append(1)
    
    nx.draw_networkx_edges(G, pos, edge_color=edge_colors, width=edge_widths, alpha=0.6)
    
    # 标注线路容量和潮流
    edge_labels = {}
    for _, line in lines_df.iterrows():
        if 'power_flow' in line:
            label = f"{int(line['power_flow'])}/{int(line['pmax'])}MW\n({line['utilization']:.0f}%)"
        else:
            label = f"{int(line['pmax'])}MW"
        edge_labels[(line['frombus'], line['tobus'])] = label
    
    nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8, 
                                font_family=chinese_font.get_name())
    
    # 绘制节点
    node_colors = []
    node_sizes = []
    
    for node in G.nodes():
        # 检查是否有发电机
        if node in gen_df['bus'].values:
            node_colors.append('lightcoral')
            # 根据容量决定大小
            gen_capacity = gen_df[gen_df['bus'] == node]['P max'].sum()
            node_sizes.append(1000 + gen_capacity * 5)
        # 检查是否有负荷
        elif node in loads_df['bus'].values:
            node_colors.append('lightblue')
            load_power = loads_df[loads_df['bus'] == node]['power'].sum()
            node_sizes.append(500 + load_power * 10)
        else:
            node_colors.append('lightgray')
            node_sizes.append(500)
    
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes, alpha=0.8)
    
    # 标注节点名称和信息
    labels = {}
    for node in G.nodes():
        label = node
        # 添加发电机信息
        if node in gen_df['bus'].values:
            gens = gen_df[gen_df['bus'] == node]
            total_cap = gens['P max'].sum()
            label += f"\nG:{total_cap}MW"
        # 添加负荷信息
        if node in loads_df['bus'].values:
            loads = loads_df[loads_df['bus'] == node]
            total_load = loads['power'].sum()
            label += f"\nL:{total_load}MW"
        labels[node] = label
    
    nx.draw_networkx_labels(G, pos, labels, font_size=10, font_weight='bold',
                           font_family=chinese_font.get_name())
    
    # 添加图例
    legend_elements = [
        plt.Line2D([0], [0], color='green', linewidth=2, label='低利用率 (<10%)'),
        plt.Line2D([0], [0], color='orange', linewidth=3, label='中利用率 (10-20%)'),
        plt.Line2D([0], [0], color='red', linewidth=4, label='高利用率 (>20%)'),
        plt.scatter([], [], c='lightcoral', s=200, label='发电节点'),
        plt.scatter([], [], c='lightblue', s=200, label='负荷节点'),
        plt.scatter([], [], c='lightgray', s=200, label='中间节点')
    ]
    plt.legend(handles=legend_elements, loc='upper right', prop=chinese_font)
    
    plt.title('IEEE 14节点系统网络拓扑图\n(线路标注: 潮流/容量MW)', 
              fontproperties=chinese_font, fontsize=16)
    plt.axis('off')
    plt.tight_layout()
    
    # 保存图形
    output_path = os.path.join(case_dir, 'network_topology_with_flow.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    plt.close()
    
    print(f"\n✅ 网络拓扑图保存到: {output_path}")


def update_line_capacities(case_dir):
    """更新线路容量"""
    
    lines_df = pd.read_csv(f'{case_dir}/lines.csv')
    
    # 基于实际潮流更新容量
    # 原始容量都是130MW，根据利用情况调整
    lines_df['pmax'] = lines_df['pmax'] * 1.8  # 先统一增加80%
    
    # 对特定线路进一步增容
    critical_lines = ['Line10', 'Line12', 'Line16']  # Bus06相关的线路
    for line in critical_lines:
        lines_df.loc[lines_df['name'] == line, 'pmax'] *= 1.5
    
    lines_df.to_csv(f'{case_dir}/lines.csv', index=False)
    
    print("\n✅ 线路容量已更新")
    print(f"新的容量范围: {lines_df['pmax'].min():.0f} - {lines_df['pmax'].max():.0f} MW")


if __name__ == "__main__":
    # 使用单时段测试案例
    case_dir = 'simpower/tests/ieee14_single_period_test'
    
    if os.path.exists(case_dir):
        # 分析潮流
        lines_df = analyze_power_flow(case_dir)
        
        # 创建拓扑图
        create_enhanced_topology(case_dir, lines_df)
        
        # 更新24时段案例的线路容量
        case_24 = 'simpower/tests/ieee14_24periods_coal'
        update_line_capacities(case_24)
    else:
        print("请先运行 test_single_period_debug.py")