"""
HFSS 自动化仿真接口包

使用示例：
    from src.simulation import run_hfss_simulation

    result = run_hfss_simulation([30.0, 25.0, 5.0], fidelity="coarse")
    print(result.freqs)
    print(result.s11_db)
"""

from src.simulation import run_hfss_simulation
from src.models import SimulationResult

__all__ = ["run_hfss_simulation", "SimulationResult"]
__version__ = "1.0.0"
