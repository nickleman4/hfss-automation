"""
HFSS 自动化仿真接口项目安装脚本
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = [
        line.strip()
        for line in fh
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="hfss-automation",
    version="1.0.0",
    author="HFSS Automation Contributors",
    description="HFSS 自动化仿真调用接口，封装 pyaedt 实现批量无人值守仿真",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    python_requires=">=3.8",
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: Microsoft :: Windows",
        "Topic :: Scientific/Engineering :: Electronic Design Automation (EDA)",
    ],
)
