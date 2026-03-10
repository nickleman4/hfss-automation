"""
配置加载模块测试

测试 Config 类的加载、验证和属性访问功能。
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from src.config_loader import Config, ConfigError, load_config


# 最小合法配置内容（用于测试基础功能）
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
        "coarse": {
            "max_passes": 5,
            "max_delta_s": 0.05,
            "sweep_type": "Interpolating",
        },
        "fine": {
            "max_passes": 15,
            "max_delta_s": 0.01,
            "sweep_type": "Interpolating",
        },
    },
}


@pytest.fixture
def config_file(tmp_path):
    """创建临时配置文件"""
    cfg_path = tmp_path / "config.yaml"
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.dump(MINIMAL_CONFIG, f, allow_unicode=True)
    return str(cfg_path)


class TestConfigLoading:
    """测试配置文件加载"""

    def test_load_valid_config(self, config_file):
        """合法配置文件应该正常加载"""
        cfg = Config(config_file)
        assert cfg is not None

    def test_file_not_found(self, tmp_path):
        """不存在的配置文件应抛出 FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            Config(str(tmp_path / "nonexistent.yaml"))

    def test_invalid_yaml_format(self, tmp_path):
        """非字典格式的 YAML 应抛出 ConfigError"""
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("- item1\n- item2\n")
        with pytest.raises(ConfigError):
            Config(str(bad_file))

    def test_load_config_convenience_function(self, config_file):
        """测试 load_config 便捷函数"""
        cfg = load_config(config_file)
        assert isinstance(cfg, Config)


class TestConfigProperties:
    """测试配置属性访问"""

    @pytest.fixture(autouse=True)
    def setup(self, config_file):
        self.cfg = Config(config_file)

    def test_hfss_version(self):
        assert self.cfg.hfss_version == "2023.1"

    def test_non_graphical(self):
        assert self.cfg.non_graphical is True

    def test_new_session(self):
        assert self.cfg.new_session is True

    def test_design_name(self):
        assert self.cfg.design_name == "HFSSDesign1"

    def test_solution_type(self):
        assert self.cfg.solution_type == "Modal"

    def test_port_name(self):
        assert self.cfg.port_name == "Port1"

    def test_variable_names(self):
        assert self.cfg.variable_names == ["Length", "Width", "Feed_X"]

    def test_variable_units(self):
        assert self.cfg.variable_units == ["mm", "mm", "mm"]

    def test_freq_start(self):
        assert self.cfg.freq_start == 2.0

    def test_freq_stop(self):
        assert self.cfg.freq_stop == 3.0

    def test_freq_num_points(self):
        assert self.cfg.freq_num_points == 101

    def test_fidelity_config_coarse(self):
        coarse = self.cfg.get_fidelity_config("coarse")
        assert coarse["max_passes"] == 5
        assert coarse["max_delta_s"] == 0.05

    def test_fidelity_config_fine(self):
        fine = self.cfg.get_fidelity_config("fine")
        assert fine["max_passes"] == 15
        assert fine["max_delta_s"] == 0.01

    def test_fidelity_config_invalid(self):
        with pytest.raises(ConfigError):
            self.cfg.get_fidelity_config("ultra")


class TestConfigValidation:
    """测试配置验证逻辑"""

    def _make_config(self, tmp_path, overrides: dict) -> str:
        """创建带有覆盖项的测试配置文件"""
        import copy
        cfg = copy.deepcopy(MINIMAL_CONFIG)
        for key_path, value in overrides.items():
            keys = key_path.split(".")
            node = cfg
            for k in keys[:-1]:
                node = node[k]
            node[keys[-1]] = value
        p = tmp_path / "config.yaml"
        with open(p, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, allow_unicode=True)
        return str(p)

    def test_missing_required_field(self, tmp_path):
        """缺少必填项应抛出 ConfigError"""
        import copy
        cfg = copy.deepcopy(MINIMAL_CONFIG)
        del cfg["hfss"]["version"]
        p = tmp_path / "config.yaml"
        with open(p, "w") as f:
            yaml.dump(cfg, f)
        with pytest.raises(ConfigError):
            Config(str(p))

    def test_variable_count_mismatch(self, tmp_path):
        """变量名和单位数量不一致应抛出 ConfigError"""
        path = self._make_config(tmp_path, {"variables.units": ["mm", "mm"]})
        with pytest.raises(ConfigError):
            Config(path)

    def test_frequency_range_invalid(self, tmp_path):
        """起始频率 >= 终止频率应抛出 ConfigError"""
        path = self._make_config(tmp_path, {"frequency.start": 3.0, "frequency.stop": 2.0})
        with pytest.raises(ConfigError):
            Config(path)
