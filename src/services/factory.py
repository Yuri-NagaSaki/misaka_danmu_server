"""
服务层工厂和依赖注入

提供服务层的创建和管理，支持依赖注入模式。
"""

import time
import logging
from typing import Type, TypeVar, Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime

from .base import BaseService
from .anime import AnimeService
from .episode import EpisodeService, DanmakuService
from .user import UserService, AuthService
from ..database.repositories.factory import RepositoryFactory

# 类型定义
ServiceType = TypeVar("ServiceType", bound=BaseService)
logger = logging.getLogger(__name__)


class ServiceFactory:
    """服务层工厂类"""
    
    def __init__(
        self, 
        repository_factory: RepositoryFactory,
        jwt_secret: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化服务工厂
        
        Args:
            repository_factory: Repository工厂实例
            jwt_secret: JWT密钥
            config: 配置字典
        """
        self.repos = repository_factory
        self.jwt_secret = jwt_secret or "default_secret_change_in_production"
        self.config = config or {}
        self._services: Dict[Type, BaseService] = {}
    
    def get_service(self, service_class: Type[ServiceType]) -> ServiceType:
        """
        获取服务实例（单例模式）
        
        Args:
            service_class: 服务类
            
        Returns:
            服务实例
        """
        if service_class not in self._services:
            if service_class == AuthService:
                # AuthService需要额外的JWT密钥参数
                self._services[service_class] = service_class(self.repos, self.jwt_secret)
            else:
                self._services[service_class] = service_class(self.repos)
        
        return self._services[service_class]
    
    # 便捷属性访问
    @property
    def anime(self) -> AnimeService:
        """获取番剧服务"""
        return self.get_service(AnimeService)
    
    @property
    def episode(self) -> EpisodeService:
        """获取分集服务"""
        return self.get_service(EpisodeService)
    
    @property
    def danmaku(self) -> DanmakuService:
        """获取弹幕服务"""
        return self.get_service(DanmakuService)
    
    @property
    def user(self) -> UserService:
        """获取用户服务"""
        return self.get_service(UserService)
    
    @property
    def auth(self) -> AuthService:
        """获取认证服务"""
        return self.get_service(AuthService)
    
    @asynccontextmanager
    async def transaction(self):
        """
        全局事务上下文管理器
        
        使用示例:
            async with service_factory.transaction():
                await service_factory.anime.create_anime_with_sources(...)
                await service_factory.episode.create_episode(...)
        """
        async with self.repos.transaction():
            yield self
    
    async def health_check(self) -> Dict[str, Any]:
        """
        服务层整体健康检查
        
        Returns:
            健康检查结果
        """
        health_results = {}
        overall_healthy = True
        
        # 检查各个服务
        services_to_check = [
            ("anime", self.anime),
            ("episode", self.episode), 
            ("danmaku", self.danmaku),
            ("user", self.user),
            ("auth", self.auth)
        ]
        
        for service_name, service in services_to_check:
            try:
                result = await service.health_check()
                health_results[service_name] = result.to_dict()
                if not result.success:
                    overall_healthy = False
            except Exception as e:
                health_results[service_name] = {
                    "success": False,
                    "error": str(e),
                    "timestamp": None
                }
                overall_healthy = False
        
        return {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "services": health_results,
            "repository_session_active": bool(self.repos.session),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def close(self):
        """关闭服务工厂"""
        await self.repos.close()


class ServiceManager:
    """
    服务管理器
    
    用于管理服务的生命周期和依赖注入
    """
    
    def __init__(
        self, 
        repository_manager,
        jwt_secret: str = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        初始化服务管理器
        
        Args:
            repository_manager: Repository管理器
            jwt_secret: JWT密钥
            config: 配置字典
        """
        self.repository_manager = repository_manager
        self.jwt_secret = jwt_secret
        self.config = config or {}
    
    @asynccontextmanager
    async def get_service_factory(self) -> ServiceFactory:
        """
        获取服务工厂的异步上下文管理器
        
        使用示例:
            async with manager.get_service_factory() as services:
                result = await services.anime.search_anime("关键词")
                anime_data = result.data if result.success else None
        """
        async with self.repository_manager.get_repository_factory() as repos:
            factory = ServiceFactory(repos, self.jwt_secret, self.config)
            try:
                yield factory
            finally:
                await factory.close()


# 依赖注入辅助函数
async def get_service_factory(
    repository_factory: RepositoryFactory,
    jwt_secret: str = None,
    config: Optional[Dict[str, Any]] = None
) -> ServiceFactory:
    """
    获取服务工厂实例
    
    这个函数可以用于FastAPI的依赖注入
    
    Args:
        repository_factory: Repository工厂
        jwt_secret: JWT密钥
        config: 配置字典
        
    Returns:
        服务工厂实例
    """
    return ServiceFactory(repository_factory, jwt_secret, config)


# FastAPI依赖注入示例（需要在应用中配置）
"""
在FastAPI应用中的使用示例：

from fastapi import Depends
from .database.repositories.factory import RepositoryFactory
from .services.factory import ServiceFactory

# 假设你有get_repository_factory依赖
async def get_repository_factory() -> RepositoryFactory:
    # 创建和管理Repository工厂的逻辑
    pass

# 服务工厂依赖
async def get_services(
    repos: RepositoryFactory = Depends(get_repository_factory)
) -> ServiceFactory:
    return ServiceFactory(repos, jwt_secret="your_jwt_secret")

# 在API端点中使用
@app.get("/anime/search")
async def search_anime(
    query: str,
    services: ServiceFactory = Depends(get_services)
):
    result = await services.anime.search_anime(query)
    if result.success:
        return {"data": result.data}
    else:
        raise HTTPException(
            status_code=400, 
            detail=result.error.message
        )

# 使用事务的示例
@app.post("/anime")
async def create_anime_complex(
    anime_data: dict,
    services: ServiceFactory = Depends(get_services)
):
    async with services.transaction():
        # 创建番剧
        anime_result = await services.anime.create_anime_with_sources(
            anime_data["anime"],
            anime_data.get("sources", []),
            anime_data.get("metadata", {}),
            anime_data.get("aliases", {})
        )
        
        if not anime_result.success:
            raise HTTPException(status_code=400, detail=anime_result.error.message)
        
        # 如果有分集数据，也一起创建
        if "episodes" in anime_data:
            episode_result = await services.episode.batch_create_episodes(
                source_id=anime_result.data["sources"][0]["id"],
                episodes_data=anime_data["episodes"]
            )
            
            return {
                "anime": anime_result.data,
                "episodes": episode_result.data if episode_result.success else None
            }
        
        return anime_result.data

# 健康检查端点
@app.get("/health")
async def health_check(
    services: ServiceFactory = Depends(get_services)
):
    health_result = await services.health_check()
    if health_result["overall_status"] == "healthy":
        return health_result
    else:
        raise HTTPException(status_code=503, detail=health_result)
"""


# 服务层中间件示例
class ServiceMiddleware:
    """服务层中间件"""
    
    def __init__(self, service_factory: ServiceFactory):
        self.service_factory = service_factory
    
    async def __call__(self, request, call_next):
        """
        中间件处理逻辑
        
        可以添加：
        - 请求日志记录
        - 性能监控
        - 错误处理
        - 认证检查
        """
        start_time = time.time()
        
        # 在请求上下文中添加服务工厂
        request.state.services = self.service_factory
        
        try:
            response = await call_next(request)
            
            # 记录成功的请求
            duration = time.time() - start_time
            logger.info(f"Request completed in {duration:.3f}s")
            
            return response
            
        except Exception as e:
            # 记录错误
            duration = time.time() - start_time
            logger.error(f"Request failed after {duration:.3f}s: {e}")
            raise