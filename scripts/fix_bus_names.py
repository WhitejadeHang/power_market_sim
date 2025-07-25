#!/usr/bin/env python3
"""
修正IEEE 50节点案例中所有文件的节点名称格式
将 "Bus_01_urban_high" 格式改为 "Bus01" 格式
"""

import os
import pandas as pd


def fix_bus_names_in_dataframe(df, columns):
    """修正DataFrame中指定列的节点名称格式"""
    
    def fix_bus_name(name):
        if isinstance(name, str) and name.startswith('Bus_'):
            parts = name.split('_')
            if len(parts) >= 2:
                try:
                    bus_num = int(parts[1])
                    return f"Bus{bus_num:02d}"
                except:
                    pass
        return name
    
    for col in columns:
        if col in df.columns:
            df[col] = df[col].apply(fix_bus_name)
    
    return df


def fix_ieee_50_bus_case(case_dir):
    """修正IEEE 50节点案例的所有文件"""
    
    print(f"🔧 修正案例目录: {case_dir}")
    
    # 1. 修正buses.csv
    print("📝 修正buses.csv...")
    buses_df = pd.read_csv(os.path.join(case_dir, 'buses.csv'))
    buses_df = fix_bus_names_in_dataframe(buses_df, ['name'])
    buses_df.to_csv(os.path.join(case_dir, 'buses.csv'), index=False)
    print(f"✅ 修正了 {len(buses_df)} 个节点名称")
    
    # 2. 修正lines.csv
    print("📝 修正lines.csv...")
    lines_df = pd.read_csv(os.path.join(case_dir, 'lines.csv'))
    lines_df = fix_bus_names_in_dataframe(lines_df, ['from bus', 'to bus'])
    lines_df.to_csv(os.path.join(case_dir, 'lines.csv'), index=False)
    print(f"✅ 修正了 {len(lines_df)} 条线路的节点引用")
    
    # 3. 修正generators.csv
    print("📝 修正generators.csv...")
    gen_df = pd.read_csv(os.path.join(case_dir, 'generators.csv'))
    gen_df = fix_bus_names_in_dataframe(gen_df, ['bus'])
    gen_df.to_csv(os.path.join(case_dir, 'generators.csv'), index=False)
    print(f"✅ 修正了 {len(gen_df)} 台发电机的节点引用")
    
    # 4. 修正loads.csv
    print("📝 修正loads.csv...")
    loads_df = pd.read_csv(os.path.join(case_dir, 'loads.csv'))
    
    # 修正负荷名称
    def fix_load_name(name):
        if isinstance(name, str) and name.startswith('Bus_'):
            parts = name.split('_')
            if len(parts) >= 2:
                try:
                    bus_num = int(parts[1])
                    return f"Load{bus_num:02d}"
                except:
                    pass
        return name
    
    loads_df['name'] = loads_df['name'].apply(fix_load_name)
    
    # 添加bus列（如果不存在）
    if 'bus' not in loads_df.columns:
        loads_df['bus'] = loads_df['name'].apply(
            lambda x: f"Bus{int(x.replace('Load', '')):02d}" if x.startswith('Load') else x
        )
    
    loads_df.to_csv(os.path.join(case_dir, 'loads.csv'), index=False)
    print(f"✅ 修正了 {len(loads_df)} 个负荷的名称和节点引用")
    
    print("\n✅ 所有文件修正完成！")


def main():
    """主函数"""
    
    # 修正主案例
    case_dir = 'simpower/tests/ieee_50_bus_case'
    if os.path.exists(case_dir):
        fix_ieee_50_bus_case(case_dir)
    
    # 修正简化测试案例
    simple_case_dir = 'simpower/tests/ieee_50_bus_simple_test'
    if os.path.exists(simple_case_dir):
        print(f"\n")
        fix_ieee_50_bus_case(simple_case_dir)


if __name__ == "__main__":
    main()