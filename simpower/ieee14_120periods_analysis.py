"""
IEEE 14节点120时段(5天)分析模块
"""

import os
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from datetime import datetime, timedelta

from simpower.ieee14_analysis import IEEE14Analysis, get_chinese_font, apply_chinese_font_to_figure


class IEEE14_120PeriodsAnalysis(IEEE14Analysis):
    """IEEE 14节点120时段分析类"""
    
    def __init__(self, case_dir, solution):
        super().__init__(case_dir, solution)
        self.periods = 120
        self.days = 5
        self.hours_per_day = 24
        
    def generate_full_report(self):
        """生成完整分析报告"""
        
        print(f"\n🔍 开始生成IEEE 14节点{self.periods}时段（{self.days}天）完整分析报告...")
        
        # 创建结果目录
        results_dir = os.path.join(self.case_dir, 'results')
        os.makedirs(results_dir, exist_ok=True)
        
        # 1. 网络拓扑图
        self.create_network_topology()
        
        # 2. 负荷曲线
        self.create_load_curve()
        
        # 3. 机组组合图
        self.create_unit_commitment()
        
        # 4. 机组出力图
        self.create_generation_dispatch()
        
        # 5. 节点电价图
        self.create_nodal_prices()
        
        # 6. 费用分析
        self.create_cost_report()
        
        # 7. 边际机组分析
        self.analyze_marginal_units()
        
        # 8. 机组启停分析
        self.analyze_unit_commitment_events()
        
        # 9. 煤电机组性能分析
        self.analyze_coal_performance()
        
        print(f"\n✅ {self.periods}时段分析报告生成完成！")
        print(f"📁 所有结果保存在: {results_dir}")
        
    def create_load_curve(self):
        """创建负荷曲线图 - 5天版本"""
        
        print("\n📈 生成5天负荷曲线...")
        
        fig, ax = plt.subplots(figsize=(16, 8))
        chinese_font = get_chinese_font()
        
        # 准备数据
        hours = list(range(self.periods))
        total_loads = []
        
        # 计算每时段总负荷
        for t in range(self.periods):
            total_load = sum(self.solution.loads_power[t])
            total_loads.append(total_load)
        
        # 绘制负荷曲线
        ax.plot(hours, total_loads, 'b-', linewidth=2, label='系统负荷')
        
        # 添加日分界线
        for day in range(1, self.days):
            ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
        
        # 标注每天
        day_names = ['第1天', '第2天', '第3天', '第4天', '第5天']
        for day in range(self.days):
            ax.text((day+0.5)*24, max(total_loads)*1.02, day_names[day], 
                   ha='center', fontsize=12, fontfamily=chinese_font.get_name() if chinese_font else None)
        
        # 标注峰谷值
        max_load = max(total_loads)
        min_load = min(total_loads)
        max_idx = total_loads.index(max_load)
        min_idx = total_loads.index(min_load)
        
        ax.plot(max_idx, max_load, 'ro', markersize=10)
        ax.plot(min_idx, min_load, 'go', markersize=10)
        
        ax.annotate(f'峰值: {max_load:.1f} MW\n第{max_idx//24+1}天{max_idx%24}时', 
                   xy=(max_idx, max_load), xytext=(max_idx+5, max_load+20),
                   arrowprops=dict(arrowstyle='->', color='red'),
                   fontsize=10, fontfamily=chinese_font.get_name() if chinese_font else None)
        
        ax.annotate(f'谷值: {min_load:.1f} MW\n第{min_idx//24+1}天{min_idx%24}时', 
                   xy=(min_idx, min_load), xytext=(min_idx+5, min_load-40),
                   arrowprops=dict(arrowstyle='->', color='green'),
                   fontsize=10, fontfamily=chinese_font.get_name() if chinese_font else None)
        
        # 设置标签
        ax.set_xlabel('时间 (小时)', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax.set_ylabel('负荷 (MW)', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax.set_title('5天系统负荷曲线', fontsize=16, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax.grid(True, alpha=0.3)
        ax.set_xlim(0, self.periods-1)
        
        # 添加统计信息
        avg_load = np.mean(total_loads)
        ax.axhline(y=avg_load, color='orange', linestyle=':', alpha=0.8, label=f'平均负荷: {avg_load:.1f} MW')
        ax.legend(loc='upper right', prop={'family': chinese_font.get_name() if chinese_font else None})
        
        apply_chinese_font_to_figure(fig, chinese_font)
        plt.tight_layout()
        
        # 保存图片
        output_path = os.path.join(self.case_dir, 'results', 'load_curve_5days.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_unit_commitment(self):
        """创建机组组合图 - 120时段版本"""
        
        print("\n⚡ 生成120时段机组组合图...")
        
        # 使用更大的图形
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(20, 12), height_ratios=[3, 1])
        chinese_font = get_chinese_font()
        
        # 准备数据
        gen_names = [gen['name'] for gen in self.generators]
        n_gens = len(gen_names)
        
        # 创建状态矩阵
        status_matrix = np.zeros((n_gens, self.periods))
        for t in range(self.periods):
            for g in range(n_gens):
                status_matrix[g, t] = self.solution.generators_status[t][g]
        
        # 绘制机组状态热力图
        im = ax1.imshow(status_matrix, aspect='auto', cmap='RdYlGn', 
                       interpolation='nearest', vmin=0, vmax=1)
        
        # 设置y轴标签
        ax1.set_yticks(range(n_gens))
        ax1.set_yticklabels(gen_names)
        
        # 设置x轴 - 每12小时一个标记
        x_ticks = list(range(0, self.periods, 12))
        x_labels = []
        for tick in x_ticks:
            day = tick // 24 + 1
            hour = tick % 24
            x_labels.append(f'D{day}-{hour}h')
        
        ax1.set_xticks(x_ticks)
        ax1.set_xticklabels(x_labels, rotation=45)
        
        # 添加日分界线
        for day in range(1, self.days):
            ax1.axvline(x=day*24-0.5, color='white', linewidth=2)
        
        # 标题和标签
        ax1.set_title('120时段机组启停状态 (绿色=开机, 红色=停机)', 
                     fontsize=16, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax1.set_xlabel('时间', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax1.set_ylabel('发电机组', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax1, orientation='horizontal', pad=0.1, shrink=0.5)
        cbar.set_label('机组状态', fontsize=12, fontfamily=chinese_font.get_name() if chinese_font else None)
        cbar.set_ticks([0, 1])
        cbar.set_ticklabels(['停机', '开机'])
        
        # 统计每时段开机台数
        units_online = np.sum(status_matrix, axis=0)
        ax2.plot(range(self.periods), units_online, 'b-', linewidth=2)
        ax2.fill_between(range(self.periods), 0, units_online, alpha=0.3)
        
        # 添加日分界线
        for day in range(1, self.days):
            ax2.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
        
        ax2.set_xlim(0, self.periods-1)
        ax2.set_ylim(0, n_gens+0.5)
        ax2.set_xlabel('时间 (小时)', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax2.set_ylabel('在线机组数', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax2.set_title('在线机组数量变化', fontsize=14, fontfamily=chinese_font.get_name() if chinese_font else None)
        ax2.grid(True, alpha=0.3)
        
        # 设置x轴
        ax2.set_xticks(list(range(0, self.periods, 12)))
        ax2.set_xticklabels(x_labels, rotation=45)
        
        apply_chinese_font_to_figure(fig, chinese_font)
        plt.tight_layout()
        
        # 保存图片
        output_path = os.path.join(self.case_dir, 'results', 'unit_commitment_120h.png')
        plt.savefig(output_path, dpi=150, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def analyze_unit_commitment_events(self):
        """分析机组启停事件"""
        
        print("\n🔄 分析机组启停事件...")
        
        # 统计启停次数
        startup_events = []
        shutdown_events = []
        
        gen_names = [gen['name'] for gen in self.generators]
        n_gens = len(gen_names)
        
        for g in range(n_gens):
            startups = 0
            shutdowns = 0
            startup_times = []
            shutdown_times = []
            
            for t in range(1, self.periods):
                prev_status = self.solution.generators_status[t-1][g]
                curr_status = self.solution.generators_status[t][g]
                
                if prev_status == 0 and curr_status == 1:
                    startups += 1
                    startup_times.append(t)
                elif prev_status == 1 and curr_status == 0:
                    shutdowns += 1
                    shutdown_times.append(t)
            
            if startups > 0 or shutdowns > 0:
                startup_events.append({
                    'generator': gen_names[g],
                    'startups': startups,
                    'shutdowns': shutdowns,
                    'startup_times': startup_times,
                    'shutdown_times': shutdown_times
                })
        
        # 创建报告
        report = {
            '启停事件统计': {
                '总启动次数': sum(e['startups'] for e in startup_events),
                '总停机次数': sum(e['shutdowns'] for e in startup_events),
                '发生启停的机组数': len(startup_events)
            },
            '机组启停详情': []
        }
        
        for event in startup_events:
            detail = {
                '机组': event['generator'],
                '启动次数': event['startups'],
                '停机次数': event['shutdowns'],
                '启动时刻': [f'第{t//24+1}天{t%24}时' for t in event['startup_times']],
                '停机时刻': [f'第{t//24+1}天{t%24}时' for t in event['shutdown_times']]
            }
            report['机组启停详情'].append(detail)
        
        # 保存报告
        output_path = os.path.join(self.case_dir, 'results', 'unit_commitment_events.json')
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 启停事件报告保存到: {output_path}")
        
        # 打印摘要
        print(f"\n启停事件摘要:")
        print(f"  总启动次数: {report['启停事件统计']['总启动次数']}")
        print(f"  总停机次数: {report['启停事件统计']['总停机次数']}")
        print(f"  发生启停的机组: {report['启停事件统计']['发生启停的机组数']}台")
        
        if startup_events:
            print("\n  详细情况:")
            for event in startup_events:
                print(f"    {event['generator']}: 启动{event['startups']}次, 停机{event['shutdowns']}次")
        
    def analyze_coal_performance(self):
        """分析煤电机组5天运行性能"""
        
        print("\n⚙️ 分析煤电机组性能...")
        
        performance_data = []
        
        for g, gen in enumerate(self.generators):
            # 统计运行小时数
            hours_online = sum(self.solution.generators_status[t][g] for t in range(self.periods))
            
            # 统计总发电量
            total_generation = sum(self.solution.generators_power[t][g] 
                                 for t in range(self.periods) 
                                 if self.solution.generators_status[t][g] > 0)
            
            # 计算容量因子
            capacity_factor = (total_generation / self.periods) / gen['pmax'] * 100
            
            # 统计启停次数
            startups = 0
            shutdowns = 0
            for t in range(1, self.periods):
                if self.solution.generators_status[t-1][g] == 0 and self.solution.generators_status[t][g] == 1:
                    startups += 1
                elif self.solution.generators_status[t-1][g] == 1 and self.solution.generators_status[t][g] == 0:
                    shutdowns += 1
            
            # 计算平均运行时长
            if hours_online > 0:
                # 简化计算：连续运行段的平均长度
                avg_run_length = hours_online / max(1, startups + 1)  # +1 for initial state
            else:
                avg_run_length = 0
            
            performance_data.append({
                '机组': gen['name'],
                '容量(MW)': gen['pmax'],
                '容量因子(%)': round(capacity_factor, 1),
                '运行小时数': hours_online,
                '启动次数': startups,
                '停机次数': shutdowns,
                '平均运行时长(h)': round(avg_run_length, 1),
                '总发电量(MWh)': round(total_generation, 1)
            })
        
        # 创建DataFrame
        performance_df = pd.DataFrame(performance_data)
        performance_df = performance_df.set_index('机组')
        
        # 保存CSV
        output_path = os.path.join(self.case_dir, 'results', 'coal_performance_5days.csv')
        performance_df.to_csv(output_path, encoding='utf-8-sig')
        
        print(f"✅ 煤电机组性能报告保存到: {output_path}")
        
        # 打印摘要
        print("\n煤电机组性能摘要:")
        print(performance_df.to_string())
        
        # 按容量分组统计
        print("\n\n按机组类型统计:")
        
        # 大型基荷机组
        large_units = ['G1', 'G2', 'G3']
        large_perf = performance_df.loc[performance_df.index.isin(large_units)]
        print(f"\n大型基荷机组 ({', '.join(large_units)}):")
        print(f"  平均容量因子: {large_perf['容量因子(%)'].mean():.1f}%")
        print(f"  平均运行时间: {large_perf['运行小时数'].mean():.1f}小时")
        print(f"  总启停次数: {large_perf['启动次数'].sum() + large_perf['停机次数'].sum()}次")
        
        # 中型机组
        medium_units = ['G4', 'G5', 'G6']
        medium_perf = performance_df.loc[performance_df.index.isin(medium_units)]
        print(f"\n中型负荷跟踪机组 ({', '.join(medium_units)}):")
        print(f"  平均容量因子: {medium_perf['容量因子(%)'].mean():.1f}%")
        print(f"  平均运行时间: {medium_perf['运行小时数'].mean():.1f}小时")
        print(f"  总启停次数: {medium_perf['启动次数'].sum() + medium_perf['停机次数'].sum()}次")
        
        # 小型调峰机组
        small_units = ['G7', 'G8', 'G9']
        small_perf = performance_df.loc[performance_df.index.isin(small_units)]
        print(f"\n小型调峰机组 ({', '.join(small_units)}):")
        print(f"  平均容量因子: {small_perf['容量因子(%)'].mean():.1f}%")
        print(f"  平均运行时间: {small_perf['运行小时数'].mean():.1f}小时")
        print(f"  总启停次数: {small_perf['启动次数'].sum() + small_perf['停机次数'].sum()}次")