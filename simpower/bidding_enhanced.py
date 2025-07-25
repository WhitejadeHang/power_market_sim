"""
增强的投标模块
支持容量段总价格和边际成本两种报价格式
"""

import numpy as np
import pandas as pd
import logging
from .bidding import Bid as OriginalBid, parse_polynomial
from .optimization import value, OptimizationObject
from .config import user_config
from .commonscripts import update_attributes
from pyomo.environ import Piecewise


class EnhancedBid(OriginalBid):
    """
    增强的投标类，支持多种报价格式
    
    支持格式:
    1. 容量段总价格 (power, cost) - 累计总成本
    2. 边际成本报价 (power, marginal_cost) - 每段边际成本
    3. 混合格式 (power, cost, marginal_cost) - 同时提供
    """
    
    def __init__(
        self,
        polynomial="10P",
        bid_points=None,
        bid_format="total_cost",  # "total_cost", "marginal_cost", "auto"
        constant_term=0,
        owner=None,
        times=None,
        input_variable=0,
        min_input=0,
        max_input=1000,
        num_breakpoints=user_config.breakpoints,
        status_variable=True,
        fixed_input=False,
    ):
        self.bid_format = bid_format
        self.original_bid_points = bid_points.copy() if bid_points is not None else None
        
        # 预处理投标数据
        if bid_points is not None:
            bid_points = self._preprocess_bid_points(bid_points, bid_format)
        
        # 设置默认值以避免AttributeError
        if owner is None:
            # 创建虚拟owner用于测试
            class DummyOwner:
                def __init__(self):
                    self._parent_problem = None
                def __str__(self):
                    return "dummy_owner"
            owner = DummyOwner()
        
        if times is None:
            # 创建虚拟times用于测试
            class DummyTimes:
                def __init__(self):
                    self.set = ['t1']
                    self._set = ['t1']
            times = DummyTimes()
        
        # 调用原始初始化
        super().__init__(
            polynomial=polynomial,
            bid_points=bid_points,
            constant_term=constant_term,
            owner=owner,
            times=times,
            input_variable=input_variable,
            min_input=min_input,
            max_input=max_input,
            num_breakpoints=num_breakpoints,
            status_variable=status_variable,
            fixed_input=fixed_input,
        )
    
    def _preprocess_bid_points(self, bid_points, bid_format):
        """
        预处理投标点数据，统一转换为总成本格式
        """
        if not isinstance(bid_points, pd.DataFrame):
            logging.error("bid_points must be a pandas DataFrame")
            return bid_points
        
        # 标准化列名
        bid_points.columns = bid_points.columns.str.strip()
        
        # 自动检测格式
        if bid_format == "auto":
            bid_format = self._detect_bid_format(bid_points)
            logging.info(f"Auto-detected bid format: {bid_format}")
        
        if bid_format == "marginal_cost":
            return self._convert_marginal_to_total(bid_points)
        elif bid_format == "total_cost":
            return self._validate_total_cost_format(bid_points)
        else:
            logging.warning(f"Unknown bid format: {bid_format}, using as-is")
            return bid_points
    
    def _detect_bid_format(self, bid_points):
        """
        自动检测投标格式
        """
        if 'marginal_cost' in bid_points.columns:
            return "marginal_cost"
        elif 'cost' in bid_points.columns:
            # 检查是否是递增的总成本
            if len(bid_points) > 1:
                costs = bid_points['cost'].values
                powers = bid_points['power'].values
                
                # 检查成本是否递增且斜率合理
                slopes = []
                for i in range(1, len(costs)):
                    if powers[i] > powers[i-1]:
                        slope = (costs[i] - costs[i-1]) / (powers[i] - powers[i-1])
                        slopes.append(slope)
                
                if slopes:
                    # 如果斜率都在合理范围内(0-1000 $/MWh)，可能是总成本
                    if all(0 <= slope <= 1000 for slope in slopes):
                        return "total_cost"
                    # 如果斜率很小(<50 $/MWh)，可能是边际成本
                    elif all(slope < 50 for slope in slopes):
                        return "marginal_cost"
            
            return "total_cost"  # 默认假设为总成本
        else:
            logging.warning("No recognized cost column found")
            return "total_cost"
    
    def _convert_marginal_to_total(self, bid_points):
        """
        将边际成本报价转换为总成本格式
        """
        if 'marginal_cost' not in bid_points.columns:
            logging.error("marginal_cost column not found for marginal cost format")
            return bid_points
        
        converted_points = bid_points.copy()
        converted_points['cost'] = 0.0
        
        # 计算累计总成本
        for i in range(1, len(converted_points)):
            power_diff = converted_points.iloc[i]['power'] - converted_points.iloc[i-1]['power']
            marginal_cost = converted_points.iloc[i]['marginal_cost']
            segment_cost = power_diff * marginal_cost
            converted_points.iloc[i, converted_points.columns.get_loc('cost')] = \
                converted_points.iloc[i-1]['cost'] + segment_cost
        
        logging.info("Converted marginal cost bidding to total cost format")
        self._log_conversion_details(bid_points, converted_points)
        
        return converted_points[['power', 'cost']]
    
    def _validate_total_cost_format(self, bid_points):
        """
        验证总成本格式的合理性
        """
        if 'cost' not in bid_points.columns:
            logging.error("cost column not found for total cost format")
            return bid_points
        
        # 检查成本递增性
        costs = bid_points['cost'].values
        powers = bid_points['power'].values
        
        for i in range(1, len(costs)):
            if costs[i] < costs[i-1]:
                logging.warning(f"Non-increasing cost detected at segment {i}: {costs[i-1]} -> {costs[i]}")
            
            if powers[i] > powers[i-1]:
                marginal = (costs[i] - costs[i-1]) / (powers[i] - powers[i-1])
                if marginal < 0:
                    logging.warning(f"Negative marginal cost detected at segment {i}: {marginal:.2f} $/MWh")
                elif marginal > 1000:
                    logging.warning(f"Very high marginal cost detected at segment {i}: {marginal:.2f} $/MWh")
        
        return bid_points[['power', 'cost']]
    
    def _log_conversion_details(self, original, converted):
        """
        记录转换详情
        """
        logging.info("Bidding conversion details:")
        for i in range(len(original)):
            power = original.iloc[i]['power']
            if 'marginal_cost' in original.columns:
                marginal = original.iloc[i]['marginal_cost']
                total = converted.iloc[i]['cost']
                logging.info(f"  Segment {i+1}: {power}MW, marginal={marginal:.1f}$/MWh -> total={total:.1f}$")
    
    def get_marginal_cost_schedule(self):
        """
        获取边际成本时间表
        """
        if not hasattr(self, 'bid_points') or self.bid_points is None:
            return None
        
        schedule = []
        bid_points = self.bid_points
        
        for i in range(1, len(bid_points)):
            power_from = bid_points.iloc[i-1]['power']
            power_to = bid_points.iloc[i]['power']
            cost_from = bid_points.iloc[i-1]['cost']
            cost_to = bid_points.iloc[i]['cost']
            
            if power_to > power_from:
                marginal_cost = (cost_to - cost_from) / (power_to - power_from)
                schedule.append({
                    'segment': i,
                    'power_from': power_from,
                    'power_to': power_to,
                    'capacity': power_to - power_from,
                    'marginal_cost': marginal_cost,
                    'segment_cost': cost_to - cost_from
                })
        
        return pd.DataFrame(schedule)
    
    def get_bid_summary(self):
        """
        获取投标总结信息
        """
        summary = {
            'bid_format': self.bid_format,
            'total_segments': len(self.bid_points) if self.bid_points is not None else 0,
            'power_range': (self.min_input, self.max_input),
            'is_piecewise_linear': self.is_pwl,
        }
        
        if self.bid_points is not None and len(self.bid_points) > 0:
            summary.update({
                'min_power': self.bid_points['power'].min(),
                'max_power': self.bid_points['power'].max(),
                'total_cost_at_max': self.bid_points['cost'].iloc[-1],
            })
            
            # 计算边际成本范围
            marginal_schedule = self.get_marginal_cost_schedule()
            if marginal_schedule is not None and len(marginal_schedule) > 0:
                summary.update({
                    'min_marginal_cost': marginal_schedule['marginal_cost'].min(),
                    'max_marginal_cost': marginal_schedule['marginal_cost'].max(),
                    'avg_marginal_cost': marginal_schedule['marginal_cost'].mean(),
                })
        
        return summary


