@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   ScreenRecorder - 安装向导
echo ============================================
echo.

:: 检查 .exe 是否存在
if not exist "dist\ScreenRecorder.exe" (
    echo [INFO] 未找到 .exe 文件，先执行构建...
    echo.
    call build.bat
    if %errorlevel% neq 0 (
        echo [ERROR] 构建失败，请手动运行 build.bat
        pause
        exit /b 1
    )
)

echo [1/3] 复制 .exe 到程序目录...
set "INSTALL_DIR=%USERPROFILE%\AppData\Local\ScreenRecorder"
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"
copy /Y "dist\ScreenRecorder.exe" "%INSTALL_DIR%\" >nul
echo       安装到: %INSTALL_DIR%

echo [2/3] 创建桌面快捷方式...
set "DESKTOP=%USERPROFILE%\Desktop"
:: 使用 PowerShell 创建快捷方式（比 VBS 更可靠）
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $lnk = $ws.CreateShortcut('%DESKTOP%\ScreenRecorder.lnk'); ^
     $lnk.TargetPath = '%INSTALL_DIR%\ScreenRecorder.exe'; ^
     $lnk.WorkingDirectory = '%INSTALL_DIR%'; ^
     $lnk.Description = 'ScreenRecorder - 轻量级桌面录屏软件'; ^
     $lnk.IconLocation = '%INSTALL_DIR%\ScreenRecorder.exe,0'; ^
     $lnk.Save()"
echo       快捷方式: %DESKTOP%\ScreenRecorder.lnk

echo [3/3] 创建开始菜单快捷方式...
set "STARTMENU=%APPDATA%\Microsoft\Windows\Start Menu\Programs"
if not exist "%STARTMENU%\ScreenRecorder" mkdir "%STARTMENU%\ScreenRecorder"
powershell -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $lnk = $ws.CreateShortcut('%STARTMENU%\ScreenRecorder\ScreenRecorder.lnk'); ^
     $lnk.TargetPath = '%INSTALL_DIR%\ScreenRecorder.exe'; ^
     $lnk.WorkingDirectory = '%INSTALL_DIR%'; ^
     $lnk.Description = 'ScreenRecorder - 轻量级桌面录屏软件'; ^
     $lnk.IconLocation = '%INSTALL_DIR%\ScreenRecorder.exe,0'; ^
     $lnk.Save()"
echo       开始菜单: %STARTMENU%\ScreenRecorder\

echo.
echo ============================================
echo   安装完成！
echo.
echo   - 桌面快捷方式已创建
echo   - 开始菜单已添加
echo   - 程序位置: %INSTALL_DIR%\ScreenRecorder.exe
echo.
echo   双击桌面的 ScreenRecorder 图标即可运行
echo ============================================
pause
