"""
Alembic 环境配置

用于PostgreSQL数据库schema管理
"""

import asyncio
import logging
import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context

# 导入应用配置和模型
import sys
from pathlib import Path

# 将项目根目录添加到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "src"))

# 导入所有模型以确保完整的metadata
from src.database.models.base import Base

# Alembic 配置对象
config = context.config

# 支持环境变量覆盖数据库URL
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option('sqlalchemy.url', database_url)

# 配置日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 目标元数据
target_metadata = Base.metadata

logger = logging.getLogger('alembic.env')

# 其他值从配置中获取，在env.py中定义的变量可以在脚本中访问
# my_important_option = config.get_main_option("my_important_option")


def run_migrations_offline() -> None:
    """
    在'离线'模式下运行迁移
    
    这配置了只有 URL 的上下文，而不是 Engine
    通过跳过 Engine 创建，我们甚至不需要 DBAPI 可用。
    
    在这种模式下调用 context.execute() 将把给定的 SQL 输出到文件。
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    """运行迁移的具体逻辑"""
    context.configure(
        connection=connection, 
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    在'在线'模式下运行异步迁移
    
    在这种情况下，我们需要创建 Engine 并将连接与上下文关联。
    """
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """在'在线'模式下运行迁移"""
    # 对于迁移生成，使用同步连接
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()