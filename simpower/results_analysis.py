#!/usr/bin/env python3
"""
IEEE 50节点案例结果分析和可视化模块
提供完整的经济调度结果分析和图表生成功能
"""

import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch
from datetime import datetime, timedelta

# 尝试导入可选依赖
try:
    import seaborn as sns
    HAS_SEABORN = True
except ImportError:
    HAS_SEABORN = False

try:
    import networkx as nx
    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False

# 设置中文字体和绘图风格
CHINESE_FONT_NAME = None
CHINESE_FONT_PROP = None

try:
    import matplotlib.font_manager as fm
    import os
    
    # 获取当前脚本的目录
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    
    # 中文字体文件路径
    font_paths = [
        os.path.join(project_root, 'fonts/SubsetOTF/CN/SourceHanSansCN-Regular.otf'),
        os.path.join(project_root, 'fonts/SubsetOTF/CN/SourceHanSansCN-Medium.otf'),
        os.path.join(project_root, 'fonts/SubsetOTF/CN/SourceHanSansCN-Bold.otf'),
    ]
    
    # 尝试使用下载的中文字体
    font_found = False
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                # 注册字体
                fm.fontManager.addfont(font_path)
                # 获取字体属性
                prop = fm.FontProperties(fname=font_path)
                font_name = prop.get_name()
                
                # 设置为默认字体
                plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans', 'Arial']
                plt.rcParams['font.family'] = 'sans-serif'
                plt.rcParams['axes.unicode_minus'] = False
                
                # 设置所有文本元素的默认字体
                plt.rcParams['font.serif'] = [font_name, 'DejaVu Serif', 'Times']
                plt.rcParams['mathtext.fontset'] = 'custom'
                plt.rcParams['mathtext.rm'] = font_name
                plt.rcParams['mathtext.it'] = font_name
                plt.rcParams['mathtext.bf'] = font_name
                
                # 保存字体名称和属性供后续使用
                CHINESE_FONT_NAME = font_name
                CHINESE_FONT_PROP = prop
                
                # 清除matplotlib字体缓存以确保新字体生效
                try:
                    import matplotlib
                    matplotlib.font_manager._load_fontmanager(try_read_cache=False)
                    # 重新构建字体缓存
                    matplotlib.font_manager.fontManager.findfont(prop=matplotlib.font_manager.FontProperties())
                    
                    # 强制替换所有默认字体为中文字体
                    matplotlib.rcParams['font.serif'] = [font_name]
                    matplotlib.rcParams['font.sans-serif'] = [font_name]
                    matplotlib.rcParams['font.cursive'] = [font_name]
                    matplotlib.rcParams['font.fantasy'] = [font_name]
                    matplotlib.rcParams['font.monospace'] = [font_name]
                except:
                    pass
                
                print(f"✅ 成功加载中文字体: {font_name} ({os.path.basename(font_path)})")
                font_found = True
                break
            except Exception as e:
                print(f"⚠️ 加载字体失败 {font_path}: {e}")
                continue
    
    if not font_found:
        # 如果没有找到中文字体，使用英文
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['axes.unicode_minus'] = False
        print("⚠️ 未找到中文字体，将使用英文显示")
        
except Exception as e:
    plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
    plt.rcParams['font.family'] = 'sans-serif'
    plt.rcParams['axes.unicode_minus'] = False
    print(f"⚠️ 字体设置失败: {e}")
    print("使用默认英文字体")

# 设置绘图风格
try:
    if HAS_SEABORN:
        plt.style.use('seaborn-v0_8')
        sns.set_palette("husl")
    else:
        plt.style.use('ggplot')
except:
    plt.style.use('default')


# 全局中文字体属性
def get_chinese_font():
    """获取中文字体属性"""
    if CHINESE_FONT_PROP:
        return CHINESE_FONT_PROP
    elif CHINESE_FONT_NAME:
        try:
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir)
            font_path = os.path.join(project_root, 'fonts/SubsetOTF/CN/SourceHanSansCN-Regular.otf')
            if os.path.exists(font_path):
                return fm.FontProperties(fname=font_path)
        except:
            pass
    return None

def set_chinese_font_for_axes(ax, chinese_font=None):
    """为axes对象设置中文字体"""
    if chinese_font is None:
        chinese_font = get_chinese_font()
    
    if chinese_font:
        # 获取当前的标题、标签
        title = ax.get_title()
        xlabel = ax.get_xlabel()
        ylabel = ax.get_ylabel()
        
        # 重新设置带有中文字体的标题和标签
        if title:
            ax.set_title(title, fontproperties=chinese_font)
        if xlabel:
            ax.set_xlabel(xlabel, fontproperties=chinese_font)
        if ylabel:
            ax.set_ylabel(ylabel, fontproperties=chinese_font)
        
        # 设置刻度标签字体
        for label in ax.get_xticklabels() + ax.get_yticklabels():
            if hasattr(label, 'get_text') and any('\u4e00' <= char <= '\u9fff' for char in label.get_text()):
                label.set_fontproperties(chinese_font)

def apply_chinese_font_to_figure(fig, chinese_font=None):
    """为整个图形应用中文字体"""
    if chinese_font is None:
        chinese_font = get_chinese_font()
    
    if chinese_font:
        # 应用到所有axes
        for ax in fig.get_axes():
            set_chinese_font_for_axes(ax, chinese_font)
            
            # 强制应用到所有文本元素
            for text in ax.texts:
                if any('\u4e00' <= char <= '\u9fff' for char in text.get_text()):
                    text.set_fontproperties(chinese_font)
            
            # 应用到轴标签
            for label in ax.get_xticklabels() + ax.get_yticklabels():
                if any('\u4e00' <= char <= '\u9fff' for char in label.get_text()):
                    label.set_fontproperties(chinese_font)
            
            # 应用到图例
            legend = ax.get_legend()
            if legend:
                for text in legend.get_texts():
                    if any('\u4e00' <= char <= '\u9fff' for char in text.get_text()):
                        text.set_fontproperties(chinese_font)
        
        # 应用到图形标题
        if hasattr(fig, '_suptitle') and fig._suptitle:
            fig._suptitle.set_fontproperties(chinese_font)

