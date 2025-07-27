"""
IEEE 14节点系统分析基础模块
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import networkx as nx
from pathlib import Path


def get_chinese_font():
    """获取中文字体"""
    # 尝试多种中文字体
    font_names = [
        'Source Han Sans CN',
        'Noto Sans CJK SC', 
        'WenQuanYi Micro Hei',
        'SimHei',
        'Microsoft YaHei',
        'DejaVu Sans'
    ]
    
    for font_name in font_names:
        try:
            font = fm.FontProperties(family=font_name)
            if font.get_name():
                return font
        except:
            continue
    
    # 尝试从文件加载
    font_paths = [
        '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
        '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',
        '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
        '/workspace/SourceHanSansCN-Regular.otf'
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                return fm.FontProperties(fname=font_path)
            except:
                continue
    
    return None


def apply_chinese_font_to_figure(fig, font):
    """应用中文字体到图形"""
    if font is None:
        return
    
    font_name = font.get_name()
    
    # 设置所有文本元素的字体
    for ax in fig.get_axes():
        # 标题
        if ax.title:
            ax.title.set_fontfamily(font_name)
        
        # 轴标签
        ax.xaxis.label.set_fontfamily(font_name)
        ax.yaxis.label.set_fontfamily(font_name)
        
        # 刻度标签
        for label in ax.get_xticklabels():
            label.set_fontfamily(font_name)
        for label in ax.get_yticklabels():
            label.set_fontfamily(font_name)
        
        # 图例
        legend = ax.get_legend()
        if legend:
            for text in legend.get_texts():
                text.set_fontfamily(font_name)


class IEEE14Analysis:
    """IEEE 14节点系统分析基类"""
    
    def __init__(self, case_dir, solution):
        self.case_dir = case_dir
        self.solution = solution
        self.load_data()
        
    def load_data(self):
        """加载案例数据"""
        # 加载发电机数据
        gen_df = pd.read_csv(os.path.join(self.case_dir, 'generators.csv'))
        self.generators = gen_df.to_dict('records')
        
        # 加载节点数据
        bus_df = pd.read_csv(os.path.join(self.case_dir, 'buses.csv'))
        self.buses = bus_df.to_dict('records')
        
        # 加载线路数据
        line_df = pd.read_csv(os.path.join(self.case_dir, 'lines.csv'))
        self.lines = line_df.to_dict('records')
        
        # 加载负荷数据
        load_df = pd.read_csv(os.path.join(self.case_dir, 'loads.csv'))
        self.loads = load_df.to_dict('records')
        
    def create_network_topology(self):
        """创建网络拓扑图"""
        
        print("\n📊 生成网络拓扑图...")
        
        # 创建图
        G = nx.Graph()
        
        # 添加节点
        for bus in self.buses:
            G.add_node(bus['name'])
        
        # 添加边（线路）
        for line in self.lines:
            G.add_edge(line['frombus'], line['tobus'])
        
        # 布局
        pos = nx.spring_layout(G, k=2, iterations=50, seed=42)
        
        # 绘图
        plt.figure(figsize=(12, 10))
        
        # 绘制边
        nx.draw_networkx_edges(G, pos, alpha=0.5, width=2)
        
        # 绘制节点 - 区分发电机节点和负荷节点
        gen_buses = [gen['bus'] for gen in self.generators]
        load_buses = [load['bus'] for load in self.loads]
        
        node_colors = []
        node_sizes = []
        for node in G.nodes():
            if node in gen_buses:
                node_colors.append('red')
                node_sizes.append(800)
            elif node in load_buses:
                node_colors.append('blue')
                node_sizes.append(600)
            else:
                node_colors.append('gray')
                node_sizes.append(400)
        
        nx.draw_networkx_nodes(G, pos, node_color=node_colors, 
                              node_size=node_sizes, alpha=0.8)
        
        # 添加标签
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # 图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='red', label='Generator Bus'),
            Patch(facecolor='blue', label='Load Bus'),
            Patch(facecolor='gray', label='Connection Bus')
        ]
        plt.legend(handles=legend_elements, loc='upper right')
        
        plt.title('IEEE 14-Bus Network Topology', fontsize=16)
        plt.axis('off')
        plt.tight_layout()
        
        # 保存
        output_path = os.path.join(self.case_dir, 'results', 'network_topology.png')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_generation_dispatch(self):
        """创建机组出力图"""
        
        print("\n⚙️ 生成机组出力图...")
        
        # 这是一个占位实现，具体实现需要根据solution的结构
        output_path = os.path.join(self.case_dir, 'results', 'generation_dispatch.png')
        
        # 创建一个简单的图
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'Generation Dispatch\n(To be implemented)', 
                ha='center', va='center', fontsize=20)
        plt.axis('off')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_nodal_prices(self):
        """创建节点电价图"""
        
        print("\n💰 生成节点电价图...")
        
        output_path = os.path.join(self.case_dir, 'results', 'nodal_prices.png')
        
        # 创建一个简单的图
        plt.figure(figsize=(12, 8))
        plt.text(0.5, 0.5, 'Nodal Prices\n(To be implemented)', 
                ha='center', va='center', fontsize=20)
        plt.axis('off')
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path)
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_cost_report(self):
        """创建费用报告"""
        
        print("\n💵 计算系统总费用...")
        
        # 创建基本费用报告
        report = {
            "费用明细": {
                "总费用": f"${self.solution.objective:,.2f}" if hasattr(self.solution, 'objective') else "N/A",
                "发电总费用": f"${self.solution.objective:,.2f}" if hasattr(self.solution, 'objective') else "N/A"
            },
            "仿真信息": {
                "机组数量": len(self.generators),
                "节点数量": len(self.buses),
                "线路数量": len(self.lines)
            }
        }
        
        # 保存报告
        output_path = os.path.join(self.case_dir, 'results', 'cost_report.json')
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 费用报告保存到: {output_path}")
        
        if hasattr(self.solution, 'objective'):
            print(f"\n系统总费用: ${self.solution.objective:,.2f}")
        
    def analyze_marginal_units(self):
        """分析边际机组"""
        
        print("\n📊 边际机组分析...")
        
        # 创建占位数据
        marginal_data = pd.DataFrame({
            '时段': ['平均'],
            '边际机组': ['N/A'],
            '边际价格($/MWh)': [0]
        })
        
        output_path = os.path.join(self.case_dir, 'results', 'marginal_analysis.csv')
        marginal_data.to_csv(output_path, index=False, encoding='utf-8-sig')
        
        print(f"✅ 边际分析保存到: {output_path}")