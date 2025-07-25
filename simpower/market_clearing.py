"""
增强的容量段报价市场出清模块
提供完整的电力市场仿真和分析功能
"""

import pandas as pd
import numpy as np
import logging
from .optimization import value
from .config import user_config


class SegmentBiddingMarket:
    """
    容量段报价市场出清器
    支持分段线性投标曲线的电力市场仿真
    """
    
    def __init__(self, power_system, times):
        self.power_system = power_system
        self.times = times
        self.generators = power_system.generators()
        self.loads = power_system.loads()
        self.buses = getattr(power_system, 'buses', [])
        
        # 市场出清结果
        self.clearing_results = {}
        self.market_summary = {}
        
    def analyze_bidding_segments(self):
        """分析所有机组的投标段信息"""
        segment_info = {}
        
        for gen in self.generators:
            gen_info = {
                'name': gen.name,
                'type': getattr(gen, 'kind', 'unknown'),
                'segments': [],
                'is_segment_bidding': False
            }
            
            # 检查是否使用分段投标
            if hasattr(gen, 'bid_points') and gen.bid_points is not None:
                gen_info['is_segment_bidding'] = True
                
                # 解析投标段
                bid_points = gen.bid_points
                for i, row in bid_points.iterrows():
                    power = float(row['power'])
                    cost = float(row['cost'])
                    
                    # 计算边际成本
                    if i == 0:
                        marginal_cost = 0
                    else:
                        prev_power = float(bid_points.iloc[i-1]['power'])
                        prev_cost = float(bid_points.iloc[i-1]['cost'])
                        if power > prev_power:
                            marginal_cost = (cost - prev_cost) / (power - prev_power)
                        else:
                            marginal_cost = 0
                    
                    segment = {
                        'segment_id': i + 1,
                        'power_mw': power,
                        'total_cost': cost,
                        'marginal_cost_mwh': marginal_cost,
                        'capacity_mw': power - (float(bid_points.iloc[i-1]['power']) if i > 0 else 0)
                    }
                    gen_info['segments'].append(segment)
            
            segment_info[gen.name] = gen_info
        
        return segment_info
    
    def create_merit_order(self):
        """创建基于容量段的报价排序"""
        all_segments = []
        segment_info = self.analyze_bidding_segments()
        
        for gen_name, gen_info in segment_info.items():
            if gen_info['is_segment_bidding']:
                for i, segment in enumerate(gen_info['segments']):
                    if i > 0:  # 跳过第一个零出力点
                        all_segments.append({
                            'generator': gen_name,
                            'segment_id': segment['segment_id'],
                            'capacity_mw': segment['capacity_mw'],
                            'marginal_cost_mwh': segment['marginal_cost_mwh'],
                            'cumulative_power': segment['power_mw']
                        })
        
        # 按边际成本排序
        merit_order = sorted(all_segments, key=lambda x: x['marginal_cost_mwh'])
        
        # 添加累计容量
        cumulative_capacity = 0
        for segment in merit_order:
            cumulative_capacity += segment['capacity_mw']
            segment['cumulative_capacity_mw'] = cumulative_capacity
        
        return merit_order
    
    def analyze_market_clearing(self, time=None):
        """分析市场出清结果"""
        if time is None:
            time = self.times[0]
        
        # 获取总负载
        total_load = 0
        for load in self.loads:
            load_val = value(load.power(time))
            total_load += float(load_val) if load_val is not None else 0.0
        
        # 获取各机组出力
        generation_dispatch = {}
        total_generation = 0
        total_cost = 0
        
        for gen in self.generators:
            try:
                power_val = value(gen.power(time))
                power_float = float(power_val) if power_val is not None else 0.0
            except:
                power_float = 0.0
                
            try:
                cost_val = value(gen.bids.output(time))
                cost_float = float(cost_val) if cost_val is not None else 0.0
            except:
                cost_float = 0.0
                
            try:
                status_val = value(gen.status(time))
                status_float = float(status_val) if status_val is not None else 0.0
            except:
                status_float = 0.0
            
            generation_dispatch[gen.name] = {
                'power_mw': power_float,
                'cost': cost_float,
                'status': status_float,
                'capacity_factor': power_float / gen.pmax if gen.pmax > 0 else 0
            }
            
            total_generation += power_float
            total_cost += cost_float
        
        # 获取电价信息
        if self.buses:
            lmps = []
            for bus in self.buses:
                price_val = value(bus.price(time))
                lmps.append(float(price_val) if price_val is not None else 0.0)
            average_lmp = np.mean(lmps) if lmps else 0
        else:
            # 单节点系统，使用系统边际电价
            average_lmp = self._calculate_system_marginal_price(time)
        
        # 计算市场效率指标
        market_metrics = self._calculate_market_metrics(
            generation_dispatch, total_load, total_cost, average_lmp
        )
        
        clearing_result = {
            'time': time,
            'total_load_mw': total_load,
            'total_generation_mw': total_generation,
            'total_cost': total_cost,
            'average_lmp_mwh': average_lmp,
            'generation_dispatch': generation_dispatch,
            'market_metrics': market_metrics,
            'load_balance': abs(total_generation - total_load) < 0.01
        }
        
        return clearing_result
    
    def _calculate_system_marginal_price(self, time):
        """计算系统边际电价"""
        # 找到运行机组的最高边际成本
        max_marginal_cost = 0
        
        for gen in self.generators:
            power_val = value(gen.power(time))
            status_val = value(gen.status(time))
            
            power = float(power_val) if power_val is not None else 0.0
            status = float(status_val) if status_val is not None else 0.0
            
            if status > 0.5 and power > 0:  # 机组运行且有出力
                if hasattr(gen, 'bids'):
                    marginal_cost_val = gen.bids.output_incremental(gen.power(time))
                    marginal_cost = float(marginal_cost_val) if marginal_cost_val is not None else 0.0
                    max_marginal_cost = max(max_marginal_cost, marginal_cost)
        
        return max_marginal_cost
    
    def _calculate_market_metrics(self, dispatch, total_load, total_cost, lmp):
        """计算市场效率指标"""
        # 计算加权平均发电成本
        total_generation = sum(gen['power_mw'] for gen in dispatch.values())
        if total_generation > 0:
            weighted_avg_cost = total_cost / total_generation
        else:
            weighted_avg_cost = 0
        
        # 计算容量利用率
        capacity_utilization = {}
        for gen_name, gen_data in dispatch.items():
            gen = next(g for g in self.generators if g.name == gen_name)
            capacity_utilization[gen_name] = gen_data['power_mw'] / gen.pmax if gen.pmax > 0 else 0
        
        # 计算市场集中度 (HHI)
        if total_generation > 0:
            market_shares = [(gen['power_mw'] / total_generation) for gen in dispatch.values()]
            hhi = sum(share ** 2 for share in market_shares) * 10000
        else:
            hhi = 0
        
        return {
            'weighted_average_cost_mwh': weighted_avg_cost,
            'market_efficiency': (weighted_avg_cost / lmp) if lmp > 0 else 0,
            'capacity_utilization': capacity_utilization,
            'herfindahl_index': hhi,
            'market_concentration': 'High' if hhi > 2500 else 'Medium' if hhi > 1500 else 'Low'
        }
    
    def generate_market_report(self, time=None):
        """生成市场分析报告"""
        segment_info = self.analyze_bidding_segments()
        merit_order = self.create_merit_order()
        clearing_result = self.analyze_market_clearing(time)
        
        report = {
            'market_overview': {
                'analysis_time': str(clearing_result['time']),
                'total_generators': len(self.generators),
                'segment_bidding_generators': sum(1 for info in segment_info.values() if info['is_segment_bidding']),
                'total_segments': sum(len(info['segments']) for info in segment_info.values()),
            },
            'bidding_segments': segment_info,
            'merit_order': merit_order,
            'clearing_results': clearing_result
        }
        
        return report
    
    def print_market_summary(self, time=None):
        """打印市场出清总结"""
        report = self.generate_market_report(time)
        
        print("=" * 60)
        print("📊 容量段报价市场出清分析报告")
        print("=" * 60)
        
        # 市场概览
        overview = report['market_overview']
        print(f"\n🏭 市场概览:")
        print(f"  分析时间: {overview['analysis_time']}")
        print(f"  发电机总数: {overview['total_generators']}")
        print(f"  容量段报价机组: {overview['segment_bidding_generators']}")
        print(f"  总投标段数: {overview['total_segments']}")
        
        # 出清结果
        clearing = report['clearing_results']
        print(f"\n⚡ 市场出清结果:")
        print(f"  总负载: {clearing['total_load_mw']:.1f} MW")
        print(f"  总发电: {clearing['total_generation_mw']:.1f} MW")
        print(f"  发电成本: {clearing['total_cost']:.0f} $")
        print(f"  平均电价: {clearing['average_lmp_mwh']:.2f} $/MWh")
        print(f"  功率平衡: {'✅ 平衡' if clearing['load_balance'] else '❌ 不平衡'}")
        
        # 机组调度
        print(f"\n🔌 机组调度结果:")
        for gen_name, gen_data in clearing['generation_dispatch'].items():
            status_icon = "🟢" if gen_data['status'] > 0.5 else "🔴"
            print(f"  {status_icon} {gen_name:15s}: {gen_data['power_mw']:6.1f} MW "
                  f"(容量系数: {gen_data['capacity_factor']:.1%})")
        
        # 投标段分析
        print(f"\n📈 投标段分析:")
        for gen_name, gen_info in report['bidding_segments'].items():
            if gen_info['is_segment_bidding']:
                print(f"  📊 {gen_name} ({gen_info['type']}):")
                for segment in gen_info['segments'][1:]:  # 跳过零出力段
                    print(f"    段{segment['segment_id']}: {segment['capacity_mw']:6.1f}MW @ "
                          f"{segment['marginal_cost_mwh']:6.1f} $/MWh")
        
        # 市场指标
        metrics = clearing['market_metrics']
        print(f"\n📊 市场效率指标:")
        print(f"  加权平均成本: {metrics['weighted_average_cost_mwh']:.2f} $/MWh")
        print(f"  市场效率: {metrics['market_efficiency']:.1%}")
        print(f"  HHI指数: {metrics['herfindahl_index']:.0f}")
        print(f"  市场集中度: {metrics['market_concentration']}")
        
        print("=" * 60)


