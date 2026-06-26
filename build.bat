@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   ScreenRecorder - 构建 .EXE
echo ============================================
echo.

:: 生成图标
echo [1/3] 生成应用图标...
C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe generate_icon.py
if %errorlevel% neq 0 (
    echo [WARN] 图标生成失败，使用默认图标
)

:: 检测 PyInstaller
echo [2/3] 检测 PyInstaller...
C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe -c "import PyInstaller" 2>nul
if %errorlevel% neq 0 (
    echo [INFO] 安装 PyInstaller...
    C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe -m pip install pyinstaller -q
)

:: 打包
echo [3/3] 打包为 .EXE ...
echo.
C:\Users\Administrator\.workbuddy\binaries\python\versions\3.13.12\python.exe -m PyInstaller ^
    --noconfirm ^
    --onefile ^
    --windowed ^
    --name ScreenRecorder ^
    --icon app_icon.ico ^
    --add-data "config.py;." ^
    --add-data "recorder.py;." ^
    --add-data "logger.py;." ^
    --hidden-import pystray._win32 ^
    --hidden-import PIL ^
    --hidden-import mss ^
    --hidden-import cv2 ^
    --hidden-import numpy ^
    main.py

if %errorlevel% neq 0 (
    echo.
    echo [ERROR] 打包失败！
    pause
    exit /b 1
)

echo.
echo ============================================
echo   构建完成！
echo   输出文件: dist\ScreenRecorder.exe
echo ============================================
pause
