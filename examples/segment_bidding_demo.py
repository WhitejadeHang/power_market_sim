#!/usr/bin/env python3
"""
Simpower 容量段报价功能演示
展示分段线性投标曲线的市场出清过程
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from simpower.solve import solve_problem
from simpower.market_clearing import enhance_bidding_analysis, create_bidding_example
import pandas as pd
import matplotlib.pyplot as plt


def demo_segment_bidding():
    """演示容量段报价功能"""
    
    print("🚀 Simpower 容量段报价功能演示")
    print("=" * 50)
    
    # 1. 创建示例案例
    print("\n📁 创建容量段报价示例案例...")
    example_dir = create_bidding_example("segment_bidding_demo_case")
    
    # 2. 运行市场出清
    print("\n⚡ 执行市场出清...")
    solution = solve_problem(example_dir)
    
    # 3. 增强分析功能
    print("\n📊 分析市场出清结果...")
    market_analysis = enhance_bidding_analysis(solution)
    
    if market_analysis:
        # 4. 显示详细的市场分析
        solution.print_bidding_summary()
        
        # 5. 生成投标曲线可视化
        create_bidding_curve_plot(market_analysis, example_dir)
        
        # 6. 生成市场报告
        generate_detailed_report(market_analysis, example_dir)
    
    print("\n✅ 容量段报价演示完成!")
    print(f"📁 详细结果保存在 {example_dir}/ 目录")


def create_bidding_curve_plot(market_analysis, output_dir):
    """创建投标曲线可视化图"""
    try:
        import matplotlib.pyplot as plt
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 获取投标段信息
        segment_info = market_analysis.analyze_bidding_segments()
        merit_order = market_analysis.create_merit_order()
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
        
        # 子图1: 各机组投标曲线
        ax1.set_title('各机组分段投标曲线', fontsize=14, fontweight='bold')
        colors = ['blue', 'green', 'red', 'orange', 'purple']
        
        for i, (gen_name, gen_info) in enumerate(segment_info.items()):
            if gen_info['is_segment_bidding']:
                segments = gen_info['segments']
                powers = [s['power_mw'] for s in segments]
                costs = [s['total_cost'] for s in segments]
                
                ax1.plot(powers, costs, 'o-', color=colors[i % len(colors)], 
                        linewidth=2, markersize=6, label=gen_name)
        
        ax1.set_xlabel('出力 (MW)')
        ax1.set_ylabel('总成本 ($)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 子图2: 系统报价堆积图 (Merit Order)
        ax2.set_title('系统报价排序 (Merit Order)', fontsize=14, fontweight='bold')
        
        if merit_order:
            cumulative_capacities = [0]
            marginal_costs = [0]
            
            for segment in merit_order:
                cumulative_capacities.append(segment['cumulative_capacity_mw'])
                marginal_costs.append(segment['marginal_cost_mwh'])
            
            # 创建阶梯函数
            for i in range(len(marginal_costs) - 1):
                ax2.hlines(marginal_costs[i+1], cumulative_capacities[i], 
                          cumulative_capacities[i+1], colors='steelblue', linewidth=3)
                ax2.vlines(cumulative_capacities[i+1], marginal_costs[i], 
                          marginal_costs[i+1], colors='steelblue', linewidth=2)
            
            # 标注负载水平
            clearing_result = market_analysis.analyze_market_clearing()
            total_load = clearing_result['total_load_mw']
            ax2.axvline(total_load, color='red', linestyle='--', linewidth=2, 
                       label=f'系统负载: {total_load:.0f} MW')
            ax2.axhline(clearing_result['average_lmp_mwh'], color='red', 
                       linestyle='--', linewidth=2, alpha=0.7,
                       label=f'市场电价: {clearing_result["average_lmp_mwh"]:.1f} $/MWh')
        
        ax2.set_xlabel('累计容量 (MW)')
        ax2.set_ylabel('边际成本 ($/MWh)')
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plot_file = f"{output_dir}/bidding_curves.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        print(f"📈 投标曲线图已保存: {plot_file}")
        
    except ImportError:
        print("⚠️  matplotlib 未安装，跳过可视化")
    except Exception as e:
        print(f"⚠️  绘图失败: {e}")


def generate_detailed_report(market_analysis, output_dir):
    """生成详细的市场分析报告"""
    
    report = market_analysis.generate_market_report()
    
    # 创建Excel报告
    try:
        report_file = f"{output_dir}/market_analysis_report.xlsx"
        
        with pd.ExcelWriter(report_file, engine='openpyxl') as writer:
            
            # 工作表1: 市场概览
            overview_df = pd.DataFrame([report['market_overview']])
            overview_df.to_excel(writer, sheet_name='市场概览', index=False)
            
            # 工作表2: 投标段详情
            bidding_details = []
            for gen_name, gen_info in report['bidding_segments'].items():
                if gen_info['is_segment_bidding']:
                    for segment in gen_info['segments']:
                        bidding_details.append({
                            '机组名称': gen_name,
                            '机组类型': gen_info['type'],
                            '投标段号': segment['segment_id'],
                            '容量(MW)': segment['capacity_mw'],
                            '累计出力(MW)': segment['power_mw'],
                            '总成本($)': segment['total_cost'],
                            '边际成本($/MWh)': segment['marginal_cost_mwh']
                        })
            
            if bidding_details:
                bidding_df = pd.DataFrame(bidding_details)
                bidding_df.to_excel(writer, sheet_name='投标段详情', index=False)
            
            # 工作表3: 报价排序
            if report['merit_order']:
                merit_df = pd.DataFrame(report['merit_order'])
                merit_df.to_excel(writer, sheet_name='报价排序', index=False)
            
            # 工作表4: 出清结果
            clearing = report['clearing_results']
            dispatch_data = []
            for gen_name, gen_data in clearing['generation_dispatch'].items():
                dispatch_data.append({
                    '机组名称': gen_name,
                    '出力(MW)': gen_data['power_mw'],
                    '发电成本($)': gen_data['cost'],
                    '运行状态': gen_data['status'],
                    '容量系数': gen_data['capacity_factor']
                })
            
            dispatch_df = pd.DataFrame(dispatch_data)
            dispatch_df.to_excel(writer, sheet_name='机组调度', index=False)
            
            # 工作表5: 市场指标
            metrics_data = [{
                '指标': '总负载(MW)',
                '数值': clearing['total_load_mw']
            }, {
                '指标': '总发电(MW)', 
                '数值': clearing['total_generation_mw']
            }, {
                '指标': '总成本($)',
                '数值': clearing['total_cost']
            }, {
                '指标': '平均电价($/MWh)',
                '数值': clearing['average_lmp_mwh']
            }, {
                '指标': '加权平均成本($/MWh)',
                '数值': clearing['market_metrics']['weighted_average_cost_mwh']
            }, {
                '指标': 'HHI指数',
                '数值': clearing['market_metrics']['herfindahl_index']
            }, {
                '指标': '市场集中度',
                '数值': clearing['market_metrics']['market_concentration']
            }]
            
            metrics_df = pd.DataFrame(metrics_data)
            metrics_df.to_excel(writer, sheet_name='市场指标', index=False)
        
        print(f"📊 详细报告已保存: {report_file}")
        
    except ImportError:
        print("⚠️  openpyxl 未安装，跳过Excel报告生成")
    except Exception as e:
        print(f"⚠️  Excel报告生成失败: {e}")
    
    # 创建文本报告
    try:
        text_report_file = f"{output_dir}/market_analysis_report.txt"
        with open(text_report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("Simpower 容量段报价市场分析报告\n")
            f.write("=" * 80 + "\n\n")
            
            # 市场概览
            f.write("📊 市场概览\n")
            f.write("-" * 40 + "\n")
            overview = report['market_overview']
            for key, value in overview.items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # 出清结果
            f.write("⚡ 市场出清结果\n")
            f.write("-" * 40 + "\n")
            clearing = report['clearing_results']
            f.write(f"总负载: {clearing['total_load_mw']:.1f} MW\n")
            f.write(f"总发电: {clearing['total_generation_mw']:.1f} MW\n")
            f.write(f"总成本: {clearing['total_cost']:.0f} $\n")
            f.write(f"平均电价: {clearing['average_lmp_mwh']:.2f} $/MWh\n")
            f.write(f"功率平衡: {'平衡' if clearing['load_balance'] else '不平衡'}\n\n")
            
            # 机组调度
            f.write("🔌 机组调度结果\n")
            f.write("-" * 40 + "\n")
            for gen_name, gen_data in clearing['generation_dispatch'].items():
                f.write(f"{gen_name}: {gen_data['power_mw']:.1f} MW "
                       f"(容量系数: {gen_data['capacity_factor']:.1%})\n")
            f.write("\n")
            
            # 市场指标
            f.write("📊 市场效率指标\n")
            f.write("-" * 40 + "\n")
            metrics = clearing['market_metrics']
            for key, value in metrics.items():
                if key != 'capacity_utilization':
                    f.write(f"{key}: {value}\n")
        
        print(f"📝 文本报告已保存: {text_report_file}")
        
    except Exception as e:
        print(f"⚠️  文本报告生成失败: {e}")


def compare_with_polynomial_bidding():
    """对比多项式投标和容量段投标的差异"""
    
    print("\n🔍 容量段投标 vs 多项式投标对比分析")
    print("=" * 50)
    
    try:
        # 测试现有的容量段投标案例
        print("📊 运行容量段投标案例...")
        segment_solution = solve_problem('simpower/tests/ed-custom-bidding-points')
        segment_cost = segment_solution.totalcost_generation.iloc[0]
        
        print(f"  容量段投标总成本: {segment_cost:.0f} $")
        
        # 对比简单的多项式投标案例
        print("📊 运行多项式投标案例...")
        poly_solution = solve_problem('simpower/tests/ed')
        poly_cost = poly_solution.totalcost_generation.iloc[0]
        
        print(f"  多项式投标总成本: {poly_cost:.0f} $")
        
        # 分析差异
        cost_diff = abs(segment_cost - poly_cost)
        cost_diff_pct = cost_diff / min(segment_cost, poly_cost) * 100
        
        print(f"\n💰 成本差异分析:")
        print(f"  绝对差异: {cost_diff:.0f} $")
        print(f"  相对差异: {cost_diff_pct:.1f}%")
        
        if cost_diff_pct > 5:
            print("  📈 容量段投标提供了更精确的成本建模")
        else:
            print("  📊 两种投标方式结果相近")
            
    except Exception as e:
        print(f"⚠️  对比分析失败: {e}")


if __name__ == "__main__":
    # 主演示
    demo_segment_bidding()
    
    # 对比分析
    compare_with_polynomial_bidding()
    
    print("\n🎉 容量段报价功能演示完成!")
    print("✅ Simpower 完全支持机组申报按容量段报价进行出清")
    print("📊 提供了完整的市场分析和可视化功能")