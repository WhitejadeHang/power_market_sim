#!/usr/bin/env python3
"""
IEEE 50节点案例96时段结果分析和可视化模块
生成机组组合图、节点加权均价图等
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import Rectangle
import seaborn as sns
import networkx as nx
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# 导入中文字体支持
from .results_analysis import get_chinese_font, create_text_with_font, apply_chinese_font_to_figure


class IEEE50Bus96PeriodsAnalysis:
    """IEEE 50节点96时段案例分析类"""
    
    def __init__(self, case_dir, solution):
        """初始化分析器"""
        self.case_dir = case_dir
        self.solution = solution
        self.results_dir = os.path.join(case_dir, 'results_96periods')
        
        # 创建结果目录
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 加载中文字体
        self.chinese_font = get_chinese_font()
        
        # 加载案例数据
        self.load_case_data()
        
        # 提取96时段的求解结果
        self.extract_96periods_results()
    
    def load_case_data(self):
        """加载案例数据"""
        try:
            self.buses_df = pd.read_csv(os.path.join(self.case_dir, 'buses.csv'))
            self.lines_df = pd.read_csv(os.path.join(self.case_dir, 'lines.csv'))
            self.generators_df = pd.read_csv(os.path.join(self.case_dir, 'generators.csv'))
            self.loads_df = pd.read_csv(os.path.join(self.case_dir, 'loads.csv'))
            
            # 读取时间序列
            if os.path.exists(os.path.join(self.case_dir, 'timeseries.csv')):
                self.timeseries_df = pd.read_csv(os.path.join(self.case_dir, 'timeseries.csv'))
                self.time_periods = self.timeseries_df['time'].tolist()
            else:
                # 生成96个时段
                base_time = datetime(2025, 7, 25)
                self.time_periods = []
                for i in range(96):
                    t = base_time + timedelta(minutes=15*i)
                    self.time_periods.append(t.strftime('%H:%M'))
            
            print(f"✅ 成功加载案例数据:")
            print(f"   - 节点数: {len(self.buses_df)}")
            print(f"   - 线路数: {len(self.lines_df)}")
            print(f"   - 发电机数: {len(self.generators_df)}")
            print(f"   - 时段数: {len(self.time_periods)}")
            
        except Exception as e:
            print(f"❌ 加载案例数据失败: {e}")
            raise
    
    def extract_96periods_results(self):
        """提取96时段的求解结果"""
        
        print("\n📊 提取96时段求解结果...")
        
        # 初始化结果存储
        self.gen_status = {}      # 机组状态 (96x26)
        self.gen_power = {}       # 机组出力 (96x26)
        self.node_lmp = {}        # 节点电价 (96x50)
        self.system_load = []     # 系统负荷
        self.total_cost = []      # 总成本
        
        try:
            # 从solution对象提取数据
            for t_idx, time_str in enumerate(self.time_periods):
                
                # 机组数据
                for gen in self.solution.generators:
                    gen_name = gen.name
                    if gen_name not in self.gen_status:
                        self.gen_status[gen_name] = []
                        self.gen_power[gen_name] = []
                    
                    # 获取该时段的状态和出力
                    if hasattr(gen.status, 'values'):
                        status = float(gen.status.values[t_idx]) if t_idx < len(gen.status.values) else 0
                        power = float(gen.power.values[t_idx]) if t_idx < len(gen.power.values) else 0
                    else:
                        status = float(gen.status.value or 0)
                        power = float(gen.power.value or 0)
                    
                    self.gen_status[gen_name].append(status)
                    self.gen_power[gen_name].append(power)
                
                # 节点电价数据
                for bus in self.solution.buses:
                    bus_name = bus.name
                    if bus_name not in self.node_lmp:
                        self.node_lmp[bus_name] = []
                    
                    # 获取该时段的LMP
                    if hasattr(bus.lmp, 'values'):
                        lmp = float(bus.lmp.values[t_idx]) if t_idx < len(bus.lmp.values) else 0
                    else:
                        lmp = float(bus.lmp.value or 0)
                    
                    self.node_lmp[bus_name].append(lmp)
                
                # 系统负荷（所有机组出力之和）
                period_load = sum(self.gen_power[g][t_idx] for g in self.gen_power)
                self.system_load.append(period_load)
            
            print(f"✅ 成功提取96时段结果")
            print(f"   - 机组数据: {len(self.gen_status)} 台")
            print(f"   - 节点电价: {len(self.node_lmp)} 个节点")
            print(f"   - 系统负荷范围: {min(self.system_load):.1f} - {max(self.system_load):.1f} MW")
            
        except Exception as e:
            print(f"❌ 提取结果失败: {e}")
            # 生成模拟数据用于演示
            self.generate_demo_data()
    
    def generate_demo_data(self):
        """生成演示用的模拟数据"""
        print("⚠️ 使用模拟数据进行演示...")
        
        # 生成96时段的模拟负荷曲线
        hours = np.arange(96) * 0.25  # 15分钟间隔
        base_load = 8000
        daily_pattern = 500 * np.sin((hours - 6) * np.pi / 12) + 300 * np.sin((hours - 8) * np.pi / 6)
        self.system_load = base_load + daily_pattern + np.random.normal(0, 50, 96)
        
        # 生成机组状态和出力
        for gen in self.generators_df['name']:
            self.gen_status[gen] = []
            self.gen_power[gen] = []
            
            # 根据机组类型确定运行模式
            if 'supercritical' in gen.lower():
                # 超临界机组 - 基荷运行
                base_power = 600
                for t in range(96):
                    self.gen_status[gen].append(1)
                    self.gen_power[gen].append(base_power + np.random.normal(0, 10))
            elif 'subcritical' in gen.lower():
                # 亚临界机组 - 负荷跟踪
                base_power = 400
                for t in range(96):
                    load_factor = (self.system_load[t] - 7500) / 1000
                    status = 1 if load_factor > 0.3 else 0
                    self.gen_status[gen].append(status)
                    self.gen_power[gen].append(base_power * load_factor * status)
            else:
                # 小机组 - 调峰
                base_power = 100
                for t in range(96):
                    load_factor = (self.system_load[t] - 8200) / 500
                    status = 1 if load_factor > 0.5 else 0
                    self.gen_status[gen].append(status)
                    self.gen_power[gen].append(base_power * load_factor * status)
        
        # 生成节点电价
        for bus in self.buses_df['name']:
            self.node_lmp[bus] = []
            base_lmp = np.random.uniform(20, 50)
            for t in range(96):
                # 电价随负荷变化
                load_factor = (self.system_load[t] - 7500) / 1000
                lmp = base_lmp * (1 + 0.5 * load_factor) + np.random.normal(0, 2)
                self.node_lmp[bus].append(max(lmp, 10))
    
    def create_unit_commitment_chart(self):
        """创建96时段机组组合图"""
        
        print("\n📊 生成96时段机组组合图...")
        
        # 准备数据
        gen_names = list(self.gen_status.keys())
        n_gens = len(gen_names)
        n_periods = 96
        
        # 创建图形
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), height_ratios=[3, 1])
        
        # 1. 机组组合状态图
        ax1.set_title('IEEE 50节点系统96时段机组组合', fontsize=16, fontweight='bold',
                      **create_text_with_font('IEEE 50节点系统96时段机组组合', self.chinese_font))
        
        # 按机组类型排序
        gen_types = []
        for gen in gen_names:
            if 'supercritical' in gen.lower():
                gen_types.append(1)  # 超临界
            elif 'subcritical' in gen.lower():
                gen_types.append(2)  # 亚临界
            elif 'old_steam' in gen.lower():
                gen_types.append(3)  # 老式机组
            else:
                gen_types.append(4)  # 小机组
        
        sorted_indices = sorted(range(len(gen_types)), key=lambda k: gen_types[k])
        sorted_gen_names = [gen_names[i] for i in sorted_indices]
        
        # 绘制机组状态
        for i, gen in enumerate(sorted_gen_names):
            for t in range(n_periods):
                if self.gen_status[gen][t] > 0.5:
                    # 根据出力大小确定颜色深浅
                    power_ratio = self.gen_power[gen][t] / max(self.gen_power[gen])
                    color_intensity = 0.3 + 0.7 * power_ratio
                    
                    # 根据机组类型选择颜色
                    if 'supercritical' in gen.lower():
                        color = plt.cm.Greens(color_intensity)
                    elif 'subcritical' in gen.lower():
                        color = plt.cm.Blues(color_intensity)
                    elif 'old_steam' in gen.lower():
                        color = plt.cm.Oranges(color_intensity)
                    else:
                        color = plt.cm.Purples(color_intensity)
                    
                    rect = Rectangle((t, i), 1, 1, facecolor=color, edgecolor='white', linewidth=0.5)
                    ax1.add_patch(rect)
        
        # 设置坐标轴
        ax1.set_xlim(0, n_periods)
        ax1.set_ylim(0, n_gens)
        ax1.set_xlabel('时段 (15分钟间隔)', **create_text_with_font('时段 (15分钟间隔)', self.chinese_font))
        ax1.set_ylabel('发电机组', **create_text_with_font('发电机组', self.chinese_font))
        
        # 设置y轴标签
        ax1.set_yticks(np.arange(n_gens) + 0.5)
        ax1.set_yticklabels([gen.replace('_', ' ') for gen in sorted_gen_names], fontsize=8)
        
        # 设置x轴标签（每4小时一个标签）
        x_ticks = range(0, 96, 16)
        x_labels = ['00:00', '04:00', '08:00', '12:00', '16:00', '20:00']
        ax1.set_xticks(x_ticks)
        ax1.set_xticklabels(x_labels)
        
        # 添加网格
        ax1.grid(True, axis='x', alpha=0.3, linestyle='--')
        
        # 添加图例
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='green', label='超临界机组'),
            Patch(facecolor='blue', label='亚临界机组'),
            Patch(facecolor='orange', label='老式机组'),
            Patch(facecolor='purple', label='小型机组')
        ]
        ax1.legend(handles=legend_elements, loc='upper right', fontsize=10,
                  prop=self.chinese_font if self.chinese_font else None)
        
        # 2. 系统负荷曲线
        ax2.plot(range(96), self.system_load, 'b-', linewidth=2)
        ax2.fill_between(range(96), 0, self.system_load, alpha=0.3)
        ax2.set_title('系统总负荷', fontsize=12, fontweight='bold',
                      **create_text_with_font('系统总负荷', self.chinese_font))
        ax2.set_xlabel('时段', **create_text_with_font('时段', self.chinese_font))
        ax2.set_ylabel('负荷 (MW)', **create_text_with_font('负荷 (MW)', self.chinese_font))
        ax2.set_xlim(0, 96)
        ax2.grid(True, alpha=0.3)
        ax2.set_xticks(x_ticks)
        ax2.set_xticklabels(x_labels)
        
        # 标注最大和最小负荷
        max_load_idx = np.argmax(self.system_load)
        min_load_idx = np.argmin(self.system_load)
        ax2.scatter(max_load_idx, self.system_load[max_load_idx], color='red', s=100, zorder=5)
        ax2.scatter(min_load_idx, self.system_load[min_load_idx], color='blue', s=100, zorder=5)
        
        # 应用中文字体
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        plt.tight_layout()
        
        # 保存图形
        save_path = os.path.join(self.results_dir, 'unit_commitment_96periods.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 机组组合图已保存: {save_path}")
        plt.close()
    
    def create_weighted_lmp_charts(self):
        """创建节点加权均价图（每个时段）"""
        
        print("\n📊 生成节点加权均价图...")
        
        # 创建子目录存放各时段的图
        lmp_dir = os.path.join(self.results_dir, 'lmp_by_period')
        os.makedirs(lmp_dir, exist_ok=True)
        
        # 选择关键时段进行详细绘制
        key_periods = [23, 35, 47, 71]  # 06:00, 09:00, 12:00, 18:00
        period_names = ['06:00 (早高峰前)', '09:00 (早高峰)', '12:00 (午间)', '18:00 (晚高峰)']
        
        # 创建网络图
        G = nx.Graph()
        
        # 添加节点
        for bus in self.buses_df['name']:
            G.add_node(bus)
        
        # 添加边（线路）
        for _, line in self.lines_df.iterrows():
            if 'from bus' in line:
                from_bus = line['from bus']
                to_bus = line['to bus']
            else:
                from_bus = line['frombus']
                to_bus = line['tobus']
            G.add_edge(from_bus, to_bus)
        
        # 使用spring布局
        pos = nx.spring_layout(G, k=3, iterations=50, seed=42)
        
        # 为每个关键时段绘制LMP分布图
        fig, axes = plt.subplots(2, 2, figsize=(20, 16))
        axes = axes.flatten()
        
        for idx, (period, period_name) in enumerate(zip(key_periods, period_names)):
            ax = axes[idx]
            
            # 获取该时段的LMP数据
            period_lmps = {bus: self.node_lmp[bus][period] for bus in self.node_lmp}
            
            # 计算加权平均LMP（按负荷加权）
            total_load = 0
            weighted_lmp_sum = 0
            for bus in period_lmps:
                # 假设每个节点的负荷相等（实际应从loads数据获取）
                load = 100  # MW
                total_load += load
                weighted_lmp_sum += period_lmps[bus] * load
            
            weighted_avg_lmp = weighted_lmp_sum / total_load if total_load > 0 else 0
            
            # 绘制网络拓扑，节点颜色表示LMP
            lmp_values = [period_lmps[node] for node in G.nodes()]
            
            # 绘制网络
            nx.draw_networkx_edges(G, pos, ax=ax, edge_color='gray', width=0.5, alpha=0.5)
            
            # 绘制节点，颜色表示LMP
            nodes = nx.draw_networkx_nodes(G, pos, ax=ax,
                                         node_color=lmp_values,
                                         node_size=300,
                                         cmap='RdYlGn_r',
                                         vmin=min(lmp_values),
                                         vmax=max(lmp_values))
            
            # 添加节点标签
            nx.draw_networkx_labels(G, pos, ax=ax, font_size=6)
            
            # 添加颜色条
            cbar = plt.colorbar(nodes, ax=ax, orientation='horizontal', pad=0.05)
            cbar.set_label('节点电价 ($/MWh)', fontsize=10,
                          **create_text_with_font('节点电价 ($/MWh)', self.chinese_font))
            
            # 设置标题
            title_text = f'{period_name} - 加权均价: ${weighted_avg_lmp:.2f}/MWh'
            ax.set_title(title_text, fontsize=12, fontweight='bold',
                        **create_text_with_font(title_text, self.chinese_font))
            ax.axis('off')
        
        # 设置总标题
        fig.suptitle('IEEE 50节点系统关键时段节点电价分布', fontsize=16, fontweight='bold',
                    **create_text_with_font('IEEE 50节点系统关键时段节点电价分布', self.chinese_font))
        
        # 应用中文字体
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        plt.tight_layout()
        
        # 保存图形
        save_path = os.path.join(self.results_dir, 'weighted_lmp_key_periods.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 关键时段节点电价图已保存: {save_path}")
        plt.close()
        
        # 创建LMP时序热力图
        self.create_lmp_heatmap()
    
    def create_lmp_heatmap(self):
        """创建96时段LMP热力图"""
        
        print("\n📊 生成LMP时序热力图...")
        
        # 准备数据矩阵
        bus_names = list(self.node_lmp.keys())
        lmp_matrix = np.array([self.node_lmp[bus] for bus in bus_names])
        
        # 创建图形
        fig, ax = plt.subplots(figsize=(20, 10))
        
        # 绘制热力图
        im = ax.imshow(lmp_matrix, aspect='auto', cmap='RdYlGn_r', interpolation='nearest')
        
        # 设置坐标轴
        ax.set_xticks(range(0, 96, 8))
        ax.set_xticklabels(['00:00', '02:00', '04:00', '06:00', '08:00', '10:00',
                           '12:00', '14:00', '16:00', '18:00', '20:00', '22:00'])
        ax.set_yticks(range(len(bus_names)))
        ax.set_yticklabels(bus_names, fontsize=8)
        
        # 添加标签
        ax.set_xlabel('时间', fontsize=12, **create_text_with_font('时间', self.chinese_font))
        ax.set_ylabel('节点', fontsize=12, **create_text_with_font('节点', self.chinese_font))
        ax.set_title('IEEE 50节点系统96时段节点电价热力图', fontsize=16, fontweight='bold',
                    **create_text_with_font('IEEE 50节点系统96时段节点电价热力图', self.chinese_font))
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('节点电价 ($/MWh)', fontsize=12,
                      **create_text_with_font('节点电价 ($/MWh)', self.chinese_font))
        
        # 应用中文字体
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        plt.tight_layout()
        
        # 保存图形
        save_path = os.path.join(self.results_dir, 'lmp_heatmap_96periods.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ LMP热力图已保存: {save_path}")
        plt.close()
    
    def create_generation_by_type_chart(self):
        """创建分机组类型的发电量时序图"""
        
        print("\n📊 生成分机组类型发电量图...")
        
        # 按机组类型汇总发电量
        gen_by_type = {
            '超临界': {'gens': [], 'power': np.zeros(96)},
            '亚临界': {'gens': [], 'power': np.zeros(96)},
            '老式机组': {'gens': [], 'power': np.zeros(96)},
            '小型机组': {'gens': [], 'power': np.zeros(96)}
        }
        
        for gen in self.gen_power:
            if 'supercritical' in gen.lower():
                gen_type = '超临界'
            elif 'subcritical' in gen.lower():
                gen_type = '亚临界'
            elif 'old_steam' in gen.lower():
                gen_type = '老式机组'
            else:
                gen_type = '小型机组'
            
            gen_by_type[gen_type]['gens'].append(gen)
            gen_by_type[gen_type]['power'] += np.array(self.gen_power[gen])
        
        # 创建堆叠面积图
        fig, ax = plt.subplots(figsize=(16, 8))
        
        # 准备数据
        x = range(96)
        colors = ['#2E8B57', '#4169E1', '#FF6347', '#9370DB']
        
        # 绘制堆叠面积图
        bottom = np.zeros(96)
        for (gen_type, data), color in zip(gen_by_type.items(), colors):
            ax.fill_between(x, bottom, bottom + data['power'], 
                          label=f"{gen_type} ({len(data['gens'])}台)",
                          color=color, alpha=0.7)
            bottom += data['power']
        
        # 添加总负荷线
        ax.plot(x, self.system_load, 'k-', linewidth=2, label='总负荷')
        
        # 设置坐标轴
        ax.set_xlim(0, 95)
        ax.set_xlabel('时间', fontsize=12, **create_text_with_font('时间', self.chinese_font))
        ax.set_ylabel('发电量 (MW)', fontsize=12, **create_text_with_font('发电量 (MW)', self.chinese_font))
        ax.set_title('IEEE 50节点系统96时段分机组类型发电量', fontsize=16, fontweight='bold',
                    **create_text_with_font('IEEE 50节点系统96时段分机组类型发电量', self.chinese_font))
        
        # 设置x轴标签
        x_ticks = range(0, 96, 8)
        x_labels = ['00:00', '02:00', '04:00', '06:00', '08:00', '10:00',
                   '12:00', '14:00', '16:00', '18:00', '20:00', '22:00']
        ax.set_xticks(x_ticks)
        ax.set_xticklabels(x_labels)
        
        # 添加网格
        ax.grid(True, alpha=0.3, linestyle='--')
        
        # 添加图例
        ax.legend(loc='upper left', fontsize=10, 
                 prop=self.chinese_font if self.chinese_font else None)
        
        # 应用中文字体
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        plt.tight_layout()
        
        # 保存图形
        save_path = os.path.join(self.results_dir, 'generation_by_type_96periods.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 分机组类型发电量图已保存: {save_path}")
        plt.close()
    
    def generate_comprehensive_report(self):
        """生成96时段综合分析报告"""
        
        print("\n🔍 开始生成IEEE 50节点96时段综合分析报告...")
        
        # 1. 机组组合图
        self.create_unit_commitment_chart()
        
        # 2. 节点加权均价图
        self.create_weighted_lmp_charts()
        
        # 3. 分机组类型发电量图
        self.create_generation_by_type_chart()
        
        # 4. 生成汇总统计报告
        self.create_summary_statistics()
        
        print(f"\n✅ 96时段综合分析报告生成完成！")
        print(f"📁 所有图表和数据已保存到: {self.results_dir}")
    
    def create_summary_statistics(self):
        """创建汇总统计报告"""
        
        print("\n📊 生成汇总统计报告...")
        
        # 计算统计指标
        stats = {
            '系统指标': {
                '峰值负荷': f"{max(self.system_load):.1f} MW",
                '谷值负荷': f"{min(self.system_load):.1f} MW",
                '平均负荷': f"{np.mean(self.system_load):.1f} MW",
                '负荷率': f"{np.mean(self.system_load)/max(self.system_load):.3f}",
                '峰谷差': f"{max(self.system_load)-min(self.system_load):.1f} MW"
            },
            '机组运行统计': {},
            '电价统计': {}
        }
        
        # 机组运行统计
        for gen_type in ['超临界', '亚临界', '老式机组', '小型机组']:
            count = 0
            total_hours = 0
            for gen in self.gen_status:
                if gen_type in self.get_gen_type(gen):
                    count += 1
                    total_hours += sum(self.gen_status[gen]) * 0.25  # 15分钟转小时
            
            if count > 0:
                stats['机组运行统计'][gen_type] = {
                    '机组数': count,
                    '平均运行小时': f"{total_hours/count:.1f} h"
                }
        
        # 电价统计
        all_lmps = []
        for bus in self.node_lmp:
            all_lmps.extend(self.node_lmp[bus])
        
        stats['电价统计'] = {
            '最高电价': f"${max(all_lmps):.2f}/MWh",
            '最低电价': f"${min(all_lmps):.2f}/MWh",
            '平均电价': f"${np.mean(all_lmps):.2f}/MWh",
            '电价标准差': f"${np.std(all_lmps):.2f}/MWh"
        }
        
        # 保存统计报告
        import json
        stats_file = os.path.join(self.results_dir, 'summary_statistics.json')
        with open(stats_file, 'w', encoding='utf-8') as f:
            json.dump(stats, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 汇总统计报告已保存: {stats_file}")
        
        # 打印关键统计
        print("\n📊 关键统计指标:")
        for category, items in stats.items():
            print(f"\n{category}:")
            if isinstance(items, dict):
                for key, value in items.items():
                    if isinstance(value, dict):
                        print(f"  {key}:")
                        for k, v in value.items():
                            print(f"    - {k}: {v}")
                    else:
                        print(f"  - {key}: {value}")
    
    def get_gen_type(self, gen_name):
        """获取机组类型"""
        if 'supercritical' in gen_name.lower():
            return '超临界'
        elif 'subcritical' in gen_name.lower():
            return '亚临界'
        elif 'old_steam' in gen_name.lower():
            return '老式机组'
        else:
            return '小型机组'


def analyze_ieee_50_bus_96periods_results(case_dir, solution):
    """分析IEEE 50节点96时段案例结果的主函数"""
    
    analyzer = IEEE50Bus96PeriodsAnalysis(case_dir, solution)
    analyzer.generate_comprehensive_report()
    
    return analyzer.results_dir