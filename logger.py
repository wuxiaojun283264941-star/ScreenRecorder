"""
日志模块

记录所有操作到文件，便于排查问题。
日志文件位于: ~/Videos/ScreenRecordings/logs/
"""

import logging
import os
import sys
from datetime import datetime
from pathlib import Path


def setup_logger(name: str = "ScreenRecorder") -> logging.Logger:
    """配置并返回日志记录器"""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)

    # 日志目录
    log_dir = os.path.join(
        os.environ.get("USERPROFILE", os.path.expanduser("~")),
        "Videos", "ScreenRecordings", "logs",
    )
    os.makedirs(log_dir, exist_ok=True)

    # 日志文件名（按日期）
    today = datetime.now().strftime("%Y-%m-%d")
    log_file = os.path.join(log_dir, f"recorder_{today}.log")

    # 文件处理器 - 详细日志
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-7s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_fmt)

    # 控制台处理器 - 简洁输出
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_fmt = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info(f"日志初始化完成 -> {log_file}")
    return logger
