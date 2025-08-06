"""
FastAPI依赖注入系统 - 新ORM架构适配

提供新ORM服务层的依赖注入，替换原有的数据库连接池依赖
"""

import logging
from typing import AsyncGenerator, Optional
from contextlib import asynccontextmanager
from functools import lru_cache

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.exc import SQLAlchemyError

# 导入新的架构组件
from .config import settings
from .database.engine import DatabaseEngine  
from .database.repositories.factory import RepositoryFactory
from .services.factory import ServiceFactory
from .services.base import ServiceError, ValidationError, ResourceNotFoundError, PermissionDeniedError
from .services.user import AuthService, AuthContext

logger = logging.getLogger(__name__)

# 全局数据库引擎和会话工厂
_database_engine: Optional[DatabaseEngine] = None
_async_session_factory: Optional[async_sessionmaker] = None
_service_manager: Optional[ServiceFactory] = None

# 认证相关
security = HTTPBearer()


class DependencyError(Exception):
    """依赖注入异常"""
    pass


@lru_cache()
def get_database_engine() -> DatabaseEngine:
    """获取数据库引擎单例"""
    global _database_engine
    if _database_engine is None:
        _database_engine = DatabaseEngine(
            database_url=settings.database.async_url,
            echo=settings.database.echo,
            pool_size=settings.database.pool_size,
            max_overflow=settings.database.max_overflow,
            pool_timeout=settings.database.pool_timeout,
            pool_recycle=settings.database.pool_recycle
        )
        logger.info("✅ 数据库引擎初始化完成")
    return _database_engine


