"""
录屏引擎模块

使用 mss 进行高速屏幕捕获，支持两种编码模式：
1. FFmpeg H.264（如果系统有 ffmpeg）—— 文件小、质量好
2. OpenCV MJPG（fallback）—— 兼容性最好、无需额外依赖

参考项目：
- ffscreencast (github.com/cytopia/ffscreencast) - ffmpeg 录屏方案
- SimpleScreenRecorder (github.com/nmd-113/SimpleScreenRecorder) - 架构参考
"""

import os
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

import cv2
import mss
import numpy as np

from logger import setup_logger

log = setup_logger()


class ScreenRecorder:
    """屏幕录制引擎"""

    def __init__(self, fps: int = 15, codec: str = "auto", show_cursor: bool = True):
        self.fps = fps
        self.codec = codec
        self.show_cursor = show_cursor

        self._recording = False
        self._paused = False
        self._thread = None
        self._lock = threading.Lock()

        self._output_file = None
        self._start_time = 0
        self._paused_duration = 0
        self._pause_start = 0
        self._writer = None
        self._ffmpeg_proc = None
        self._use_ffmpeg = False
        self._frame_size = None
        self._frame_count = 0

        # 检测 ffmpeg 可用性
        self._ffmpeg_available = self._check_ffmpeg()
        log.info(f"录屏引擎初始化 | FPS={fps} 编码={codec} FFmpeg={'可用' if self._ffmpeg_available else '不可用'}")

    @property
    def is_recording(self) -> bool:
        return self._recording

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def output_file(self) -> str:
        return self._output_file or ""

    @property
    def duration(self) -> float:
        if not self._recording:
            return 0
        elapsed = time.time() - self._start_time - self._paused_duration
        if self._paused:
            elapsed -= (time.time() - self._pause_start)
        return max(0, elapsed)

    def start(self, output_dir: str) -> bool:
        """开始录制"""
        with self._lock:
            if self._recording:
                log.warning("尝试开始录制，但已在录制中")
                return False

            # 生成输出文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            ext = ".mp4"
            self._output_file = os.path.join(output_dir, f"录屏_{timestamp}{ext}")
            os.makedirs(output_dir, exist_ok=True)

            # 获取屏幕尺寸
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                self._frame_size = (monitor["width"], monitor["height"])

            # 尝试使用 ffmpeg
            if self._ffmpeg_available and self.codec != "mjpg":
                if self._try_ffmpeg_start():
                    self._use_ffmpeg = True
                else:
                    if not self._try_opencv_start():
                        log.error("所有编码器启动失败")
                        return False
                    self._use_ffmpeg = False
            else:
                if not self._try_opencv_start():
                    log.error("OpenCV 编码器启动失败")
                    return False
                self._use_ffmpeg = False

            self._recording = True
            self._paused = False
            self._start_time = time.time()
            self._paused_duration = 0
            self._frame_count = 0

            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()

            mode = "FFmpeg H.264" if self._use_ffmpeg else "OpenCV MJPG"
            log.info(f"开始录制 ({mode}) | 分辨率={self._frame_size[0]}x{self._frame_size[1]} -> {self._output_file}")
            return True

    def stop(self) -> str:
        """停止录制，返回输出文件路径"""
        with self._lock:
            if not self._recording:
                log.warning("尝试停止录制，但未在录制中")
                return ""
            self._recording = False
            self._paused = False

        if self._thread:
            self._thread.join(timeout=5)

        # 清理编码器
        if self._use_ffmpeg and self._ffmpeg_proc:
            try:
                self._ffmpeg_proc.stdin.close()
                self._ffmpeg_proc.wait(timeout=5)
            except Exception:
                self._ffmpeg_proc.kill()
            self._ffmpeg_proc = None
        elif self._writer:
            self._writer.release()
            self._writer = None

        output = self._output_file
        if output and os.path.exists(output):
            size_mb = os.path.getsize(output) / (1024 * 1024)
            log.info(f"录制完成 | 时长={self.duration:.1f}s 帧数={self._frame_count} 大小={size_mb:.1f}MB -> {output}")
        else:
            log.warning(f"录制文件不存在: {output}")
        return output or ""

    def toggle_pause(self) -> bool:
        """切换暂停状态，返回是否已暂停"""
        if not self._recording:
            return False
        if self._paused:
            self._paused_duration += time.time() - self._pause_start
            self._paused = False
            log.info("恢复录制")
        else:
            self._pause_start = time.time()
            self._paused = True
            log.info("暂停录制")
        return self._paused

    def _record_loop(self):
        """录制主循环（在独立线程中运行）"""
        frame_interval = 1.0 / self.fps
        log.debug("录制线程启动")
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                while self._recording:
                    if self._paused:
                        time.sleep(0.1)
                        continue

                    loop_start = time.time()

                    # 捕获屏幕
                    sct_img = sct.grab(monitor)
                    frame = np.array(sct_img)
                    frame_bgr = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)

                    # 写入帧
                    try:
                        if self._use_ffmpeg and self._ffmpeg_proc:
                            self._ffmpeg_proc.stdin.write(frame_bgr.tobytes())
                        elif self._writer:
                            self._writer.write(frame_bgr)
                        self._frame_count += 1
                    except Exception as e:
                        log.error(f"写入帧失败: {e}")
                        break

                    # 保持帧率稳定
                    elapsed = time.time() - loop_start
                    sleep_time = frame_interval - elapsed
                    if sleep_time > 0:
                        time.sleep(sleep_time)
        except Exception as e:
            log.error(f"录制线程异常: {e}", exc_info=True)
        log.debug("录制线程结束")

    def _try_ffmpeg_start(self) -> bool:
        """尝试使用 ffmpeg 开始录制"""
        w, h = self._frame_size
        cmd = [
            "ffmpeg", "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "bgr24",
            "-r", str(self.fps),
            "-i", "-",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-crf", "23",
            "-pix_fmt", "yuv420p",
            self._output_file,
        ]
        try:
            log.debug(f"启动 FFmpeg: {' '.join(cmd)}")
            self._ffmpeg_proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            # 测试写入
            blank = np.zeros((h, w, 3), dtype=np.uint8)
            self._ffmpeg_proc.stdin.write(blank.tobytes())
            log.info("FFmpeg H.264 编码器启动成功")
            return True
        except Exception as e:
            log.error(f"FFmpeg 启动失败: {e}")
            self._ffmpeg_proc = None
            return False

    def _try_opencv_start(self) -> bool:
        """使用 OpenCV MJPG 编码开始录制"""
        w, h = self._frame_size
        # 使用 MJPG 编码器，兼容性最好
        fourcc = cv2.VideoWriter_fourcc(*"MJPG")
        output_avi = self._output_file.replace(".mp4", ".avi")
        self._writer = cv2.VideoWriter(output_avi, fourcc, self.fps, (w, h))
        if not self._writer.isOpened():
            log.error("OpenCV VideoWriter 打开失败")
            self._writer = None
            return False
        # 更新输出文件扩展名
        self._output_file = output_avi
        log.info("OpenCV MJPG 编码器启动成功")
        return True

    def _check_ffmpeg(self) -> bool:
        """检测系统是否安装了 ffmpeg"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=3,
            )
            available = result.returncode == 0
            log.debug(f"FFmpeg 检测: {'可用' if available else '不可用'}")
            return available
        except (FileNotFoundError, subprocess.TimeoutExpired):
            log.debug("FFmpeg 检测: 不可用 (未找到)")
            return False
