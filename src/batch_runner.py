"""
批量运行模块

提供支持断点续跑的批量仿真运行器，适用于连续运行 1000+ 组参数的场景。

核心功能：
- 自动将每次仿真结果写入 JSON 文件（断点续跑依赖此文件）
- 从检查点文件恢复未完成的运行
- 汇总成功/失败统计
"""

import json
import os
import time
from pathlib import Path
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Union

import numpy as np

from src.config_loader import Config, load_config
from src.logger import get_logger
from src.models import SimulationResult
from src.simulation import run_hfss_simulation

logger = get_logger("hfss_automation")


class BatchRunner:
    """
    批量仿真运行器（支持断点续跑）

    将参数列表分批次运行，每次仿真后立即写入结果文件。
    如果运行中断，再次启动时会自动跳过已完成的任务。

    使用示例：
        runner = BatchRunner("config.yaml")
        runner.run(param_list, fidelity="coarse")
        summary = runner.get_summary()
    """

    def __init__(
        self,
        config_path: str = "config.yaml",
        checkpoint_file: Optional[str] = None,
    ):
        """
        Args:
            config_path: 配置文件路径
            checkpoint_file: 断点记录文件路径（JSON）。
                若为 None，则自动在 results_dir 下创建。
        """
        self._config = load_config(config_path)
        self._config_path = config_path
        self._results_dir = Path(self._config.results_dir)
        self._results_dir.mkdir(parents=True, exist_ok=True)

        # 断点文件：记录已完成的任务序号及其结果路径
        if checkpoint_file is None:
            self._checkpoint_path = self._results_dir / "batch_checkpoint.json"
        else:
            self._checkpoint_path = Path(checkpoint_file)

        # 加载已有的断点记录
        self._checkpoint: Dict[int, str] = self._load_checkpoint()

        # 统计数据
        self._success_count = 0
        self._failure_count = 0
        self._results: List[Optional[SimulationResult]] = []

    # ------------------------------------------------------------------ #
    # 公开接口
    # ------------------------------------------------------------------ #

    def run(
        self,
        param_list: List[Union[list, np.ndarray]],
        fidelity: str = "coarse",
    ) -> List[Optional[SimulationResult]]:
        """
        批量运行仿真

        Args:
            param_list: 参数列表，每个元素是一组尺寸参数，
                        例如 [[30.0, 25.0, 5.0], [31.0, 24.0, 4.5], ...]
            fidelity: 仿真精度，"coarse" 或 "fine"

        Returns:
            list: SimulationResult 列表，失败的任务对应位置为 None
        """
        total = len(param_list)
        logger.info(f"批量仿真启动：共 {total} 组参数，精度: {fidelity}")

        self._results = [None] * total

        # 恢复已完成的任务
        already_done = self._restore_completed(total)
        if already_done:
            logger.info(f"已从断点恢复 {len(already_done)} 个已完成任务")

        for idx, x in enumerate(param_list):
            # 跳过已完成的任务
            if idx in self._checkpoint:
                logger.info(f"[{idx + 1}/{total}] 跳过（已完成）")
                continue

            logger.info(f"[{idx + 1}/{total}] 运行仿真...")
            start = time.time()

            try:
                result = run_hfss_simulation(
                    x=x,
                    fidelity=fidelity,
                    config_path=self._config_path,
                )
                self._results[idx] = result
                self._success_count += 1

                # 保存结果并更新断点
                if self._config.save_results:
                    result_path = self._save_result(idx, result)
                    self._update_checkpoint(idx, result_path)

                elapsed = time.time() - start
                logger.info(
                    f"[{idx + 1}/{total}] 成功 | 耗时: {elapsed:.1f}s | "
                    f"S11_min: {result.s11_min_db:.2f} dB"
                )

            except Exception as e:
                self._failure_count += 1
                elapsed = time.time() - start
                logger.error(
                    f"[{idx + 1}/{total}] 失败（耗时 {elapsed:.1f}s）: {e}"
                )

        total_done = self._success_count + len(already_done)
        logger.info(
            f"批量仿真完成 | 本次成功: {self._success_count} | "
            f"本次失败: {self._failure_count} | "
            f"总计成功: {total_done}/{total}"
        )
        return self._results

    def get_summary(self) -> dict:
        """
        返回当前批量运行的统计摘要

        Returns:
            dict: 包含 total, success, failure, checkpoint_file 等键
        """
        return {
            "success_count": self._success_count,
            "failure_count": self._failure_count,
            "total_completed_in_checkpoint": len(self._checkpoint),
            "checkpoint_file": str(self._checkpoint_path),
            "results_dir": str(self._results_dir),
        }

    def reset_checkpoint(self) -> None:
        """清除断点记录，下次 run() 将从头开始"""
        self._checkpoint = {}
        if self._checkpoint_path.exists():
            self._checkpoint_path.unlink()
        logger.info("断点记录已清除")

    # ------------------------------------------------------------------ #
    # 内部方法
    # ------------------------------------------------------------------ #

    def _load_checkpoint(self) -> Dict[int, str]:
        """从文件加载已有的断点记录"""
        if not self._checkpoint_path.exists():
            return {}
        try:
            with open(self._checkpoint_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            # JSON key 都是字符串，需转换为 int
            return {int(k): v for k, v in raw.items()}
        except Exception as e:
            logger.warning(f"加载断点文件失败，将从头开始: {e}")
            return {}

    def _update_checkpoint(self, idx: int, result_path: str) -> None:
        """更新断点记录文件"""
        self._checkpoint[idx] = result_path
        try:
            with open(self._checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(self._checkpoint, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"写入断点文件失败: {e}")

    def _save_result(self, idx: int, result: SimulationResult) -> str:
        """将单次仿真结果保存为 JSON 文件"""
        filename = f"{self._config.results_prefix}_{idx:06d}.json"
        path = self._results_dir / filename
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result.to_dict(), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"保存结果文件失败: {e}")
        return str(path)

    def _restore_completed(self, total: int) -> List[int]:
        """
        从断点记录中加载已完成任务的结果到 self._results

        Returns:
            已完成任务的序号列表
        """
        completed = []
        for idx, result_path in self._checkpoint.items():
            if 0 <= idx < total:
                try:
                    self._results[idx] = self._load_result(result_path)
                    completed.append(idx)
                except Exception as e:
                    logger.warning(f"恢复任务 {idx} 的结果失败: {e}")
        return completed

    @staticmethod
    def _load_result(path: str) -> Optional[SimulationResult]:
        """从 JSON 文件重建 SimulationResult 对象"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return SimulationResult(
            freqs=np.array(data["freqs"]),
            s11_db=np.array(data["s11_db"]),
            parameters=data["parameters"],
            fidelity=data["fidelity"],
            simulation_time=data["simulation_time"],
            extra_results=data.get("extra_results", {}),
        )
