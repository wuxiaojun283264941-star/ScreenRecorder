' 创建桌面快捷方式
' 双击运行此脚本即可在桌面创建 ScreenRecorder 快捷方式

Set oWS = WScript.CreateObject("WScript.Shell")
Set oFSO = CreateObject("Scripting.FileSystemObject")

' 获取脚本所在目录
sScriptDir = oFSO.GetParentFolderName(WScript.ScriptFullName)

' .exe 路径
sExePath = sScriptDir & "\dist\ScreenRecorder.exe"

' 如果 .exe 不在 dist 目录，尝试当前目录
If Not oFSO.FileExists(sExePath) Then
    sExePath = sScriptDir & "\ScreenRecorder.exe"
End If

' 如果还是不存在，提示用户
If Not oFSO.FileExists(sExePath) Then
    MsgBox "找不到 ScreenRecorder.exe" & vbCrLf & vbCrLf & _
           "请先运行 build.bat 构建 .exe 文件", vbExclamation, "ScreenRecorder"
    WScript.Quit
End If

' 桌面路径
sDesktop = oWS.SpecialFolders("Desktop")

' 创建快捷方式
Set oLink = oWS.CreateShortcut(sDesktop & "\ScreenRecorder.lnk")
oLink.TargetPath = sExePath
oLink.WorkingDirectory = sScriptDir & "\dist"
oLink.Description = "ScreenRecorder - 轻量级桌面录屏软件"
oLink.IconLocation = sExePath & ",0"
oLink.WindowStyle = 1  ' 正常窗口
oLink.Save

MsgBox "快捷方式已创建到桌面！" & vbCrLf & vbCrLf & _
       "位置: " & sDesktop & "\ScreenRecorder.lnk", vbInformation, "ScreenRecorder"
