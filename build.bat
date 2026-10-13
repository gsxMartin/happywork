@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo 未找到 python 命令，请先安装 Python 并加入 PATH。
    exit /b 1
)

echo [1/3] 清理旧产物...
if exist "build" rmdir /s /q "build"
if exist "dist\lezi" rmdir /s /q "dist\lezi"

echo [2/3] 打包中（目录模式 + 无控制台窗口）...
python -m PyInstaller lezi.spec --noconfirm
if errorlevel 1 (
    echo.
    echo 打包失败。
    exit /b 1
)

echo [3/3] 打包完成。
echo 产物：dist\lezi\lezi.exe
echo 分发时请连同 dist\lezi\_internal 一起拷贝。
exit /b 0