"""
IEEE 14节点72时段（3天）分析模块
"""

import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta

from .ieee14_12periods_analysis import IEEE14Analysis


class IEEE14_72PeriodsAnalysis(IEEE14Analysis):
    """IEEE 14节点72时段分析类"""
    
    def __init__(self, case_dir, solution):
        # 先设置基本属性
        self.case_dir = case_dir
        self.solution = solution
        self.periods = 72
        self.days = 3
        
        # 加载案例数据
        self.load_case_data()
        
        # 获取中文字体
        from .results_analysis import get_chinese_font
        self.chinese_font = get_chinese_font()
        
        # 创建结果目录
        self.results_dir = os.path.join(case_dir, 'results')
        if not os.path.exists(self.results_dir):
            os.makedirs(self.results_dir)
            
    def get_generator_data(self, data_type='power'):
        """获取发电机数据，兼容多阶段解"""
        try:
            if hasattr(self.solution, 'generators_power') and data_type == 'power':
                return self.solution.generators_power
            elif hasattr(self.solution, 'generators_status') and data_type == 'status':
                return self.solution.generators_status
            else:
                # 尝试使用gen_time_df方法
                return self.solution.gen_time_df(data_type)
        except:
            return None
        
    def create_load_curve(self):
        """生成3天的负荷曲线"""
        print("\n📈 生成3天负荷曲线...")
        
        # 获取总负荷数据
        total_loads = []
        times = []
        
        start_time = datetime(2025, 1, 15, 0, 0, 0)
        
        for t_idx in range(self.periods):
            time = start_time + timedelta(hours=t_idx)
            times.append(time)
            
            # 计算该时段的总负荷
            total_load = 0
            for _, load_row in self.loads_df.iterrows():
                load_file = os.path.join(self.case_dir, f"{load_row['name']}_timeseries.csv")
                if os.path.exists(load_file):
                    ts_df = pd.read_csv(load_file)
                    if t_idx < len(ts_df):
                        total_load += ts_df.iloc[t_idx]['power']
            
            total_loads.append(total_load)
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(14, 6))
        
        # 绘制负荷曲线
        ax.plot(times, total_loads, 'b-', linewidth=2, label='系统总负荷')
        
        # 标记每天的峰值
        for day in range(self.days):
            day_start = day * 24
            day_end = (day + 1) * 24
            day_loads = total_loads[day_start:day_end]
            day_times = times[day_start:day_end]
            
            peak_idx = np.argmax(day_loads)
            peak_load = day_loads[peak_idx]
            peak_time = day_times[peak_idx]
            
            ax.plot(peak_time, peak_load, 'ro', markersize=8)
            ax.annotate(f'Day{day+1}峰值\\n{peak_load:.1f}MW', 
                       xy=(peak_time, peak_load), 
                       xytext=(10, 10), 
                       textcoords='offset points',
                       fontproperties=self.chinese_font,
                       bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        # 设置x轴日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:00'))
        ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
        plt.xticks(rotation=45)
        
        ax.set_xlabel('时间', fontproperties=self.chinese_font)
        ax.set_ylabel('负荷 (MW)', fontproperties=self.chinese_font)
        ax.set_title('72时段（3天）系统负荷曲线', fontproperties=self.chinese_font, fontsize=14)
        ax.grid(True, alpha=0.3)
        ax.legend(prop=self.chinese_font)
        
        # 添加日分隔线
        for day in range(1, self.days):
            day_time = start_time + timedelta(days=day)
            ax.axvline(x=day_time, color='gray', linestyle='--', alpha=0.5)
            ax.text(day_time, ax.get_ylim()[1], f'Day {day+1}', 
                   ha='center', va='bottom', fontproperties=self.chinese_font)
        
        plt.tight_layout()
        
        output_path = os.path.join(self.results_dir, 'load_curve_3days.png')
        plt.savefig(output_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"✅ 保存到: {output_path}")
        
    def create_unit_commitment(self):
        """生成72时段机组组合状态图"""
        print("\n⚡ 生成72时段机组组合图...")
        
        try:
            # 获取机组状态数据
            status_df = self.get_generator_data('status')
            if status_df is None:
                print("❌ 无机组状态数据")
                return
                
            # 创建3个子图，每个代表一天
            fig, axes = plt.subplots(3, 1, figsize=(14, 12), sharex=True)
            
            gen_names = [f'G{i+1}' for i in range(len(self.generators_df))]
            
            for day in range(self.days):
                ax = axes[day]
                
                # 获取该天的数据
                day_start = day * 24
                day_end = (day + 1) * 24
                day_status = status_df.iloc[day_start:day_end].values.T
                
                # 绘制热力图
                im = ax.imshow(day_status, aspect='auto', cmap='RdYlGn', 
                             interpolation='nearest', vmin=0, vmax=1)
                
                # 设置坐标轴
                ax.set_yticks(range(len(gen_names)))
                ax.set_yticklabels(gen_names)
                ax.set_xticks(range(24))
                ax.set_xticklabels([f'{h}:00' for h in range(24)])
                
                # 添加网格
                ax.set_xticks(np.arange(25)-0.5, minor=True)
                ax.set_yticks(np.arange(len(gen_names)+1)-0.5, minor=True)
                ax.grid(which='minor', color='gray', linestyle='-', linewidth=0.5)
                
                ax.set_ylabel(f'Day {day+1}', fontproperties=self.chinese_font, fontsize=12)
                
                # 添加启停次数统计
                starts = 0
                for gen_idx in range(len(gen_names)):
                    gen_status = day_status[gen_idx]
                    starts += np.sum(np.diff(np.concatenate([[0], gen_status])) > 0)
                
                ax.text(1.01, 0.5, f'启动次数: {starts}', 
                       transform=ax.transAxes, va='center',
                       fontproperties=self.chinese_font)
            
            axes[-1].set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
            fig.suptitle('72时段（3天）煤电机组组合状态', 
                        fontproperties=self.chinese_font, fontsize=16)
            
            # 添加颜色条
            cbar = fig.colorbar(im, ax=axes, pad=0.1)
            cbar.set_label('机组状态 (0=停机, 1=运行)', fontproperties=self.chinese_font)
            
            plt.tight_layout()
            
            output_path = os.path.join(self.results_dir, 'unit_commitment_3days.png')
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 保存到: {output_path}")
            
        except AttributeError:
            print("❌ 无机组状态数据")
            
    def analyze_coal_performance(self):
        """分析煤电机组性能"""
        print("\n⚙️ 分析煤电机组性能...")
        
        try:
            # 获取出力数据
            power_df = self.get_generator_data('power')
            status_df = self.get_generator_data('status')
            
            # 计算各机组的性能指标
            performance = {}
            
            for gen_idx, gen in self.generators_df.iterrows():
                gen_name = gen['name']
                gen_col = f'g{gen_idx}'
                
                if gen_col in power_df.columns:
                    # 容量因子
                    avg_power = power_df[gen_col].mean()
                    capacity_factor = avg_power / gen['P max']
                    
                    # 运行小时数
                    running_hours = status_df[gen_col].sum()
                    
                    # 启停次数
                    status = status_df[gen_col].values
                    starts = np.sum(np.diff(np.concatenate([[0], status])) > 0)
                    
                    # 平均运行时长
                    if starts > 0:
                        avg_run_time = running_hours / starts
                    else:
                        avg_run_time = running_hours
                    
                    performance[gen_name] = {
                        '容量(MW)': gen['P max'],
                        '容量因子(%)': round(capacity_factor * 100, 1),
                        '运行小时数': int(running_hours),
                        '启停次数': starts,
                        '平均运行时长(h)': round(avg_run_time, 1)
                    }
            
            # 创建性能报告
            perf_df = pd.DataFrame(performance).T
            
            output_path = os.path.join(self.results_dir, 'coal_performance.csv')
            perf_df.to_csv(output_path, encoding='utf-8')
            
            print(f"✅ 煤电机组性能报告保存到: {output_path}")
            
            # 打印摘要
            print("\n煤电机组性能摘要:")
            print(perf_df)
            
        except Exception as e:
            print(f"❌ 性能分析失败: {str(e)}")
            
    def create_generation_dispatch(self):
        """生成机组出力图"""
        print("\n⚙️ 生成机组出力图...")
        
        try:
            # 获取出力数据
            power_df = self.get_generator_data('power')
            if power_df is None:
                print("❌ 无机组出力数据")
                return
                
            # 转换数据格式
            hours = list(range(self.periods))
            gen_names = [f'G{i+1}' for i in range(len(self.generators_df))]
            
            fig, ax = plt.subplots(figsize=(14, 8))
            
            # 堆叠面积图
            power_data = []
            for i in range(len(self.generators_df)):
                if f'g{i}' in power_df.columns:
                    power_data.append(power_df[f'g{i}'].values)
                else:
                    power_data.append(power_df.iloc[:, i].values)
                    
            ax.stackplot(hours, *power_data, labels=gen_names, alpha=0.8)
            
            ax.set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
            ax.set_ylabel('发电量 (MW)', fontproperties=self.chinese_font)
            ax.set_title('72时段机组出力堆叠图', fontproperties=self.chinese_font, fontsize=14)
            ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1))
            ax.grid(True, alpha=0.3)
            
            # 添加日分隔线
            for day in range(1, self.days):
                ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
            
            plt.tight_layout()
            
            output_path = os.path.join(self.results_dir, 'generation_dispatch.png')
            plt.savefig(output_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"✅ 保存到: {output_path}")
        except Exception as e:
            print(f"❌ 机组出力数据错误: {str(e)}")
            
    def create_nodal_prices(self):
        """生成节点电价图"""
        print("\n💰 生成节点电价图...")
        
        try:
            # 获取电价数据
            if hasattr(self.solution, 'lmps'):
                lmp_data = self.solution.lmps
                
                # 创建电价数据框
                lmp_df = pd.DataFrame(lmp_data).T
                hours = list(range(len(lmp_df)))
                
                fig, ax = plt.subplots(figsize=(14, 6))
                
                # 绘制平均电价曲线
                avg_lmp = lmp_df.mean(axis=1)
                ax.plot(hours, avg_lmp, 'b-', linewidth=2, label='系统平均电价')
                
                ax.set_xlabel('时间 (小时)', fontproperties=self.chinese_font)
                ax.set_ylabel('节点电价 ($/MWh)', fontproperties=self.chinese_font)
                ax.set_title('72时段系统平均节点电价', fontproperties=self.chinese_font, fontsize=14)
                ax.grid(True, alpha=0.3)
                ax.legend(prop=self.chinese_font)
                
                # 添加日分隔线
                for day in range(1, self.days):
                    ax.axvline(x=day*24, color='gray', linestyle='--', alpha=0.5)
                
                plt.tight_layout()
                
                output_path = os.path.join(self.results_dir, 'nodal_prices.png')
                plt.savefig(output_path, dpi=300, bbox_inches='tight')
                plt.close()
                
                print(f"✅ 保存到: {output_path}")
            else:
                print("❌ 无节点电价数据")
        except Exception as e:
            print(f"❌ 节点电价分析失败: {str(e)}")
            
    def calculate_total_costs(self):
        """计算总费用"""
        print("\n💵 计算系统总费用...")
        
        try:
            # 从solution对象获取费用信息
            total_cost = self.solution.objective if hasattr(self.solution, 'objective') else 0
            
            # 创建费用汇总
            cost_report = {
                '费用明细': {
                    '总费用': f"${total_cost:,.2f}",
                    '发电总费用': f"${total_cost:,.2f}"
                },
                '仿真信息': {
                    '仿真时段数': self.periods,
                    '仿真天数': self.days,
                    '机组数量': len(self.generators_df),
                    '机组类型': '全部为煤电机组'
                }
            }
            
            # 添加容量段报价信息
            if 'costcurvepointsfilename' in self.generators_df.columns:
                bid_info = {}
                for _, gen in self.generators_df.iterrows():
                    gen_name = gen['name']
                    bid_file = gen['costcurvepointsfilename']
                    try:
                        bid_df = pd.read_csv(os.path.join(self.case_dir, bid_file))
                        bid_info[gen_name] = {
                            '容量段数': len(bid_df) - 1,
                            '最低报价($/MWh)': f"{(bid_df['cost'].iloc[1] - bid_df['cost'].iloc[0]) / (bid_df['power'].iloc[1] - bid_df['power'].iloc[0]):.2f}",
                            '最高报价($/MWh)': f"{(bid_df['cost'].iloc[-1] - bid_df['cost'].iloc[-2]) / (bid_df['power'].iloc[-1] - bid_df['power'].iloc[-2]):.2f}"
                        }
                    except:
                        pass
                
                if bid_info:
                    cost_report['容量段报价信息'] = bid_info
            
            # 保存报告
            output_path = os.path.join(self.results_dir, 'cost_report.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                import json
                json.dump(cost_report, f, ensure_ascii=False, indent=2)
            
            print(f"✅ 费用报告保存到: {output_path}")
            
            # 打印摘要
            print(f"\n系统总费用: ${total_cost:,.2f}")
            print(f"平均小时费用: ${total_cost/self.periods:,.2f}")
            
        except Exception as e:
            print(f"❌ 费用计算失败: {str(e)}")
            
    def analyze_marginal_units(self):
        """分析边际机组"""
        print("\n📊 边际机组分析...")
        
        try:
            # 获取电价数据
            if hasattr(self.solution, 'lmps'):
                lmp_data = self.solution.lmps
                
                # 分析边际价格分布
                all_prices = []
                for t_str, prices in lmp_data.items():
                    if prices:
                        all_prices.append(prices[0])  # 使用第一个节点的价格
                
                if all_prices:
                    marginal_report = pd.DataFrame({
                        '统计指标': ['最低价', '最高价', '平均价', '中位数'],
                        '边际价格($/MWh)': [
                            f"{min(all_prices):.2f}",
                            f"{max(all_prices):.2f}",
                            f"{sum(all_prices)/len(all_prices):.2f}",
                            f"{sorted(all_prices)[len(all_prices)//2]:.2f}"
                        ]
                    })
                    
                    output_path = os.path.join(self.results_dir, 'marginal_analysis.csv')
                    marginal_report.to_csv(output_path, index=False, encoding='utf-8')
                    
                    print(f"✅ 边际分析保存到: {output_path}")
                    print("\n边际价格统计:")
                    print(marginal_report)
            else:
                print("❌ 无边际价格数据")
                
        except Exception as e:
            print(f"❌ 边际机组分析失败: {str(e)}")
            
    def generate_full_report(self):
        """生成完整的72时段报告"""
        print("\n🔍 开始生成IEEE 14节点72时段（3天）完整分析报告...")
        
        # 1. 网络拓扑图
        self.create_network_topology()
        
        # 2. 3天负荷曲线
        self.create_load_curve()
        
        # 3. 机组组合状态
        self.create_unit_commitment()
        
        # 4. 机组出力
        self.create_generation_dispatch()
        
        # 5. 节点电价
        self.create_nodal_prices()
        
        # 6. 费用分析
        self.calculate_total_costs()
        
        # 7. 边际机组分析
        self.analyze_marginal_units()
        
        # 8. 煤电机组性能分析
        self.analyze_coal_performance()
        
        print("\n✅ 72时段分析报告生成完成！")
        print(f"📁 所有结果保存在: {self.results_dir}")