"""
数据库初始化模块

统一管理数据库引擎初始化、依赖注入和生命周期管理
"""

import logging
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from .engine import DatabaseEngine, init_database, get_db_session, close_database
from .models.base import Base
from ..config import settings

logger = logging.getLogger(__name__)

# 全局数据库引擎实例
database_engine: DatabaseEngine = None


async def initialize_database() -> None:
    """
    初始化数据库系统
    
    在FastAPI应用启动时调用
    """
    global database_engine
    
    try:
        # 获取数据库配置
        database_url = settings.database.async_url
        engine_config = settings.database.get_engine_config()
        
        logger.info(f"初始化数据库: {settings.database.type}")
        logger.info(f"数据库URL: {database_url.split('@')[1] if '@' in database_url else database_url}")
        
        # 初始化数据库引擎
        database_engine = await init_database(database_url, **engine_config)
        
        logger.info("数据库初始化成功")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise


async def shutdown_database() -> None:
    """
    关闭数据库连接
    
    在FastAPI应用关闭时调用
    """
    try:
        await close_database()
        logger.info("数据库连接已关闭")
    except Exception as e:
        logger.error(f"关闭数据库连接时出错: {e}")


# 导出FastAPI依赖注入函数
async def get_database_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI依赖注入：获取数据库会话
    
    Usage:
        @app.get("/api/example")
        async def example_endpoint(
            session: AsyncSession = Depends(get_database_session)
        ):
            # 使用 session 进行数据库操作
            pass
    """
    async with get_db_session() as session:
        yield session


# 为了兼容性，保留旧的函数名
get_db_session_dep = get_database_session


def get_engine() -> DatabaseEngine:
    """获取当前数据库引擎实例"""
    if database_engine is None:
        raise RuntimeError("数据库引擎未初始化")
    return database_engine


__all__ = [
    "Base",
    "initialize_database", 
    "shutdown_database",
    "get_database_session",
    "get_db_session_dep",
    "get_engine",
]