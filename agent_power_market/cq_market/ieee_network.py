"""
IEEE 标准测试网络构建
提供 IEEE 6-bus (Wood & Wollenberg) 和 IEEE 14-bus 网络拓扑
用于带网络约束的电力现货市场出清仿真
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import pypsa


def create_ieee6bus(snapshots: pd.DatetimeIndex | None = None) -> pypsa.Network:
    """
    构建 IEEE 6-bus 测试网络 (Wood & Wollenberg)
    
    拓扑:
      Bus1(slack) -- Bus2 -- Bus3
        |    \\        |      /  |
      Bus4 -- Bus5 -------- Bus6
    
    包含 3 台发电机 (Bus1, Bus2, Bus6) 和 3 个负荷节点 (Bus4, Bus5, Bus6)
    线路采用 DC 近似 (仅含电抗)
    
    Returns: pypsa.Network 对象 (不含 snapshots/generators/loads — 需外部添加)
    """
    n = pypsa.Network()
    if snapshots is not None:
        n.set_snapshots(snapshots)

    # === Buses (6个母线) ===
    for i in range(1, 7):
        n.add("Bus", f"Bus{i}", v_nom=230)

    # === Lines (11条线路, DC 近似) ===
    # (from, to, r_pu, x_pu, rating_MW) — 阻抗以100MVA基准标幺
    lines_data = [
        ("Bus1", "Bus2", 0.10, 0.20, 350),
        ("Bus1", "Bus4", 0.05, 0.20, 180),   # 关键断面: 限制 Bus1→Bus4 送电
        ("Bus1", "Bus5", 0.08, 0.30, 150),   # 关键断面: 限制 Bus1→Bus5 送电
        ("Bus2", "Bus3", 0.05, 0.25, 300),
        ("Bus2", "Bus4", 0.05, 0.10, 250),
        ("Bus2", "Bus5", 0.10, 0.30, 150),   # 较窄
        ("Bus2", "Bus6", 0.07, 0.20, 300),
        ("Bus3", "Bus5", 0.12, 0.26, 120),   # 较窄 → 阻塞
        ("Bus3", "Bus6", 0.02, 0.10, 300),
        ("Bus4", "Bus5", 0.20, 0.40, 120),   # 较窄
        ("Bus5", "Bus6", 0.10, 0.30, 150),
    ]
    base_mva = 100
    v_nom = 230
    z_base = v_nom ** 2 / base_mva  # Ω

    for i, (b0, b1, r_pu, x_pu, rating) in enumerate(lines_data):
        n.add("Line", f"Line_{b0}_{b1}",
               bus0=b0, bus1=b1,
               x=x_pu * z_base,
               r=r_pu * z_base,
               s_nom=rating)

    return n


def create_ieee14bus(snapshots: pd.DatetimeIndex | None = None) -> pypsa.Network:
    """
    构建 IEEE 14-bus 标准测试网络
    
    5 台发电机 (Bus1, Bus2, Bus3, Bus6, Bus8)
    11 个负荷节点
    20 条输电线路
    
    Returns: pypsa.Network 对象
    """
    n = pypsa.Network()
    if snapshots is not None:
        n.set_snapshots(snapshots)

    # === Buses ===
    for i in range(1, 15):
        v_nom = 69 if i <= 5 else 13.8
        if i in (6, 7, 8):
            v_nom = 18
        n.add("Bus", f"Bus{i}", v_nom=v_nom)

    # === Lines (20条) ===
    # (from, to, r_pu, x_pu, rating_MW) — 100MVA base
    lines_14 = [
        ("Bus1",  "Bus2",  0.01938, 0.05917, 200),
        ("Bus1",  "Bus5",  0.05403, 0.22304, 150),
        ("Bus2",  "Bus3",  0.04699, 0.19797, 150),
        ("Bus2",  "Bus4",  0.05811, 0.17632, 150),
        ("Bus2",  "Bus5",  0.05695, 0.17388, 150),
        ("Bus3",  "Bus4",  0.06701, 0.17103, 150),
        ("Bus4",  "Bus5",  0.01335, 0.04211, 150),
        ("Bus4",  "Bus7",  0.0,     0.20912, 150),
        ("Bus4",  "Bus9",  0.0,     0.55618, 100),
        ("Bus5",  "Bus6",  0.0,     0.25202, 100),
        ("Bus6",  "Bus11", 0.09498, 0.19890, 80),
        ("Bus6",  "Bus12", 0.12291, 0.25581, 80),
        ("Bus6",  "Bus13", 0.06615, 0.13027, 80),
        ("Bus7",  "Bus8",  0.0,     0.17615, 100),
        ("Bus7",  "Bus9",  0.0,     0.11001, 100),
        ("Bus9",  "Bus10", 0.03181, 0.08450, 80),
        ("Bus9",  "Bus14", 0.12711, 0.27038, 80),
        ("Bus10", "Bus11", 0.08205, 0.19207, 80),
        ("Bus12", "Bus13", 0.22092, 0.19988, 80),
        ("Bus13", "Bus14", 0.17093, 0.34802, 80),
    ]

    base_mva = 100
    for b0, b1, r_pu, x_pu, rating in lines_14:
        v_base = n.buses.loc[b0, "v_nom"]
        z_base = v_base ** 2 / base_mva
        n.add("Line", f"Line_{b0}_{b1}",
               bus0=b0, bus1=b1,
               x=max(x_pu * z_base, 0.001),
               r=r_pu * z_base,
               s_nom=rating)

    return n


def add_ieee6bus_generators_and_loads(
    n: pypsa.Network,
    gen_config: dict | None = None,
    load_base: dict | None = None,
) -> pypsa.Network:
    """
    向 IEEE 6-bus 网络添加默认发电机与负荷
    
    发电机布局:
      - Bus1: 2×300MW 煤机 (基荷)
      - Bus2: 2×300MW 煤机 (中间负荷)  
      - Bus3: 1×200MW 新能源
      - Bus6: 1×100MW/200MWh 储能
    
    负荷布局:
      - Bus3: 工业负荷
      - Bus4: 城市负荷
      - Bus5: 商业负荷
    """
    if gen_config is None:
        gen_config = {
            "Coal_B1_1": {"bus": "Bus1", "p_nom": 300, "type": "coal"},
            "Coal_B1_2": {"bus": "Bus1", "p_nom": 300, "type": "coal"},
            "Coal_B2_1": {"bus": "Bus2", "p_nom": 300, "type": "coal"},
            "Coal_B2_2": {"bus": "Bus2", "p_nom": 300, "type": "coal"},
            "Wind_B3":   {"bus": "Bus3", "p_nom": 200, "type": "renewable"},
            "ESS_B6":    {"bus": "Bus6", "p_nom": 100, "type": "storage"},
        }

    if load_base is None:
        load_base = {
            "Load_B3": {"bus": "Bus3", "base_mw": 200},
            "Load_B4": {"bus": "Bus4", "base_mw": 350},
            "Load_B5": {"bus": "Bus5", "base_mw": 250},
        }

    return n, gen_config, load_base


def generate_load_profile_96(base_mw: float, seed: int = 42) -> np.ndarray:
    """生成96点(15min)典型日负荷曲线
    
    基于典型冬季日负荷特征:
    - 凌晨低谷 (0-6h): base * 0.55~0.65
    - 早高峰   (7-11h): base * 0.85~1.0
    - 午间     (11-14h): base * 0.90~0.95
    - 晚高峰   (17-21h): base * 0.95~1.10
    - 晚间回落 (22-24h): base * 0.70~0.80
    """
    rng = np.random.default_rng(seed)
    hours = np.arange(96) * 0.25

    # 基础日负荷形状 (正弦叠加)
    shape = (0.75
             + 0.15 * np.sin((hours - 6) / 24 * 2 * np.pi)
             + 0.10 * np.sin((hours - 3) / 12 * 2 * np.pi)
             )

    # 加入随机波动
    noise = rng.normal(0, 0.02, 96)
    profile = base_mw * np.clip(shape + noise, 0.5, 1.2)
    return profile


def generate_wind_profile_96(p_nom: float, seed: int = 123) -> np.ndarray:
    """生成96点风电出力预测曲线
    
    特征: 夜间/凌晨出力较高, 午后较低, 随机波动大
    """
    rng = np.random.default_rng(seed)
    hours = np.arange(96) * 0.25

    cf = (0.35
          + 0.15 * np.sin((hours + 6) / 24 * 2 * np.pi)
          + rng.normal(0, 0.08, 96))
    cf = np.clip(cf, 0.05, 0.85)
    return p_nom * cf


def generate_solar_profile_96(p_nom: float, seed: int = 456) -> np.ndarray:
    """生成96点光伏出力预测曲线"""
    hours = np.arange(96) * 0.25
    rng = np.random.default_rng(seed)
    cf = np.zeros(96)
    for i, h in enumerate(hours):
        if 6 <= h <= 18:
            cf[i] = max(0, np.sin((h - 6) / 12 * np.pi)) * (0.6 + rng.normal(0, 0.1))
    cf = np.clip(cf, 0, 0.9)
    return p_nom * cf
