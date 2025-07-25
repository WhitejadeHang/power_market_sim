#!/usr/bin/env python3
"""
最终修正列名，确保与simpower兼容
"""

import os
import pandas as pd


def fix_case_columns(case_dir):
    """修正案例中所有文件的列名"""
    
    print(f"🔧 修正案例: {case_dir}")
    
    # 1. 修正generators.csv
    gen_file = os.path.join(case_dir, 'generators.csv')
    if os.path.exists(gen_file):
        print("📝 修正generators.csv...")
        gen_df = pd.read_csv(gen_file)
        
        # 删除plant_type列，如果存在
        if 'plant_type' in gen_df.columns:
            gen_df = gen_df.drop('plant_type', axis=1)
            print("   - 删除了plant_type列")
        
        # 如果没有type列，添加它
        if 'type' not in gen_df.columns:
            gen_df['type'] = 'coal'
            print("   - 添加了type列")
        
        # 如果没有no load cost列，从原始案例获取
        if 'no load cost' not in gen_df.columns:
            try:
                orig_gen_df = pd.read_csv('simpower/tests/ieee_50_bus_case/generators.csv')
                if 'no load cost' in orig_gen_df.columns:
                    gen_df = gen_df.merge(orig_gen_df[['name', 'no load cost']], on='name', how='left')
                    print("   - 添加了no load cost列")
            except:
                # 如果失败，使用默认值
                gen_df['no load cost'] = 0
                print("   - 添加了no load cost列（默认值）")
        
        # 确保列顺序正确
        expected_columns = ['name', 'bus', 'type', 'P min', 'P max', 'no load cost', 'cost curve points filename']
        actual_columns = []
        for col in expected_columns:
            if col in gen_df.columns:
                actual_columns.append(col)
        
        gen_df = gen_df[actual_columns]
        gen_df.to_csv(gen_file, index=False)
        print("✅ generators.csv已修正")
    
    # 2. 确保lines.csv列名正确
    lines_file = os.path.join(case_dir, 'lines.csv')
    if os.path.exists(lines_file):
        print("📝 检查lines.csv...")
        lines_df = pd.read_csv(lines_file)
        
        # 确保列名是"from bus"和"to bus"（带空格）
        if 'frombus' in lines_df.columns:
            lines_df.rename(columns={'frombus': 'from bus', 'tobus': 'to bus'}, inplace=True)
            lines_df.to_csv(lines_file, index=False)
            print("✅ lines.csv列名已修正")
        else:
            print("✅ lines.csv列名正确")


def main():
    """主函数"""
    
    print("🚀 最终列名修正")
    print("=" * 60)
    
    # 修正所有相关案例
    cases = [
        'simpower/tests/ieee_50_single_period',
        'simpower/tests/ieee_50_complete',
        'simpower/tests/ieee_50_bus_working'
    ]
    
    for case in cases:
        if os.path.exists(case):
            fix_case_columns(case)
            print()
    
    print("✅ 所有修正完成！")
    print("\n测试命令:")
    print("python3 simpower/tests/test_single_period_only.py")


if __name__ == "__main__":
    main()