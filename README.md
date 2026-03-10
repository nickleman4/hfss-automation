# HFSS 自动化仿真调用接口

> 封装 HFSS 为黑盒函数，主程序传入天线物理尺寸参数，后台自动运行仿真并返回 S11 数据，支持 1000+ 次无人值守批量仿真。

---

## 目录

1. [项目简介](#项目简介)
2. [功能特性](#功能特性)
3. [环境要求](#环境要求)
4. [安装步骤](#安装步骤)
5. [快速开始](#快速开始)
6. [配置文件说明](#配置文件说明)
7. [API 参考](#api-参考)
8. [使用示例](#使用示例)
9. [重要注意事项](#重要注意事项)
10. [项目结构说明](#项目结构说明)
11. [后续开发指引](#后续开发指引)
12. [常见问题（FAQ）](#常见问题faq)
13. [更新日志](#更新日志)

---

## 项目简介

本项目提供一个 Python 黑盒函数 `run_hfss_simulation(x, fidelity)`，调用者只需传入一组天线物理尺寸参数（如贴片长度、宽度、馈电点坐标），程序在后台自动启动 HFSS（非图形模式）、修改参数、运行仿真、提取 S11 数据，最后将结果以结构化对象的形式返回给主程序。

**核心价值**：让 HFSS 仿真像调用普通 Python 函数一样简单，完全支持无人值守的批量仿真（1000+ 次）。

---

## 功能特性

- **黑盒函数接口**：一行代码完成完整仿真，无需手动操作 HFSS
- **非图形模式**：`non_graphical=True`，无任何弹窗，适合服务器部署
- **双精度支持**：`coarse`（粗网格，快速）和 `fine`（细网格，精确）可灵活切换
- **自动重试机制**：单次失败最多重试 3 次，不中断整体批量流程
- **超时强制终止**：检测到 HFSS 卡死后自动终止进程并重启，防止永久阻塞
- **内存安全**：每次仿真后关闭工程并释放 Desktop 资源，防止内存累积泄露
- **断点续跑**：批量仿真中断后，下次启动自动从上次完成位置继续
- **结构化结果**：返回 `SimulationResult` 数据类，含频率数组、S11 数组、参数记录、耗时等
- **预留扩展字段**：`gain`、`impedance`、`radiation_pattern` 字段预留，方便后续添加新结果类型
- **完整日志**：每次仿真的参数、耗时、成功/失败自动写入日志文件
- **配置驱动**：所有参数均通过 `config.yaml` 配置，无需修改代码

---

## 环境要求

| 项目 | 要求 |
|------|------|
| **操作系统** | Windows 10/11（HFSS 仅支持 Windows） |
| **HFSS 版本** | 2023R1（`v231`），其他版本需调整 `config.yaml` 中的版本号 |
| **Python 版本** | 3.8 及以上 |
| **pyaedt 版本** | 0.6.73（Ansys 官方驱动库） |
| **HFSS License** | 需要有效的 Ansys HFSS License（服务器或本地 License） |

---

## 安装步骤

### 第一步：安装 HFSS 2023R1

1. 从 Ansys 官网或内部渠道下载 HFSS 2023R1 安装包
2. 按默认路径安装，安装目录通常为 `C:\Program Files\AnsysEM\v231\Win64`
3. 确认 HFSS License 已激活（可通过 Ansys License Manager 验证）

### 第二步：安装 Python 环境

推荐使用 Anaconda 管理环境：

```bash
# 创建专用虚拟环境
conda create -n hfss-auto python=3.10 -y
conda activate hfss-auto
```

或使用 venv：

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
```

### 第三步：安装依赖包

```bash
# 克隆项目（或下载代码包）
git clone https://github.com/nickleman4/hfss-automation.git
cd hfss-automation

# 安装所有依赖
pip install -r requirements.txt
```

> **关于 pyaedt 安装**：`pip install pyaedt==0.6.73` 会自动安装 Ansys 官方 Python 驱动库。
> 如需最新版本，可省略版本号：`pip install pyaedt`，但需注意 API 可能有变化。

### 第四步：配置项目

1. 将 `config_example.yaml` 复制为 `config.yaml`
2. 将你的 `.aedt` 模板工程文件放入 `templates/` 目录
3. 打开 `config.yaml`，修改以下关键项：
   - `hfss.install_dir`：你的 HFSS 安装路径
   - `project.template_path`：模板文件名（如 `templates/my_antenna.aedt`）
   - `project.design_name`：HFSS 模板中的设计名称
   - `variables.names`：从 HFSS 模型中获取的参数化变量名（**区分大小写！**）
   - `frequency.start` / `frequency.stop`：你的仿真频段

### 第五步：验证安装

```bash
python scripts/validate_setup.py
```

所有项目显示 ✓ 表示环境配置正确。

---

## 快速开始

**3 分钟跑通第一个仿真：**

```python
from src.simulation import run_hfss_simulation

# 传入天线尺寸参数（单位与 config.yaml 中 variables.units 定义一致）
# 参数顺序与 config.yaml 中 variables.names 列表顺序一一对应
x = [30.0, 25.0, 5.0]  # [Length(mm), Width(mm), Feed_X(mm)]

# 运行仿真（首次启动 HFSS 需要约 10-30 秒）
result = run_hfss_simulation(x, fidelity="coarse")

# 获取结果
print(result.freqs)                    # 频率数组（GHz）
print(result.s11_db)                   # S11 数组（dB）
print(result.s11_min_db)               # S11 最小值（dB）
print(result.resonance_frequency)      # 谐振频率（GHz）
print(result.simulation_time)          # 仿真耗时（秒）
```

---

## 配置文件说明

配置文件 `config.yaml` 分为以下几个部分：

### `hfss` — HFSS 安装配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `version` | 字符串 | HFSS 版本号，2023R1 填 `"2023.1"` |
| `install_dir` | 字符串 | HFSS 安装目录的完整路径 |
| `non_graphical` | 布尔 | `true` 表示无界面模式（推荐），`false` 有界面（调试用） |
| `new_session` | 布尔 | `true` 表示每次启动新进程（推荐，防内存泄漏） |

### `project` — 工程文件配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `template_path` | 字符串 | `.aedt` 模板文件路径（相对或绝对路径） |
| `design_name` | 字符串 | HFSS 模板中的设计名称（区分大小写） |
| `solution_type` | 字符串 | `"Modal"` 或 `"Terminal"` |
| `port_name` | 字符串 | S 参数端口名（如 `"Port1"`，区分大小写） |

### `variables` — 参数化变量

| 字段 | 类型 | 说明 |
|------|------|------|
| `names` | 列表 | 变量名列表，与 `x` 数组下标一一对应，**必须与 HFSS 模型中完全一致** |
| `units` | 列表 | 对应的单位列表（如 `"mm"`） |

> ⚠️ **重要**：变量名的大小写必须与 HFSS Design Properties 中完全一致！

### `frequency` — 频率扫描配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `start` | 浮点数 | 起始频率（GHz） |
| `stop` | 浮点数 | 终止频率（GHz） |
| `num_points` | 整数 | 扫频点总数 |

### `fidelity` — 仿真精度配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `coarse.max_passes` | 整数 | 粗网格最大迭代次数（建议 3-6） |
| `coarse.max_delta_s` | 浮点数 | 粗网格收敛阈值（建议 0.02-0.05） |
| `fine.max_passes` | 整数 | 细网格最大迭代次数（建议 10-20） |
| `fine.max_delta_s` | 浮点数 | 细网格收敛阈值（建议 0.005-0.02） |

### `stability` — 稳定性配置

| 字段 | 类型 | 说明 |
|------|------|------|
| `timeout_seconds` | 整数 | 单次仿真超时时间（秒），超时后强制终止 HFSS |
| `max_retries` | 整数 | 单次失败后的最大重试次数 |
| `retry_delay_seconds` | 整数 | 重试前等待时间（秒） |

---

## API 参考

### `run_hfss_simulation(x, fidelity="coarse", config_path="config.yaml")`

**核心黑盒函数**，封装完整的 HFSS 仿真流程。

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `x` | `list` 或 `numpy.ndarray` | 天线几何尺寸参数数组，顺序与 `config.yaml` 中 `variables.names` 一致 |
| `fidelity` | `str` | 仿真精度：`"coarse"`（粗网格，快）或 `"fine"`（细网格，精确） |
| `config_path` | `str` | 配置文件路径，默认为 `"config.yaml"` |

**返回值：** `SimulationResult`

**异常：**

| 异常 | 触发条件 |
|------|---------|
| `ParameterError` | 参数数量与 `config.yaml` 中变量数量不一致 |
| `RuntimeError` | 仿真在 `max_retries` 次重试后仍然失败 |

---

### `SimulationResult`

仿真结果数据类，包含以下字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `freqs` | `numpy.ndarray` | 频率数组（GHz） |
| `s11_db` | `numpy.ndarray` | S11 幅值数组（dB） |
| `parameters` | `dict` | 本次仿真使用的参数字典，如 `{"Length": 30.0}` |
| `fidelity` | `str` | 本次仿真精度 |
| `simulation_time` | `float` | 仿真总耗时（秒） |
| `gain` | `numpy.ndarray 或 None` | 天线增益（dBi），预留字段 |
| `impedance` | `numpy.ndarray 或 None` | 输入阻抗（复数），预留字段 |
| `radiation_pattern` | `numpy.ndarray 或 None` | 方向图，预留字段 |
| `extra_results` | `dict` | 其他任意扩展结果 |

**计算属性：**

| 属性 | 说明 |
|------|------|
| `s11_min_db` | S11 最小值（dB），即最佳谐振点 |
| `resonance_frequency` | S11 最小值对应的谐振频率（GHz） |

**方法：**

| 方法 | 说明 |
|------|------|
| `to_dict()` | 将结果序列化为字典，numpy 数组转为列表，可直接 JSON 保存 |

---

### `BatchRunner`

批量仿真运行器，支持断点续跑。

```python
from src.batch_runner import BatchRunner

runner = BatchRunner(config_path="config.yaml")
results = runner.run(param_list, fidelity="coarse")
summary = runner.get_summary()
runner.reset_checkpoint()  # 清除断点，从头开始
```

---

## 使用示例

### 单次仿真

```python
from src.simulation import run_hfss_simulation

x = [30.0, 25.0, 5.0]
result = run_hfss_simulation(x, fidelity="coarse")

print(f"S11 最小值: {result.s11_min_db:.2f} dB")
print(f"谐振频率: {result.resonance_frequency:.3f} GHz")
```

### 批量仿真（1000 次，支持断点续跑）

```python
import numpy as np
from src.batch_runner import BatchRunner

# 生成 1000 组参数（可替换为优化算法的输出）
rng = np.random.default_rng(seed=42)
param_list = [
    [rng.uniform(25, 35), rng.uniform(20, 30), rng.uniform(3, 8)]
    for _ in range(1000)
]

runner = BatchRunner(config_path="config.yaml")
results = runner.run(param_list, fidelity="coarse")

# 打印统计
valid = [r for r in results if r is not None]
print(f"成功: {len(valid)}/1000")
print(f"平均谐振频率: {np.mean([r.resonance_frequency for r in valid]):.3f} GHz")
```

### 与优化算法集成

```python
import numpy as np
from scipy.optimize import differential_evolution
from src.simulation import run_hfss_simulation

def objective(x):
    result = run_hfss_simulation(x, fidelity="coarse")
    target_idx = np.argmin(np.abs(result.freqs - 2.45))
    return result.s11_db[target_idx]

bounds = [(25, 35), (20, 30), (3, 8)]
opt = differential_evolution(objective, bounds, maxiter=50, seed=42)
print(f"最优参数: {opt.x}")
```

### 自定义结果提取

在 `src/result_extractor.py` 的 `get_gain()` 方法中实现增益提取，
然后在 `src/simulation.py` 的 `_run_single_simulation()` 中将返回值填入 `SimulationResult.gain`：

```python
# src/result_extractor.py 中实现
def get_gain(self) -> np.ndarray:
    data = self._hfss.post.get_far_field_data(...)
    return np.array(data.data_magnitude())
```

---

## 重要注意事项

### ⚠️ 变量名大小写必须一致

在 HFSS 中，变量名是**区分大小写**的。例如：

- HFSS 中定义的变量叫 `Length`，`config.yaml` 中必须写 `Length`，而不是 `length` 或 `LENGTH`

查看方法：打开 HFSS 模板工程 → 菜单 **HFSS → Design Properties**，查看所有参数化变量名称。

### ⚠️ HFSS License 要求

- 每次仿真都会占用一个 HFSS License，批量仿真期间需要持续占用
- 如 License 不足，仿真将会失败，重试也无济于事
- 建议在 License 充足且非高峰期运行大批量仿真

### ⚠️ 内存和磁盘空间建议

- **内存**：每次 HFSS 仿真约占 2-8 GB 内存，建议系统空闲内存 ≥ 16 GB
- **磁盘**：每次仿真会产生临时文件，确保有 ≥ 50 GB 空闲磁盘空间
- **CPU**：HFSS 会自动使用多线程，建议 ≥ 8 核 CPU

### ⚠️ 端口名称

`config.yaml` 中的 `port_name` 必须与 HFSS 中的激励端口名完全一致（区分大小写）。查看方法：展开设计 → **Excitations** → 查看端口名称。

---

## 项目结构说明

```
hfss-automation/
├── README.md              # 本文档
├── requirements.txt       # 依赖包清单
├── setup.py               # 可选安装脚本
├── config.yaml            # 用户配置文件（需按实际环境修改）
├── config_example.yaml    # 配置文件模板（带详细中文注释）
├── .gitignore             # Git 忽略规则
│
├── src/                   # 核心源码包
│   ├── __init__.py        # 包入口，导出常用符号
│   ├── simulation.py      # 核心黑盒函数 run_hfss_simulation()
│   ├── hfss_driver.py     # HFSS 连接/启动/关闭的封装（基于 pyaedt）
│   ├── parameter_manager.py  # 参数数组与 HFSS 变量名的映射和验证
│   ├── result_extractor.py   # S11 及其他结果的提取（预留扩展接口）
│   ├── models.py          # SimulationResult 数据类定义
│   ├── config_loader.py   # 配置文件加载与字段验证
│   ├── logger.py          # 统一日志配置模块
│   ├── process_manager.py # HFSS 进程管理（超时检测、强制终止）
│   └── batch_runner.py    # 批量运行器（断点续跑、结果持久化）
│
├── scripts/               # 可直接运行的脚本
│   ├── run_single.py      # 单次仿真示例脚本
│   ├── run_batch.py       # 批量仿真脚本（支持命令行参数）
│   └── validate_setup.py  # 环境验证脚本
│
├── tests/                 # 测试套件
│   ├── __init__.py
│   ├── test_config.py     # 配置加载和验证测试
│   ├── test_models.py     # SimulationResult 数据模型测试
│   ├── test_simulation.py # 仿真流程集成测试（Mock 模式）
│   └── test_mock.py       # 全量 Mock 测试（无需 HFSS 环境）
│
├── logs/                  # 运行日志目录（自动创建日志文件）
├── results/               # 仿真结果输出目录（JSON 格式）
└── templates/             # 放置 .aedt 模板工程文件
```

---

## 后续开发指引

### 如何添加新的结果提取类型（增益、阻抗、方向图等）

**第一步**：在 `src/result_extractor.py` 中实现对应的 `get_xxx()` 方法：

```python
def get_gain(self) -> np.ndarray:
    data = self._hfss.post.get_far_field_data(
        setup_sweep_name="AutoSetup : AutoSweep",
        expression="GainTotal",
    )
    return np.array(data.data_magnitude())
```

**第二步**：在 `src/simulation.py` 的 `_run_single_simulation()` 中调用新方法：

```python
gain = extractor.get_gain()
```

**第三步**：`SimulationResult.gain` 字段已预留，无需修改数据类。

---

### 如何支持其他仿真类型（HFSS 3D Layout、Maxwell 等）

`src/hfss_driver.py` 中的 `_launch_hfss()` 方法目前使用 `pyaedt.Hfss`。若需切换到其他求解器：

```python
from pyaedt import Hfss3dLayout  # HFSS 3D Layout
from pyaedt import Maxwell3d     # Maxwell 电磁场仿真
```

建议将 `HFSSDriver` 重构为抽象基类，为每种求解器创建子类。

---

### 如何集成到优化算法中

`run_hfss_simulation()` 已设计为标准的黑盒函数接口，可直接与以下优化库配合使用：

- **SciPy**：`scipy.optimize.differential_evolution`、`minimize`
- **Ax**：贝叶斯优化（适合高成本函数）
- **DEAP**：遗传算法
- **BoTorch/GPyTorch**：高斯过程代理模型

---

### 如何添加新的配置项

1. 在 `config.yaml` 和 `config_example.yaml` 中添加新字段（带中文注释）
2. 在 `src/config_loader.py` 的 `Config` 类中添加对应的 `@property`
3. 如果是必填项，在 `_REQUIRED_FIELDS` 列表中添加点分路径
4. 在 `tests/test_config.py` 中添加测试用例

---

## 常见问题（FAQ）

**Q: 运行时提示 `无法导入 pyaedt`？**
A: 运行 `pip install pyaedt==0.6.73`。在 conda 环境中确保激活了正确的环境。

**Q: 提示 `模板工程文件不存在`？**
A: 将 `.aedt` 文件放入 `templates/` 目录，并确认 `config.yaml` 中 `project.template_path` 与实际文件名一致（区分大小写）。

**Q: 提示 `配置文件缺少必填项`？**
A: 参考 `config_example.yaml` 中的注释，补全 `config.yaml` 中的所有必填字段。

**Q: 变量设置失败，提示找不到变量名？**
A: 检查 `config.yaml` 中 `variables.names` 里的变量名是否与 HFSS Design Properties 中完全一致（大小写、下划线等）。

**Q: 仿真超时了怎么办？**
A: 增大 `config.yaml` 中的 `stability.timeout_seconds`，或减少 `fidelity.coarse.max_passes` 以加快仿真速度。

**Q: 断点续跑时，如何从头重新运行？**
A: 运行 `python scripts/run_batch.py --reset`，或手动删除 `results/batch_checkpoint.json`。

**Q: 如何在没有 HFSS 的机器上运行测试？**
A: 所有测试均使用 Mock，无需安装 HFSS：`python -m pytest tests/ -v`

**Q: 支持 Linux/macOS 吗？**
A: HFSS 本身仅支持 Windows，仿真相关功能仅在 Windows 上可用。纯 Python 部分（配置加载、数据模型等）在任何平台均可运行和测试。

**Q: 如何查看 HFSS 中的设计名称和端口名称？**
A: 打开 `.aedt` 文件后，在 HFSS Project Manager 左侧树形结构中可看到设计名称，展开 Excitations 可看到端口名称。

---

## 更新日志

### v1.0.0（2026-03-10）

- 初始版本发布
- 实现核心 `run_hfss_simulation()` 黑盒函数
- 支持 coarse/fine 双精度模式
- 实现自动重试、超时终止、进程清理机制
- 实现批量运行器（`BatchRunner`）与断点续跑
- 完整的中文文档和配置示例
- 52 个单元测试覆盖核心模块（无需 HFSS 环境即可运行）
- 预留 gain、impedance、radiation_pattern 扩展字段