def create_text_with_font(text, chinese_font=None, **kwargs):
    """创建带有中文字体的文本"""
    if chinese_font is None:
        chinese_font = get_chinese_font()
    
    if chinese_font and any('\u4e00' <= char <= '\u9fff' for char in str(text)):
        kwargs['fontproperties'] = chinese_font
    
    return kwargs

class IEEE50BusResultsAnalyzer:
    """IEEE 50节点案例结果分析器"""
    
    def __init__(self, case_dir, solution=None):
        """
        初始化分析器
        
        Args:
            case_dir: 案例目录路径
            solution: 求解结果对象
        """
        self.case_dir = case_dir
        self.solution = solution
        self.results_dir = os.path.join(case_dir, 'results')
        os.makedirs(self.results_dir, exist_ok=True)
        
        # 加载案例数据
        self.load_case_data()
    
    def load_case_data(self):
        """加载案例基础数据"""
        
        try:
            self.buses_df = pd.read_csv(os.path.join(self.case_dir, 'buses.csv'))
            self.lines_df = pd.read_csv(os.path.join(self.case_dir, 'lines.csv'))
            self.generators_df = pd.read_csv(os.path.join(self.case_dir, 'generators.csv'))
            self.loads_df = pd.read_csv(os.path.join(self.case_dir, 'loads.csv'))
            
            # 加载系统负荷曲线
            if os.path.exists(os.path.join(self.case_dir, 'system_load_curve.csv')):
                self.load_curve_df = pd.read_csv(os.path.join(self.case_dir, 'system_load_curve.csv'))
            else:
                self.load_curve_df = None
                
            print(f"✅ 成功加载案例数据:")
            print(f"   - 节点数: {len(self.buses_df)}")
            print(f"   - 线路数: {len(self.lines_df)}")
            print(f"   - 发电机数: {len(self.generators_df)}")
            print(f"   - 负荷点数: {len(self.loads_df)}")
            
        except Exception as e:
            print(f"❌ 加载案例数据失败: {e}")
    
    def extract_solution_results(self):
        """提取求解结果数据"""
        
        if self.solution is None:
            print("❌ 没有提供求解结果")
            return None
        
        results = {
            'generators': {},
            'buses': {},
            'lines': {},
            'system': {},
            'costs': {}
        }
        
        try:
            # 从simpower solution提取发电机结果
            if hasattr(self.solution, 'generators_power') and hasattr(self.solution, 'generators_status'):
                power_df = self.solution.generators_power
                status_df = self.solution.generators_status
                ic_df = getattr(self.solution, 'incremental_cost', None)
                
                # 获取第一行数据（假设是单时段）
                if len(power_df) > 0:
                    power_row = power_df.iloc[0]
                    status_row = status_df.iloc[0]
                    ic_row = ic_df.iloc[0] if ic_df is not None else None
                    
                    for i, gen_col in enumerate(power_df.columns):
                        # 获取发电机名称
                        if i < len(self.generators_df):
                            gen_name = self.generators_df.iloc[i]['name']
                        else:
                            gen_name = f'Gen_{i}'
                            
                        # 获取发电机的基础信息
                        gen_row = self.generators_df.iloc[i] if i < len(self.generators_df) else None
                        no_load_cost = float(gen_row['no load cost']) if gen_row is not None else 0
                        
                        gen_info = {
                            'name': gen_name,
                            'power': float(power_row[gen_col]),
                            'status': int(status_row[gen_col]),
                            'marginal_cost': float(ic_row[gen_col] if ic_row is not None else 0),
                            'startup_cost': 0,  # 可以从no_load_cost估算
                            'fuel_cost': 0,     # 需要计算
                            'no_load_cost': no_load_cost,
                            'total_cost': 0
                        }
                        
                        # 计算燃料成本（包含空载成本）
                        if gen_info['status'] > 0:  # 机组运行
                            # 空载成本（固定成本）
                            gen_info['startup_cost'] = no_load_cost
                            # 燃料成本（变动成本）= 功率 × 边际成本
                            if gen_info['power'] > 0:
                                gen_info['fuel_cost'] = gen_info['power'] * gen_info['marginal_cost']
                            # 总成本 = 空载成本 + 燃料成本
                            gen_info['total_cost'] = gen_info['startup_cost'] + gen_info['fuel_cost']
                        
                        results['generators'][gen_name] = gen_info
            
            # 从simpower solution提取节点结果
            if hasattr(self.solution, 'lmps'):
                lmp_data = self.solution.lmps
                
                # 处理LMP数据
                if isinstance(lmp_data, dict):
                    for time_key, lmp_values in lmp_data.items():
                        if isinstance(lmp_values, list):
                            for i, lmp in enumerate(lmp_values):
                                if i < len(self.buses_df):
                                    bus_name = self.buses_df.iloc[i]['name']
                                    
                                    # 处理异常LMP值（10000表示负荷切除或约束违反）
                                    lmp_value = float(lmp)
                                    if lmp_value >= 9999:
                                        lmp_status = "负荷切除"
                                        lmp_value = 0  # 用于计算显示为0
                                    else:
                                        lmp_status = "正常"
                                    
                                    bus_info = {
                                        'name': bus_name,
                                        'lmp': lmp_value,
                                        'lmp_raw': float(lmp),  # 保留原始值
                                        'lmp_status': lmp_status,
                                        'angle': 0,  # 需要从其他地方获取
                                        'load': 0,   # 需要从其他地方获取
                                        'generation': 0  # 需要计算
                                    }
                                    
                                    # 获取负荷数据
                                    if i < len(self.loads_df):
                                        bus_info['load'] = float(self.loads_df.iloc[i]['power'])
                                    
                                    # 计算该节点的发电量
                                    bus_generation = 0
                                    for gen_name, gen_info in results['generators'].items():
                                        # 从发电机数据中找到对应节点的发电机
                                        gen_row = self.generators_df[self.generators_df['name'] == gen_name]
                                        if len(gen_row) > 0 and gen_row.iloc[0]['bus'] == bus_name:
                                            bus_generation += gen_info['power']
                                    
                                    bus_info['generation'] = bus_generation
                                    results['buses'][bus_name] = bus_info
            
            # 提取系统总体结果
            if hasattr(self.solution, 'objective'):
                results['system']['total_cost'] = float(self.solution.objective)
            elif hasattr(self.solution, 'totalcost_generation'):
                results['system']['total_cost'] = float(self.solution.totalcost_generation)
            
            # 计算各类成本
            total_fuel_cost = sum(gen['fuel_cost'] for gen in results['generators'].values())
            total_startup_cost = sum(gen['startup_cost'] for gen in results['generators'].values())
            total_generation = sum(gen['power'] for gen in results['generators'].values())
            
            results['costs'] = {
                'total_fuel_cost': total_fuel_cost,
                'total_startup_cost': total_startup_cost,
                'total_generation': total_generation,
                'average_cost': total_fuel_cost / max(total_generation, 1) if total_generation > 0 else 0
            }
            
            print(f"✅ 成功提取求解结果:")
            print(f"   - 发电机数据: {len(results['generators'])}")
            print(f"   - 节点数据: {len(results['buses'])}")
            print(f"   - 总发电量: {total_generation:.1f} MW")
            print(f"   - 总燃料成本: ${total_fuel_cost:,.0f}")
            print(f"   - 总启动成本: ${total_startup_cost:,.0f}")
            
            return results
            
        except Exception as e:
            print(f"❌ 提取求解结果失败: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def create_generation_dispatch_plot(self, results):
        """生成发电调度图表"""
        
        if not results or 'generators' not in results:
            print("❌ 无发电机结果数据")
            return
        
        # 准备数据
        gen_data = []
        for gen_name, gen_info in results['generators'].items():
            # 从名称提取机组类型
            if 'supercritical' in gen_name.lower():
                plant_type = '超临界'
                color = '#2E8B57'  # 深绿色
            elif 'subcritical' in gen_name.lower():
                plant_type = '亚临界'
                color = '#4169E1'  # 蓝色
            elif 'old_steam' in gen_name.lower():
                plant_type = '老式机组'
                color = '#FF6347'  # 橙红色
            else:
                plant_type = '小机组'
                color = '#9370DB'  # 紫色
            
            gen_data.append({
                'name': gen_name,
                'type': plant_type,
                'power': gen_info['power'],
                'status': gen_info['status'],
                'marginal_cost': gen_info['marginal_cost'],
                'color': color
            })
        
        gen_df = pd.DataFrame(gen_data)
        
        # 创建图形
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        
        # 设置图表标题和字体
        chinese_font = get_chinese_font()
        fig.suptitle('IEEE 50节点系统发电调度结果分析', fontsize=16, fontweight='bold', 
                     **create_text_with_font('IEEE 50节点系统发电调度结果分析', chinese_font))
        
        # 1. 按机组类型的发电量分布
        type_power = gen_df.groupby('type')['power'].sum()
        colors = ['#2E8B57', '#4169E1', '#FF6347', '#9370DB']
        
        wedges, texts, autotexts = ax1.pie(type_power.values, labels=type_power.index, 
                                          autopct='%1.1f%%', colors=colors, startangle=90)
        ax1.set_title('各类机组发电量占比', fontweight='bold', 
                      **create_text_with_font('各类机组发电量占比', chinese_font))
        
        # 美化饼图并设置中文字体
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        # 设置饼图标签字体
        if chinese_font:
            for text in texts:
                text.set_fontproperties(chinese_font)
        
        # 2. 机组功率输出柱状图
        dispatched_gens = gen_df[gen_df['power'] > 1].sort_values('power', ascending=False)
        
        bars = ax2.bar(range(len(dispatched_gens)), dispatched_gens['power'], 
                      color=dispatched_gens['color'], alpha=0.8)
        ax2.set_title('机组功率输出排序', fontweight='bold', 
                      **create_text_with_font('机组功率输出排序', chinese_font))
        ax2.set_xlabel('机组排序', **create_text_with_font('机组排序', chinese_font))
        ax2.set_ylabel('功率输出 (MW)', **create_text_with_font('功率输出 (MW)', chinese_font))
        ax2.grid(True, alpha=0.3)
        
        # 添加数值标签
        for i, (bar, power) in enumerate(zip(bars, dispatched_gens['power'])):
            if power > 0:
                ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 5, 
                        f'{power:.0f}', ha='center', va='bottom', fontsize=8, 
                        **create_text_with_font(f'{power:.0f}', chinese_font))
        
        # 3. 边际成本与功率输出散点图
        active_gens = gen_df[gen_df['power'] > 1]
        
        scatter = ax3.scatter(active_gens['power'], active_gens['marginal_cost'], 
                             c=active_gens['marginal_cost'], s=100, alpha=0.7, 
                             cmap='viridis', edgecolors='black', linewidth=0.5)
        ax3.set_title('功率输出 vs 边际成本', fontweight='bold', 
                      **create_text_with_font('功率输出 vs 边际成本', chinese_font))
        ax3.set_xlabel('功率输出 (MW)', **create_text_with_font('功率输出 (MW)', chinese_font))
        ax3.set_ylabel('边际成本 ($/MWh)', **create_text_with_font('边际成本 ($/MWh)', chinese_font))
        ax3.grid(True, alpha=0.3)
        
        # 添加颜色条
        cbar = plt.colorbar(scatter, ax=ax3)
        cbar.set_label('边际成本 ($/MWh)', **create_text_with_font('边际成本 ($/MWh)', chinese_font))
        
        # 4. 机组类型统计表
        type_stats = gen_df.groupby('type').agg({
            'power': ['count', 'sum', 'mean'],
            'marginal_cost': ['mean', 'std'],
            'status': 'sum'
        }).round(2)
        
        # 清空第四个子图用于显示表格
        ax4.axis('off')
        
        # 创建统计表格
        table_data = []
        for plant_type in type_stats.index:
            row = [
                plant_type,
                f"{type_stats.loc[plant_type, ('status', 'sum')]:.0f}",
                f"{type_stats.loc[plant_type, ('power', 'sum')]:.0f}",
                f"{type_stats.loc[plant_type, ('power', 'mean')]:.0f}",
                f"{type_stats.loc[plant_type, ('marginal_cost', 'mean')]:.1f}"
            ]
            table_data.append(row)
        
        table = ax4.table(cellText=table_data,
                         colLabels=['机组类型', '运行台数', '总功率(MW)', '平均功率(MW)', '平均成本($/MWh)'],
                         cellLoc='center',
                         loc='center',
                         bbox=[0, 0.3, 1, 0.6])
        
        table.auto_set_font_size(False)
        table.set_fontsize(10)
        table.scale(1, 2)
        
        # 设置表格样式
        for i in range(len(table_data) + 1):
            for j in range(5):
                cell = table[(i, j)]
                if i == 0:  # 表头
                    cell.set_facecolor('#4472C4')
                    cell.set_text_props(weight='bold', color='white')
                else:
                    cell.set_facecolor('#F2F2F2' if i % 2 == 0 else 'white')
        
        ax4.set_title('机组类型统计', fontweight='bold', pad=20, 
                      **create_text_with_font('机组类型统计', chinese_font))
        
        # 设置表格中文字体
        if chinese_font:
            for key, cell in table.get_celld().items():
                if key[0] == 0:  # 表头行
                    cell.get_text().set_fontproperties(chinese_font)
        
        # 在图形级别应用中文字体
        apply_chinese_font_to_figure(fig, chinese_font)
        
        plt.tight_layout()
        
        # 保存图表
        save_path = os.path.join(self.results_dir, 'generation_dispatch_analysis.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 发电调度分析图表已保存: {save_path}")
        
        plt.close()
    
    def create_lmp_analysis_plot(self, results):
        """生成节点电价(LMP)分析图表"""
        
        if not results or 'buses' not in results:
            print("❌ 无节点结果数据")
            return
        
        # 准备节点电价数据
        bus_data = []
        for bus_name, bus_info in results['buses'].items():
            # 提取区域信息
            if 'urban_high' in bus_name:
                zone = '都市高负荷区'
                color = '#FF6B6B'
            elif 'urban_medium' in bus_name:
                zone = '都市中负荷区'
                color = '#4ECDC4'
            elif 'suburban' in bus_name:
                zone = '郊区'
                color = '#45B7D1'
            elif 'industrial' in bus_name:
                zone = '工业区'
                color = '#96CEB4'
            else:
                zone = '农村区'
                color = '#FFEAA7'
            
            bus_data.append({
                'name': bus_name,
                'zone': zone,
                'lmp': bus_info['lmp'],
                'load': bus_info['load'],
                'generation': bus_info['generation'],
                'color': color
            })
        
        bus_df = pd.DataFrame(bus_data)
        
        # 创建图形和设置字体
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        chinese_font = get_chinese_font()
        fig.suptitle('IEEE 50节点系统节点电价(LMP)分析', fontsize=16, fontweight='bold', 
                     **create_text_with_font('IEEE 50节点系统节点电价(LMP)分析', chinese_font))
        
        # 1. 各区域LMP分布箱线图
        zone_order = ['都市高负荷区', '都市中负荷区', '郊区', '工业区', '农村区']
        zone_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7']
        
        box_data = [bus_df[bus_df['zone'] == zone]['lmp'].values for zone in zone_order]
        
        bp = ax1.boxplot(box_data, labels=zone_order, patch_artist=True)
        ax1.set_title('各区域节点电价分布', fontweight='bold', 
                      **create_text_with_font('各区域节点电价分布', chinese_font))
        ax1.set_ylabel('节点电价 ($/MWh)', **create_text_with_font('节点电价 ($/MWh)', chinese_font))
        ax1.tick_params(axis='x', rotation=45)
        ax1.grid(True, alpha=0.3)
        
        # 设置x轴标签字体
        if chinese_font:
            for label in ax1.get_xticklabels():
                label.set_fontproperties(chinese_font)
        
        # 设置箱线图颜色
        for patch, color in zip(bp['boxes'], zone_colors):
            patch.set_facecolor(color)
            patch.set_alpha(0.7)
        
        # 2. LMP热力图
        # 创建5x10的网格来表示50个节点
        lmp_matrix = np.zeros((5, 10))
        for i, (_, bus) in enumerate(bus_df.iterrows()):
            row = i // 10
            col = i % 10
            lmp_matrix[row, col] = bus['lmp']
        
        im = ax2.imshow(lmp_matrix, cmap='RdYlBu_r', aspect='auto')
        ax2.set_title('节点电价热力图', fontweight='bold', 
                      **create_text_with_font('节点电价热力图', chinese_font))
        ax2.set_xlabel('节点列', **create_text_with_font('节点列', chinese_font))
        ax2.set_ylabel('节点行', **create_text_with_font('节点行', chinese_font))
        
        # 添加颜色条
        cbar = plt.colorbar(im, ax=ax2)
        cbar.set_label('LMP ($/MWh)', **create_text_with_font('LMP ($/MWh)', chinese_font))
        
        # 在热力图上添加数值
        for i in range(5):
            for j in range(10):
                if lmp_matrix[i, j] > 0:
                    text = ax2.text(j, i, f'{lmp_matrix[i, j]:.1f}', 
                                   ha="center", va="center", color="black", fontsize=8, 
                                   **create_text_with_font(f'{lmp_matrix[i, j]:.1f}', chinese_font))
        
        # 3. LMP与负荷关系散点图
        non_zero_buses = bus_df[bus_df['lmp'] > 0]
        
        scatter = ax3.scatter(non_zero_buses['load'], non_zero_buses['lmp'], 
                             c=non_zero_buses['lmp'], s=80, alpha=0.7, 
                             cmap='plasma', edgecolors='black', linewidth=0.5)
        ax3.set_title('节点负荷 vs 节点电价', fontweight='bold', 
                      **create_text_with_font('节点负荷 vs 节点电价', chinese_font))
        ax3.set_xlabel('节点负荷 (MW)', **create_text_with_font('节点负荷 (MW)', chinese_font))
        ax3.set_ylabel('节点电价 ($/MWh)', **create_text_with_font('节点电价 ($/MWh)', chinese_font))
        ax3.grid(True, alpha=0.3)
        
        # 添加趋势线
        if len(non_zero_buses) > 1:
            z = np.polyfit(non_zero_buses['load'], non_zero_buses['lmp'], 1)
            p = np.poly1d(z)
            ax3.plot(non_zero_buses['load'], p(non_zero_buses['load']), 
                    "r--", alpha=0.8, linewidth=2)
        
        # 4. LMP统计信息
        ax4.axis('off')
        
        # 计算统计信息
        lmp_stats = bus_df[bus_df['lmp'] > 0]['lmp']
        zone_lmp_avg = bus_df.groupby('zone')['lmp'].mean().sort_values(ascending=False)
        
        stats_text = f"""
节点电价统计摘要

总体统计:
• 节点数量: {len(bus_df)}
• 有效LMP节点: {len(lmp_stats)}
• 平均LMP: ${lmp_stats.mean():.2f}/MWh
• LMP范围: ${lmp_stats.min():.2f} - ${lmp_stats.max():.2f}/MWh
• 标准差: ${lmp_stats.std():.2f}/MWh

各区域平均LMP排序:
"""
        
        for zone, avg_lmp in zone_lmp_avg.items():
            stats_text += f"• {zone}: ${avg_lmp:.2f}/MWh\n"
        
        # 价格差异分析
        price_spread = lmp_stats.max() - lmp_stats.min()
        stats_text += f"\n价格分析:\n• 最大价差: ${price_spread:.2f}/MWh"
        
        if price_spread > 0:
            relative_spread = (price_spread / lmp_stats.mean()) * 100
            stats_text += f"\n• 相对价差: {relative_spread:.1f}%"
        
        ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor="lightblue", alpha=0.8), 
                **create_text_with_font(stats_text, chinese_font))
        
        # 在图形级别应用中文字体
        apply_chinese_font_to_figure(fig, chinese_font)
        
        plt.tight_layout()
        
        # 保存图表
        save_path = os.path.join(self.results_dir, 'lmp_analysis.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 节点电价分析图表已保存: {save_path}")
        
        plt.close()
    
    def create_cost_analysis_plot(self, results):
        """生成成本分析图表"""
        
        if not results or 'costs' not in results:
            print("❌ 无成本结果数据")
            return
        
        costs = results['costs']
        generators = results['generators']
        
        # 创建图形
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 12))
        chinese_font = get_chinese_font()
        fig.suptitle('IEEE 50节点系统成本分析', fontsize=16, fontweight='bold', 
                     **create_text_with_font('IEEE 50节点系统成本分析', chinese_font))
        
        # 1. 总成本构成饼图
        cost_components = {
            '燃料成本': costs['total_fuel_cost'],
            '启动成本': costs['total_startup_cost']
        }
        
        # 移除零值项
        cost_components = {k: v for k, v in cost_components.items() if v > 0}
        
        if cost_components:
            colors = ['#FF9999', '#66B2FF']
            wedges, texts, autotexts = ax1.pie(cost_components.values(), 
                                              labels=cost_components.keys(), 
                                              autopct='%1.1f%%', colors=colors, 
                                              startangle=90)
            ax1.set_title('总成本构成', fontweight='bold', 
                          **create_text_with_font('总成本构成', chinese_font))
            
            # 设置饼图标签字体
            if chinese_font:
                for text in texts:
                    text.set_fontproperties(chinese_font)
            
            for autotext in autotexts:
                autotext.set_color('white')
                autotext.set_fontweight('bold')
            
            # 设置饼图标签字体
            if chinese_font:
                for text in texts:
                    text.set_fontproperties(chinese_font)
        else:
            ax1.text(0.5, 0.5, '无成本数据', ha='center', va='center', 
                    transform=ax1.transAxes, fontsize=14, 
                    **create_text_with_font('无成本数据', chinese_font))
            ax1.set_title('总成本构成', fontweight='bold', 
                          **create_text_with_font('总成本构成', chinese_font))
        
        # 2. 各机组燃料成本柱状图
        gen_costs = []
        for gen_name, gen_info in generators.items():
            if gen_info['fuel_cost'] > 0:
                # 提取机组类型
                if 'supercritical' in gen_name.lower():
                    plant_type = '超临界'
                    color = '#2E8B57'
                elif 'subcritical' in gen_name.lower():
                    plant_type = '亚临界'
                    color = '#4169E1'
                elif 'old_steam' in gen_name.lower():
                    plant_type = '老式机组'
                    color = '#FF6347'
                else:
                    plant_type = '小机组'
                    color = '#9370DB'
                
                gen_costs.append({
                    'name': gen_name,
                    'type': plant_type,
                    'fuel_cost': gen_info['fuel_cost'],
                    'power': gen_info['power'],
                    'color': color
                })
        
        if gen_costs:
            gen_costs_df = pd.DataFrame(gen_costs)
            gen_costs_df = gen_costs_df.sort_values('fuel_cost', ascending=False)
            
            bars = ax2.bar(range(len(gen_costs_df)), gen_costs_df['fuel_cost'], 
                          color=gen_costs_df['color'], alpha=0.8)
            ax2.set_title('各机组燃料成本', fontweight='bold', 
                          **create_text_with_font('各机组燃料成本', chinese_font))
            ax2.set_xlabel('机组排序', **create_text_with_font('机组排序', chinese_font))
            ax2.set_ylabel('燃料成本 ($)', **create_text_with_font('燃料成本 ($)', chinese_font))
            ax2.grid(True, alpha=0.3)
            
            # 添加数值标签
            for i, (bar, cost) in enumerate(zip(bars, gen_costs_df['fuel_cost'])):
                if cost > 0:
                    ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(gen_costs_df['fuel_cost'])*0.01, 
                            f'${cost:,.0f}', ha='center', va='bottom', fontsize=8, rotation=90, 
                            **create_text_with_font(f'${cost:,.0f}', chinese_font))
        else:
            ax2.text(0.5, 0.5, '无燃料成本数据', ha='center', va='center', 
                    transform=ax2.transAxes, fontsize=14, 
                    **create_text_with_font('无燃料成本数据', chinese_font))
            ax2.set_title('各机组燃料成本', fontweight='bold', 
                          **create_text_with_font('各机组燃料成本', chinese_font))
        
        # 3. 功率-成本效率散点图
        if gen_costs:
            # 计算单位发电成本
            gen_costs_df['unit_cost'] = gen_costs_df['fuel_cost'] / gen_costs_df['power'].replace(0, np.nan)
            valid_gens = gen_costs_df.dropna()
            
            if len(valid_gens) > 0:
                scatter = ax3.scatter(valid_gens['power'], valid_gens['unit_cost'], 
                                     c=valid_gens['unit_cost'], s=100, alpha=0.7, 
                                     cmap='Reds', edgecolors='black', linewidth=0.5)
                ax3.set_title('发电量 vs 单位成本', fontweight='bold', 
                              **create_text_with_font('发电量 vs 单位成本', chinese_font))
                ax3.set_xlabel('发电量 (MW)', **create_text_with_font('发电量 (MW)', chinese_font))
                ax3.set_ylabel('单位成本 ($/MWh)', **create_text_with_font('单位成本 ($/MWh)', chinese_font))
                ax3.grid(True, alpha=0.3)
                
                # 添加颜色条
                cbar = plt.colorbar(scatter, ax=ax3)
                cbar.set_label('单位成本 ($/MWh)', **create_text_with_font('单位成本 ($/MWh)', chinese_font))
            else:
                ax3.text(0.5, 0.5, '无有效单位成本数据', ha='center', va='center', 
                        transform=ax3.transAxes, fontsize=14, 
                        **create_text_with_font('无有效单位成本数据', chinese_font))
                ax3.set_title('发电量 vs 单位成本', fontweight='bold', 
                              **create_text_with_font('发电量 vs 单位成本', chinese_font))
        else:
            ax3.text(0.5, 0.5, '无成本数据', ha='center', va='center', 
                    transform=ax3.transAxes, fontsize=14, 
                    **create_text_with_font('无成本数据', chinese_font))
            ax3.set_title('发电量 vs 单位成本', fontweight='bold', 
                          **create_text_with_font('发电量 vs 单位成本', chinese_font))
        
        # 4. 成本统计表
        ax4.axis('off')
        
        # 创建成本统计信息
        stats_text = f"""
系统成本统计摘要

总体成本:
• 总燃料成本: ${costs['total_fuel_cost']:,.0f}
• 总启动成本: ${costs['total_startup_cost']:,.0f}
• 系统总成本: ${costs['total_fuel_cost'] + costs['total_startup_cost']:,.0f}

运行指标:
• 总发电量: {costs['total_generation']:,.1f} MW
• 平均燃料成本: ${costs['average_cost']:.2f}/MWh
"""
        
        if gen_costs:
            type_costs = gen_costs_df.groupby('type')['fuel_cost'].sum()
            stats_text += "\n各类机组燃料成本:\n"
            for plant_type, total_cost in type_costs.items():
                percentage = (total_cost / costs['total_fuel_cost']) * 100 if costs['total_fuel_cost'] > 0 else 0
                stats_text += f"• {plant_type}: ${total_cost:,.0f} ({percentage:.1f}%)\n"
        
        ax4.text(0.05, 0.95, stats_text, transform=ax4.transAxes, fontsize=11,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor="lightgreen", alpha=0.8), 
                **create_text_with_font(stats_text, chinese_font))
        
        # 在图形级别应用中文字体
        apply_chinese_font_to_figure(fig, chinese_font)
        
        plt.tight_layout()
        
        # 保存图表
        save_path = os.path.join(self.results_dir, 'cost_analysis.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 成本分析图表已保存: {save_path}")
        
        plt.close()
    
    def create_network_topology_plot(self):
        """生成网络拓扑图"""
        
        if not HAS_NETWORKX:
            print("⚠️ NetworkX未安装，跳过网络拓扑图生成")
            return
        
        try:
            # 创建网络图
            G = nx.Graph()
            
            # 添加节点
            node_positions = {}
            node_colors = []
            node_sizes = []
            
            for i, (_, bus) in enumerate(self.buses_df.iterrows()):
                bus_name = bus['name']
                G.add_node(bus_name)
                
                # 根据区域设置节点位置和颜色
                if 'urban_high' in bus_name:
                    # 都市高负荷区 - 左上角
                    base_x, base_y = 0, 4
                    color = '#FF6B6B'
                    size = 800
                elif 'urban_medium' in bus_name:
                    # 都市中负荷区 - 右上角
                    base_x, base_y = 4, 4
                    color = '#4ECDC4'
                    size = 600
                elif 'suburban' in bus_name:
                    # 郊区 - 左中
                    base_x, base_y = 0, 2
                    color = '#45B7D1'
                    size = 400
                elif 'industrial' in bus_name:
                    # 工业区 - 右中
                    base_x, base_y = 4, 2
                    color = '#96CEB4'
                    size = 700
                else:
                    # 农村区 - 下方
                    base_x, base_y = 2, 0
                    color = '#FFEAA7'
                    size = 300
                
                # 在区域内随机分布
                x = base_x + np.random.uniform(-0.8, 0.8)
                y = base_y + np.random.uniform(-0.8, 0.8)
                
                node_positions[bus_name] = (x, y)
                node_colors.append(color)
                node_sizes.append(size)
            
            # 添加边（传输线）
            edge_weights = []
            for _, line in self.lines_df.iterrows():
                from_bus = line['from bus']
                to_bus = line['to bus']
                capacity = line['Pmax']
                
                if from_bus in G.nodes and to_bus in G.nodes:
                    G.add_edge(from_bus, to_bus, capacity=capacity)
                    edge_weights.append(capacity / 1000)  # 标准化权重
            
            # 创建图形
            fig, ax = plt.subplots(1, 1, figsize=(16, 12))
            
            # 绘制网络
            nx.draw_networkx_nodes(G, node_positions, node_color=node_colors, 
                                  node_size=node_sizes, alpha=0.8, ax=ax)
            
            nx.draw_networkx_edges(G, node_positions, width=edge_weights, 
                                  alpha=0.6, edge_color='gray', ax=ax)
            
            # 添加节点标签（只显示节点编号）
            node_labels = {}
            for node in G.nodes():
                # 提取节点编号
                if 'Bus_' in node:
                    bus_num = node.split('_')[1]
                    node_labels[node] = bus_num
                else:
                    node_labels[node] = node[:3]
            
            nx.draw_networkx_labels(G, node_positions, node_labels, 
                                   font_size=6, font_weight='bold', ax=ax)
            
            # 添加发电机位置标记
            for _, gen in self.generators_df.iterrows():
                gen_bus = gen['bus']
                if gen_bus in node_positions:
                    x, y = node_positions[gen_bus]
                    ax.scatter(x, y, s=200, c='red', marker='^', 
                             edgecolors='black', linewidth=1, alpha=0.9, zorder=5)
            
            chinese_font = get_chinese_font()
            ax.set_title('IEEE 50节点网络拓扑图', fontsize=16, fontweight='bold', pad=20, fontproperties=chinese_font)
            ax.axis('off')
            
            # 添加图例
            legend_elements = [
                plt.scatter([], [], c='#FF6B6B', s=100, label='都市高负荷区'),
                plt.scatter([], [], c='#4ECDC4', s=100, label='都市中负荷区'),
                plt.scatter([], [], c='#45B7D1', s=100, label='郊区'),
                plt.scatter([], [], c='#96CEB4', s=100, label='工业区'),
                plt.scatter([], [], c='#FFEAA7', s=100, label='农村区'),
                plt.scatter([], [], c='red', s=100, marker='^', label='发电厂')
            ]
            
            if chinese_font:
                legend = ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1), prop=chinese_font)
            else:
                legend = ax.legend(handles=legend_elements, loc='upper left', bbox_to_anchor=(0, 1))
            
            # 添加统计信息
            stats_text = f"""
网络统计:
• 节点数: {len(G.nodes())}
• 线路数: {len(G.edges())}
• 发电机数: {len(self.generators_df)}
• 平均连接度: {2*len(G.edges())/len(G.nodes()):.1f}
"""
            
            ax.text(0.02, 0.02, stats_text, transform=ax.transAxes, fontsize=10,
                   verticalalignment='bottom', bbox=dict(boxstyle="round,pad=0.3", 
                   facecolor="white", alpha=0.9), 
                   **create_text_with_font(stats_text, chinese_font))
            
            plt.tight_layout()
            
            # 保存图表
            save_path = os.path.join(self.results_dir, 'network_topology.png')
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ 网络拓扑图已保存: {save_path}")
            
            plt.close()
            
        except Exception as e:
            print(f"❌ 生成网络拓扑图失败: {e}")
    
    def create_load_curve_plot(self):
        """生成负荷曲线图"""
        
        if self.load_curve_df is None:
            print("❌ 无负荷曲线数据")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(16, 10))
        chinese_font = get_chinese_font()
        fig.suptitle('IEEE 50节点系统负荷曲线分析', fontsize=16, fontweight='bold', 
                     **create_text_with_font('IEEE 50节点系统负荷曲线分析', chinese_font))
        
        # 1. 24小时负荷曲线
        times = self.load_curve_df['time'].values
        loads = self.load_curve_df['system_load_mw'].values
        
        # 创建时间轴
        time_labels = []
        for i in range(0, 96, 4):  # 每小时标记一次
            hour = i // 4
            time_labels.append(f"{hour:02d}:00")
        
        ax1.plot(range(len(loads)), loads, linewidth=2, color='#2E8B57', marker='o', markersize=3)
        ax1.set_title('系统负荷曲线 (96个时段)', fontweight='bold', 
                      **create_text_with_font('系统负荷曲线 (96个时段)', chinese_font))
        ax1.set_xlabel('时间', **create_text_with_font('时间', chinese_font))
        ax1.set_ylabel('系统负荷 (MW)', **create_text_with_font('系统负荷 (MW)', chinese_font))
        ax1.grid(True, alpha=0.3)
        
        # 设置x轴标签
        x_ticks = range(0, 96, 4)
        ax1.set_xticks(x_ticks)
        ax1.set_xticklabels(time_labels)
        
        # 标记峰值和谷值
        max_idx = np.argmax(loads)
        min_idx = np.argmin(loads)
        
        ax1.scatter(max_idx, loads[max_idx], color='red', s=100, zorder=5)
        ax1.scatter(min_idx, loads[min_idx], color='blue', s=100, zorder=5)
        
        ax1.annotate(f'峰值: {loads[max_idx]:.1f} MW\n{times[max_idx]}', 
                    xy=(max_idx, loads[max_idx]), xytext=(max_idx+10, loads[max_idx]+100),
                    arrowprops=dict(arrowstyle='->', color='red'), fontsize=10, 
                    **create_text_with_font(f'峰值: {loads[max_idx]:.1f} MW\n{times[max_idx]}', chinese_font))
        
        ax1.annotate(f'谷值: {loads[min_idx]:.1f} MW\n{times[min_idx]}', 
                    xy=(min_idx, loads[min_idx]), xytext=(min_idx+10, loads[min_idx]-100),
                    arrowprops=dict(arrowstyle='->', color='blue'), fontsize=10, 
                    **create_text_with_font(f'谷值: {loads[min_idx]:.1f} MW\n{times[min_idx]}', chinese_font))
        
        # 2. 负荷统计分析
        ax2.axis('off')
        
        # 计算负荷统计
        load_stats = {
            '峰值负荷': np.max(loads),
            '谷值负荷': np.min(loads),
            '平均负荷': np.mean(loads),
            '负荷率': np.mean(loads) / np.max(loads),
            '峰谷差': np.max(loads) - np.min(loads),
            '峰谷差率': (np.max(loads) - np.min(loads)) / np.max(loads)
        }
        
        # 负荷分布分析
        load_ranges = {
            '8000+ MW': np.sum(loads >= 8000),
            '7500-8000 MW': np.sum((loads >= 7500) & (loads < 8000)),
            '7000-7500 MW': np.sum((loads >= 7000) & (loads < 7500)),
            '<7000 MW': np.sum(loads < 7000)
        }
        
        stats_text = f"""
负荷曲线统计分析

基本统计:
• 峰值负荷: {load_stats['峰值负荷']:,.1f} MW
• 谷值负荷: {load_stats['谷值负荷']:,.1f} MW  
• 平均负荷: {load_stats['平均负荷']:,.1f} MW
• 负荷率: {load_stats['负荷率']:.3f}
• 峰谷差: {load_stats['峰谷差']:,.1f} MW
• 峰谷差率: {load_stats['峰谷差率']:.1%}

负荷分布 (时段数):
• 8000+ MW: {load_ranges['8000+ MW']} 时段
• 7500-8000 MW: {load_ranges['7500-8000 MW']} 时段  
• 7000-7500 MW: {load_ranges['7000-7500 MW']} 时段
• <7000 MW: {load_ranges['<7000 MW']} 时段

负荷特征:
• 典型双峰曲线（上午峰+晚峰）
• 高负荷率表明负荷相对稳定
• 适合基荷+调峰机组组合
"""
        
        ax2.text(0.05, 0.95, stats_text, transform=ax2.transAxes, fontsize=12,
                verticalalignment='top', bbox=dict(boxstyle="round,pad=0.5", 
                facecolor="lightyellow", alpha=0.9), 
                **create_text_with_font(stats_text, chinese_font))
        
        # 在图形级别应用中文字体
        apply_chinese_font_to_figure(fig, chinese_font)
        
        plt.tight_layout()
        
        # 保存图表
        save_path = os.path.join(self.results_dir, 'load_curve_analysis.png')
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"✅ 负荷曲线分析图表已保存: {save_path}")
        
        plt.close()
    
    def generate_comprehensive_report(self, results=None):
        """生成综合分析报告"""
        
        print(f"\n🔍 开始生成IEEE 50节点案例综合分析报告...")
        
        # 创建所有可视化图表
        print("📊 生成网络拓扑图...")
        self.create_network_topology_plot()
        
        print("📈 生成负荷曲线分析...")
        self.create_load_curve_plot()
        
        if results:
            print("⚡ 生成发电调度分析...")
            self.create_generation_dispatch_plot(results)
            
            print("💰 生成节点电价分析...")
            self.create_lmp_analysis_plot(results)
            
            print("💵 生成成本分析...")
            self.create_cost_analysis_plot(results)
        
        # 保存结果数据到CSV
        if results:
            self.save_results_to_csv(results)
        
        print(f"\n✅ 综合分析报告生成完成！")
        print(f"📁 所有图表和数据已保存到: {self.results_dir}")
        
        return self.results_dir
    
    def save_results_to_csv(self, results):
        """保存结果数据到CSV文件"""
        
        try:
            # 保存发电机结果
            if 'generators' in results:
                gen_df = pd.DataFrame(results['generators']).T
                gen_df.to_csv(os.path.join(self.results_dir, 'generator_results.csv'))
                print(f"✅ 发电机结果已保存: generator_results.csv")
            
            # 保存节点结果
            if 'buses' in results:
                bus_df = pd.DataFrame(results['buses']).T
                bus_df.to_csv(os.path.join(self.results_dir, 'bus_results.csv'))
                print(f"✅ 节点结果已保存: bus_results.csv")
            
            # 保存成本汇总
            if 'costs' in results:
                costs_df = pd.DataFrame([results['costs']])
                costs_df.to_csv(os.path.join(self.results_dir, 'cost_summary.csv'), index=False)
                print(f"✅ 成本汇总已保存: cost_summary.csv")
            
        except Exception as e:
            print(f"❌ 保存结果数据失败: {e}")


def analyze_ieee_50_bus_results(case_dir, solution=None):
    """
    分析IEEE 50节点案例结果的主函数
    
    Args:
        case_dir: 案例目录路径
        solution: 求解结果对象
    
    Returns:
        results_dir: 结果保存目录
    """
    
    analyzer = IEEE50BusResultsAnalyzer(case_dir, solution)
    
    # 提取求解结果
    results = None
    if solution:
        results = analyzer.extract_solution_results()
    
    # 生成综合报告
    results_dir = analyzer.generate_comprehensive_report(results)
    
    return results_dir


if __name__ == "__main__":
    # 测试分析器
    case_dir = "simpower/tests/ieee_50_bus_case"
    if os.path.exists(case_dir):
        analyze_ieee_50_bus_results(case_dir)
    else:
        print(f"❌ 案例目录不存在: {case_dir}")