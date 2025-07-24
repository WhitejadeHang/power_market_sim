"""
容量段报价bidding模块
支持标准的容量段报价格式 (power, price)，单位为$/MWh
"""

import numpy as np
import pandas as pd
import logging
from .bidding import Bid as OriginalBid, parse_polynomial
from .optimization import value, OptimizationObject
from .config import user_config
from .commonscripts import update_attributes
from pyomo.environ import Piecewise


class BlockBid(OriginalBid):
    """
    容量段报价类
    支持标准的电力市场容量段报价格式:
    - 输入格式: (power, price) 其中price单位为$/MWh
    - 内部转换: 自动转换为累计总成本用于优化
    - 输出格式: 支持容量段报价和累计总成本两种格式
    """
    
    def __init__(
        self,
        polynomial="10P",
        bid_points=None,
        block_format=True,  # True表示输入为容量段报价格式
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
        self.block_format = block_format
        self.original_bid_points = bid_points.copy() if bid_points is not None else None
        
        # 预处理投标数据
        if bid_points is not None and block_format:
            bid_points = self._convert_block_to_cumulative(bid_points)
        
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
    
    def _convert_block_to_cumulative(self, block_data):
        """
        将容量段报价格式转换为累计总成本格式
        输入: (power, price) 其中price为$/MWh
        输出: (power, cost) 其中cost为累计总成本$
        """
        if not isinstance(block_data, pd.DataFrame):
            logging.error("bid_points must be a pandas DataFrame")
            return block_data
        
        # 标准化列名
        block_data.columns = block_data.columns.str.strip()
        
        # 检查列名，支持多种命名方式
        power_col = None
        price_col = None
        
        for col in block_data.columns:
            col_lower = col.lower()
            if col_lower in ['power', 'capacity', 'mw', 'p']:
                power_col = col
            elif col_lower in ['price', 'cost', 'rate', '$/mwh', 'price_mwh']:
                price_col = col
        
        if power_col is None:
            logging.error("No power column found. Expected column names: 'power', 'capacity', 'MW', 'P'")
            return block_data
        
        if price_col is None:
            logging.error("No price column found. Expected column names: 'price', 'cost', 'rate', '$/MWh'")
            return block_data
        
        # 排序确保功率递增
        block_data = block_data.sort_values(power_col).reset_index(drop=True)
        
        # 转换为累计总成本格式
        cumulative_data = []
        cumulative_cost = 0.0
        
        for i, row in block_data.iterrows():
            power = row[power_col]
            price = row[price_col]
            
            if i == 0:
                # 第一个点，通常是起始点
                cumulative_data.append({
                    'power': power,
                    'cost': cumulative_cost
                })
            else:
                # 计算该段的成本
                prev_power = block_data.iloc[i-1][power_col]
                segment_capacity = power - prev_power
                segment_cost = segment_capacity * price
                cumulative_cost += segment_cost
                
                cumulative_data.append({
                    'power': power,
                    'cost': cumulative_cost
                })
        
        result = pd.DataFrame(cumulative_data)
        
        logging.info(f"Converted block bidding to cumulative cost format: {len(result)} points")
        self._log_conversion_details(block_data, result, power_col, price_col)
        
        return result
    
    def _log_conversion_details(self, original, converted, power_col, price_col):
        """记录转换详情"""
        logging.info("Block bidding conversion details:")
        for i in range(len(original)):
            power = original.iloc[i][power_col]
            if i == 0:
                logging.info(f"  Point {i+1}: {power}MW (starting point)")
            else:
                prev_power = original.iloc[i-1][power_col] 
                price = original.iloc[i][price_col]
                cumulative_cost = converted.iloc[i]['cost']
                segment_capacity = power - prev_power
                logging.info(f"  Point {i+1}: {prev_power}-{power}MW @ {price:.1f}$/MWh → cumulative cost {cumulative_cost:.1f}$")
    
    def get_block_schedule(self):
        """
        获取容量段报价时间表
        返回标准的容量段报价格式
        """
        if not hasattr(self, 'bid_points') or self.bid_points is None:
            return None
        
        if self.block_format and hasattr(self, 'original_bid_points'):
            # 如果原始输入就是容量段格式，直接使用
            original = self.original_bid_points.copy()
            original.columns = original.columns.str.strip()
            
            # 标准化列名
            power_col = None
            price_col = None
            for col in original.columns:
                col_lower = col.lower()
                if col_lower in ['power', 'capacity', 'mw', 'p']:
                    power_col = col
                elif col_lower in ['price', 'cost', 'rate', '$/mwh', 'price_mwh']:
                    price_col = col
            
            if power_col and price_col:
                schedule = []
                for i in range(1, len(original)):
                    power_from = original.iloc[i-1][power_col]
                    power_to = original.iloc[i][power_col]
                    price = original.iloc[i][price_col]
                    
                    schedule.append({
                        'block': i,
                        'power_from': power_from,
                        'power_to': power_to,
                        'capacity_mw': power_to - power_from,
                        'price_mwh': price
                    })
                
                return pd.DataFrame(schedule)
        
        # 从累计总成本格式反推容量段报价
        schedule = []
        bid_points = self.bid_points
        
        for i in range(1, len(bid_points)):
            power_from = bid_points.iloc[i-1]['power']
            power_to = bid_points.iloc[i]['power']
            cost_from = bid_points.iloc[i-1]['cost']
            cost_to = bid_points.iloc[i]['cost']
            
            capacity = power_to - power_from
            segment_cost = cost_to - cost_from
            price = segment_cost / capacity if capacity > 0 else 0
            
            schedule.append({
                'block': i,
                'power_from': power_from,
                'power_to': power_to,
                'capacity_mw': capacity,
                'price_mwh': price
            })
        
        return pd.DataFrame(schedule)
    
    def get_cumulative_cost_data(self):
        """
        获取累计总成本数据 (内部格式)
        """
        return self.bid_points.copy() if self.bid_points is not None else None
    
    def output_block_price(self, power_level):
        """
        计算指定功率水平的容量段价格
        """
        if not hasattr(self, 'bid_points') or self.bid_points is None:
            return 0
        
        bid_points = self.bid_points
        power_val = value(power_level) if hasattr(power_level, '__call__') else power_level
        
        # 找到对应的容量段
        for i in range(1, len(bid_points)):
            power_from = bid_points.iloc[i-1]['power']
            power_to = bid_points.iloc[i]['power']
            
            if power_from <= power_val <= power_to:
                cost_from = bid_points.iloc[i-1]['cost']
                cost_to = bid_points.iloc[i]['cost']
                capacity = power_to - power_from
                segment_cost = cost_to - cost_from
                return segment_cost / capacity if capacity > 0 else 0
        
        # 如果超出范围，使用最后一段的价格
        if len(bid_points) >= 2:
            last_segment = len(bid_points) - 1
            power_from = bid_points.iloc[last_segment-1]['power']
            power_to = bid_points.iloc[last_segment]['power']
            cost_from = bid_points.iloc[last_segment-1]['cost']
            cost_to = bid_points.iloc[last_segment]['cost']
            capacity = power_to - power_from
            segment_cost = cost_to - cost_from
            return segment_cost / capacity if capacity > 0 else 0
        
        return 0
    
    def get_bid_summary(self):
        """
        获取投标总结信息
        """
        summary = {
            'format': 'block_bidding' if self.block_format else 'cumulative_cost',
            'total_blocks': 0,
            'power_range': (self.min_input, self.max_input),
            'is_piecewise_linear': self.is_pwl,
        }
        
        block_schedule = self.get_block_schedule()
        if block_schedule is not None and len(block_schedule) > 0:
            summary.update({
                'total_blocks': len(block_schedule),
                'min_power': block_schedule['power_from'].min(),
                'max_power': block_schedule['power_to'].max(),
                'min_price': block_schedule['price_mwh'].min(),
                'max_price': block_schedule['price_mwh'].max(),
                'avg_price': block_schedule['price_mwh'].mean(),
                'total_capacity': block_schedule['capacity_mw'].sum(),
            })
        
        return summary


def create_block_bid_from_prices(power_points, prices, **kwargs):
    """
    从功率点和价格创建容量段报价对象
    
    Args:
        power_points: 功率端点列表 [0, 100, 200, 300] MW
        prices: 价格列表 [10, 15, 20] $/MWh (比功率点少1个)
        **kwargs: 其他BlockBid参数
    
    Returns:
        BlockBid对象
    """
    if len(prices) != len(power_points) - 1:
        raise ValueError("prices length must be power_points length - 1")
    
    # 构建容量段报价数据
    bid_data = []
    
    for i, power in enumerate(power_points):
        if i == 0:
            # 起始点
            bid_data.append({
                'power': power,
                'price': 0  # 起始点价格为0
            })
        else:
            # 容量段价格
            price = prices[i-1]
            bid_data.append({
                'power': power,
                'price': price
            })
    
    bid_points = pd.DataFrame(bid_data)
    
    return BlockBid(
        bid_points=bid_points,
        block_format=True,
        **kwargs
    )


def create_block_bid_from_segments(segments, **kwargs):
    """
    从容量段列表创建容量段报价对象
    
    Args:
        segments: 容量段列表 [{'from': 0, 'to': 100, 'price': 10}, ...]
        **kwargs: 其他BlockBid参数
    
    Returns:
        BlockBid对象
    """
    # 提取所有功率点
    power_points = set()
    for seg in segments:
        power_points.add(seg['from'])
        power_points.add(seg['to'])
    
    power_points = sorted(list(power_points))
    
    # 构建价格数据
    bid_data = []
    
    for power in power_points:
        # 找到这个功率点对应的价格
        price = 0
        for seg in segments:
            if seg['from'] < power <= seg['to']:
                price = seg['price']
                break
        
        bid_data.append({
            'power': power,
            'price': price
        })
    
    bid_points = pd.DataFrame(bid_data)
    
    return BlockBid(
        bid_points=bid_points,
        block_format=True,
        **kwargs
    )


# 为了向后兼容，创建别名
Bid = BlockBid