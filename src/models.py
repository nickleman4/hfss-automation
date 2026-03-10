"""
数据模型模块

定义仿真结果的数据结构 SimulationResult，供核心函数返回使用。
预留了增益、阻抗、方向图等后续扩展字段。
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import numpy as np


@dataclass
class SimulationResult:
    """
    仿真结果数据类

    包含本次仿真的所有输出数据，支持后续扩展。

    属性:
        freqs (np.ndarray): 频率数组（单位：GHz）
        s11_db (np.ndarray): S11 幅值数组（单位：dB）
        parameters (dict): 本次仿真使用的参数字典，如 {"Length": 30.0, "Width": 25.0}
        fidelity (str): 本次仿真精度，"coarse" 或 "fine"
        simulation_time (float): 仿真总耗时（单位：秒）

        # 预留后续扩展字段
        gain (np.ndarray | None): 天线增益（dBi），后续扩展时填入
        impedance (np.ndarray | None): 输入阻抗（复数），后续扩展时填入
        radiation_pattern (np.ndarray | None): 方向图数据，后续扩展时填入
        extra_results (dict): 其他任意扩展结果，键值对形式
    """

    # 核心返回字段
    freqs: np.ndarray
    s11_db: np.ndarray
    parameters: Dict[str, float]
    fidelity: str
    simulation_time: float

    # 预留扩展字段（默认为 None，供后续开发填充）
    gain: Optional[np.ndarray] = None
    impedance: Optional[np.ndarray] = None
    radiation_pattern: Optional[np.ndarray] = None
    extra_results: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """
        将结果转换为可序列化的字典（用于保存 JSON 文件）

        Returns:
            dict: 包含所有结果数据的字典，numpy 数组转换为列表
        """
        data = {
            "freqs": self.freqs.tolist(),
            "s11_db": self.s11_db.tolist(),
            "parameters": self.parameters,
            "fidelity": self.fidelity,
            "simulation_time": self.simulation_time,
            "extra_results": self.extra_results,
        }
        # 仅在非 None 时序列化可选字段
        if self.gain is not None:
            data["gain"] = self.gain.tolist()
        if self.impedance is not None:
            # 复数需要特殊处理
            data["impedance"] = {
                "real": np.real(self.impedance).tolist(),
                "imag": np.imag(self.impedance).tolist(),
            }
        if self.radiation_pattern is not None:
            data["radiation_pattern"] = self.radiation_pattern.tolist()
        return data

    @property
    def s11_min_db(self) -> float:
        """S11 最小值（dB），即最佳谐振点"""
        return float(np.min(self.s11_db))

    @property
    def resonance_frequency(self) -> float:
        """S11 最小值对应的谐振频率（GHz）"""
        idx = int(np.argmin(self.s11_db))
        return float(self.freqs[idx])

    def __repr__(self) -> str:
        return (
            f"SimulationResult("
            f"fidelity={self.fidelity!r}, "
            f"freq_range=[{self.freqs[0]:.2f}, {self.freqs[-1]:.2f}] GHz, "
            f"s11_min={self.s11_min_db:.2f} dB @ {self.resonance_frequency:.3f} GHz, "
            f"time={self.simulation_time:.1f}s)"
        )