@lru_cache()
def get_session_factory() -> async_sessionmaker:
    """获取会话工厂单例"""
    global _async_session_factory
    if _async_session_factory is None:
        engine = get_database_engine()
        _async_session_factory = async_sessionmaker(
            bind=engine.engine,  # 使用正确的属性名
            class_=AsyncSession,
            expire_on_commit=False
        )
        logger.info("✅ 会话工厂初始化完成")
    return _async_session_factory


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    获取数据库会话依赖
    
    这是FastAPI依赖注入的核心函数，替换原有的get_db_pool
    """
    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            yield session
        except SQLAlchemyError as e:
            logger.error(f"数据库会话错误: {e}")
            await session.rollback()
            raise HTTPException(status_code=500, detail="数据库操作失败")
        finally:
            await session.close()


async def get_repository_factory(
    session: AsyncSession = Depends(get_db_session)
) -> RepositoryFactory:
    """获取Repository工厂依赖"""
    try:
        return RepositoryFactory(session)
    except Exception as e:
        logger.error(f"Repository工厂创建失败: {e}")
        raise HTTPException(status_code=500, detail="系统初始化失败")


async def get_service_factory(
    repos: RepositoryFactory = Depends(get_repository_factory)
) -> ServiceFactory:
    """获取Service工厂依赖"""
    try:
        return ServiceFactory(
            repository_factory=repos,
            jwt_secret=settings.jwt.secret_key,
            config={
                "jwt_algorithm": settings.jwt.algorithm,
                "jwt_expire_minutes": settings.jwt.access_token_expire_minutes
            }
        )
    except Exception as e:
        logger.error(f"Service工厂创建失败: {e}")
        raise HTTPException(status_code=500, detail="服务初始化失败")


# 快捷服务依赖
async def get_anime_service(services: ServiceFactory = Depends(get_service_factory)):
    """获取番剧服务"""
    return services.anime


async def get_episode_service(services: ServiceFactory = Depends(get_service_factory)):
    """获取分集服务"""
    return services.episode


async def get_danmaku_service(services: ServiceFactory = Depends(get_service_factory)):
    """获取弹幕服务"""
    return services.danmaku


async def get_user_service(services: ServiceFactory = Depends(get_service_factory)):
    """获取用户服务"""
    return services.user


async def get_auth_service(services: ServiceFactory = Depends(get_service_factory)):
    """获取认证服务"""
    return services.auth


# 认证相关依赖
async def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> Optional[AuthContext]:
    """
    获取当前用户（可选）
    
    如果没有提供认证信息或认证失败，返回None，不抛出异常
    """
    if not credentials:
        return None
    
    try:
        result = await auth_service.validate_jwt_token(credentials.credentials)
        if result.success:
            return result.data
        else:
            return None
    except Exception as e:
        logger.warning(f"可选认证失败: {e}")
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    auth_service: AuthService = Depends(get_auth_service)
) -> AuthContext:
    """
    获取当前用户（必须）
    
    如果认证失败，抛出HTTP异常
    """
    try:
        result = await auth_service.validate_jwt_token(credentials.credentials)
        if result.success:
            return result.data
        else:
            raise HTTPException(
                status_code=401,
                detail=result.error.message if result.error else "认证失败",
                headers={"WWW-Authenticate": "Bearer"}
            )
    except ServiceError as e:
        raise HTTPException(
            status_code=401,
            detail=e.message,
            headers={"WWW-Authenticate": "Bearer"}
        )
    except Exception as e:
        logger.error(f"认证过程异常: {e}")
        raise HTTPException(
            status_code=500,
            detail="认证系统错误"
        )


async def get_current_active_user(
    current_user: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """获取当前活跃用户"""
    # 可以在这里添加用户状态检查逻辑
    return current_user


# 管理员权限检查
async def require_admin_user(
    current_user: AuthContext = Depends(get_current_user)
) -> AuthContext:
    """要求管理员权限"""
    if "admin" not in current_user.permissions:
        raise HTTPException(
            status_code=403,
            detail="需要管理员权限"
        )
    return current_user


# 兼容性依赖 - 为了保持与现有代码的兼容性
async def get_legacy_db_pool(request: Request):
    """
    兼容性依赖：获取旧的数据库连接池
    
    在迁移期间保持与现有代码的兼容性
    """
    if hasattr(request.app.state, "db_pool"):
        return request.app.state.db_pool
    else:
        raise HTTPException(status_code=500, detail="数据库连接池未初始化")


# 应用状态管理器（保持兼容性）
async def get_scraper_manager(request: Request):
    """获取爬虫管理器"""
    return getattr(request.app.state, "scraper_manager", None)


async def get_task_manager(request: Request):
    """获取任务管理器"""
    return getattr(request.app.state, "task_manager", None)


async def get_webhook_manager(request: Request):
    """获取Webhook管理器"""
    return getattr(request.app.state, "webhook_manager", None)


# 异常处理器
def handle_service_error(error: ServiceError) -> HTTPException:
    """将服务层异常转换为HTTP异常"""
    if isinstance(error, ValidationError):
        return HTTPException(status_code=400, detail=error.message)
    elif isinstance(error, ResourceNotFoundError):
        return HTTPException(status_code=404, detail=error.message)
    elif isinstance(error, PermissionDeniedError):
        return HTTPException(status_code=403, detail=error.message)
    else:
        return HTTPException(status_code=500, detail=error.message)


# 全局初始化和清理
@asynccontextmanager
async def lifespan_manager():
    """应用生命周期管理器"""
    logger.info("🚀 启动新ORM服务层...")
    
    try:
        # 初始化数据库引擎
        engine = get_database_engine()
        await engine.test_connection()
        
        # 初始化会话工厂
        get_session_factory()
        
        logger.info("✅ 新ORM服务层初始化完成")
        
        yield
        
    except Exception as e:
        logger.error(f"❌ 新ORM服务层初始化失败: {e}")
        raise
    finally:
        logger.info("🛑 关闭新ORM服务层...")
        
        # 清理资源
        global _database_engine, _async_session_factory, _service_manager
        if _database_engine:
            await _database_engine.close()
            _database_engine = None
        
        _async_session_factory = None
        _service_manager = None
        
        logger.info("✅ 新ORM服务层清理完成")


# 健康检查依赖
async def get_health_check_info(
    services: ServiceFactory = Depends(get_service_factory)
) -> dict:
    """获取系统健康检查信息"""
    try:
        health_result = await services.health_check()
        return health_result
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return {
            "overall_status": "unhealthy",
            "error": str(e)
        }


# API版本兼容性装饰器
def with_service_error_handling(func):
    """服务错误处理装饰器"""
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ServiceError as e:
            raise handle_service_error(e)
        except Exception as e:
            logger.error(f"API处理异常: {e}")
            raise HTTPException(status_code=500, detail="内部服务器错误")
    
    return wrapper