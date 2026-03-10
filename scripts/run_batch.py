"""
批量仿真示例脚本（1000 次）

演示如何使用 BatchRunner 连续运行 1000 组不同参数的仿真，
支持断点续跑：如果中途中断，再次运行此脚本会自动从上次位置继续。

使用方法：
    python scripts/run_batch.py

如需重新从头运行（清除断点记录）：
    python scripts/run_batch.py --reset
"""

import argparse
import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import numpy as np

from src.batch_runner import BatchRunner


def generate_param_list(n: int = 1000) -> list:
    """
    生成 n 组随机天线参数（示例）

    在实际使用中，将此函数替换为你的参数来源：
    - 从优化算法（如遗传算法、贝叶斯优化）获取
    - 从 CSV 文件读取
    - 使用拉丁超立方采样（LHS）生成

    Returns:
        list: 参数列表，每个元素是 [Length, Width, Feed_X] 数组
    """
    rng = np.random.default_rng(seed=42)

    # 参数范围（根据你的天线模型修改）
    length_range = (25.0, 35.0)   # mm
    width_range  = (20.0, 30.0)   # mm
    feed_x_range = (3.0, 8.0)     # mm

    param_list = []
    for _ in range(n):
        x = [
            rng.uniform(*length_range),
            rng.uniform(*width_range),
            rng.uniform(*feed_x_range),
        ]
        param_list.append(x)
    return param_list


def main():
    # 解析命令行参数
    parser = argparse.ArgumentParser(description="HFSS 批量仿真（1000 次）")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="清除断点记录，从头开始运行",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=1000,
        help="仿真总次数（默认：1000）",
    )
    parser.add_argument(
        "--fidelity",
        choices=["coarse", "fine"],
        default="coarse",
        help="仿真精度（默认：coarse）",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("HFSS 批量仿真示例")
    print("=" * 60)
    print(f"总次数: {args.n}")
    print(f"精度: {args.fidelity}")
    print()

    # 生成参数列表
    param_list = generate_param_list(args.n)
    print(f"已生成 {len(param_list)} 组参数")

    # 创建批量运行器
    runner = BatchRunner(config_path="config.yaml")

    # 如果指定 --reset，清除断点记录
    if args.reset:
        runner.reset_checkpoint()
        print("断点记录已清除，将从头开始运行")

    print("开始批量仿真...")
    print("-" * 40)

    # 运行批量仿真
    results = runner.run(param_list, fidelity=args.fidelity)

    # 打印摘要
    summary = runner.get_summary()
    print()
    print("=" * 60)
    print("批量仿真完成！")
    print("-" * 40)
    print(f"本次成功: {summary['success_count']}")
    print(f"本次失败: {summary['failure_count']}")
    print(f"断点记录已保存到: {summary['checkpoint_file']}")
    print(f"结果文件目录: {summary['results_dir']}")

    # 统计成功结果的 S11 分布
    valid_results = [r for r in results if r is not None]
    if valid_results:
        s11_mins = [r.s11_min_db for r in valid_results]
        res_freqs = [r.resonance_frequency for r in valid_results]
        print()
        print("S11 统计（成功仿真）:")
        print(f"  最小 S11 均值: {np.mean(s11_mins):.2f} dB")
        print(f"  最小 S11 范围: [{min(s11_mins):.2f}, {max(s11_mins):.2f}] dB")
        print(f"  谐振频率均值: {np.mean(res_freqs):.3f} GHz")


if __name__ == "__main__":
    main()
