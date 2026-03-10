"""
核心仿真模块

提供 run_hfss_simulation() 黑盒函数，封装完整的仿真流程：
参数映射 → 启动 HFSS → 运行分析 → 提取结果 → 释放资源

支持自动重试和超时终止，适用于 1000+ 次无人值守批量仿真。
"""

import tempfile
import time
from typing import Union

import numpy as np

from src.config_loader import Config, load_config
from src.hfss_driver import HFSSDriver, HFSSDriverError
from src.logger import get_logger, setup_logger
from src.models import SimulationResult
from src.parameter_manager import ParameterError, ParameterManager
from src.process_manager import SimulationTimeoutError, TimeoutGuard, kill_hfss_processes
from src.result_extractor import ResultExtractor, ResultExtractorError

# 模块级默认配置（首次调用时懒加载）
_default_config: Config = None
_logger = None


def _get_config_and_logger(config_path: str = "config.yaml"):
    """懒加载全局默认配置和日志记录器"""
    global _default_config, _logger
    if _default_config is None:
        _default_config = load_config(config_path)
        _logger = setup_logger(
            name="hfss_automation",
            log_dir=_default_config.log_dir,
            log_prefix=_default_config.log_prefix,
            level=_default_config.log_level,
            console_output=_default_config.console_output,
        )
    return _default_config, _logger


def run_hfss_simulation(
    x: Union[list, np.ndarray],
    fidelity: str = "coarse",
    config_path: str = "config.yaml",
) -> SimulationResult:
    """
    HFSS 仿真黑盒函数（核心接口）

    输入一组天线物理尺寸参数，在后台自动启动 HFSS、运行仿真、
    提取 S11 数据，最后返回完整结果对象。

    支持自动重试（最多 max_retries 次）和超时终止（超过 timeout_seconds 强制 kill）。
    每次仿真结束后自动关闭工程并释放内存，适合连续批量调用。

    Args:
        x (list | np.ndarray): 天线几何尺寸参数数组。
            顺序与 config.yaml 中 variables.names 定义一致，
            例如 x = [Length, Width, Feed_X]。
        fidelity (str): 仿真精度，"coarse" 或 "fine"。
            - "coarse": 粗网格，速度快（适合优化搜索阶段）
            - "fine"  : 细网格，精度高（适合最终验证阶段）
        config_path (str): 配置文件路径，默认为 "config.yaml"。

    Returns:
        SimulationResult: 包含以下字段的结果对象：
            - freqs (np.ndarray): 频率数组（GHz）
            - s11_db (np.ndarray): S11 幅值（dB）
            - parameters (dict): 本次使用的参数字典
            - fidelity (str): 本次仿真精度
            - simulation_time (float): 仿真耗时（秒）
            - gain, impedance, radiation_pattern: 预留扩展字段（默认 None）

    Raises:
        ParameterError: 参数数量与配置不匹配
        RuntimeError: 仿真在 max_retries 次后仍然失败

    Examples:
        >>> result = run_hfss_simulation([30.0, 25.0, 5.0], fidelity="coarse")
        >>> print(result.freqs)
        >>> print(result.s11_db)
        >>> print(result.s11_min_db)      # 最小 S11 值（dB）
        >>> print(result.resonance_frequency)  # 谐振频率（GHz）
    """
    config, logger = _get_config_and_logger(config_path)
    param_mgr = ParameterManager(config)

    # 参数验证（在重试前先验证，避免无效重试）
    param_mgr.validate(x)
    param_record = param_mgr.build_parameter_record(x)
    var_dict = param_mgr.build_variable_dict(x)

    logger.info(f"开始仿真 | 精度: {fidelity} | 参数: {param_record}")

    last_error = None
    for attempt in range(1, config.max_retries + 1):
        if attempt > 1:
            logger.warning(
                f"第 {attempt}/{config.max_retries} 次重试，"
                f"等待 {config.retry_delay_seconds} 秒..."
            )
            time.sleep(config.retry_delay_seconds)
            # 重试前清理可能残留的 HFSS 进程
            kill_hfss_processes()

        try:
            result = _run_single_simulation(
                config=config,
                var_dict=var_dict,
                param_record=param_record,
                fidelity=fidelity,
            )
            logger.info(
                f"仿真成功 | 耗时: {result.simulation_time:.1f}s | "
                f"S11_min: {result.s11_min_db:.2f} dB @ "
                f"{result.resonance_frequency:.3f} GHz"
            )
            return result

        except (SimulationTimeoutError, HFSSDriverError, ResultExtractorError) as e:
            last_error = e
            logger.error(f"仿真失败（第 {attempt} 次）: {e}")
            # 确保 HFSS 进程被清理
            kill_hfss_processes()

    # 所有重试均失败
    raise RuntimeError(
        f"仿真在 {config.max_retries} 次尝试后仍然失败，"
        f"最后一次错误: {last_error}"
    ) from last_error


def _run_single_simulation(
    config: Config,
    var_dict: dict,
    param_record: dict,
    fidelity: str,
) -> SimulationResult:
    """
    执行一次完整仿真流程（不含重试逻辑）

    Args:
        config: 配置对象
        var_dict: 带单位的变量字典，如 {"Length": "30.0mm"}
        param_record: 纯数值的变量字典，如 {"Length": 30.0}
        fidelity: "coarse" 或 "fine"

    Returns:
        SimulationResult

    Raises:
        SimulationTimeoutError: 仿真超时
        HFSSDriverError: HFSS 操作失败
        ResultExtractorError: 结果提取失败
    """
    logger = get_logger("hfss_automation")
    start_time = time.time()

    with tempfile.TemporaryDirectory(prefix="hfss_sim_") as work_dir:
        with TimeoutGuard(seconds=config.timeout_seconds):
            with HFSSDriver(config) as driver:
                # 1. 启动 HFSS 并打开工程副本
                driver.setup_project(work_dir)

                # 2. 设置参数变量
                driver.set_variables(var_dict)

                # 3. 配置仿真精度
                driver.setup_analysis(fidelity)

                # 4. 运行仿真
                driver.run_analysis()

                # 5. 提取结果
                hfss_instance = driver.get_hfss_instance()
                extractor = ResultExtractor(config, hfss_instance)
                freqs, s11_db = extractor.get_s11()

                # 6. 提取可选扩展结果（当前均为 None，后续扩展时实现）
                gain = extractor.get_gain()
                impedance = extractor.get_impedance()
                radiation_pattern = extractor.get_radiation_pattern()

    elapsed = time.time() - start_time

    return SimulationResult(
        freqs=freqs,
        s11_db=s11_db,
        parameters=param_record,
        fidelity=fidelity,
        simulation_time=elapsed,
        gain=gain,
        impedance=impedance,
        radiation_pattern=radiation_pattern,
    )
