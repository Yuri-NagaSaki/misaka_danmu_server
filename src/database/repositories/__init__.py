"""
Repository 模式实现

Repository模式将数据访问逻辑封装在独立的类中，提供统一的数据访问接口。
这样可以将业务逻辑与数据访问逻辑分离，提高代码的可测试性和可维护性。
"""

from .base import BaseRepository
from .anime import AnimeRepository
from .episode import EpisodeRepository
from .user import UserRepository
from .system import (
    ConfigRepository, CacheDataRepository, ScraperRepository,
    ScheduledTaskRepository, TaskHistoryRepository
)
from .factory import RepositoryFactory

__all__ = [
    "BaseRepository",
    "AnimeRepository", 
    "EpisodeRepository",
    "UserRepository",
    "ConfigRepository",
    "CacheDataRepository", 
    "ScraperRepository",
    "ScheduledTaskRepository",
    "TaskHistoryRepository",
    "RepositoryFactory",
]