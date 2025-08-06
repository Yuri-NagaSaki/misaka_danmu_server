#!/bin/bash
# Misaka Danmu Server 生产环境启动脚本

echo "🚀 启动 Misaka Danmu Server (生产模式)"

# 检查配置
if [ ! -f ".env" ]; then
    echo "⚠️  警告：未找到.env文件，请配置环境变量"
fi

# 运行数据库迁移
echo "运行数据库迁移..."
uv run alembic upgrade head

# 启动应用（使用uvicorn生产配置）
echo "启动应用..."
uv run uvicorn src.main_new:app \
    --host 0.0.0.0 \
    --port ${SERVER_PORT:-7768} \
    --workers ${WORKERS:-4} \
    --access-log \
    --log-level info

echo "✅ 应用已启动"
