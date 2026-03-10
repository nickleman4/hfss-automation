"""
数据模型测试

测试 SimulationResult 数据类的属性、方法和序列化功能。
"""

import numpy as np
import pytest

from src.models import SimulationResult


@pytest.fixture
def sample_result():
    """创建一个用于测试的示例 SimulationResult"""
    freqs = np.linspace(2.0, 3.0, 101)
    # 在 2.45 GHz 附近制造一个 S11 凹陷
    s11_db = -5.0 + 20.0 * ((freqs - 2.45) / 0.5) ** 2
    return SimulationResult(
        freqs=freqs,
        s11_db=s11_db,
        parameters={"Length": 30.0, "Width": 25.0, "Feed_X": 5.0},
        fidelity="coarse",
        simulation_time=45.0,
    )


class TestSimulationResultBasic:
    """测试基础属性"""

    def test_freqs_array(self, sample_result):
        """freqs 应是 numpy 数组"""
        assert isinstance(sample_result.freqs, np.ndarray)
        assert len(sample_result.freqs) == 101

    def test_s11_db_array(self, sample_result):
        """s11_db 应是 numpy 数组"""
        assert isinstance(sample_result.s11_db, np.ndarray)
        assert len(sample_result.s11_db) == 101

    def test_parameters_dict(self, sample_result):
        """parameters 应包含正确的键值"""
        assert sample_result.parameters["Length"] == 30.0
        assert sample_result.parameters["Width"] == 25.0

    def test_fidelity(self, sample_result):
        assert sample_result.fidelity == "coarse"

    def test_simulation_time(self, sample_result):
        assert sample_result.simulation_time == 45.0

    def test_optional_fields_default_none(self, sample_result):
        """可选扩展字段默认应为 None"""
        assert sample_result.gain is None
        assert sample_result.impedance is None
        assert sample_result.radiation_pattern is None
        assert sample_result.extra_results == {}


class TestSimulationResultComputedProperties:
    """测试计算属性"""

    def test_s11_min_db(self, sample_result):
        """s11_min_db 应返回 S11 最小值"""
        expected = float(np.min(sample_result.s11_db))
        assert abs(sample_result.s11_min_db - expected) < 1e-10

    def test_resonance_frequency(self, sample_result):
        """resonance_frequency 应返回 S11 最小值对应的频率"""
        min_idx = int(np.argmin(sample_result.s11_db))
        expected = float(sample_result.freqs[min_idx])
        assert abs(sample_result.resonance_frequency - expected) < 1e-10

    def test_resonance_near_2_45_ghz(self, sample_result):
        """谐振频率应接近 2.45 GHz（由 fixture 数据决定）"""
        assert abs(sample_result.resonance_frequency - 2.45) < 0.05


class TestSimulationResultSerialization:
    """测试序列化功能"""

    def test_to_dict_has_required_keys(self, sample_result):
        """to_dict() 应包含所有必需键"""
        d = sample_result.to_dict()
        assert "freqs" in d
        assert "s11_db" in d
        assert "parameters" in d
        assert "fidelity" in d
        assert "simulation_time" in d
        assert "extra_results" in d

    def test_to_dict_arrays_are_lists(self, sample_result):
        """to_dict() 中的 numpy 数组应转换为 Python list"""
        d = sample_result.to_dict()
        assert isinstance(d["freqs"], list)
        assert isinstance(d["s11_db"], list)

    def test_to_dict_optional_fields_absent_when_none(self, sample_result):
        """可选字段为 None 时不应出现在 to_dict() 结果中"""
        d = sample_result.to_dict()
        assert "gain" not in d
        assert "impedance" not in d
        assert "radiation_pattern" not in d

    def test_to_dict_with_gain(self):
        """有增益数据时应出现在 to_dict() 中"""
        result = SimulationResult(
            freqs=np.array([2.0, 2.5, 3.0]),
            s11_db=np.array([-5.0, -20.0, -5.0]),
            parameters={"Length": 30.0},
            fidelity="fine",
            simulation_time=120.0,
            gain=np.array([3.0, 5.0, 3.0]),
        )
        d = result.to_dict()
        assert "gain" in d
        assert d["gain"] == [3.0, 5.0, 3.0]

    def test_to_dict_with_complex_impedance(self):
        """复数阻抗应分 real/imag 序列化"""
        result = SimulationResult(
            freqs=np.array([2.0, 2.5, 3.0]),
            s11_db=np.array([-5.0, -20.0, -5.0]),
            parameters={},
            fidelity="coarse",
            simulation_time=30.0,
            impedance=np.array([50 + 0j, 50 + 10j, 50 - 5j]),
        )
        d = result.to_dict()
        assert "impedance" in d
        assert "real" in d["impedance"]
        assert "imag" in d["impedance"]


class TestSimulationResultRepr:
    """测试字符串表示"""

    def test_repr_contains_fidelity(self, sample_result):
        r = repr(sample_result)
        assert "coarse" in r

    def test_repr_contains_ghz(self, sample_result):
        r = repr(sample_result)
        assert "GHz" in r

    def test_repr_contains_db(self, sample_result):
        r = repr(sample_result)
        assert "dB" in r
