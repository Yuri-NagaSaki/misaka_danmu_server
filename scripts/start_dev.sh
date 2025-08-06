#!/bin/bash
# Misaka Danmu Server 开发环境启动脚本

echo "🚀 启动 Misaka Danmu Server (开发模式)"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    uv sync
fi

# 启动应用
echo "启动应用..."
uv run python -m src.main_new

echo "✅ 应用已启动"
