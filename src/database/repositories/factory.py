"""
Repository工厂和依赖注入

提供Repository的创建和管理，支持依赖注入模式。
"""

from typing import Type, TypeVar, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager

from .base import BaseRepository
from .anime import (
    AnimeRepository, AnimeSourceRepository, AnimeMetadataRepository,
    AnimeAliasRepository, TMDBEpisodeMappingRepository
)
from .episode import EpisodeRepository, CommentRepository
from .user import (
    UserRepository, APITokenRepository, TokenAccessLogRepository,
    BangumiAuthRepository, OAuthStateRepository, UARulesRepository
)
from .system import (
    ConfigRepository, CacheDataRepository, ScraperRepository,
    ScheduledTaskRepository, TaskHistoryRepository
)

# 类型定义
RepositoryType = TypeVar("RepositoryType", bound=BaseRepository)


class RepositoryFactory:
    """Repository工厂类"""
    
    def __init__(self, session: AsyncSession):
        """
        初始化工厂
        
        Args:
            session: SQLAlchemy异步会话
        """
        self.session = session
        self._repositories: Dict[Type, BaseRepository] = {}
    
    def get_repository(self, repository_class: Type[RepositoryType]) -> RepositoryType:
        """
        获取Repository实例（单例模式）
        
        Args:
            repository_class: Repository类
            
        Returns:
            Repository实例
        """
        if repository_class not in self._repositories:
            self._repositories[repository_class] = repository_class(self.session)
        
        return self._repositories[repository_class]
    
    # 番剧相关Repository
    @property
    def anime(self) -> AnimeRepository:
        """获取番剧Repository"""
        return self.get_repository(AnimeRepository)
    
    @property
    def anime_source(self) -> AnimeSourceRepository:
        """获取番剧数据源Repository"""
        return self.get_repository(AnimeSourceRepository)
    
    @property
    def anime_metadata(self) -> AnimeMetadataRepository:
        """获取番剧元数据Repository"""
        return self.get_repository(AnimeMetadataRepository)
    
    @property
    def anime_alias(self) -> AnimeAliasRepository:
        """获取番剧别名Repository"""
        return self.get_repository(AnimeAliasRepository)
    
    @property
    def tmdb_episode_mapping(self) -> TMDBEpisodeMappingRepository:
        """获取TMDB分集映射Repository"""
        return self.get_repository(TMDBEpisodeMappingRepository)
    
    # 分集和弹幕相关Repository
    @property
    def episode(self) -> EpisodeRepository:
        """获取分集Repository"""
        return self.get_repository(EpisodeRepository)
    
    @property
    def comment(self) -> CommentRepository:
        """获取弹幕Repository"""
        return self.get_repository(CommentRepository)
    
    # 用户和认证相关Repository
    @property
    def user(self) -> UserRepository:
        """获取用户Repository"""
        return self.get_repository(UserRepository)
    
    @property
    def api_token(self) -> APITokenRepository:
        """获取API令牌Repository"""
        return self.get_repository(APITokenRepository)
    
    @property
    def token_access_log(self) -> TokenAccessLogRepository:
        """获取令牌访问日志Repository"""
        return self.get_repository(TokenAccessLogRepository)
    
    @property
    def bangumi_auth(self) -> BangumiAuthRepository:
        """获取Bangumi认证Repository"""
        return self.get_repository(BangumiAuthRepository)
    
    @property
    def oauth_state(self) -> OAuthStateRepository:
        """获取OAuth状态Repository"""
        return self.get_repository(OAuthStateRepository)
    
    @property
    def ua_rules(self) -> UARulesRepository:
        """获取UA规则Repository"""
        return self.get_repository(UARulesRepository)
    
    # 系统配置相关Repository
    @property
    def config(self) -> ConfigRepository:
        """获取配置Repository"""
        return self.get_repository(ConfigRepository)
    
    @property
    def cache_data(self) -> CacheDataRepository:
        """获取缓存数据Repository"""
        return self.get_repository(CacheDataRepository)
    
    @property
    def scraper(self) -> ScraperRepository:
        """获取爬虫Repository"""
        return self.get_repository(ScraperRepository)
    
    @property
    def scheduled_task(self) -> ScheduledTaskRepository:
        """获取定时任务Repository"""
        return self.get_repository(ScheduledTaskRepository)
    
    @property
    def task_history(self) -> TaskHistoryRepository:
        """获取任务历史Repository"""
        return self.get_repository(TaskHistoryRepository)
    
    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器
        
        使用示例:
            async with factory.transaction():
                await factory.anime.create(...)
                await factory.episode.create(...)
        """
        try:
            yield self
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise
    
    async def close(self):
        """关闭会话"""
        await self.session.close()


class RepositoryManager:
    """
    Repository管理器
    
    用于管理数据库会话的生命周期和Repository的创建
    """
    
    def __init__(self, session_factory):
        """
        初始化管理器
        
        Args:
            session_factory: 会话工厂函数
        """
        self.session_factory = session_factory
    
    @asynccontextmanager
    async def get_repository_factory(self) -> RepositoryFactory:
        """
        获取Repository工厂的异步上下文管理器
        
        使用示例:
            async with manager.get_repository_factory() as repos:
                anime = await repos.anime.get_by_id(1)
                episodes = await repos.episode.get_episodes_by_source(anime.sources[0].id)
        """
        async with self.session_factory() as session:
            factory = RepositoryFactory(session)
            try:
                yield factory
            finally:
                await factory.close()


# 依赖注入辅助函数
async def get_repository_factory(session: AsyncSession) -> RepositoryFactory:
    """
    获取Repository工厂实例
    
    这个函数可以用于FastAPI的依赖注入
    
    Args:
        session: SQLAlchemy异步会话
        
    Returns:
        Repository工厂实例
    """
    return RepositoryFactory(session)


# FastAPI依赖注入示例（需要在应用中配置）
"""
在FastAPI应用中的使用示例：

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

# 假设你有一个get_session依赖
async def get_session() -> AsyncSession:
    # 创建和管理数据库会话的逻辑
    pass

# Repository工厂依赖
async def get_repos(session: AsyncSession = Depends(get_session)) -> RepositoryFactory:
    return RepositoryFactory(session)

# 在API端点中使用
@app.get("/anime/{anime_id}")
async def get_anime(
    anime_id: int, 
    repos: RepositoryFactory = Depends(get_repos)
):
    anime = await repos.anime.get_with_full_details(anime_id)
    return anime

# 使用事务的示例
@app.post("/anime")
async def create_anime(
    anime_data: dict,
    repos: RepositoryFactory = Depends(get_repos)
):
    async with repos.transaction():
        # 创建番剧
        anime = await repos.anime.create(**anime_data)
        
        # 创建数据源
        source_data = {...}
        source = await repos.anime_source.create(**source_data)
        
        return anime
"""