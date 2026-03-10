"""
HFSS 进程管理模块

负责监控和管理 HFSS 进程的生命周期，包括：
- 超时检测与强制终止
- 僵尸进程清理
- 进程状态查询
"""

import logging
import os
import signal
import time
from typing import List, Optional

import psutil

from src.logger import get_logger

logger = get_logger("hfss_automation")

# HFSS 主进程的可执行文件名称（不区分大小写）
_HFSS_PROCESS_NAMES = ("ansysedt.exe", "ansysedt")


def find_hfss_processes() -> List[psutil.Process]:
    """
    查找系统中所有正在运行的 HFSS 进程

    Returns:
        list[psutil.Process]: HFSS 进程列表（可能为空）
    """
    hfss_procs = []
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() in _HFSS_PROCESS_NAMES:
                hfss_procs.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return hfss_procs


def kill_hfss_processes(timeout: float = 10.0) -> int:
    """
    强制终止所有 HFSS 进程

    先发送 SIGTERM，等待 timeout 秒后若仍存在则发送 SIGKILL。

    Args:
        timeout: 等待进程自然退出的时间（秒）

    Returns:
        int: 成功终止的进程数量
    """
    procs = find_hfss_processes()
    if not procs:
        logger.debug("未发现 HFSS 进程，无需清理")
        return 0

    killed = 0
    logger.warning(f"发现 {len(procs)} 个 HFSS 进程，开始强制终止...")

    for proc in procs:
        try:
            logger.debug(f"终止进程 PID={proc.pid}")
            proc.terminate()  # 发送 SIGTERM
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"终止进程 PID={proc.pid} 失败: {e}")

    # 等待进程自然退出
    _, still_alive = psutil.wait_procs(procs, timeout=timeout)

    # 对仍存活的进程发送 SIGKILL
    for proc in still_alive:
        try:
            logger.warning(f"进程 PID={proc.pid} 未响应 SIGTERM，发送 SIGKILL")
            proc.kill()
            killed += 1
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            logger.debug(f"SIGKILL 失败 PID={proc.pid}: {e}")

    killed += len(procs) - len(still_alive)
    logger.info(f"成功终止 {killed} 个 HFSS 进程")
    return killed


class SimulationTimeoutError(Exception):
    """仿真超时错误"""


class TimeoutGuard:
    """
    仿真超时守卫（上下文管理器）

    通过独立线程监控主线程中仿真函数的执行时间，
    超时后终止 HFSS 进程并抛出 SimulationTimeoutError。

    注意：此实现不依赖 UNIX 信号（signal.SIGALRM），
    在 Windows 上同样可用。

    使用示例：
        with TimeoutGuard(seconds=300):
            run_hfss_analysis()
    """

    def __init__(self, seconds: int):
        """
        Args:
            seconds: 超时时间（秒）
        """
        self._seconds = seconds
        self._timer: Optional[object] = None
        self._timed_out = False

    def __enter__(self):
        import threading

        self._timed_out = False

        def _on_timeout():
            self._timed_out = True
            logger.error(
                f"仿真超时（超过 {self._seconds} 秒），正在强制终止 HFSS 进程..."
            )
            kill_hfss_processes()

        self._timer = threading.Timer(self._seconds, _on_timeout)
        self._timer.daemon = True
        self._timer.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._timer is not None:
            self._timer.cancel()
        if self._timed_out:
            raise SimulationTimeoutError(
                f"仿真执行时间超过 {self._seconds} 秒，已强制终止"
            )
        return False
