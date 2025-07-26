"""
IEEE 14节点12时段分析模块
包含所有要求的可视化和分析功能
"""

import os
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import networkx as nx
from datetime import datetime
from simpower.results_analysis import get_chinese_font, apply_chinese_font_to_figure


class IEEE14Analysis:
    """IEEE 14节点12时段分析类"""
    
    def __init__(self, case_dir, solution):
        self.case_dir = case_dir
        self.solution = solution
        self.results_dir = os.path.join(case_dir, 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        self.chinese_font = get_chinese_font()
        
        # 加载案例数据
        self.load_case_data()
        
    def load_case_data(self):
        """加载案例数据"""
        self.buses_df = pd.read_csv(os.path.join(self.case_dir, 'buses.csv'))
        self.lines_df = pd.read_csv(os.path.join(self.case_dir, 'lines.csv'))
        self.generators_df = pd.read_csv(os.path.join(self.case_dir, 'generators.csv'))
        self.loads_df = pd.read_csv(os.path.join(self.case_dir, 'loads.csv'))
        self.timeseries_df = pd.read_csv(os.path.join(self.case_dir, 'timeseries.csv'))
        
    def create_network_topology(self):
        """1. 创建网络拓扑图"""
        print("\n📊 生成网络拓扑图...")
        
        G = nx.Graph()
        
        # 添加节点
        for idx, bus in self.buses_df.iterrows():
            G.add_node(bus['name'], 
                      demand=bus['real_power_demand'],
                      bus_type=bus['bus_type'])
        
        # 添加边
        for idx, line in self.lines_df.iterrows():
            G.add_edge(line['from bus'], line['to bus'])
        
        # 创建布局
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # 绘制
        fig, ax = plt.subplots(figsize=(12, 10))
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, ax=ax, alpha=0.5, width=2)
        
        # 根据节点类型绘制节点
        node_colors = []
        node_sizes = []
        
        for node in G.nodes():
            node_data = G.nodes[node]
            # 平衡节点 - 红色
            if node_data['bus_type'] == 'slack':
                node_colors.append('red')
                node_sizes.append(800)
            # PV节点（有发电机）- 绿色
            elif node in self.generators_df['bus'].values:
                node_colors.append('green')
                node_sizes.append(600)
            # PQ节点（纯负荷）- 蓝色
            else:
                node_colors.append('lightblue')
                node_sizes.append(400)
        
        nx.draw_networkx_nodes(G, pos, ax=ax, node_color=node_colors, 
                             node_size=node_sizes, alpha=0.8)
        
        # 添加节点标签
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=10)
        
        # 添加发电机标签
        gen_labels = {}
        for idx, gen in self.generators_df.iterrows():
            bus = gen['bus']
            if bus in pos:
                gen_labels[bus] = gen['name'].split('_')[0]
        
        # 绘制发电机标签
        label_pos = {k: (v[0], v[1]+0.08) for k, v in pos.items() if k in gen_labels}
        nx.draw_networkx_labels(G, label_pos, gen_labels, ax=ax, 
                              font_size=8, font_color='darkgreen')
        
        # 添加图例
        red_patch = mpatches.Patch(color='red', label='平衡节点')
        green_patch = mpatches.Patch(color='green', label='发电节点')
        blue_patch = mpatches.Patch(color='lightblue', label='负荷节点')
        ax.legend(handles=[red_patch, green_patch, blue_patch], 
                 loc='upper right', fontsize=10)
        
        ax.set_title('IEEE 14节点系统网络拓扑图', fontproperties=self.chinese_font, fontsize=14)
        ax.axis('off')
        
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'network_topology.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_load_curve(self):
        """2. 创建负荷曲线"""
        print("\n📈 生成负荷曲线...")
        
        # 计算各时段总负荷
        base_load = self.buses_df['real_power_demand'].sum()
        load_factors = self.timeseries_df['load_factor'].values
        hours = list(range(12))
        total_loads = base_load * load_factors
        
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # 绘制负荷曲线
        ax.plot(hours, total_loads, 'b-o', linewidth=2, markersize=8)
        ax.fill_between(hours, 0, total_loads, alpha=0.3)
        
        # 标注最大最小值
        max_idx = np.argmax(total_loads)
        min_idx = np.argmin(total_loads)
        
        ax.annotate(f'峰值: {total_loads[max_idx]:.1f} MW', 
                   xy=(hours[max_idx], total_loads[max_idx]),
                   xytext=(hours[max_idx]+0.5, total_loads[max_idx]+5),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontproperties=self.chinese_font)
        
        ax.annotate(f'谷值: {total_loads[min_idx]:.1f} MW', 
                   xy=(hours[min_idx], total_loads[min_idx]),
                   xytext=(hours[min_idx]+0.5, total_loads[min_idx]-10),
                   arrowprops=dict(arrowstyle='->', color='blue'),
                   fontproperties=self.chinese_font)
        
        ax.set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
        ax.set_ylabel('总负荷 (MW)', fontproperties=self.chinese_font)
        ax.set_title('12时段系统负荷曲线', fontproperties=self.chinese_font, fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(hours)
        ax.set_xticklabels([f'{h}:00' for h in hours])
        
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'load_curve.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_unit_commitment(self):
        """3. 创建机组组合图"""
        print("\n⚡ 生成机组组合图...")
        
        if 'Status' not in self.solution:
            print("❌ 无机组状态数据")
            return
            
        status_df = self.solution['Status']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        # 创建热力图数据
        gen_names = list(status_df.columns)
        hours = list(range(len(status_df)))
        status_data = status_df.values.T
        
        # 绘制热力图
        im = ax.imshow(status_data, aspect='auto', cmap='RdYlGn', 
                      interpolation='nearest', vmin=0, vmax=1)
        
        # 设置坐标轴
        ax.set_yticks(range(len(gen_names)))
        ax.set_yticklabels(gen_names)
        ax.set_xticks(hours)
        ax.set_xticklabels([f'{h}:00' for h in hours])
        
        # 添加网格
        ax.set_xticks(np.arange(len(hours)+1)-0.5, minor=True)
        ax.set_yticks(np.arange(len(gen_names)+1)-0.5, minor=True)
        ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('机组状态 (0=停机, 1=运行)', fontproperties=self.chinese_font)
        
        ax.set_xlabel('时间', fontproperties=self.chinese_font)
        ax.set_ylabel('发电机组', fontproperties=self.chinese_font)
        ax.set_title('12时段机组组合状态', fontproperties=self.chinese_font, fontsize=14)
        
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'unit_commitment.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_generation_dispatch(self):
        """4. 创建机组出力图"""
        print("\n⚙️ 生成机组出力图...")
        
        if 'Power' not in self.solution:
            print("❌ 无机组出力数据")
            return
            
        power_df = self.solution['Power']
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # 1. 堆叠面积图
        hours = list(range(len(power_df)))
        bottom = np.zeros(len(hours))
        
        colors = plt.cm.Set3(np.linspace(0, 1, len(power_df.columns)))
        
        for i, gen in enumerate(power_df.columns):
            ax1.fill_between(hours, bottom, bottom + power_df[gen].values,
                           label=gen, color=colors[i], alpha=0.8)
            bottom += power_df[gen].values
        
        ax1.set_xlabel('时间', fontproperties=self.chinese_font)
        ax1.set_ylabel('发电量 (MW)', fontproperties=self.chinese_font)
        ax1.set_title('12时段机组出力堆叠图', fontproperties=self.chinese_font, fontsize=14)
        ax1.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(hours)
        ax1.set_xticklabels([f'{h}:00' for h in hours])
        
        # 2. 分机组出力曲线
        for i, gen in enumerate(power_df.columns):
            ax2.plot(hours, power_df[gen].values, '-o', label=gen, 
                    color=colors[i], linewidth=2, markersize=6)
        
        ax2.set_xlabel('时间', fontproperties=self.chinese_font)
        ax2.set_ylabel('发电量 (MW)', fontproperties=self.chinese_font)
        ax2.set_title('12时段各机组出力曲线', fontproperties=self.chinese_font, fontsize=14)
        ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(hours)
        ax2.set_xticklabels([f'{h}:00' for h in hours])
        
        plt.tight_layout()
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'generation_dispatch.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_nodal_prices(self):
        """5. 创建节点电价图"""
        print("\n💰 生成节点电价图...")
        
        if 'LMP' not in self.solution:
            print("❌ 无节点电价数据")
            return
            
        lmp_df = self.solution['LMP']
        
        # 只显示有发电机的节点
        gen_buses = self.generators_df['bus'].unique()
        lmp_gen_buses = lmp_df[gen_buses]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        hours = list(range(len(lmp_gen_buses)))
        
        # 1. 发电节点电价曲线
        for bus in lmp_gen_buses.columns:
            ax1.plot(hours, lmp_gen_buses[bus].values, '-o', label=bus, linewidth=2)
        
        ax1.set_xlabel('时间', fontproperties=self.chinese_font)
        ax1.set_ylabel('节点电价 ($/MWh)', fontproperties=self.chinese_font)
        ax1.set_title('12时段发电节点电价', fontproperties=self.chinese_font, fontsize=14)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(hours)
        ax1.set_xticklabels([f'{h}:00' for h in hours])
        
        # 2. 电价热力图
        lmp_data = lmp_df.values.T
        im = ax2.imshow(lmp_data, aspect='auto', cmap='RdYlGn_r', interpolation='nearest')
        
        ax2.set_yticks(range(len(lmp_df.columns)))
        ax2.set_yticklabels(lmp_df.columns, fontsize=8)
        ax2.set_xticks(hours)
        ax2.set_xticklabels([f'{h}:00' for h in hours])
        
        cbar = plt.colorbar(im, ax=ax2)
        cbar.set_label('节点电价 ($/MWh)', fontproperties=self.chinese_font)
        
        ax2.set_xlabel('时间', fontproperties=self.chinese_font)
        ax2.set_ylabel('节点', fontproperties=self.chinese_font)
        ax2.set_title('12时段全网节点电价热力图', fontproperties=self.chinese_font, fontsize=14)
        
        plt.tight_layout()
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'nodal_prices.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def calculate_total_costs(self):
        """6. 计算总费用"""
        print("\n💵 计算系统总费用...")
        
        costs = {
            '电能量费用': 0,
            '启动费用': 0,
            '空载费用': 0,
            '总费用': 0
        }
        
        if 'Power' in self.solution and 'Status' in self.solution:
            power_df = self.solution['Power']
            status_df = self.solution['Status']
            
            # 计算电能量费用（基于容量段报价）
            for gen_idx, gen in self.generators_df.iterrows():
                gen_name = gen['name']
                if gen_name in power_df.columns:
                    # 简化计算：使用平均电价
                    avg_price = 30  # $/MWh 平均电价估计
                    energy_cost = (power_df[gen_name] * avg_price).sum()
                    costs['电能量费用'] += energy_cost
            
            # 计算启动费用
            for gen_name in status_df.columns:
                status = status_df[gen_name].values
                # 计算启动次数
                starts = np.sum(np.diff(np.concatenate([[0], status])) > 0)
                gen_info = self.generators_df[self.generators_df['name'] == gen_name]
                if not gen_info.empty:
                    start_cost = gen_info['start cost'].values[0]
                    costs['启动费用'] += starts * start_cost
            
            # 计算空载费用
            for gen_idx, gen in self.generators_df.iterrows():
                gen_name = gen['name']
                if gen_name in status_df.columns:
                    running_hours = status_df[gen_name].sum()
                    no_load_cost = gen['no load cost']
                    costs['空载费用'] += running_hours * no_load_cost
        
        costs['总费用'] = costs['电能量费用'] + costs['启动费用'] + costs['空载费用']
        
        # 保存费用报告
        cost_report = {
            '费用明细': {
                '电能量费用': f"${costs['电能量费用']:,.2f}",
                '启动费用': f"${costs['启动费用']:,.2f}",
                '空载费用': f"${costs['空载费用']:,.2f}",
                '总费用': f"${costs['总费用']:,.2f}"
            },
            '费用占比': {
                '电能量费用占比': f"{costs['电能量费用']/costs['总费用']*100:.1f}%",
                '启动费用占比': f"{costs['启动费用']/costs['总费用']*100:.1f}%",
                '空载费用占比': f"{costs['空载费用']/costs['总费用']*100:.1f}%"
            }
        }
        
        output_path = os.path.join(self.results_dir, 'cost_report.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(cost_report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 费用报告保存到: {output_path}")
        
        # 打印费用汇总
        print("\n📊 系统费用汇总:")
        for category, details in cost_report.items():
            print(f"\n{category}:")
            for key, value in details.items():
                print(f"  {key}: {value}")
        
        # 创建费用饼图
        fig, ax = plt.subplots(figsize=(8, 8))
        
        labels = ['电能量费用', '启动费用', '空载费用']
        sizes = [costs['电能量费用'], costs['启动费用'], costs['空载费用']]
        colors = ['#ff9999', '#66b3ff', '#99ff99']
        
        # 过滤掉0值
        non_zero = [(l, s, c) for l, s, c in zip(labels, sizes, colors) if s > 0]
        if non_zero:
            labels, sizes, colors = zip(*non_zero)
            
            wedges, texts, autotexts = ax.pie(sizes, labels=labels, colors=colors,
                                             autopct='%1.1f%%', startangle=90)
            
            # 设置中文字体
            for text in texts:
                text.set_fontproperties(self.chinese_font)
            
            ax.set_title('系统运行费用构成', fontproperties=self.chinese_font, fontsize=14)
        
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'cost_pie_chart.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 费用构成图保存到: {output_path}")
        
    def generate_full_report(self):
        """生成完整报告"""
        print("\n🔍 开始生成IEEE 14节点12时段完整分析报告...")
        
        # 1. 网络拓扑图
        self.create_network_topology()
        
        # 2. 负荷曲线
        self.create_load_curve()
        
        # 3. 机组组合
        self.create_unit_commitment()
        
        # 4. 机组出力
        self.create_generation_dispatch()
        
        # 5. 节点电价
        self.create_nodal_prices()
        
        # 6. 费用分析
        self.calculate_total_costs()
        
        print(f"\n✅ 分析报告生成完成！")
        print(f"📁 所有结果保存在: {self.results_dir}")