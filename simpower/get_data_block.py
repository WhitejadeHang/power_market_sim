"""
支持容量段报价格式的数据读取模块
扩展原有的get_data模块，支持标准的容量段报价格式
"""

import pandas as pd
import logging
from .get_data import *  # 导入所有原有功能
from .bidding_block import BlockBid


def read_block_bid_points(filename, format_hint=None):
    """
    读取容量段报价文件
    
    Args:
        filename: CSV文件路径
        format_hint: 格式提示 ('block', 'cumulative', 'auto')
                    'block' - 容量段报价格式 (power, price)
                    'cumulative' - 累计总成本格式 (power, cost)  
                    'auto' - 自动检测
    
    Returns:
        dict: {'data': DataFrame, 'format': str, 'converted': bool}
    """
    try:
        # 读取CSV文件
        data = read_csv(filename)
        
        if data is None or len(data) == 0:
            logging.error(f"Empty or invalid bid points file: {filename}")
            return {'data': None, 'format': 'unknown', 'converted': False}
        
        # 标准化列名
        data.columns = data.columns.str.strip()
        
        # 检测格式
        detected_format = _detect_bid_format(data)
        
        # 确定最终格式
        if format_hint == 'auto' or format_hint is None:
            final_format = detected_format
        else:
            final_format = format_hint
        
        logging.info(f"Bid file {filename}: detected={detected_format}, using={final_format}")
        
        # 确保数据类型正确
        data = _ensure_numeric_data(data, final_format)
        
        return {
            'data': data,
            'format': final_format,
            'converted': detected_format != final_format
        }
        
    except Exception as e:
        logging.error(f"Error reading bid points file {filename}: {e}")
        return {'data': None, 'format': 'error', 'converted': False}


def _detect_bid_format(data):
    """
    自动检测投标数据格式
    """
    columns = [col.lower() for col in data.columns]
    
    # 检查列名特征
    has_power = any(col in columns for col in ['power', 'capacity', 'mw', 'p'])
    has_price = any(col in columns for col in ['price', 'rate', '$/mwh', 'price_mwh'])
    has_cost = any(col in columns for col in ['cost', 'total_cost', 'cumulative_cost'])
    
    if has_power and has_price and not has_cost:
        return 'block'
    elif has_power and has_cost and not has_price:
        return 'cumulative'
    elif has_power and has_cost:
        # 同时有cost和price，通过数值特征判断
        return _detect_by_values(data)
    else:
        # 默认检查前两列
        if len(data.columns) >= 2:
            return _detect_by_values(data)
        else:
            return 'unknown'


def _detect_by_values(data):
    """
    通过数值特征检测格式
    """
    if len(data) < 2:
        return 'unknown'
    
    # 使用前两列进行分析
    col1 = data.columns[0]  # 假设是power
    col2 = data.columns[1]  # 假设是price或cost
    
    try:
        powers = pd.to_numeric(data[col1], errors='coerce')
        values = pd.to_numeric(data[col2], errors='coerce')
        
        # 检查是否有NaN
        if powers.isna().any() or values.isna().any():
            return 'unknown'
        
        # 计算隐含边际成本
        marginal_costs = []
        for i in range(1, len(powers)):
            if powers.iloc[i] > powers.iloc[i-1]:
                mc = (values.iloc[i] - values.iloc[i-1]) / (powers.iloc[i] - powers.iloc[i-1])
                marginal_costs.append(mc)
        
        if marginal_costs:
            avg_mc = sum(marginal_costs) / len(marginal_costs)
            max_mc = max(marginal_costs)
            
            # 判断逻辑
            if max_mc > 1000 or avg_mc > 500:
                # 边际成本过高，可能是累计总成本
                return 'cumulative'
            elif avg_mc < 100 and all(0 <= mc <= 1000 for mc in marginal_costs):
                # 边际成本合理，可能是容量段报价
                return 'block'
            else:
                # 边际成本中等，可能是累计总成本
                return 'cumulative'
        
        return 'cumulative'  # 默认
        
    except Exception:
        return 'unknown'


def _ensure_numeric_data(data, format_type):
    """
    确保数据为数值类型
    """
    data = data.copy()
    
    if format_type == 'block':
        # 容量段报价格式
        power_col, price_col = _find_columns(data, 'block')
        if power_col and price_col:
            data[power_col] = pd.to_numeric(data[power_col], errors='coerce')
            data[price_col] = pd.to_numeric(data[price_col], errors='coerce')
            # 重命名为标准列名
            if power_col != 'power':
                data = data.rename(columns={power_col: 'power'})
            if price_col != 'price':
                data = data.rename(columns={price_col: 'price'})
    
    elif format_type == 'cumulative':
        # 累计总成本格式
        power_col, cost_col = _find_columns(data, 'cumulative')
        if power_col and cost_col:
            data[power_col] = pd.to_numeric(data[power_col], errors='coerce')
            data[cost_col] = pd.to_numeric(data[cost_col], errors='coerce')
            # 重命名为标准列名
            if power_col != 'power':
                data = data.rename(columns={power_col: 'power'})
            if cost_col != 'cost':
                data = data.rename(columns={cost_col: 'cost'})
    
    else:
        # 未知格式，尝试转换前两列
        if len(data.columns) >= 2:
            col1, col2 = data.columns[0], data.columns[1]
            data[col1] = pd.to_numeric(data[col1], errors='coerce')
            data[col2] = pd.to_numeric(data[col2], errors='coerce')
            data.columns = ['power', 'cost']  # 默认为累计成本格式
    
    return data