def create_bidding_from_marginal_costs(power_segments, marginal_costs, **kwargs):
    """
    从边际成本创建投标对象
    
    Args:
        power_segments: 功率段端点列表 [0, 100, 200, 300]
        marginal_costs: 边际成本列表 [10, 15, 20] (比功率段少1个)
        **kwargs: 其他Bid参数
    
    Returns:
        EnhancedBid对象
    """
    if len(marginal_costs) != len(power_segments) - 1:
        raise ValueError("marginal_costs length must be power_segments length - 1")
    
    # 构建投标点数据
    bid_data = []
    cumulative_cost = 0
    
    for i, power in enumerate(power_segments):
        bid_data.append({
            'power': power,
            'marginal_cost': marginal_costs[i] if i < len(marginal_costs) else marginal_costs[-1],
            'cost': cumulative_cost
        })
        
        # 计算下一段的累计成本
        if i < len(marginal_costs):
            power_diff = power_segments[i+1] - power if i+1 < len(power_segments) else 0
            cumulative_cost += power_diff * marginal_costs[i]
    
    bid_points = pd.DataFrame(bid_data)
    
    return EnhancedBid(
        bid_points=bid_points,
        bid_format="marginal_cost",
        **kwargs
    )


def create_bidding_from_total_costs(power_points, total_costs, **kwargs):
    """
    从总成本创建投标对象 (当前标准格式)
    
    Args:
        power_points: 功率点列表 [0, 100, 150, 200]
        total_costs: 总成本列表 [0, 1000, 1550, 2200]
        **kwargs: 其他Bid参数
    
    Returns:
        EnhancedBid对象
    """
    if len(power_points) != len(total_costs):
        raise ValueError("power_points and total_costs must have same length")
    
    bid_points = pd.DataFrame({
        'power': power_points,
        'cost': total_costs
    })
    
    return EnhancedBid(
        bid_points=bid_points,
        bid_format="total_cost",
        **kwargs
    )


