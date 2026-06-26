"""
ScreenRecorder - 轻量级桌面录屏软件

功能：
- 一键录屏，手动停止
- 最小化到系统托盘（任务栏右下角）
- 托盘菜单控制录制
- 支持 FFmpeg H.264 / OpenCV MJPG 双编码
- 录制计时器
- 安全密码保护（防止误操作退出）
- 运行日志

参考项目：
- SimpleScreenRecorder (github.com/nmd-113/SimpleScreenRecorder) - UI/托盘设计
- ShareX (github.com/ShareX/ShareX) - 功能参考
- Captura (github.com/MathewSachin/Captura) - 录制引擎参考

技术栈：
- mss: 高速屏幕捕获
- OpenCV: 视频编码 (MJPG fallback)
- FFmpeg: 视频编码 (H.264, 如果可用)
- pystray: 系统托盘
- tkinter: GUI
"""

import os
import sys
import threading
import time
import tkinter as tk
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox, ttk
from pathlib import Path

from PIL import Image, ImageDraw, ImageTk

from config import load_config, save_config, hash_password, verify_password
from logger import setup_logger
from recorder import ScreenRecorder

log = setup_logger()


# ============================================================
# 系统托盘图标
# ============================================================

def create_tray_icon(state: str = "idle") -> Image.Image:
    """创建托盘图标
    state: idle(空闲), recording(录制中), paused(暂停)
    """
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    if state == "idle":
        draw.ellipse([8, 8, 56, 56], fill=(120, 120, 120, 200))
        draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255, 230))
    elif state == "recording":
        draw.ellipse([8, 8, 56, 56], fill=(220, 50, 50, 240))
        draw.ellipse([24, 24, 40, 40], fill=(255, 255, 255, 230))
    elif state == "paused":
        draw.ellipse([8, 8, 56, 56], fill=(240, 160, 40, 240))
        draw.rectangle([23, 20, 29, 44], fill=(255, 255, 255, 230))
        draw.rectangle([35, 20, 41, 44], fill=(255, 255, 255, 230))

    return img


def create_app_icon() -> Image.Image:
    """创建应用图标（用于窗口和 .exe）"""
    img = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 蓝色圆角矩形背景
    draw.rounded_rectangle([8, 8, 248, 248], radius=40, fill=(37, 99, 235, 255))
    # 白色圆形（摄像头镜头）
    draw.ellipse([68, 68, 188, 188], fill=(255, 255, 255, 240))
    # 红色录制点
    draw.ellipse([108, 108, 148, 148], fill=(239, 68, 68, 255))
    return img


# ============================================================
# 密码设置对话框
# ============================================================

