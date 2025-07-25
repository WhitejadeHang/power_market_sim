"""
投标格式转换工具
支持边际成本和容量段总价格两种格式的相互转换
"""

import pandas as pd
import numpy as np
import logging
import os
from typing import Union, Tuple, Dict, List


class BiddingFormatConverter:
    """
    投标格式转换器
    支持边际成本和容量段总价格格式的相互转换
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def detect_format(self, data: Union[pd.DataFrame, str]) -> Dict:
        """
        自动检测投标数据格式
        
        Args:
            data: DataFrame或CSV文件路径
            
        Returns:
            dict: 检测结果
        """
        if isinstance(data, str):
            if not os.path.exists(data):
                return {'error': f'File not found: {data}'}
            data = pd.read_csv(data)
        
        # 标准化列名
        data.columns = data.columns.str.strip()
        
        result = {
            'columns': data.columns.tolist(),
            'num_rows': len(data),
            'detected_format': 'unknown',
            'confidence': 0.0,
            'recommendations': []
        }
        
        # 检测列类型
        if 'marginal_cost' in data.columns:
            result['detected_format'] = 'marginal_cost'
            result['confidence'] = 0.95
            result['recommendations'].append("使用边际成本格式")
        elif 'cost' in data.columns and 'power' in data.columns:
            # 分析成本数据特征
            if len(data) > 1:
                powers = data['power'].values
                costs = data['cost'].values
                
                # 计算隐含的边际成本
                marginal_costs = []
                for i in range(1, len(costs)):
                    if powers[i] > powers[i-1]:
                        mc = (costs[i] - costs[i-1]) / (powers[i] - powers[i-1])
                        marginal_costs.append(mc)
                
                if marginal_costs:
                    avg_mc = np.mean(marginal_costs)
                    std_mc = np.std(marginal_costs)
                    max_mc = np.max(marginal_costs)
                    min_mc = np.min(marginal_costs)
                    
                    result['marginal_cost_stats'] = {
                        'min': min_mc,
                        'max': max_mc,
                        'mean': avg_mc,
                        'std': std_mc
                    }
                    
                    # 判断逻辑
                    if all(c >= 0 for c in marginal_costs) and max_mc < 1000:
                        result['detected_format'] = 'total_cost'
                        result['confidence'] = 0.85
                        result['recommendations'].append("使用容量段总价格格式")
                    elif avg_mc < 50:
                        result['detected_format'] = 'possibly_marginal_cost'
                        result['confidence'] = 0.6
                        result['recommendations'].append("可能是边际成本格式，建议确认")
                    else:
                        result['detected_format'] = 'total_cost'
                        result['confidence'] = 0.7
                        result['recommendations'].append("可能是容量段总价格格式")
        
        return result
    
    def marginal_to_total(self, data: Union[pd.DataFrame, str], 
                         power_col: str = 'power', 
                         marginal_col: str = 'marginal_cost') -> pd.DataFrame:
        """
        将边际成本格式转换为容量段总价格格式
        
        Args:
            data: 边际成本数据
            power_col: 功率列名
            marginal_col: 边际成本列名
            
        Returns:
            pd.DataFrame: 转换后的总价格格式数据
        """
        if isinstance(data, str):
            data = pd.read_csv(data)
        
        data = data.copy()
        data.columns = data.columns.str.strip()
        
        if power_col not in data.columns:
            raise ValueError(f"Power column '{power_col}' not found")
        if marginal_col not in data.columns:
            raise ValueError(f"Marginal cost column '{marginal_col}' not found")
        
        # 排序确保功率递增
        data = data.sort_values(power_col).reset_index(drop=True)
        
        # 计算累计总成本
        data['cost'] = 0.0
        
        for i in range(1, len(data)):
            power_diff = data.iloc[i][power_col] - data.iloc[i-1][power_col]
            marginal_cost = data.iloc[i][marginal_col]
            segment_cost = power_diff * marginal_cost
            data.iloc[i, data.columns.get_loc('cost')] = \
                data.iloc[i-1]['cost'] + segment_cost
        
        # 返回标准格式
        result = data[[power_col, 'cost']].copy()
        result.columns = ['power', 'cost']
        
        self.logger.info(f"Converted marginal cost to total cost format: {len(result)} segments")
        return result
    
    def total_to_marginal(self, data: Union[pd.DataFrame, str],
                         power_col: str = 'power',
                         cost_col: str = 'cost') -> pd.DataFrame:
        """
        将容量段总价格格式转换为边际成本格式
        
        Args:
            data: 总价格数据
            power_col: 功率列名
            cost_col: 成本列名
            
        Returns:
            pd.DataFrame: 边际成本格式数据
        """
        if isinstance(data, str):
            data = pd.read_csv(data)
        
        data = data.copy()
        data.columns = data.columns.str.strip()
        
        if power_col not in data.columns:
            raise ValueError(f"Power column '{power_col}' not found")
        if cost_col not in data.columns:
            raise ValueError(f"Cost column '{cost_col}' not found")
        
        # 排序确保功率递增
        data = data.sort_values(power_col).reset_index(drop=True)
        
        # 计算边际成本
        marginal_data = []
        
        for i in range(len(data)):
            power = data.iloc[i][power_col]
            
            if i == 0:
                marginal_cost = 0.0  # 第一个点的边际成本设为0
            else:
                power_diff = data.iloc[i][power_col] - data.iloc[i-1][power_col]
                cost_diff = data.iloc[i][cost_col] - data.iloc[i-1][cost_col]
                marginal_cost = cost_diff / power_diff if power_diff > 0 else 0.0
            
            marginal_data.append({
                'power': power,
                'marginal_cost': marginal_cost
            })
        
        result = pd.DataFrame(marginal_data)
        
        self.logger.info(f"Converted total cost to marginal cost format: {len(result)} segments")
        return result
    
    def convert_csv(self, input_file: str, output_file: str, 
                   source_format: str = 'auto', target_format: str = None) -> bool:
        """
        转换CSV文件格式
        
        Args:
            input_file: 输入文件路径
            output_file: 输出文件路径
            source_format: 源格式 ('marginal_cost', 'total_cost', 'auto')
            target_format: 目标格式 ('marginal_cost', 'total_cost')
            
        Returns:
            bool: 转换是否成功
        """
        try:
            # 检测源格式
            if source_format == 'auto':
                detection = self.detect_format(input_file)
                source_format = detection['detected_format']
                self.logger.info(f"Auto-detected format: {source_format}")
            
            # 自动确定目标格式
            if target_format is None:
                if source_format == 'marginal_cost':
                    target_format = 'total_cost'
                elif source_format == 'total_cost':
                    target_format = 'marginal_cost'
                else:
                    raise ValueError(f"Cannot determine target format from source: {source_format}")
            
            # 执行转换
            data = pd.read_csv(input_file)
            
            if source_format == 'marginal_cost' and target_format == 'total_cost':
                result = self.marginal_to_total(data)
            elif source_format == 'total_cost' and target_format == 'marginal_cost':
                result = self.total_to_marginal(data)
            else:
                raise ValueError(f"Unsupported conversion: {source_format} -> {target_format}")
            
            # 保存结果
            result.to_csv(output_file, index=False)
            self.logger.info(f"Successfully converted {input_file} to {output_file}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Conversion failed: {e}")
            return False
    
    def validate_data(self, data: Union[pd.DataFrame, str], 
                     format_type: str = 'auto') -> Dict:
        """
        验证投标数据的合理性
        
        Args:
            data: 投标数据
            format_type: 数据格式类型
            
        Returns:
            dict: 验证结果
        """
        if isinstance(data, str):
            data = pd.read_csv(data)
        
        data = data.copy()
        data.columns = data.columns.str.strip()
        
        validation = {
            'is_valid': True,
            'warnings': [],
            'errors': [],
            'statistics': {}
        }
        
        # 自动检测格式
        if format_type == 'auto':
            detection = self.detect_format(data)
            format_type = detection['detected_format']
        
        # 基本检查
        if 'power' not in data.columns:
            validation['errors'].append("Missing 'power' column")
            validation['is_valid'] = False
        
        if format_type == 'total_cost' and 'cost' not in data.columns:
            validation['errors'].append("Missing 'cost' column for total cost format")
            validation['is_valid'] = False
        elif format_type == 'marginal_cost' and 'marginal_cost' not in data.columns:
            validation['errors'].append("Missing 'marginal_cost' column for marginal cost format")
            validation['is_valid'] = False
        
        if not validation['is_valid']:
            return validation
        
        # 数据质量检查
        powers = data['power'].values
        
        # 检查功率递增性
        if not all(powers[i] <= powers[i+1] for i in range(len(powers)-1)):
            validation['warnings'].append("Power values are not in ascending order")
        
        # 检查负值
        if any(p < 0 for p in powers):
            validation['errors'].append("Negative power values found")
            validation['is_valid'] = False
        
        # 格式特定检查
        if format_type == 'total_cost':
            costs = data['cost'].values
            
            # 检查成本递增性
            if not all(costs[i] <= costs[i+1] for i in range(len(costs)-1)):
                validation['warnings'].append("Cost values are not monotonically increasing")
            
            # 计算边际成本统计
            marginal_costs = []
            for i in range(1, len(costs)):
                if powers[i] > powers[i-1]:
                    mc = (costs[i] - costs[i-1]) / (powers[i] - powers[i-1])
                    marginal_costs.append(mc)
            
            if marginal_costs:
                validation['statistics']['marginal_costs'] = {
                    'min': np.min(marginal_costs),
                    'max': np.max(marginal_costs),
                    'mean': np.mean(marginal_costs),
                    'std': np.std(marginal_costs)
                }
                
                # 检查边际成本合理性
                if any(mc < 0 for mc in marginal_costs):
                    validation['warnings'].append("Negative marginal costs detected")
                if any(mc > 1000 for mc in marginal_costs):
                    validation['warnings'].append("Very high marginal costs detected (>1000 $/MWh)")
        
        elif format_type == 'marginal_cost':
            marginal_costs = data['marginal_cost'].values
            
            # 检查边际成本合理性
            if any(mc < 0 for mc in marginal_costs):
                validation['warnings'].append("Negative marginal costs found")
            if any(mc > 1000 for mc in marginal_costs):
                validation['warnings'].append("Very high marginal costs found (>1000 $/MWh)")
            
            validation['statistics']['marginal_costs'] = {
                'min': np.min(marginal_costs),
                'max': np.max(marginal_costs),
                'mean': np.mean(marginal_costs),
                'std': np.std(marginal_costs)
            }
        
        return validation


def convert_bidding_file(input_file: str, output_file: str = None, 
                        target_format: str = None) -> str:
    """
    便捷的文件转换函数
    
    Args:
        input_file: 输入文件路径
        output_file: 输出文件路径 (可选)
        target_format: 目标格式 (可选)
        
    Returns:
        str: 输出文件路径
    """
    converter = BiddingFormatConverter()
    
    # 检测输入格式
    detection = converter.detect_format(input_file)
    source_format = detection['detected_format']
    
    # 确定目标格式
    if target_format is None:
        if source_format == 'marginal_cost':
            target_format = 'total_cost'
        elif source_format == 'total_cost':
            target_format = 'marginal_cost'
        else:
            raise ValueError(f"Cannot determine target format from detected format: {source_format}")
    
    # 确定输出文件名
    if output_file is None:
        base, ext = os.path.splitext(input_file)
        output_file = f"{base}_{target_format}{ext}"
    
    # 执行转换
    success = converter.convert_csv(input_file, output_file, source_format, target_format)
    
    if success:
        return output_file
    else:
        raise RuntimeError(f"Conversion failed for {input_file}")


def create_example_files():
    """创建示例文件用于测试"""
    
    # 边际成本格式示例
    marginal_example = pd.DataFrame({
        'power': [0, 100, 200, 300, 400],
        'marginal_cost': [0, 15.0, 20.0, 28.0, 35.0]
    })
    marginal_example.to_csv('example_marginal_cost.csv', index=False)
    
    # 总成本格式示例
    total_example = pd.DataFrame({
        'power': [0, 80, 160, 240, 320],
        'cost': [0, 1000, 2400, 4200, 6800]
    })
    total_example.to_csv('example_total_cost.csv', index=False)
    
    print("✅ 创建示例文件:")
    print("  - example_marginal_cost.csv")
    print("  - example_total_cost.csv")
    
    return 'example_marginal_cost.csv', 'example_total_cost.csv'


if __name__ == "__main__":
    # 示例用法
    print("🔄 投标格式转换工具演示")
    print("=" * 40)
    
    # 创建转换器
    converter = BiddingFormatConverter()
    
    # 创建示例文件
    marginal_file, total_file = create_example_files()
    
    # 检测格式
    print("\n🔍 格式检测:")
    detection1 = converter.detect_format(marginal_file)
    print(f"  {marginal_file}: {detection1['detected_format']} (置信度: {detection1['confidence']:.2f})")
    
    detection2 = converter.detect_format(total_file)
    print(f"  {total_file}: {detection2['detected_format']} (置信度: {detection2['confidence']:.2f})")
    
    # 转换文件
    print("\n🔄 格式转换:")
    converted1 = convert_bidding_file(marginal_file)
    print(f"  {marginal_file} -> {converted1}")
    
    converted2 = convert_bidding_file(total_file)
    print(f"  {total_file} -> {converted2}")
    
    # 验证数据
    print("\n✅ 数据验证:")
    validation = converter.validate_data(total_file)
    print(f"  {total_file}: {'有效' if validation['is_valid'] else '无效'}")
    if validation['warnings']:
        print(f"    警告: {validation['warnings']}")
    
    # 清理临时文件
    for file in [marginal_file, total_file, converted1, converted2]:
        if os.path.exists(file):
            os.remove(file)
    
    print("\n🎉 演示完成!")