def _find_columns(data, format_type):
    """
    查找对应格式的列名
    """
    columns = data.columns
    power_col = None
    value_col = None
    
    # 查找功率列
    for col in columns:
        col_lower = col.lower()
        if col_lower in ['power', 'capacity', 'mw', 'p']:
            power_col = col
            break
    
    # 查找价值列
    if format_type == 'block':
        # 查找价格列
        for col in columns:
            col_lower = col.lower()
            if col_lower in ['price', 'rate', '$/mwh', 'price_mwh']:
                value_col = col
                break
    elif format_type == 'cumulative':
        # 查找成本列
        for col in columns:
            col_lower = col.lower()
            if col_lower in ['cost', 'total_cost', 'cumulative_cost']:
                value_col = col
                break
    
    # 如果没有找到，使用前两列
    if power_col is None and len(columns) >= 1:
        power_col = columns[0]
    if value_col is None and len(columns) >= 2:
        value_col = columns[1]
    
    return power_col, value_col


def create_generator_with_block_bidding(generator_data, bid_file=None, bid_format='auto'):
    """
    使用容量段报价创建发电机
    
    Args:
        generator_data: 发电机基本数据字典
        bid_file: 投标文件路径
        bid_format: 投标格式 ('block', 'cumulative', 'auto')
    
    Returns:
        发电机对象
    """
    from .generators import Generator
    
    # 读取投标数据
    if bid_file:
        bid_info = read_block_bid_points(bid_file, bid_format)
        if bid_info['data'] is not None:
            # 创建BlockBid对象
            block_format = bid_info['format'] == 'block'
            bid_obj = BlockBid(
                bid_points=bid_info['data'],
                block_format=block_format
            )
            generator_data['bid_points'] = bid_obj.get_cumulative_cost_data()
    
    # 创建发电机
    generator = Generator(**generator_data)
    
    # 如果有投标数据，替换默认的bid对象
    if bid_file and bid_info['data'] is not None:
        generator.bids = BlockBid(
            bid_points=bid_info['data'],
            block_format=bid_info['format'] == 'block',
            owner=generator
        )
    
    return generator


def convert_csv_format(input_file, output_file, source_format='auto', target_format='cumulative'):
    """
    转换CSV文件格式
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径  
        source_format: 源格式 ('block', 'cumulative', 'auto')
        target_format: 目标格式 ('block', 'cumulative')
    
    Returns:
        bool: 转换是否成功
    """
    try:
        # 读取源文件
        bid_info = read_block_bid_points(input_file, source_format)
        
        if bid_info['data'] is None:
            logging.error(f"Cannot read input file: {input_file}")
            return False
        
        source_fmt = bid_info['format']
        data = bid_info['data']
        
        if source_fmt == target_format:
            # 格式相同，直接复制
            data.to_csv(output_file, index=False)
            logging.info(f"File copied: {input_file} -> {output_file}")
            return True
        
        elif source_fmt == 'block' and target_format == 'cumulative':
            # 容量段报价 -> 累计总成本
            bid_obj = BlockBid(bid_points=data, block_format=True)
            cumulative_data = bid_obj.get_cumulative_cost_data()
            cumulative_data.to_csv(output_file, index=False)
            logging.info(f"Converted block to cumulative: {input_file} -> {output_file}")
            return True
        
        elif source_fmt == 'cumulative' and target_format == 'block':
            # 累计总成本 -> 容量段报价
            bid_obj = BlockBid(bid_points=data, block_format=False)
            block_schedule = bid_obj.get_block_schedule()
            
            # 转换为标准容量段报价格式
            block_data = []
            for i, row in block_schedule.iterrows():
                if i == 0:
                    # 添加起始点
                    block_data.append({
                        'power': row['power_from'],
                        'price': 0
                    })
                block_data.append({
                    'power': row['power_to'],
                    'price': row['price_mwh']
                })
            
            result_df = pd.DataFrame(block_data)
            result_df.to_csv(output_file, index=False)
            logging.info(f"Converted cumulative to block: {input_file} -> {output_file}")
            return True
        
        else:
            logging.error(f"Unsupported conversion: {source_fmt} -> {target_format}")
            return False
    
    except Exception as e:
        logging.error(f"Conversion failed: {e}")
        return False


# 重写原有的read_bid_points函数，支持新格式
def read_bid_points(filename, format_hint='auto'):
    """
    增强版的投标点读取函数
    自动检测和支持多种格式
    """
    bid_info = read_block_bid_points(filename, format_hint)
    
    if bid_info['data'] is None:
        return None
    
    # 确保返回累计总成本格式（保持向后兼容）
    if bid_info['format'] == 'block':
        # 需要转换为累计总成本格式
        bid_obj = BlockBid(bid_points=bid_info['data'], block_format=True)
        return bid_obj.get_cumulative_cost_data()
    else:
        # 已经是累计总成本格式
        return bid_info['data']