def enhance_bidding_analysis(solution):
    """
    为现有解决方案添加增强的投标分析功能
    """
    if hasattr(solution, 'power_system') and hasattr(solution, 'times'):
        market = SegmentBiddingMarket(solution.power_system, solution.times)
        
        # 添加市场分析方法到解决方案对象
        solution.market_clearing_analysis = market
        solution.print_bidding_summary = lambda: market.print_market_summary()
        solution.get_market_report = lambda: market.generate_market_report()
        
        return market
    else:
        logging.warning("Solution object does not have required attributes for bidding analysis")
        return None


def create_bidding_example(output_dir="bidding_example"):
    """
    创建容量段报价示例案例
    """
    import os
    
    # 创建示例目录
    os.makedirs(output_dir, exist_ok=True)
    
    # 创建发电机配置
    generators_csv = """name,type,P max,no load cost,cost curve points filename
Coal_Unit_1,coal,300,150,coal_unit_1_bids.csv
Gas_Unit_1,natural gas,200,80,gas_unit_1_bids.csv
Gas_Unit_2,natural gas,150,60,gas_unit_2_bids.csv
Hydro_Unit,hydro,100,10,hydro_unit_bids.csv"""
    
    with open(f"{output_dir}/generators.csv", "w") as f:
        f.write(generators_csv)
    
    # 创建负载配置
    loads_csv = """name,power
Industrial_Load,300
Residential_Load,250"""
    
    with open(f"{output_dir}/loads.csv", "w") as f:
        f.write(loads_csv)
    
    # 创建各机组投标文件
    
    # 煤电机组 - 低成本但启动成本高
    coal_bids = """power,cost
0,0
50,800
100,1500
150,2100
200,2800
250,3600
300,4500"""
    
    with open(f"{output_dir}/coal_unit_1_bids.csv", "w") as f:
        f.write(coal_bids)
    
    # 燃气机组1 - 中等成本，灵活启停
    gas1_bids = """power,cost
0,0
40,600
80,1300
120,2100
160,3000
200,4000"""
    
    with open(f"{output_dir}/gas_unit_1_bids.csv", "w") as f:
        f.write(gas1_bids)
    
    # 燃气机组2 - 高效但小容量
    gas2_bids = """power,cost
0,0
30,450
60,950
90,1500
120,2100
150,2750"""
    
    with open(f"{output_dir}/gas_unit_2_bids.csv", "w") as f:
        f.write(gas2_bids)
    
    # 水电机组 - 极低边际成本
    hydro_bids = """power,cost
0,0
25,50
50,100
75,150
100,200"""
    
    with open(f"{output_dir}/hydro_unit_bids.csv", "w") as f:
        f.write(hydro_bids)
    
    print(f"✅ 容量段报价示例已创建在 {output_dir}/ 目录")
    print("📊 包含4台不同类型机组的分段投标配置")
    print("⚡ 可直接运行: solve_problem('{}')".format(output_dir))
    
    return output_dir