class PasswordDialog(tk.Toplevel):
    """密码输入对话框"""

    def __init__(self, parent, title: str, prompt: str, show_confirm: bool = False):
        super().__init__(parent)
        self.title(title)
        self.result = None
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        # 居中显示
        w, h = 340, 200 if not show_confirm else 260
        x = parent.winfo_x() + (parent.winfo_width() - w) // 2
        y = parent.winfo_y() + (parent.winfo_height() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")
        self.configure(bg="#f8f9fa")

        # 提示文字
        tk.Label(
            self, text=prompt, font=("Segoe UI", 10),
            bg="#f8f9fa", fg="#374151", wraplength=300,
        ).pack(pady=(20, 10))

        # 密码输入
        tk.Label(self, text="密码:", font=("Segoe UI", 9), bg="#f8f9fa", fg="#374151").pack(anchor="w", padx=30)
        self._pwd_entry = tk.Entry(self, show="*", font=("Segoe UI", 11), width=28)
        self._pwd_entry.pack(padx=30, pady=2)
        self._pwd_entry.focus_set()

        # 确认密码（仅设置模式）
        self._confirm_entry = None
        if show_confirm:
            tk.Label(self, text="确认密码:", font=("Segoe UI", 9), bg="#f8f9fa", fg="#374151").pack(anchor="w", padx=30)
            self._confirm_entry = tk.Entry(self, show="*", font=("Segoe UI", 11), width=28)
            self._confirm_entry.pack(padx=30, pady=2)

        # 按钮
        btn_frame = tk.Frame(self, bg="#f8f9fa")
        btn_frame.pack(pady=12)
        tk.Button(
            btn_frame, text="确定", font=("Segoe UI", 9, "bold"),
            bg="#2563eb", fg="white", relief="flat", padx=20, pady=4,
            command=self._on_ok,
        ).pack(side="left", padx=6)
        tk.Button(
            btn_frame, text="取消", font=("Segoe UI", 9),
            bg="#e5e7eb", relief="flat", padx=20, pady=4,
            command=self._on_cancel,
        ).pack(side="left", padx=6)

        # Enter 键确认
        self.bind("<Return>", lambda e: self._on_ok())
        self.bind("<Escape>", lambda e: self._on_cancel())

        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _on_ok(self):
        pwd = self._pwd_entry.get()
        if not pwd:
            messagebox.showwarning("提示", "请输入密码", parent=self)
            return
        if self._confirm_entry is not None:
            confirm = self._confirm_entry.get()
            if pwd != confirm:
                messagebox.showwarning("提示", "两次密码不一致", parent=self)
                return
        self.result = pwd
        self.destroy()

    def _on_cancel(self):
        self.result = None
        self.destroy()


# ============================================================
# 主窗口
# ============================================================

class ScreenRecorderApp:
    """主应用程序"""

    def __init__(self):
        log.info("=" * 50)
        log.info("ScreenRecorder 启动")
        log.info(f"Python: {sys.version}")
        log.info(f"工作目录: {os.getcwd()}")

        self.config = load_config()
        self.recorder = ScreenRecorder(
            fps=self.config.get("fps", 15),
            codec=self.config.get("codec", "auto"),
            show_cursor=self.config.get("show_cursor", True),
        )

        self._build_window()
        self._build_ui()
        self._build_tray()
        self._check_password_setup()
        self._update_timer()

        log.info("应用初始化完成")

    def _build_window(self):
        """创建主窗口"""
        self.root = tk.Tk()
        self.root.title("ScreenRecorder")
        self.root.geometry("400x380")
        self.root.resizable(False, False)
        self.root.configure(bg="#f8f9fa")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 恢复窗口位置
        x = self.config.get("window_x")
        y = self.config.get("window_y")
        if x is not None and y is not None:
            self.root.geometry(f"+{x}+{y}")

        # 窗口图标
        try:
            icon_img = create_app_icon()
            icon_path = str(Path(__file__).parent / "app_icon.ico")
            icon_img.save(icon_path, format="ICO", sizes=[(256, 256), (64, 64), (32, 32), (16, 16)])
            self.root.iconbitmap(icon_path)
            self._app_icon_path = icon_path
        except Exception as e:
            log.warning(f"设置窗口图标失败: {e}")
            self._app_icon_path = None

    def _build_ui(self):
        """构建界面"""
        style = ttk.Style()
        style.theme_use("clam")

        # === 标题栏 ===
        header = tk.Frame(self.root, bg="#2563eb", height=48)
        header.pack(fill="x")
        header.pack_propagate(False)

        title_inner = tk.Frame(header, bg="#2563eb")
        title_inner.pack(fill="both", expand=True, padx=12)

        tk.Label(
            title_inner, text="  ScreenRecorder",
            font=("Segoe UI", 14, "bold"), fg="white", bg="#2563eb", anchor="w",
        ).pack(side="left")

        # 最小化按钮（标题栏右上角）
        tk.Button(
            title_inner, text="—", font=("Segoe UI", 12),
            fg="white", bg="#2563eb", activebackground="#1d4ed8",
            activeforeground="white", relief="flat", width=3,
            cursor="hand2", command=self._minimize_to_tray,
        ).pack(side="right", padx=(4, 0))

        # === 状态区域 ===
        status_frame = tk.Frame(self.root, bg="#f8f9fa", pady=10)
        status_frame.pack(fill="x", padx=16)

        status_inner = tk.Frame(status_frame, bg="#f8f9fa")
        status_inner.pack()

        self._status_dot = tk.Canvas(
            status_inner, width=16, height=16, bg="#f8f9fa", highlightthickness=0,
        )
        self._status_dot.pack(side="left", padx=(0, 8))
        self._dot_id = self._status_dot.create_oval(2, 2, 14, 14, fill="#9ca3af", outline="")

        self._status_label = tk.Label(
            status_inner, text="就绪", font=("Segoe UI", 12), fg="#374151", bg="#f8f9fa",
        )
        self._status_label.pack(side="left")

        # 密码状态指示
        self._lock_label = tk.Label(
            status_inner, text="", font=("Segoe UI", 9), fg="#9ca3af", bg="#f8f9fa",
        )
        self._lock_label.pack(side="right")

        self._duration_label = tk.Label(
            status_frame, text="00:00:00",
            font=("Consolas", 22, "bold"), fg="#1f2937", bg="#f8f9fa",
        )
        self._duration_label.pack(pady=(4, 0))

        ttk.Separator(self.root, orient="horizontal").pack(fill="x", padx=16, pady=4)

        # === 控制按钮 ===
        btn_frame = tk.Frame(self.root, bg="#f8f9fa")
        btn_frame.pack(fill="x", padx=16, pady=6)

        self._btn_start = tk.Button(
            btn_frame, text="  开始录制", font=("Segoe UI", 10, "bold"),
            bg="#22c55e", fg="white", activebackground="#16a34a",
            activeforeground="white", relief="flat", cursor="hand2",
            padx=16, pady=8, command=self._on_start,
        )
        self._btn_start.pack(side="left", expand=True, fill="x", padx=(0, 4))

        self._btn_stop = tk.Button(
            btn_frame, text="  停止", font=("Segoe UI", 10, "bold"),
            bg="#ef4444", fg="white", activeforeground="white",
            activebackground="#dc2626", relief="flat", cursor="hand2",
            padx=16, pady=8, state="disabled", command=self._on_stop,
        )
        self._btn_stop.pack(side="left", expand=True, fill="x", padx=4)

        self._btn_pause = tk.Button(
            btn_frame, text="  暂停", font=("Segoe UI", 10),
            bg="#f59e0b", fg="white", activeforeground="white",
            activebackground="#d97706", relief="flat", cursor="hand2",
            padx=16, pady=8, state="disabled", command=self._on_pause,
        )
        self._btn_pause.pack(side="left", expand=True, fill="x", padx=(4, 0))

        # === 保存路径 ===
        path_frame = tk.LabelFrame(
            self.root, text=" 保存位置 ", font=("Segoe UI", 9),
            bg="#f8f9fa", fg="#374151", padx=8, pady=4,
        )
        path_frame.pack(fill="x", padx=16, pady=4)

        path_inner = tk.Frame(path_frame, bg="#f8f9fa")
        path_inner.pack(fill="x")

        self._path_var = tk.StringVar(value=self.config["recordings_path"])
        self._path_entry = tk.Entry(
            path_inner, textvariable=self._path_var,
            font=("Segoe UI", 9), state="readonly", relief="solid",
        )
        self._path_entry.pack(side="left", fill="x", expand=True, padx=(0, 6))

        tk.Button(
            path_inner, text="浏览...", font=("Segoe UI", 9),
            bg="#e5e7eb", relief="flat", cursor="hand2",
            command=self._browse_path,
        ).pack(side="right")

        # === 设置 ===
        settings_frame = tk.LabelFrame(
            self.root, text=" 设置 ", font=("Segoe UI", 9),
            bg="#f8f9fa", fg="#374151", padx=8, pady=4,
        )
        settings_frame.pack(fill="x", padx=16, pady=4)

        settings_inner = tk.Frame(settings_frame, bg="#f8f9fa")
        settings_inner.pack(fill="x")

        tk.Label(settings_inner, text="帧率:", font=("Segoe UI", 9), bg="#f8f9fa").pack(side="left")
        self._fps_var = tk.StringVar(value=str(self.config["fps"]))
        fps_combo = ttk.Combobox(
            settings_inner, textvariable=self._fps_var,
            values=["10", "15", "20", "24", "30"], width=4, state="readonly",
        )
        fps_combo.pack(side="left", padx=(4, 16))
        fps_combo.bind("<<ComboboxSelected>>", self._on_settings_change)

        tk.Label(settings_inner, text="编码:", font=("Segoe UI", 9), bg="#f8f9fa").pack(side="left")
        self._codec_var = tk.StringVar(value=self.config.get("codec", "auto"))
        codec_combo = ttk.Combobox(
            settings_inner, textvariable=self._codec_var,
            values=["auto", "h264", "mjpg"], width=6, state="readonly",
        )
        codec_combo.pack(side="left", padx=(4, 0))
        codec_combo.bind("<<ComboboxSelected>>", self._on_settings_change)

        ff_status = "FFmpeg: 已安装" if self.recorder._ffmpeg_available else "FFmpeg: 未安装 (MJPG)"
        ff_color = "#16a34a" if self.recorder._ffmpeg_available else "#f59e0b"
        tk.Label(
            settings_inner, text=ff_status, font=("Segoe UI", 8),
            fg=ff_color, bg="#f8f9fa",
        ).pack(side="right")

        # === 状态栏 ===
        self._bottom_bar = tk.Label(
            self.root, text="就绪 - 点击「开始录制」开始",
            font=("Segoe UI", 8), fg="#6b7280", bg="#f1f5f9", anchor="w", padx=8, pady=3,
        )
        self._bottom_bar.pack(side="bottom", fill="x")

        # 更新密码状态显示
        self._update_lock_indicator()

    def _build_tray(self):
        """构建系统托盘"""
        try:
            import pystray

            menu = pystray.Menu(
                pystray.MenuItem("显示主窗口", self._tray_show, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("开始录制", self._tray_start),
                pystray.MenuItem("停止录制", self._tray_stop),
                pystray.MenuItem("暂停/恢复", self._tray_pause),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("打开录制文件夹", self._tray_open_folder),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("退出", self._tray_exit),
            )

            self._tray_icon = pystray.Icon(
                "ScreenRecorder",
                create_tray_icon("idle"),
                "ScreenRecorder - 就绪",
                menu,
            )
            self._tray_thread = threading.Thread(target=self._tray_icon.run, daemon=True)
            self._tray_thread.start()
            log.info("系统托盘已启动")
        except ImportError:
            log.warning("pystray 未安装，系统托盘不可用")
            self._tray_icon = None

    # ----------------------------------------------------------
    # 密码管理
    # ----------------------------------------------------------

    def _check_password_setup(self):
        """检查是否需要设置密码（首次运行时提示）"""
        if not self.config.get("exit_password_hash"):
            self.root.after(500, self._prompt_password_setup)

    def _prompt_password_setup(self):
        """提示用户设置安全密码"""
        result = messagebox.askyesno(
            "安全设置",
            "首次运行，建议设置安全密码。\n\n"
            "设置密码后，退出程序需要输入密码，\n"
            "防止录制过程中误操作退出。\n\n"
            "是否现在设置？",
            parent=self.root,
        )
        if result:
            self._show_set_password_dialog()

    def _show_set_password_dialog(self):
        """显示设置密码对话框"""
        dialog = PasswordDialog(
            self.root,
            title="设置安全密码",
            prompt="请设置安全密码（防止误操作退出）：",
            show_confirm=True,
        )
        self.root.wait_window(dialog)
        if dialog.result:
            pwd_hash = hash_password(dialog.result)
            self.config["exit_password_hash"] = pwd_hash
            save_config(self.config)
            self._update_lock_indicator()
            log.info("安全密码已设置")
            messagebox.showinfo("成功", "安全密码已设置！\n退出程序时需要输入密码。", parent=self.root)

    def _update_lock_indicator(self):
        """更新密码状态指示器"""
        has_pwd = bool(self.config.get("exit_password_hash"))
        if has_pwd:
            self._lock_label.config(text="[已锁定]", fg="#ef4444")
        else:
            self._lock_label.config(text="[未设密码]", fg="#9ca3af")

    def _verify_exit_password(self) -> bool:
        """验证退出密码，返回是否允许退出"""
        pwd_hash = self.config.get("exit_password_hash", "")
        if not pwd_hash:
            return True  # 未设置密码，允许退出

        # 如果正在录制，额外警告
        warning = ""
        if self.recorder.is_recording:
            warning = "\n\n⚠️ 当前正在录制中！退出将自动停止录制。"

        dialog = PasswordDialog(
            self.root,
            title="验证密码",
            prompt=f"请输入安全密码以退出程序{warning}",
            show_confirm=False,
        )
        self.root.wait_window(dialog)
        if dialog.result is None:
            return False  # 用户取消

        if verify_password(dialog.result, pwd_hash):
            log.info("密码验证通过")
            return True
        else:
            log.warning("密码验证失败")
            messagebox.showerror("错误", "密码不正确！", parent=self.root)
            return False

    # ----------------------------------------------------------
    # 按钮事件
    # ----------------------------------------------------------

    def _on_start(self):
        """点击开始录制"""
        if self.recorder.is_recording:
            return

        output_dir = self._path_var.get()
        if not output_dir:
            messagebox.showwarning("提示", "请先选择保存位置")
            return

        # 更新录制器配置
        self.recorder.fps = int(self._fps_var.get())
        self.recorder.codec = self._codec_var.get()

        if self.recorder.start(output_dir):
            self._set_recording_ui(True)
            self._update_tray_icon("recording")
            self._bottom_bar.config(text=f"录制中 -> {self.recorder.output_file}")
            log.info(f"用户点击开始录制")
        else:
            messagebox.showerror("错误", "无法开始录制，请检查保存路径和编码器设置")
            log.error("用户尝试开始录制失败")

    def _on_stop(self):
        """点击停止录制"""
        if not self.recorder.is_recording:
            return

        log.info("用户点击停止录制")
        output = self.recorder.stop()
        self._set_recording_ui(False)
        self._update_tray_icon("idle")

        if output and os.path.exists(output):
            size_mb = os.path.getsize(output) / (1024 * 1024)
            self._bottom_bar.config(text=f"已保存: {os.path.basename(output)} ({size_mb:.1f} MB)")
            messagebox.showinfo(
                "录制完成",
                f"视频已保存到:\n{output}\n\n大小: {size_mb:.1f} MB",
            )
        else:
            self._bottom_bar.config(text="录制已停止")

    def _on_pause(self):
        """点击暂停/恢复"""
        if not self.recorder.is_recording:
            return
        is_paused = self.recorder.toggle_pause()
        if is_paused:
            self._btn_pause.config(text="  恢复", bg="#3b82f6", activebackground="#2563eb")
            self._status_label.config(text="已暂停")
            self._status_dot.itemconfig(self._dot_id, fill="#f59e0b")
            self._update_tray_icon("paused")
        else:
            self._btn_pause.config(text="  暂停", bg="#f59e0b", activebackground="#d97706")
            self._status_label.config(text="录制中")
            self._status_dot.itemconfig(self._dot_id, fill="#ef4444")
            self._update_tray_icon("recording")

    def _browse_path(self):
        """选择保存路径"""
        path = filedialog.askdirectory(
            title="选择录制文件保存位置",
            initialdir=self._path_var.get(),
        )
        if path:
            self._path_var.set(path)
            self.config["recordings_path"] = path
            save_config(self.config)
            log.info(f"保存路径变更为: {path}")

    def _on_settings_change(self, event=None):
        """设置变更"""
        self.config["fps"] = int(self._fps_var.get())
        self.config["codec"] = self._codec_var.get()
        save_config(self.config)
        log.info(f"设置变更: FPS={self.config['fps']} 编码={self.config['codec']}")

    # ----------------------------------------------------------
    # 最小化到托盘
    # ----------------------------------------------------------

    def _minimize_to_tray(self):
        """最小化到系统托盘"""
        log.info("最小化到系统托盘")
        self._save_window_position()
        self.root.withdraw()

    # ----------------------------------------------------------
    # 系统托盘回调
    # ----------------------------------------------------------

    def _tray_show(self, icon=None, item=None):
        """从托盘恢复窗口"""
        log.debug("从托盘恢复窗口")
        self.root.after(0, self._restore_window)

    def _tray_start(self, icon=None, item=None):
        """托盘开始录制"""
        self.root.after(0, self._on_start)

    def _tray_stop(self, icon=None, item=None):
        """托盘停止录制"""
        self.root.after(0, self._on_stop)

    def _tray_pause(self, icon=None, item=None):
        """托盘暂停/恢复"""
        self.root.after(0, self._on_pause)

    def _tray_open_folder(self, icon=None, item=None):
        """打开录制文件夹"""
        path = self._path_var.get()
        if os.path.exists(path):
            webbrowser.open(path)
            log.debug(f"打开录制文件夹: {path}")

    def _tray_exit(self, icon=None, item=None):
        """从托盘退出（需要密码验证）"""
        log.info("用户从托盘请求退出")
        # 先弹出密码验证（需要在主线程中处理）
        self.root.after(0, self._exit_with_password)

    # ----------------------------------------------------------
    # 辅助方法
    # ----------------------------------------------------------

    def _set_recording_ui(self, recording: bool):
        """更新按钮状态"""
        if recording:
            self._btn_start.config(state="disabled", bg="#9ca3af")
            self._btn_stop.config(state="normal")
            self._btn_pause.config(state="normal")
            self._status_label.config(text="录制中")
            self._status_dot.itemconfig(self._dot_id, fill="#ef4444")
        else:
            self._btn_start.config(state="normal", bg="#22c55e")
            self._btn_stop.config(state="disabled")
            self._btn_pause.config(state="disabled", text="  暂停", bg="#f59e0b")
            self._status_label.config(text="就绪")
            self._status_dot.itemconfig(self._dot_id, fill="#9ca3af")
            self._duration_label.config(text="00:00:00")

    def _update_tray_icon(self, state: str):
        """更新托盘图标"""
        if self._tray_icon:
            try:
                self._tray_icon.icon = create_tray_icon(state)
                labels = {"idle": "就绪", "recording": "录制中", "paused": "已暂停"}
                self._tray_icon.title = f"ScreenRecorder - {labels.get(state, '')}"
            except Exception:
                pass

    def _update_timer(self):
        """定时更新录制时间显示"""
        if self.recorder.is_recording:
            dur = self.recorder.duration
            h = int(dur // 3600)
            m = int((dur % 3600) // 60)
            s = int(dur % 60)
            self._duration_label.config(text=f"{h:02d}:{m:02d}:{s:02d}")
        self.root.after(500, self._update_timer)

    def _restore_window(self):
        """恢复主窗口"""
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def _save_window_position(self):
        """保存窗口位置"""
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        self.config["window_x"] = x
        self.config["window_y"] = y
        save_config(self.config)

    def _on_close(self):
        """点击关闭按钮 -> 最小化到托盘（不退出）"""
        log.debug("点击关闭按钮，最小化到托盘")
        self._save_window_position()
        self.root.withdraw()

    def _exit_with_password(self):
        """密码验证后退出"""
        if self._verify_exit_password():
            self._exit_app()
        else:
            log.info("用户取消退出（密码验证失败或取消）")

    def _exit_app(self):
        """彻底退出程序"""
        log.info("程序退出")
        if self.recorder.is_recording:
            log.info("退出前停止录制")
            self.recorder.stop()
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
        self._save_window_position()
        self.root.destroy()

    def run(self):
        """启动应用"""
        print("[App] ScreenRecorder 已启动")
        print(f"[App] 录制文件保存到: {self.config['recordings_path']}")
        self.root.mainloop()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    app = ScreenRecorderApp()
    app.run()
