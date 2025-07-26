#!/usr/bin/env python3
"""
创建完整的96时段IEEE 50节点测试案例
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta


def create_96periods_case():
    """创建96时段测试案例"""
    
    # 源目录和目标目录
    src_dir = 'simpower/tests/ieee_50_single_period'
    dst_dir = 'simpower/tests/ieee_50_96periods_final'
    
    # 创建目标目录
    os.makedirs(dst_dir, exist_ok=True)
    print(f"📁 创建目标目录: {dst_dir}")
    
    # 1. 复制基础文件
    import shutil
    for file in ['buses.csv', 'lines.csv', 'generators.csv']:
        src = os.path.join(src_dir, file)
        dst = os.path.join(dst_dir, file)
        if os.path.exists(src):
            shutil.copy(src, dst)
            print(f"✅ 复制 {file}")
    
    # 2. 创建96时段的时间序列
    print("\n⏰ 创建96时段时间序列...")
    
    base_time = datetime(2025, 7, 26, 0, 0)
    times = []
    load_factors = []
    
    for i in range(96):
        current_time = base_time + timedelta(minutes=15*i)
        times.append(current_time.strftime("%Y-%m-%d %H:%M:%S"))
        
        # 创建负荷曲线：早晚高峰，午夜低谷
        hour = current_time.hour + current_time.minute/60
        
        if 0 <= hour < 6:  # 深夜低谷
            factor = 0.6 + 0.1 * np.sin(hour * np.pi / 6)
        elif 6 <= hour < 9:  # 早高峰
            factor = 0.7 + 0.3 * (hour - 6) / 3
        elif 9 <= hour < 11:  # 上午平峰
            factor = 0.95 + 0.05 * np.sin((hour - 9) * np.pi)
        elif 11 <= hour < 14:  # 午间低谷
            factor = 0.85 - 0.1 * np.sin((hour - 11) * np.pi / 3)
        elif 14 <= hour < 18:  # 下午平峰
            factor = 0.85 + 0.1 * (hour - 14) / 4
        elif 18 <= hour < 21:  # 晚高峰
            factor = 0.95 + 0.05 * np.sin((hour - 18) * np.pi / 3)
        else:  # 夜间下降
            factor = 0.95 - 0.25 * (hour - 21) / 3
        
        # 添加随机扰动
        factor += np.random.normal(0, 0.02)
        factor = max(0.5, min(1.05, factor))  # 限制在合理范围
        
        load_factors.append(factor)
    
    # 保存时间序列
    timeseries_df = pd.DataFrame({
        'time': times,
        'load_factor': load_factors
    })
    timeseries_df.to_csv(os.path.join(dst_dir, 'timeseries.csv'), index=False)
    print(f"✅ 创建时间序列文件 (96时段)")
    
    # 3. 创建loads.csv - 指向统一的时间序列文件
    loads_df = pd.read_csv(os.path.join(src_dir, 'loads.csv'))
    
    # 确保有正确的列
    if 'schedule filename' not in loads_df.columns:
        loads_df['schedule filename'] = 'timeseries.csv'
    else:
        loads_df['schedule filename'] = 'timeseries.csv'
    
    # 移除可能的重复行
    loads_df = loads_df.drop_duplicates(subset=['name', 'bus'])
    
    loads_df.to_csv(os.path.join(dst_dir, 'loads.csv'), index=False)
    print(f"✅ 创建负荷文件")
    
    # 4. 检查generators.csv - 确保有必要的列
    gen_df = pd.read_csv(os.path.join(dst_dir, 'generators.csv'))
    
    # 添加缺失的列
    if 'ramp rate' not in gen_df.columns:
        # 设置爬坡率为最大容量的10%/15分钟
        gen_df['ramp rate'] = gen_df['P max'] * 0.1
    
    if 'start cost' not in gen_df.columns:
        # 根据容量设置启动成本
        gen_df['start cost'] = gen_df['P max'] * 50  # $50/MW
    
    if 'no load cost' not in gen_df.columns:
        # 设置空载成本
        gen_df['no load cost'] = gen_df['P max'] * 10  # $10/MW
    
    gen_df.to_csv(os.path.join(dst_dir, 'generators.csv'), index=False)
    print(f"✅ 更新发电机文件")
    
    # 5. 打印案例信息
    print("\n📊 案例信息:")
    print(f"  - 节点数: {len(pd.read_csv(os.path.join(dst_dir, 'buses.csv')))}")
    print(f"  - 线路数: {len(pd.read_csv(os.path.join(dst_dir, 'lines.csv')))}")
    print(f"  - 发电机数: {len(gen_df)}")
    print(f"  - 负荷点数: {len(loads_df)}")
    print(f"  - 时段数: 96")
    print(f"  - 时间跨度: 24小时")
    print(f"  - 负荷因子范围: {min(load_factors):.3f} - {max(load_factors):.3f}")
    
    # 6. 绘制负荷曲线预览
    try:
        import matplotlib.pyplot as plt
        
        plt.figure(figsize=(12, 6))
        hours = np.arange(96) * 0.25
        plt.plot(hours, load_factors, 'b-', linewidth=2)
        plt.fill_between(hours, 0, load_factors, alpha=0.3)
        plt.xlabel('Time (hours)')
        plt.ylabel('Load Factor')
        plt.title('96-Period Load Curve (24 hours)')
        plt.grid(True, alpha=0.3)
        plt.xlim(0, 24)
        plt.xticks(range(0, 25, 3))
        
        preview_path = os.path.join(dst_dir, 'load_curve_preview.png')
        plt.savefig(preview_path, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"\n📈 负荷曲线预览已保存: {preview_path}")
    except:
        pass
    
    return dst_dir


def main():
    """主函数"""
    print("🚀 创建96时段IEEE 50节点测试案例")
    print("=" * 60)
    
    case_dir = create_96periods_case()
    
    print(f"\n✅ 96时段案例创建成功！")
    print(f"📁 案例目录: {case_dir}")
    print("\n💡 下一步：运行 solve_problem('{case_dir}') 进行求解")


if __name__ == "__main__":
    main()