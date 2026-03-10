"""
单次仿真示例脚本

演示如何调用 run_hfss_simulation() 执行一次仿真并打印结果。

使用方法：
    python scripts/run_single.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径（确保能找到 src 包）
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from src.simulation import run_hfss_simulation


def main():
    # ------------------------------------------------------------------ #
    # 设置仿真参数（根据你的模型和 config.yaml 中的变量名修改）
    # ------------------------------------------------------------------ #
    # x[0] = Length (mm)，x[1] = Width (mm)，x[2] = Feed_X (mm)
    x = [30.0, 25.0, 5.0]

    # 选择仿真精度："coarse"（快）或 "fine"（精确）
    fidelity = "coarse"

    print("=" * 60)
    print("HFSS 单次仿真示例")
    print("=" * 60)
    print(f"参数: {x}")
    print(f"精度: {fidelity}")
    print()

    # ------------------------------------------------------------------ #
    # 运行仿真
    # ------------------------------------------------------------------ #
    try:
        result = run_hfss_simulation(x, fidelity=fidelity)
    except Exception as e:
        print(f"[错误] 仿真失败: {e}")
        sys.exit(1)

    # ------------------------------------------------------------------ #
    # 打印结果
    # ------------------------------------------------------------------ #
    print("仿真完成！")
    print("-" * 40)
    print(f"仿真耗时: {result.simulation_time:.1f} 秒")
    print(f"频率范围: {result.freqs[0]:.2f} ~ {result.freqs[-1]:.2f} GHz")
    print(f"频率点数: {len(result.freqs)}")
    print(f"S11 最小值: {result.s11_min_db:.2f} dB")
    print(f"谐振频率: {result.resonance_frequency:.3f} GHz")
    print()
    print("参数详情:")
    for k, v in result.parameters.items():
        print(f"  {k} = {v}")
    print()
    print("S11 数据（前 5 个频点）:")
    for freq, s11 in zip(result.freqs[:5], result.s11_db[:5]):
        print(f"  {freq:.3f} GHz: {s11:.2f} dB")
    print("  ...")

    # 可选：将 freqs 和 s11_db 保存为 numpy 数组
    # np.save("s11_freqs.npy", result.freqs)
    # np.save("s11_values.npy", result.s11_db)

    return result


if __name__ == "__main__":
    main()
