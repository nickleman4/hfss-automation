"""
仿真流程集成测试

在没有真实 HFSS 的环境中，使用 Mock 验证仿真流程的完整集成路径。
实际有 HFSS 安装时，可通过修改此文件进行端到端测试。
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import yaml

from src.config_loader import Config
from src.models import SimulationResult


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
        "num_points": 51,
        "unit": "GHz",
    },
    "fidelity": {
        "coarse": {"max_passes": 3, "max_delta_s": 0.05, "sweep_type": "Interpolating"},
        "fine": {"max_passes": 10, "max_delta_s": 0.01, "sweep_type": "Interpolating"},
    },
    "stability": {"timeout_seconds": 30, "max_retries": 1, "retry_delay_seconds": 0},
    "output": {"results_dir": "results", "save_results": False, "results_prefix": "sim"},
    "logging": {"log_dir": "logs", "level": "DEBUG", "log_prefix": "test", "console_output": False},
}


@pytest.fixture
def config_file(tmp_path):
    import copy
    cfg = copy.deepcopy(MINIMAL_CONFIG)
    cfg["output"]["results_dir"] = str(tmp_path / "results")
    cfg["logging"]["log_dir"] = str(tmp_path / "logs")
    p = tmp_path / "config.yaml"
    with open(p, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True)
    return str(p)


def make_mock_hfss_instance():
    """创建模拟 HFSS 实例，返回合理的仿真数据"""
    mock_hfss = MagicMock()
    mock_hfss.setup_names = []

    freqs_hz = np.linspace(2e9, 3e9, 51).tolist()
    s11_values = (-5.0 + 20.0 * ((np.linspace(2.0, 3.0, 51) - 2.45) / 0.5) ** 2).tolist()

    mock_solution_data = MagicMock()
    mock_solution_data.primary_sweep_values = freqs_hz
    mock_solution_data.data_real.return_value = s11_values
    mock_hfss.post.get_solution_data.return_value = mock_solution_data

    return mock_hfss


class TestSimulationPipeline:
    """完整仿真流程的集成测试（使用 Mock）"""

    @pytest.fixture(autouse=True)
    def reset_globals(self):
        """每个测试前重置模块级缓存，避免测试间相互污染"""
        import src.simulation as sim_module
        sim_module._default_config = None
        sim_module._logger = None
        yield
        sim_module._default_config = None
        sim_module._logger = None

    def test_coarse_simulation_result_shape(self, config_file):
        """coarse 仿真应返回正确形状的数组"""
        mock_hfss = make_mock_hfss_instance()

        with patch("src.hfss_driver.HFSSDriver.setup_project"), \
             patch("src.hfss_driver.HFSSDriver.set_variables"), \
             patch("src.hfss_driver.HFSSDriver.setup_analysis"), \
             patch("src.hfss_driver.HFSSDriver.run_analysis"), \
             patch("src.hfss_driver.HFSSDriver.get_hfss_instance",
                   return_value=mock_hfss), \
             patch("src.hfss_driver.HFSSDriver.close"):

            from src.simulation import run_hfss_simulation
            result = run_hfss_simulation(
                [30.0, 25.0, 5.0],
                fidelity="coarse",
                config_path=config_file,
            )

        assert result.freqs.shape == (51,)
        assert result.s11_db.shape == (51,)
        assert result.fidelity == "coarse"

    def test_fine_simulation_result_shape(self, config_file):
        """fine 仿真应返回正确形状的数组"""
        mock_hfss = make_mock_hfss_instance()

        with patch("src.hfss_driver.HFSSDriver.setup_project"), \
             patch("src.hfss_driver.HFSSDriver.set_variables"), \
             patch("src.hfss_driver.HFSSDriver.setup_analysis"), \
             patch("src.hfss_driver.HFSSDriver.run_analysis"), \
             patch("src.hfss_driver.HFSSDriver.get_hfss_instance",
                   return_value=mock_hfss), \
             patch("src.hfss_driver.HFSSDriver.close"):

            from src.simulation import run_hfss_simulation
            result = run_hfss_simulation(
                [30.0, 25.0, 5.0],
                fidelity="fine",
                config_path=config_file,
            )

        assert result.fidelity == "fine"

    def test_result_parameters_match_input(self, config_file):
        """返回结果中的 parameters 字段应与输入一致"""
        mock_hfss = make_mock_hfss_instance()
        x = [32.5, 27.0, 6.0]

        with patch("src.hfss_driver.HFSSDriver.setup_project"), \
             patch("src.hfss_driver.HFSSDriver.set_variables"), \
             patch("src.hfss_driver.HFSSDriver.setup_analysis"), \
             patch("src.hfss_driver.HFSSDriver.run_analysis"), \
             patch("src.hfss_driver.HFSSDriver.get_hfss_instance",
                   return_value=mock_hfss), \
             patch("src.hfss_driver.HFSSDriver.close"):

            from src.simulation import run_hfss_simulation
            result = run_hfss_simulation(x, config_path=config_file)

        assert abs(result.parameters["Length"] - 32.5) < 1e-10
        assert abs(result.parameters["Width"] - 27.0) < 1e-10
        assert abs(result.parameters["Feed_X"] - 6.0) < 1e-10

    def test_simulation_time_is_positive(self, config_file):
        """仿真耗时应为正数"""
        mock_hfss = make_mock_hfss_instance()

        with patch("src.hfss_driver.HFSSDriver.setup_project"), \
             patch("src.hfss_driver.HFSSDriver.set_variables"), \
             patch("src.hfss_driver.HFSSDriver.setup_analysis"), \
             patch("src.hfss_driver.HFSSDriver.run_analysis"), \
             patch("src.hfss_driver.HFSSDriver.get_hfss_instance",
                   return_value=mock_hfss), \
             patch("src.hfss_driver.HFSSDriver.close"):

            from src.simulation import run_hfss_simulation
            result = run_hfss_simulation(
                [30.0, 25.0, 5.0], config_path=config_file
            )

        assert result.simulation_time >= 0
