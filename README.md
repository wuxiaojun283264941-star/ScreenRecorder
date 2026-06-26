# ScreenRecorder - 轻量级桌面录屏软件

一款简洁易用的桌面录屏工具，支持一键录制、系统托盘最小化、安全密码保护。

## 功能特性

- **一键录制** — 点击「开始录制」即录，手动点「停止」才停
- **暂停/恢复** — 录制过程中可暂停，恢复后继续
- **最小化到托盘** — 关闭窗口 = 最小化到任务栏右下角，不退出
- **托盘菜单控制** — 右键托盘图标可开始/停止/暂停录制
- **安全密码保护** — 设置密码防止误操作退出，退出需输入密码
- **双编码模式** — FFmpeg H.264（文件小）/ MJPG（兼容性好）
- **帧率可调** — 10/15/20/24/30 FPS
- **实时计时** — 录制时显示 HH:MM:SS
- **运行日志** — 自动记录操作日志，便于排查问题

## 快速开始

### 方式一：直接运行 Python 脚本

```bash
# 安装依赖
pip install -r requirements.txt

# 运行
python main.py
```

### 方式二：打包为 .exe

```bash
# 构建 .exe（需要 PyInstaller）
build.bat

# 安装（创建桌面快捷方式）
setup.bat
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `main.py` | 主程序（UI + 系统托盘） |
| `recorder.py` | 录屏引擎（mss + OpenCV/FFmpeg） |
| `config.py` | 配置管理 |
| `logger.py` | 日志模块 |
| `generate_icon.py` | 图标生成工具 |
| `requirements.txt` | Python 依赖 |
| `install.bat` | 安装依赖脚本 |
| `run.bat` | 快速运行脚本 |
| `build.bat` | 构建 .exe 脚本 |
| `setup.bat` | 安装向导（创建桌面快捷方式） |
| `create_shortcut.vbs` | 手动创建桌面快捷方式 |

## 技术栈

- **mss** — 高速屏幕捕获（比 pyautogui 快 5-10 倍）
- **OpenCV** — 视频编码（MJPG）
- **FFmpeg** — 视频编码（H.264，可选）
- **pystray** — 系统托盘
- **tkinter** — GUI 界面
- **Pillow** — 图像处理

## 参考项目

- [SimpleScreenRecorder](https://github.com/nmd-113/SimpleScreenRecorder) — UI 设计参考
- [ShareX](https://github.com/ShareX/ShareX) (38k stars) — 功能参考
- [Captura](https://github.com/MathewSachin/Captura) (10k stars) — 录制引擎参考
- [ffscreencast](https://github.com/cytopia/ffscreencast) (1.8k stars) — FFmpeg 录屏方案

## 配置文件

配置自动保存在 `settings.json`：

```json
{
  "fps": 15,
  "codec": "auto",
  "recordings_path": "C:\\Users\\xxx\\Videos\\ScreenRecordings",
  "exit_password_hash": "",
  "minimize_on_close": true
}
```

## 许可证

MIT License
