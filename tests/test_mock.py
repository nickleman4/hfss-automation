"""
Mock 测试模块（无需真实 HFSS 环境）

使用 unittest.mock 模拟 pyaedt 和 HFSS 驱动，
验证仿真流程的各个环节在无 HFSS 安装环境下也能正确测试。
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import numpy as np
import pytest
import yaml

from src.config_loader import Config
from src.models import SimulationResult
from src.parameter_manager import ParameterError, ParameterManager


# 共用的最小配置数据
MINIMAL_CONFIG = {
    "hfss": {
        "version": "2023.1",
        "install_dir": "C:/Program Files/AnsysEM/v231/Win64",
        "non_graphical": True,
        "new_session": True,
    },
    "project": {
        "template_path": "templates/test.aedt",
        "design_name": "HFSSDesign1",
        "solution_type": "Modal",
        "port_name": "Port1",
    },
    "variables": {
        "names": ["Length", "Width", "Feed_X"],
        "units": ["mm", "mm", "mm"],
    },
    "frequency": {
        "start": 2.0,
        "stop": 3.0,
        "num_points": 101,
        "unit": "GHz",
    },
    "fidelity": {
        "coarse": {"max_passes": 5, "max_delta_s": 0.05, "sweep_type": "Interpolating"},
        "fine": {"max_passes": 15, "max_delta_s": 0.01, "sweep_type": "Interpolating"},
    },
    "stability": {"timeout_seconds": 60, "max_retries": 2, "retry_delay_seconds": 1},
    "output": {"results_dir": "results", "save_results": True, "results_prefix": "sim"},
    "logging": {"log_dir": "logs", "level": "DEBUG", "log_prefix": "test", "console_output": False},
}


@pytest.fixture
def config_file(tmp_path):
    """创建临时配置文件，results_dir 和 log_dir 指向 tmp_path"""
    import copy
    cfg = copy.deepcopy(MINIMAL_CONFIG)
    cfg["output"]["results_dir"] = str(tmp_path / "results")
    cfg["logging"]["log_dir"] = str(tmp_path / "logs")

    p = tmp_path / "config.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)
    return str(p)


@pytest.fixture
def config(config_file):
    return Config(config_file)


# ========================================================
# ParameterManager 测试
# ========================================================

class TestParameterManager:
    """测试参数管理器（不需要 HFSS）"""

    def test_build_variable_dict_correct(self, config):
        mgr = ParameterManager(config)
        result = mgr.build_variable_dict([30.0, 25.0, 5.0])
        assert result == {"Length": "30.0mm", "Width": "25.0mm", "Feed_X": "5.0mm"}

    def test_build_variable_dict_with_numpy(self, config):
        mgr = ParameterManager(config)
        x = np.array([30.0, 25.0, 5.0])
        result = mgr.build_variable_dict(x)
        assert result["Length"] == "30.0mm"

    def test_validate_wrong_length(self, config):
        mgr = ParameterManager(config)
        with pytest.raises(ParameterError):
            mgr.validate([30.0, 25.0])  # 只传 2 个，期望 3 个

    def test_build_parameter_record(self, config):
        mgr = ParameterManager(config)
        record = mgr.build_parameter_record([30.0, 25.0, 5.0])
        assert record == {"Length": 30.0, "Width": 25.0, "Feed_X": 5.0}

    def test_num_variables(self, config):
        mgr = ParameterManager(config)
        assert mgr.num_variables == 3


# ========================================================
# 模拟 HFSSDriver 的仿真流程测试
# ========================================================

def make_mock_hfss():
    """创建一个模拟 pyaedt Hfss 实例"""
    mock_hfss = MagicMock()
    mock_hfss.setup_names = []
    # 模拟 S11 数据提取
    mock_solution_data = MagicMock()
    mock_solution_data.primary_sweep_values = (
        np.linspace(2e9, 3e9, 101).tolist()
    )
    mock_solution_data.data_real.return_value = (
        (-5.0 + 20.0 * ((np.linspace(2.0, 3.0, 101) - 2.45) / 0.5) ** 2).tolist()
    )
    mock_hfss.post.get_solution_data.return_value = mock_solution_data
    return mock_hfss


class TestRunHFSSSimulationMocked:
    """Mock 测试：模拟完整的 run_hfss_simulation 流程"""

    def test_run_returns_simulation_result(self, tmp_path, config_file):
        """Mock HFSSDriver 后，run_hfss_simulation 应返回 SimulationResult"""
        # 创建假模板文件
        (tmp_path / "templates").mkdir(exist_ok=True)
        (tmp_path / "templates" / "test.aedt").write_text("fake aedt")

        # 模拟 HFSSDriver 和 ResultExtractor
        mock_hfss_instance = make_mock_hfss()

        with patch("src.simulation._default_config", None), \
             patch("src.simulation._logger", None), \
             patch("src.hfss_driver.HFSSDriver.setup_project"), \
             patch("src.hfss_driver.HFSSDriver.set_variables"), \
             patch("src.hfss_driver.HFSSDriver.setup_analysis"), \
             patch("src.hfss_driver.HFSSDriver.run_analysis"), \
             patch("src.hfss_driver.HFSSDriver.get_hfss_instance",
                   return_value=mock_hfss_instance), \
             patch("src.hfss_driver.HFSSDriver.close"):

            from src.simulation import run_hfss_simulation
            result = run_hfss_simulation(
                [30.0, 25.0, 5.0],
                fidelity="coarse",
                config_path=config_file,
            )

        assert isinstance(result, SimulationResult)
        assert len(result.freqs) == 101
        assert len(result.s11_db) == 101
        assert result.fidelity == "coarse"
        assert result.simulation_time >= 0

    def test_run_raises_on_wrong_param_count(self, config_file):
        """参数数量不对时应抛出 ParameterError，不尝试启动 HFSS"""
        with patch("src.simulation._default_config", None), \
             patch("src.simulation._logger", None):
            from src.simulation import run_hfss_simulation
            with pytest.raises(ParameterError):
                run_hfss_simulation(
                    [30.0, 25.0],   # 只有 2 个，期望 3 个
                    config_path=config_file,
                )

    def test_run_retries_on_failure(self, tmp_path, config_file):
        """HFSSDriver 失败时应自动重试，超过最大次数后抛出 RuntimeError"""
        from src.hfss_driver import HFSSDriverError

        with patch("src.simulation._default_config", None), \
             patch("src.simulation._logger", None), \
             patch("src.hfss_driver.HFSSDriver.setup_project",
                   side_effect=HFSSDriverError("模拟 HFSS 失败")), \
             patch("src.hfss_driver.HFSSDriver.close"), \
             patch("src.process_manager.kill_hfss_processes"), \
             patch("time.sleep"):  # 跳过重试等待时间

            from src.simulation import run_hfss_simulation
            with pytest.raises(RuntimeError):
                run_hfss_simulation(
                    [30.0, 25.0, 5.0],
                    config_path=config_file,
                )


# ========================================================
# BatchRunner 测试（Mock 模式）
# ========================================================

class TestBatchRunnerMocked:
    """测试批量运行器（Mock run_hfss_simulation）"""

    def _make_mock_result(self, idx: int) -> SimulationResult:
        freqs = np.linspace(2.0, 3.0, 11)
        s11_db = np.full(11, -float(idx + 10))
        return SimulationResult(
            freqs=freqs,
            s11_db=s11_db,
            parameters={"Length": float(30 + idx)},
            fidelity="coarse",
            simulation_time=1.0,
        )

    def test_batch_run_all_success(self, tmp_path, config_file):
        """所有仿真成功时，results 列表长度应与参数数量一致"""
        from src.batch_runner import BatchRunner

        call_count = 0

        def mock_sim(x, fidelity="coarse", config_path="config.yaml"):
            nonlocal call_count
            result = self._make_mock_result(call_count)
            call_count += 1
            return result

        checkpoint_file = str(tmp_path / "checkpoint.json")
        with patch("src.batch_runner.run_hfss_simulation", side_effect=mock_sim), \
             patch("src.simulation._default_config", None), \
             patch("src.simulation._logger", None):
            runner = BatchRunner(config_path=config_file, checkpoint_file=checkpoint_file)
            param_list = [[30.0 + i, 25.0, 5.0] for i in range(5)]
            results = runner.run(param_list, fidelity="coarse")

        assert len(results) == 5
        assert all(r is not None for r in results)

    def test_batch_run_checkpoint_resume(self, tmp_path, config_file):
        """断点续跑：预写检查点后，已完成的任务应被跳过"""
        from src.batch_runner import BatchRunner

        # 预先模拟第 0 个任务已完成
        results_dir = tmp_path / "batch_results"
        results_dir.mkdir()
        saved_result = self._make_mock_result(0).to_dict()
        result_file = results_dir / "sim_000000.json"
        with open(result_file, "w") as f:
            json.dump(saved_result, f)

        # 写入断点文件
        checkpoint_file = tmp_path / "checkpoint.json"
        with open(checkpoint_file, "w") as f:
            json.dump({"0": str(result_file)}, f)

        call_count = 0

        def mock_sim(x, fidelity="coarse", config_path="config.yaml"):
            nonlocal call_count
            result = self._make_mock_result(call_count + 1)
            call_count += 1
            return result

        with patch("src.batch_runner.run_hfss_simulation", side_effect=mock_sim), \
             patch("src.simulation._default_config", None), \
             patch("src.simulation._logger", None):
            runner = BatchRunner(
                config_path=config_file,
                checkpoint_file=str(checkpoint_file),
            )
            # 覆盖 results_dir 以匹配上面创建的目录
            runner._results_dir = results_dir
            param_list = [[30.0 + i, 25.0, 5.0] for i in range(3)]
            results = runner.run(param_list)

        # 第 0 个从断点恢复，run_hfss_simulation 只调用 2 次（任务 1 和 2）
        assert call_count == 2
        assert len(results) == 3
