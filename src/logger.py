"""
日志模块

提供统一的日志配置和获取接口，支持同时输出到文件和控制台。
"""

import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional


# 全局日志记录器缓存，避免重复配置
_loggers: dict = {}


def setup_logger(
    name: str = "hfss_automation",
    log_dir: str = "logs",
    log_prefix: str = "hfss_simulation",
    level: str = "INFO",
    console_output: bool = True,
) -> logging.Logger:
    """
    配置并返回一个日志记录器

    如果同名的记录器已经配置过，直接返回已有实例（避免重复添加 Handler）。

    Args:
        name: 日志记录器名称
        log_dir: 日志文件保存目录
        log_prefix: 日志文件名前缀
        level: 日志级别字符串，如 "INFO"、"DEBUG"
        console_output: 是否同时在控制台输出

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 如已配置，直接返回
    if name in _loggers:
        return _loggers[name]

    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    # 防止日志向父记录器传播（避免重复输出）
    logger.propagate = False

    # 日志格式
    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 文件 Handler
    Path(log_dir).mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = Path(log_dir) / f"{log_prefix}_{timestamp}.log"
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # 控制台 Handler（可选）
    if console_output:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

    _loggers[name] = logger
    logger.info(f"日志已初始化，日志文件: {log_file}")
    return logger


def get_logger(name: str = "hfss_automation") -> logging.Logger:
    """
    获取已初始化的日志记录器

    如果该名称的记录器尚未通过 setup_logger 初始化，
    则返回一个只输出到控制台的基础记录器。

    Args:
        name: 日志记录器名称

    Returns:
        logging.Logger
    """
    if name in _loggers:
        return _loggers[name]
    # 返回一个基础的后备记录器
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
        )
        logger.addHandler(handler)
    return logger
