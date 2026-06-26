"""
配置管理模块

管理所有应用设置，包括录制参数、窗口位置、安全密码等。
配置文件: settings.json（与程序同目录）
"""

import hashlib
import json
import os
from pathlib import Path

DEFAULT_CONFIG = {
    "fps": 15,
    "codec": "auto",
    "recordings_path": str(Path.home() / "Videos" / "ScreenRecordings"),
    "show_cursor": True,
    "window_x": None,
    "window_y": None,
    "exit_password_hash": "",  # 退出密码的 SHA256 哈希值，空字符串表示未设置
    "minimize_on_close": True,  # 关闭窗口时最小化到托盘
}

CONFIG_FILE = Path(__file__).parent / "settings.json"


def load_config() -> dict:
    """加载配置，不存在则创建默认配置"""
    config = DEFAULT_CONFIG.copy()
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
            config.update(saved)
        except (json.JSONDecodeError, IOError):
            pass
    # 确保录制目录存在
    os.makedirs(config["recordings_path"], exist_ok=True)
    return config


def save_config(config: dict):
    """保存配置到文件"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[Config] 保存配置失败: {e}")


def hash_password(password: str) -> str:
    """将密码转换为 SHA256 哈希值"""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """验证密码是否匹配"""
    if not password_hash:
        return True  # 未设置密码，直接通过
    return hash_password(password) == password_hash