def analyze_bidding_format(bid_file):
    """
    分析CSV投标文件的格式
    
    Args:
        bid_file: CSV文件路径
        
    Returns:
        dict: 分析结果
    """
    try:
        df = pd.read_csv(bid_file)
        df.columns = df.columns.str.strip()
        
        analysis = {
            'file': bid_file,
            'columns': df.columns.tolist(),
            'num_segments': len(df),
            'detected_format': None,
            'recommendations': []
        }
        
        # 检测格式
        if 'marginal_cost' in df.columns:
            analysis['detected_format'] = 'marginal_cost'
            analysis['recommendations'].append("Use bid_format='marginal_cost' when loading")
        elif 'cost' in df.columns:
            # 分析成本数据特征
            if len(df) > 1:
                powers = df['power'].values
                costs = df['cost'].values
                
                marginal_costs = []
                for i in range(1, len(costs)):
                    if powers[i] > powers[i-1]:
                        mc = (costs[i] - costs[i-1]) / (powers[i] - powers[i-1])
                        marginal_costs.append(mc)
                
                if marginal_costs:
                    avg_mc = np.mean(marginal_costs)
                    max_mc = np.max(marginal_costs)
                    
                    analysis['marginal_cost_stats'] = {
                        'min': np.min(marginal_costs),
                        'max': max_mc,
                        'mean': avg_mc,
                        'std': np.std(marginal_costs)
                    }
                    
                    if max_mc > 1000 or avg_mc > 500:
                        analysis['detected_format'] = 'unclear_high_values'
                        analysis['recommendations'].append("High cost values detected - verify if these are total costs or marginal costs")
                    else:
                        analysis['detected_format'] = 'total_cost'
                        analysis['recommendations'].append("Use bid_format='total_cost' (default)")
        
        return analysis
        
    except Exception as e:
        return {
            'file': bid_file,
            'error': str(e),
            'recommendations': ['Check file format and accessibility']
        }


def convert_marginal_to_total_csv(input_file, output_file):
    """
    将边际成本CSV转换为总成本CSV
    
    Args:
        input_file: 输入的边际成本CSV文件
        output_file: 输出的总成本CSV文件
    """
    try:
        df = pd.read_csv(input_file)
        df.columns = df.columns.str.strip()
        
        if 'marginal_cost' not in df.columns:
            raise ValueError("Input file must have 'marginal_cost' column")
        
        # 创建增强投标对象进行转换
        enhanced_bid = EnhancedBid(bid_points=df, bid_format="marginal_cost")
        converted_points = enhanced_bid.bid_points
        
        # 保存转换结果
        converted_points.to_csv(output_file, index=False)
        
        logging.info(f"Converted {input_file} to {output_file}")
        return True
        
    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        return False


# 为了向后兼容，创建别名
Bid = EnhancedBid