"""
仿真结果提取模块

从 HFSS 中提取 S11 数据及其他可扩展结果，
返回供 SimulationResult 使用的 numpy 数组。
"""

from typing import Any, Optional, Tuple

import numpy as np

from src.config_loader import Config
from src.logger import get_logger

logger = get_logger("hfss_automation")


class ResultExtractorError(Exception):
    """结果提取错误"""


class ResultExtractor:
    """
    结果提取器

    从 pyaedt Hfss 实例中读取 S 参数等仿真结果，
    转换为 numpy 数组格式返回。

    后续扩展指引：
        若需提取增益（Gain）、阻抗（Impedance）或方向图（Radiation Pattern），
        在本类中新增对应的 get_xxx() 方法，调用 pyaedt 的相应 API 即可。
        然后在 simulation.py 的 run_hfss_simulation() 中调用新方法，
        并将结果填入 SimulationResult 的预留字段。

    使用示例：
        extractor = ResultExtractor(config, hfss_instance)
        freqs, s11_db = extractor.get_s11()
    """

    def __init__(self, config: Config, hfss: Any):
        """
        Args:
            config: 配置对象
            hfss: pyaedt Hfss 实例
        """
        self._config = config
        self._hfss = hfss

    def get_s11(self) -> Tuple[np.ndarray, np.ndarray]:
        """
        提取 S11 数据

        Returns:
            tuple: (freqs, s11_db)
                - freqs: 频率数组，单位 GHz，shape=(N,)
                - s11_db: S11 幅值，单位 dB，shape=(N,)

        Raises:
            ResultExtractorError: 数据提取失败
        """
        port = self._config.port_name
        # S11 的表达式：dB(S(Port1,Port1))
        s11_expression = f"dB(S({port},{port}))"

        try:
            # pyaedt 获取报告数据的通用接口
            data = self._hfss.post.get_solution_data(
                expressions=s11_expression,
                report_category="S Parameter",
            )
            if data is None:
                raise ResultExtractorError(
                    f"无法获取 S 参数数据，请检查端口名称 '{port}' 是否与 HFSS 模型一致"
                )

            freqs_hz = np.array(data.primary_sweep_values, dtype=float)
            s11_values = np.array(data.data_real(s11_expression), dtype=float)

            # 将频率从 Hz 转换为 GHz
            freqs_ghz = freqs_hz / 1e9

            logger.debug(
                f"成功提取 S11 数据：{len(freqs_ghz)} 个频点，"
                f"频率范围 [{freqs_ghz[0]:.3f}, {freqs_ghz[-1]:.3f}] GHz"
            )
            return freqs_ghz, s11_values

        except ResultExtractorError:
            raise
        except Exception as e:
            raise ResultExtractorError(f"提取 S11 数据时发生错误: {e}") from e

    # ------------------------------------------------------------------ #
    # 预留扩展接口（后续开发时实现以下方法）
    # ------------------------------------------------------------------ #

    def get_gain(self) -> Optional[np.ndarray]:
        """
        【预留接口】提取天线增益数据

        后续开发指引：
            调用 pyaedt Far Field 报告 API 提取增益（dBi）。
            示例：self._hfss.post.get_far_field_data(...)

        Returns:
            np.ndarray | None: 增益数组，或 None（未实现时）
        """
        logger.debug("get_gain() 暂未实现，返回 None")
        return None

    def get_impedance(self) -> Optional[np.ndarray]:
        """
        【预留接口】提取输入阻抗数据

        后续开发指引：
            调用 pyaedt 获取 Z 参数：self._hfss.post.get_solution_data("Zin(Port1)")

        Returns:
            np.ndarray | None: 复数阻抗数组，或 None（未实现时）
        """
        logger.debug("get_impedance() 暂未实现，返回 None")
        return None

    def get_radiation_pattern(self) -> Optional[np.ndarray]:
        """
        【预留接口】提取方向图数据

        后续开发指引：
            调用 pyaedt Far Field 报告 API 提取 E 面/H 面方向图。

        Returns:
            np.ndarray | None: 方向图数组，或 None（未实现时）
        """
        logger.debug("get_radiation_pattern() 暂未实现，返回 None")
        return None
