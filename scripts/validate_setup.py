"""
环境验证脚本

检查运行 HFSS 自动化所需的各项依赖是否正确安装，
包括 Python 版本、pyaedt、HFSS 安装路径、配置文件等。

使用方法：
    python scripts/validate_setup.py
"""

import sys
from pathlib import Path

# 将项目根目录加入 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


def check_python_version():
    """检查 Python 版本（要求 >= 3.8）"""
    ver = sys.version_info
    ok = ver >= (3, 8)
    status = "✓" if ok else "✗"
    print(f"  {status} Python 版本: {sys.version.split()[0]}", end="")
    if not ok:
        print(f"  [警告] 要求 Python >= 3.8")
    else:
        print()
    return ok


def check_pyaedt():
    """检查 pyaedt 是否已安装"""
    try:
        import pyaedt
        print(f"  ✓ pyaedt 已安装，版本: {pyaedt.__version__}")
        return True
    except ImportError:
        print("  ✗ pyaedt 未安装，请运行: pip install pyaedt")
        return False


def check_numpy():
    """检查 numpy 是否已安装"""
    try:
        import numpy as np
        print(f"  ✓ numpy 已安装，版本: {np.__version__}")
        return True
    except ImportError:
        print("  ✗ numpy 未安装，请运行: pip install numpy")
        return False


def check_yaml():
    """检查 PyYAML 是否已安装"""
    try:
        import yaml
        print(f"  ✓ PyYAML 已安装，版本: {yaml.__version__}")
        return True
    except ImportError:
        print("  ✗ PyYAML 未安装，请运行: pip install PyYAML")
        return False


def check_psutil():
    """检查 psutil 是否已安装"""
    try:
        import psutil
        print(f"  ✓ psutil 已安装，版本: {psutil.__version__}")
        return True
    except ImportError:
        print("  ✗ psutil 未安装，请运行: pip install psutil")
        return False


def check_config():
    """检查配置文件是否存在且格式正确"""
    config_path = Path("config.yaml")
    if not config_path.exists():
        print(f"  ✗ 配置文件不存在: {config_path.resolve()}")
        print("    请参考 config_example.yaml 创建 config.yaml")
        return False
    try:
        from src.config_loader import load_config
        cfg = load_config("config.yaml")
        print(f"  ✓ 配置文件格式正确")
        print(f"    HFSS 版本: {cfg.hfss_version}")
        print(f"    安装目录: {cfg.hfss_install_dir}")
        print(f"    模板文件: {cfg.template_path}")
        print(f"    变量名称: {cfg.variable_names}")
        return True
    except Exception as e:
        print(f"  ✗ 配置文件存在问题: {e}")
        return False


def check_template(config):
    """检查模板工程文件是否存在"""
    try:
        from src.config_loader import load_config
        cfg = load_config("config.yaml")
        template = Path(cfg.template_path)
        if template.exists():
            print(f"  ✓ 模板工程文件存在: {template}")
            return True
        else:
            print(f"  ✗ 模板工程文件不存在: {template}")
            print(f"    请将 .aedt 文件放入 templates/ 目录")
            return False
    except Exception:
        return False


def check_hfss_install(config=None):
    """检查 HFSS 安装目录是否存在"""
    try:
        from src.config_loader import load_config
        cfg = load_config("config.yaml")
        install_dir = Path(cfg.hfss_install_dir)
        if install_dir.exists():
            print(f"  ✓ HFSS 安装目录存在: {install_dir}")
            return True
        else:
            print(f"  ✗ HFSS 安装目录不存在: {install_dir}")
            print(f"    请检查 config.yaml 中的 hfss.install_dir 配置")
            return False
    except Exception:
        return False


def check_output_dirs():
    """检查输出目录是否可写"""
    all_ok = True
    for dir_name in ("logs", "results", "templates"):
        d = Path(dir_name)
        d.mkdir(exist_ok=True)
        # 尝试写入测试文件
        test_file = d / ".write_test"
        try:
            test_file.write_text("test")
            test_file.unlink()
            print(f"  ✓ 目录可写: {d.resolve()}")
        except Exception as e:
            print(f"  ✗ 目录不可写: {d.resolve()} ({e})")
            all_ok = False
    return all_ok


def main():
    print()
    print("=" * 60)
    print("HFSS 自动化环境验证")
    print("=" * 60)

    checks = []

    print()
    print("【Python 环境】")
    checks.append(check_python_version())

    print()
    print("【依赖库】")
    checks.append(check_numpy())
    checks.append(check_yaml())
    checks.append(check_psutil())
    pyaedt_ok = check_pyaedt()
    checks.append(pyaedt_ok)

    print()
    print("【配置文件】")
    config_ok = check_config()
    checks.append(config_ok)

    if config_ok:
        print()
        print("【HFSS 安装】")
        checks.append(check_hfss_install())

        print()
        print("【模板工程文件】")
        checks.append(check_template(None))

    print()
    print("【输出目录】")
    checks.append(check_output_dirs())

    print()
    print("=" * 60)
    if all(checks):
        print("✓ 所有检查通过，环境配置正确！")
    else:
        failed = checks.count(False)
        print(f"✗ {failed} 项检查未通过，请根据上方提示修复问题。")
    print("=" * 60)
    print()


if __name__ == "__main__":
    main()
