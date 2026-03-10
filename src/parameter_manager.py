"""
参数管理模块

负责将用户输入的参数数组（x）映射为 HFSS 变量字典，
并验证参数数量和合法性。
"""

from typing import Dict, List, Union

import numpy as np

from src.config_loader import Config
from src.logger import get_logger

logger = get_logger("hfss_automation")


class ParameterError(Exception):
    """参数映射或验证错误"""


class ParameterManager:
    """
    参数管理器

    将用户输入的参数数组 x 与配置文件中的变量名列表对应，
    生成 HFSS 可用的变量字典。

    使用示例：
        mgr = ParameterManager(config)
        variables = mgr.build_variable_dict([30.0, 25.0, 5.0])
        # {'Length': '30.0mm', 'Width': '25.0mm', 'Feed_X': '5.0mm'}
    """

    def __init__(self, config: Config):
        """
        Args:
            config: 配置对象
        """
        self._names = config.variable_names
        self._units = config.variable_units

    @property
    def num_variables(self) -> int:
        """期望的参数变量个数"""
        return len(self._names)

    def validate(self, x: Union[list, np.ndarray]) -> None:
        """
        验证参数数组长度与配置中变量数量一致

        Args:
            x: 参数数组

        Raises:
            ParameterError: 参数数量不匹配
        """
        if len(x) != self.num_variables:
            raise ParameterError(
                f"参数数量不匹配：期望 {self.num_variables} 个 "
                f"（{self._names}），实际传入 {len(x)} 个"
            )

    def build_variable_dict(
        self, x: Union[list, np.ndarray]
    ) -> Dict[str, str]:
        """
        将参数数组映射为 HFSS 变量字典（带单位的字符串格式）

        pyaedt 接受带单位字符串格式，如 "30.0mm"。

        Args:
            x: 参数值数组，长度必须与配置中 variables.names 一致

        Returns:
            dict: 形如 {"Length": "30.0mm", "Width": "25.0mm", ...}

        Raises:
            ParameterError: 参数数量不匹配
        """
        self.validate(x)
        result = {}
        for i, (name, unit) in enumerate(zip(self._names, self._units)):
            value = float(x[i])
            result[name] = f"{value}{unit}"
            logger.debug(f"  参数映射: {name} = {value}{unit}")
        return result

    def build_parameter_record(
        self, x: Union[list, np.ndarray]
    ) -> Dict[str, float]:
        """
        将参数数组映射为纯数值字典（用于结果记录）

        Args:
            x: 参数值数组

        Returns:
            dict: 形如 {"Length": 30.0, "Width": 25.0, ...}

        Raises:
            ParameterError: 参数数量不匹配
        """
        self.validate(x)
        return {
            name: float(x[i])
            for i, name in enumerate(self._names)
        }
