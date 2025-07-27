"""
IEEE 50节点案例96时段结果分析模块
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from simpower.results_analysis import get_chinese_font, apply_chinese_font_to_figure


class IEEE50Bus96PeriodsAnalysis:
    """IEEE 50节点96时段仿真结果分析类"""
    
    def __init__(self, case_dir, solution):
        self.case_dir = case_dir
        self.solution = solution
        self.results_dir = os.path.join(case_dir, 'results_96periods')
        os.makedirs(self.results_dir, exist_ok=True)
        self.chinese_font = get_chinese_font()
        
    def extract_96periods_results(self):
        """提取96时段的仿真结果"""
        print("\n📊 提取96时段仿真结果...")
        
        # 提取发电机状态和出力
        self.gen_status = self.solution['Status']  # 机组开停状态
        self.gen_power = self.solution['Power']    # 机组出力
        
        # 获取时间索引
        self.time_periods = self.gen_status.index
        self.num_periods = len(self.time_periods)
        
        print(f"✅ 成功提取{self.num_periods}个时段的数据")
        
    def create_unit_commitment_chart(self):
        """生成96时段机组组合图"""
        print("\n📊 生成机组组合图...")
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10), sharex=True)
        
        # 1. 机组开停状态热力图
        status_data = self.gen_status.T.values
        im1 = ax1.imshow(status_data, aspect='auto', cmap='RdYlGn', 
                         interpolation='nearest', vmin=0, vmax=1)
        
        ax1.set_yticks(range(len(self.gen_status.columns)))
        ax1.set_yticklabels(self.gen_status.columns)
        ax1.set_title('96时段机组开停状态', fontproperties=self.chinese_font, fontsize=14)
        ax1.set_ylabel('发电机组', fontproperties=self.chinese_font)
        
        # 添加颜色条
        cbar1 = plt.colorbar(im1, ax=ax1, orientation='vertical', pad=0.02)
        cbar1.set_label('状态 (0=停机, 1=运行)', fontproperties=self.chinese_font)
        
        # 2. 总发电量曲线
        total_gen = self.gen_power.sum(axis=1)
        hours = np.arange(len(self.time_periods)) * 0.25  # 15分钟间隔
        
        ax2.plot(hours, total_gen, 'b-', linewidth=2)
        ax2.fill_between(hours, 0, total_gen, alpha=0.3)
        ax2.set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
        ax2.set_ylabel('总发电量 (MW)', fontproperties=self.chinese_font)
        ax2.set_title('96时段总发电量曲线', fontproperties=self.chinese_font, fontsize=14)
        ax2.grid(True, alpha=0.3)
        
        # 设置x轴
        ax2.set_xlim(0, 24)
        ax2.set_xticks(range(0, 25, 3))
        
        plt.tight_layout()
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'unit_commitment_96periods.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 机组组合图已保存: {output_path}")
        
    def create_weighted_lmp_charts(self):
        """生成关键时段的节点加权均价图"""
        print("\n💰 生成节点加权均价图...")
        
        # 选择关键时段：早高峰、午间、晚高峰、深夜
        key_periods = {
            '深夜低谷 (03:00)': 12,   # 第12个15分钟 = 3:00
            '早高峰 (08:00)': 32,     # 第32个15分钟 = 8:00
            '午间 (12:00)': 48,       # 第48个15分钟 = 12:00
            '晚高峰 (19:00)': 76      # 第76个15分钟 = 19:00
        }
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        axes = axes.flatten()
        
        for idx, (period_name, period_idx) in enumerate(key_periods.items()):
            ax = axes[idx]
            
            # 获取该时段的LMP数据
            if hasattr(self.solution, 'LMP') and period_idx < len(self.solution.LMP):
                lmp_data = self.solution.LMP.iloc[period_idx]
                
                # 绘制LMP分布
                ax.hist(lmp_data, bins=20, alpha=0.7, color='blue', edgecolor='black')
                ax.axvline(lmp_data.mean(), color='red', linestyle='--', linewidth=2,
                          label=f'平均值: {lmp_data.mean():.2f} $/MWh')
                
                ax.set_xlabel('节点电价 ($/MWh)', fontproperties=self.chinese_font)
                ax.set_ylabel('节点数量', fontproperties=self.chinese_font)
                ax.set_title(f'{period_name} LMP分布', fontproperties=self.chinese_font)
                ax.legend(prop={'family': self.chinese_font.get_name()})
                ax.grid(True, alpha=0.3)
            else:
                # 如果没有LMP数据，生成模拟数据
                np.random.seed(period_idx)
                lmp_data = np.random.normal(50 + period_idx/2, 10, 50)
                ax.text(0.5, 0.5, '暂无LMP数据', ha='center', va='center',
                       transform=ax.transAxes, fontproperties=self.chinese_font,
                       fontsize=14)
        
        plt.suptitle('96时段关键时刻节点加权均价分布', fontproperties=self.chinese_font, fontsize=16)
        plt.tight_layout()
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'weighted_lmp_key_periods.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 节点加权均价图已保存: {output_path}")
        
    def create_generation_by_type_chart(self):
        """生成分机组类型发电量图"""
        print("\n⚡ 生成分机组类型发电量图...")
        
        # 定义机组类型（简化分类）
        gen_types = {
            'Coal': ['g0', 'g1', 'g2', 'g3', 'g4', 'g5'],
            'Gas': ['g6', 'g7', 'g8', 'g9', 'g10', 'g11', 'g12', 'g13'],
            'Hydro': ['g14', 'g15', 'g16', 'g17'],
            'Other': ['g18', 'g19', 'g20', 'g21', 'g22', 'g23', 'g24', 'g25']
        }
        
        fig, ax = plt.subplots(figsize=(14, 8))
        
        hours = np.arange(len(self.time_periods)) * 0.25
        bottom = np.zeros(len(self.time_periods))
        
        colors = ['#8B4513', '#4169E1', '#00CED1', '#FFD700']
        
        for (gen_type, gens), color in zip(gen_types.items(), colors):
            # 计算该类型机组的总发电量
            type_gens = [g for g in gens if g in self.gen_power.columns]
            if type_gens:
                type_power = self.gen_power[type_gens].sum(axis=1)
                ax.fill_between(hours, bottom, bottom + type_power, 
                               label=gen_type, color=color, alpha=0.7)
                bottom += type_power
        
        ax.set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
        ax.set_ylabel('发电量 (MW)', fontproperties=self.chinese_font)
        ax.set_title('96时段分机组类型发电量', fontproperties=self.chinese_font, fontsize=14)
        ax.legend(prop={'family': self.chinese_font.get_name()})
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, 24)
        ax.set_xticks(range(0, 25, 3))
        
        plt.tight_layout()
        apply_chinese_font_to_figure(fig, self.chinese_font)
        
        output_path = os.path.join(self.results_dir, 'generation_by_type_96periods.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 分机组类型发电量图已保存: {output_path}")
        
    def create_summary_statistics(self):
        """生成96时段统计汇总"""
        print("\n📊 生成统计汇总报告...")
        
        summary = {
            '仿真概况': {
                '总时段数': self.num_periods,
                '时间间隔': '15分钟',
                '总时长': '24小时'
            },
            '发电统计': {
                '平均总发电量': f"{self.gen_power.sum(axis=1).mean():.2f} MW",
                '峰值发电量': f"{self.gen_power.sum(axis=1).max():.2f} MW",
                '谷值发电量': f"{self.gen_power.sum(axis=1).min():.2f} MW",
                '峰谷差': f"{self.gen_power.sum(axis=1).max() - self.gen_power.sum(axis=1).min():.2f} MW"
            },
            '机组运行统计': {
                '平均运行机组数': f"{self.gen_status.sum(axis=1).mean():.1f}",
                '最多运行机组数': int(self.gen_status.sum(axis=1).max()),
                '最少运行机组数': int(self.gen_status.sum(axis=1).min())
            }
        }
        
        # 保存JSON格式
        output_path = os.path.join(self.results_dir, 'summary_statistics.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(summary, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 统计汇总已保存: {output_path}")
        
        # 打印汇总
        for category, stats in summary.items():
            print(f"\n{category}:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
    def generate_comprehensive_report(self):
        """生成96时段综合分析报告"""
        print("\n🔍 开始生成IEEE 50节点96时段综合分析报告...")
        
        # 提取结果数据
        self.extract_96periods_results()
        
        # 生成各类图表
        self.create_unit_commitment_chart()
        self.create_weighted_lmp_charts()
        self.create_generation_by_type_chart()
        self.create_summary_statistics()
        
        print(f"\n✅ 96时段综合分析报告生成完成！")
        print(f"📁 所有图表和数据已保存到: {self.results_dir}")
        

def analyze_ieee_50_bus_96periods_results(case_dir, solution):
    """96时段结果分析主函数"""
    analyzer = IEEE50Bus96PeriodsAnalysis(case_dir, solution)
    analyzer.generate_comprehensive_report()
    return analyzer.results_dir