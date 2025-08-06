@echo off
REM Misaka Danmu Server Windows启动脚本

echo 🚀 启动 Misaka Danmu Server

REM 检查虚拟环境
if not exist ".venv" (
    echo 创建虚拟环境...
    uv sync
)

REM 启动应用
echo 启动应用...
uv run python -m src.main_new

echo ✅ 应用已启动
pause
