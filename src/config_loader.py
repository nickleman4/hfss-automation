"""
配置文件加载与验证模块

负责读取和校验 config.yaml 配置文件，提供统一的配置访问接口。
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml


# 必填配置项路径（使用点分隔符表示嵌套层级）
_REQUIRED_FIELDS = [
    "hfss.version",
    "hfss.install_dir",
    "project.template_path",
    "project.design_name",
    "project.solution_type",
    "project.port_name",
    "variables.names",
    "variables.units",
    "frequency.start",
    "frequency.stop",
    "frequency.num_points",
    "fidelity.coarse.max_passes",
    "fidelity.coarse.max_delta_s",
    "fidelity.fine.max_passes",
    "fidelity.fine.max_delta_s",
]


class ConfigError(Exception):
    """配置文件错误，表示配置项缺失或不合法"""


class Config:
    """
    配置管理类，封装对 config.yaml 的读取和验证。

    使用方法：
        cfg = Config("config.yaml")
        install_dir = cfg.hfss_install_dir
        var_names = cfg.variable_names
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化并加载配置文件

        Args:
            config_path: 配置文件路径（绝对路径或相对于调用脚本的相对路径）

        Raises:
            FileNotFoundError: 配置文件不存在
            ConfigError: 配置文件格式错误或必填项缺失
        """
        self._path = Path(config_path)
        self._data: Dict[str, Any] = self._load()
        self._validate()

    def _load(self) -> Dict[str, Any]:
        """读取 YAML 配置文件"""
        if not self._path.exists():
            raise FileNotFoundError(
                f"配置文件未找到: {self._path.resolve()}\n"
                f"请参考 config_example.yaml 创建配置文件。"
            )
        with open(self._path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            raise ConfigError(f"配置文件格式错误，顶层必须是键值对映射: {self._path}")
        return data

    def _get_nested(self, key_path: str) -> Any:
        """根据点分路径获取嵌套配置值，不存在则返回 None"""
        keys = key_path.split(".")
        node = self._data
        for k in keys:
            if not isinstance(node, dict) or k not in node:
                return None
            node = node[k]
        return node

    def _validate(self) -> None:
        """验证必填配置项均已存在"""
        missing = [
            field for field in _REQUIRED_FIELDS
            if self._get_nested(field) is None
        ]
        if missing:
            raise ConfigError(
                f"配置文件缺少以下必填项：\n"
                + "\n".join(f"  - {f}" for f in missing)
                + f"\n请参考 config_example.yaml 补全配置。"
            )

        # 校验变量名和单位列表长度一致
        names = self.variable_names
        units = self.variable_units
        if len(names) != len(units):
            raise ConfigError(
                f"variables.names 长度 ({len(names)}) "
                f"与 variables.units 长度 ({len(units)}) 不一致"
            )

        # 校验频率范围
        if self.freq_start >= self.freq_stop:
            raise ConfigError(
                f"frequency.start ({self.freq_start}) "
                f"必须小于 frequency.stop ({self.freq_stop})"
            )

    # ------------------------------------------------------------------ #
    # HFSS 安装相关属性
    # ------------------------------------------------------------------ #

    @property
    def hfss_version(self) -> str:
        """HFSS 版本号，如 '2023.1'"""
        return str(self._data["hfss"]["version"])

    @property
    def hfss_install_dir(self) -> str:
        """HFSS 安装目录"""
        return str(self._data["hfss"]["install_dir"])

    @property
    def non_graphical(self) -> bool:
        """是否以非图形模式运行"""
        return bool(self._data["hfss"].get("non_graphical", True))

    @property
    def new_session(self) -> bool:
        """是否每次仿真启动新进程"""
        return bool(self._data["hfss"].get("new_session", True))

    # ------------------------------------------------------------------ #
    # 工程文件相关属性
    # ------------------------------------------------------------------ #

    @property
    def template_path(self) -> str:
        """模板工程文件路径（已解析为绝对路径）"""
        raw = self._data["project"]["template_path"]
        p = Path(raw)
        if p.is_absolute():
            return str(p)
        # 相对路径以配置文件所在目录为基准
        return str((self._path.parent / p).resolve())

    @property
    def design_name(self) -> str:
        """HFSS 设计名称"""
        return str(self._data["project"]["design_name"])

    @property
    def solution_type(self) -> str:
        """求解类型：'Modal' 或 'Terminal'"""
        return str(self._data["project"]["solution_type"])

    @property
    def port_name(self) -> str:
        """激励端口名称"""
        return str(self._data["project"]["port_name"])

    # ------------------------------------------------------------------ #
    # 变量参数相关属性
    # ------------------------------------------------------------------ #

    @property
    def variable_names(self) -> List[str]:
        """参数化变量名称列表"""
        return list(self._data["variables"]["names"])

    @property
    def variable_units(self) -> List[str]:
        """参数化变量单位列表"""
        return list(self._data["variables"]["units"])

    # ------------------------------------------------------------------ #
    # 频率相关属性
    # ------------------------------------------------------------------ #

    @property
    def freq_start(self) -> float:
        """起始频率（GHz）"""
        return float(self._data["frequency"]["start"])

    @property
    def freq_stop(self) -> float:
        """终止频率（GHz）"""
        return float(self._data["frequency"]["stop"])

    @property
    def freq_num_points(self) -> int:
        """频率扫描点数"""
        return int(self._data["frequency"]["num_points"])

    @property
    def freq_unit(self) -> str:
        """频率单位"""
        return str(self._data["frequency"].get("unit", "GHz"))

    # ------------------------------------------------------------------ #
    # 精度配置相关方法
    # ------------------------------------------------------------------ #

    def get_fidelity_config(self, fidelity: str) -> Dict[str, Any]:
        """
        获取指定精度的仿真参数

        Args:
            fidelity: "coarse" 或 "fine"

        Returns:
            dict: 包含 max_passes、max_delta_s、sweep_type 等键的字典

        Raises:
            ConfigError: 不支持的精度名称
        """
        if fidelity not in ("coarse", "fine"):
            raise ConfigError(
                f"不支持的 fidelity 值: {fidelity!r}，只能是 'coarse' 或 'fine'"
            )
        return dict(self._data["fidelity"][fidelity])

    # ------------------------------------------------------------------ #
    # 稳定性配置属性
    # ------------------------------------------------------------------ #

    @property
    def timeout_seconds(self) -> int:
        """单次仿真超时时间（秒）"""
        return int(self._data.get("stability", {}).get("timeout_seconds", 600))

    @property
    def max_retries(self) -> int:
        """最大重试次数"""
        return int(self._data.get("stability", {}).get("max_retries", 3))

    @property
    def retry_delay_seconds(self) -> int:
        """重试前等待时间（秒）"""
        return int(self._data.get("stability", {}).get("retry_delay_seconds", 10))

    # ------------------------------------------------------------------ #
    # 输出配置属性
    # ------------------------------------------------------------------ #

    @property
    def results_dir(self) -> str:
        """结果保存目录（已解析为绝对路径）"""
        raw = self._data.get("output", {}).get("results_dir", "results")
        p = Path(raw)
        if p.is_absolute():
            return str(p)
        return str((self._path.parent / p).resolve())

    @property
    def save_results(self) -> bool:
        """是否保存每次仿真结果到文件"""
        return bool(self._data.get("output", {}).get("save_results", True))

    @property
    def results_prefix(self) -> str:
        """结果文件名前缀"""
        return str(self._data.get("output", {}).get("results_prefix", "simulation"))

    # ------------------------------------------------------------------ #
    # 日志配置属性
    # ------------------------------------------------------------------ #

    @property
    def log_dir(self) -> str:
        """日志保存目录（已解析为绝对路径）"""
        raw = self._data.get("logging", {}).get("log_dir", "logs")
        p = Path(raw)
        if p.is_absolute():
            return str(p)
        return str((self._path.parent / p).resolve())

    @property
    def log_level(self) -> str:
        """日志级别"""
        return str(self._data.get("logging", {}).get("level", "INFO")).upper()

    @property
    def log_prefix(self) -> str:
        """日志文件名前缀"""
        return str(self._data.get("logging", {}).get("log_prefix", "hfss_simulation"))

    @property
    def console_output(self) -> bool:
        """是否在控制台同时输出日志"""
        return bool(self._data.get("logging", {}).get("console_output", True))


def load_config(config_path: str = "config.yaml") -> Config:
    """
    加载配置文件的便捷函数

    Args:
        config_path: 配置文件路径，默认为项目根目录的 config.yaml

    Returns:
        Config: 配置对象实例
    """
    return Config(config_path)
