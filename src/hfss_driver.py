"""
HFSS 驱动模块

封装对 pyaedt 库的调用，负责：
- 启动 HFSS（非图形模式）
- 打开和复制模板工程文件
- 运行仿真分析
- 关闭工程并释放资源
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

from src.config_loader import Config
from src.logger import get_logger

logger = get_logger("hfss_automation")


class HFSSDriverError(Exception):
    """HFSS 驱动操作错误"""


class HFSSDriver:
    """
    HFSS 驱动类

    封装 pyaedt 的 Hfss 对象，提供更高级的操作接口。
    每个实例对应一次仿真会话，使用完毕后务必调用 close() 释放资源。

    推荐使用 with 语句管理生命周期：
        with HFSSDriver(config) as driver:
            driver.setup_project(work_dir)
            driver.run_analysis()
    """

    def __init__(self, config: Config):
        """
        Args:
            config: 配置对象
        """
        self._config = config
        self._hfss: Optional[Any] = None          # pyaedt Hfss 实例
        self._project_path: Optional[str] = None  # 本次仿真工作副本路径
        self._work_dir: Optional[str] = None      # 工作临时目录

    # ------------------------------------------------------------------ #
    # 上下文管理器支持
    # ------------------------------------------------------------------ #

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    def setup_project(self, work_dir: str) -> None:
        """
        启动 HFSS 并准备工程工作副本

        将模板工程复制到 work_dir，然后用 pyaedt 打开副本，
        避免多次仿真时修改原始模板文件。

        Args:
            work_dir: 本次仿真的工作目录（由调用方提供临时目录）

        Raises:
            HFSSDriverError: 模板文件不存在或 pyaedt 启动失败
        """
        template = self._config.template_path
        if not Path(template).exists():
            raise HFSSDriverError(
                f"模板工程文件不存在: {template}\n"
                f"请将 .aedt 文件放入 templates/ 目录，并在 config.yaml 中正确设置路径。"
            )

        # 将模板复制到工作目录
        self._work_dir = work_dir
        project_name = Path(template).stem
        self._project_path = str(Path(work_dir) / Path(template).name)
        shutil.copy2(template, self._project_path)
        logger.debug(f"已复制模板到工作目录: {self._project_path}")

        # 启动 pyaedt / Hfss
        self._hfss = self._launch_hfss()
        logger.debug(f"HFSS 已成功启动，设计: {self._config.design_name}")

    def _launch_hfss(self) -> Any:
        """
        调用 pyaedt 启动 HFSS 并打开工程

        Returns:
            pyaedt.Hfss: 实例对象

        Raises:
            HFSSDriverError: pyaedt 未安装或启动失败
        """
        try:
            from pyaedt import Hfss
        except ImportError as e:
            raise HFSSDriverError(
                "无法导入 pyaedt，请先安装：pip install pyaedt\n"
                f"原始错误: {e}"
            ) from e

        try:
            hfss = Hfss(
                project=self._project_path,
                design=self._config.design_name,
                solution_type=self._config.solution_type,
                non_graphical=self._config.non_graphical,
                new_desktop_session=self._config.new_session,
                close_on_exit=True,
            )
        except Exception as e:
            raise HFSSDriverError(f"HFSS 启动失败: {e}") from e

        return hfss

    def set_variables(self, variables: dict) -> None:
        """
        设置工程中的参数化变量值

        Args:
            variables: 字典，键为变量名（必须与 HFSS 中完全一致），
                       值为数值（float）

        Raises:
            HFSSDriverError: HFSS 实例未初始化或变量设置失败
        """
        self._ensure_ready()
        for name, value in variables.items():
            try:
                self._hfss[name] = value
                logger.debug(f"设置变量: {name} = {value}")
            except Exception as e:
                raise HFSSDriverError(
                    f"设置变量 {name!r} = {value} 失败: {e}"
                ) from e

    def setup_analysis(self, fidelity: str) -> None:
        """
        配置仿真精度参数（网格密度和扫频设置）

        Args:
            fidelity: "coarse" 或 "fine"

        Raises:
            HFSSDriverError: 分析设置失败
        """
        self._ensure_ready()
        cfg = self._config.get_fidelity_config(fidelity)
        freq_start = self._config.freq_start
        freq_stop = self._config.freq_stop
        num_points = self._config.freq_num_points

        try:
            # 删除原有的求解设置（如有），重新创建以确保参数干净
            setup_name = "AutoSetup"
            if setup_name in self._hfss.setup_names:
                self._hfss.delete_setup(setup_name)

            setup = self._hfss.create_setup(name=setup_name)
            setup.props["MaximumPasses"] = cfg["max_passes"]
            setup.props["MaxDeltaS"] = cfg["max_delta_s"]
            setup.update()

            # 配置频率扫描
            sweep_name = "AutoSweep"
            self._hfss.create_linear_count_sweep(
                setup=setup_name,
                units=self._config.freq_unit,
                start_frequency=freq_start,
                stop_frequency=freq_stop,
                num_of_freq_points=num_points,
                name=sweep_name,
                sweep_type=cfg.get("sweep_type", "Interpolating"),
                save_fields=False,
            )
            logger.debug(
                f"已配置 {fidelity} 精度：max_passes={cfg['max_passes']}, "
                f"max_delta_s={cfg['max_delta_s']}, "
                f"freq=[{freq_start}, {freq_stop}] GHz, "
                f"points={num_points}"
            )
        except Exception as e:
            raise HFSSDriverError(f"配置分析设置失败: {e}") from e

    def run_analysis(self) -> None:
        """
        运行 HFSS 仿真分析

        Raises:
            HFSSDriverError: 仿真执行失败
        """
        self._ensure_ready()
        logger.debug("开始运行 HFSS 仿真...")
        try:
            self._hfss.analyze_all()
            logger.debug("HFSS 仿真完成")
        except Exception as e:
            raise HFSSDriverError(f"HFSS 仿真执行失败: {e}") from e

    def get_hfss_instance(self) -> Any:
        """
        返回底层 pyaedt Hfss 实例，供 result_extractor 使用

        Returns:
            pyaedt.Hfss 实例
        """
        self._ensure_ready()
        return self._hfss

    def close(self) -> None:
        """
        关闭 HFSS 工程并释放资源

        此方法无论如何都会尝试执行，即使 HFSS 实例未正常初始化。
        """
        if self._hfss is not None:
            try:
                self._hfss.close_project()
                logger.debug("已关闭 HFSS 工程")
            except Exception as e:
                logger.warning(f"关闭 HFSS 工程时发生异常（可忽略）: {e}")
            try:
                self._hfss.release_desktop()
                logger.debug("已释放 HFSS Desktop 资源")
            except Exception as e:
                logger.warning(f"释放 Desktop 时发生异常（可忽略）: {e}")
            self._hfss = None

        # 清理工作副本文件
        if self._project_path and Path(self._project_path).exists():
            try:
                Path(self._project_path).unlink()
                logger.debug(f"已删除工作副本: {self._project_path}")
            except Exception as e:
                logger.debug(f"删除工作副本失败（可忽略）: {e}")

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    def _ensure_ready(self) -> None:
        """检查 HFSS 实例是否已就绪，否则抛出异常"""
        if self._hfss is None:
            raise HFSSDriverError(
                "HFSS 实例尚未初始化，请先调用 setup_project()"
            )
