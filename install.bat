@echo off
chcp 65001 >nul
echo ============================================
echo   ScreenRecorder - 安装依赖
echo ============================================
echo.

:: 检测 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] 未检测到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

:: 安装 Python 依赖
echo [1/2] 安装 Python 依赖...
pip install mss opencv-python numpy Pillow pystray -q
if %errorlevel% neq 0 (
    echo [WARN] pip install 部分失败，尝试继续...
)

:: 检测 ffmpeg
echo [2/2] 检测 ffmpeg...
ffmpeg -version >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] ffmpeg 已安装，将使用 H.264 编码
) else (
    echo [INFO] ffmpeg 未安装，将使用 MJPG 编码（文件稍大但兼容性好）
    echo [INFO] 如需 H.264 编码，请手动安装 ffmpeg:
    echo        winget install Gyan.FFmpeg
    echo        或从 https://ffmpeg.org/download.html 下载
)

echo.
echo ============================================
echo   安装完成！
echo   运行方式: 双击 run.bat 或执行 python main.py
echo ============================================
pause
