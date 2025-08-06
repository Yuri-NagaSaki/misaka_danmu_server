"""
SQLAlchemy 2.0 数据库引擎配置

支持多种数据库类型：
- MySQL (使用 aiomysql)
- PostgreSQL (使用 asyncpg)
- SQLite (使用 aiosqlite)
"""

import logging
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker,
    AsyncEngine
)
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.engine import make_url
from sqlalchemy import text

logger = logging.getLogger(__name__)


class DatabaseEngine:
    """数据库引擎管理类"""
    
    def __init__(self, database_url: str, **engine_kwargs):
        """
        初始化数据库引擎
        
        Args:
            database_url: 数据库连接字符串
            **engine_kwargs: 额外的引擎参数
        """
        self.database_url = database_url
        self.url = make_url(database_url)
        
        # 根据数据库类型设置默认配置
        self.engine_config = self._get_engine_config(**engine_kwargs)
        
        # 创建异步引擎
        self.engine: AsyncEngine = create_async_engine(
            database_url,
            **self.engine_config
        )
        
        # 创建会话工厂
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        logger.info(f"数据库引擎初始化完成: {self.url.drivername}://{self.url.host}:{self.url.port}/{self.url.database}")
    
    def _get_engine_config(self, **kwargs) -> Dict[str, Any]:
        """根据数据库类型获取引擎配置"""
        config = {
            "echo": False,  # 生产环境关闭SQL日志
            "pool_pre_ping": True,  # 连接池预检
            "pool_recycle": 3600,   # 连接回收时间(秒)
        }
        
        # 根据数据库类型优化配置
        if self.url.drivername.startswith("sqlite"):
            # SQLite 配置
            config.update({
                "poolclass": NullPool,  # SQLite 不支持连接池
                "connect_args": {"check_same_thread": False},
            })
        elif self.url.drivername.startswith(("mysql", "mariadb", "postgresql")):
            # MySQL/PostgreSQL 异步配置 - 让SQLAlchemy自动选择合适的连接池
            config.update({
                "pool_size": 10,        # 连接池大小
                "max_overflow": 20,     # 最大溢出连接
                "pool_timeout": 30,     # 获取连接超时
            })
        
        # 覆盖用户自定义配置
        config.update(kwargs)
        return config
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        获取数据库会话（依赖注入使用）
        
        自动处理事务：
        - 成功时提交事务
        - 异常时回滚事务
        - 确保会话正确关闭
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    async def create_session(self) -> AsyncSession:
        """创建新的数据库会话（手动管理）"""
        return self.session_factory()
    
    async def close(self) -> None:
        """关闭数据库引擎"""
        if self.engine:
            await self.engine.dispose()
            logger.info("数据库引擎已关闭")
    
    async def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            async with self.engine.begin() as conn:
                await conn.execute(text("SELECT 1"))
            logger.info("数据库连接测试成功")
            return True
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    @property
    def database_type(self) -> str:
        """获取数据库类型"""
        return self.url.drivername.split('+')[0]
    
    def __repr__(self) -> str:
        return f"DatabaseEngine(url='{self.url}', type='{self.database_type}')"


# 全局数据库引擎实例（将在应用启动时初始化）
db_engine: Optional[DatabaseEngine] = None


async def init_database(database_url: str, **engine_kwargs) -> DatabaseEngine:
    """
    初始化全局数据库引擎
    
    Args:
        database_url: 数据库连接字符串
        **engine_kwargs: 引擎额外参数
    
    Returns:
        DatabaseEngine: 数据库引擎实例
    """
    global db_engine
    
    if db_engine is not None:
        logger.warning("数据库引擎已初始化，关闭现有引擎")
        await db_engine.close()
    
    db_engine = DatabaseEngine(database_url, **engine_kwargs)
    
    # 测试连接
    if not await db_engine.test_connection():
        raise RuntimeError("数据库连接失败")
    
    return db_engine


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI 依赖注入：获取数据库会话
    
    Usage:
        @app.get("/api/endpoint")
        async def endpoint(session: AsyncSession = Depends(get_db_session)):
            # 使用 session 进行数据库操作
    """
    if db_engine is None:
        raise RuntimeError("数据库引擎未初始化，请先调用 init_database()")
    
    async with db_engine.get_session() as session:
        yield session


async def close_database() -> None:
    """关闭全局数据库引擎"""
    global db_engine
    if db_engine is not None:
        await db_engine.close()
        db_engine = None