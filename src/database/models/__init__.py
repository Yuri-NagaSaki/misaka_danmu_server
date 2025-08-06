"""
SQLAlchemy ORM 模型定义

导入所有数据库模型，确保SQLAlchemy能够发现所有表和关系
"""

# 导入基类
from .base import Base, IDMixin, TimestampMixin

# 导入番剧相关模型
from .anime import (
    AnimeType,
    Anime,
    AnimeSource,
    AnimeMetadata,
    AnimeAlias,
    TMDBEpisodeMapping
)

# 导入分集和弹幕模型
from .episode import Episode, Comment

# 导入用户和认证模型
from .user import (
    User,
    APIToken,
    TokenAccessLog,
    BangumiAuth,
    OAuthState,
    UARules
)

# 导入系统配置模型
from .system import (
    Config,
    CacheData,
    Scraper,
    ScheduledTask,
    TaskHistory
)

# 导出所有模型供外部使用
__all__ = [
    # 基类
    "Base",
    "IDMixin", 
    "TimestampMixin",
    
    # 枚举
    "AnimeType",
    
    # 番剧相关模型
    "Anime",
    "AnimeSource", 
    "AnimeMetadata",
    "AnimeAlias",
    "TMDBEpisodeMapping",
    
    # 分集和弹幕模型
    "Episode",
    "Comment",
    
    # 用户和认证模型
    "User",
    "APIToken",
    "TokenAccessLog",
    "BangumiAuth",
    "OAuthState",
    "UARules",
    
    # 系统配置模型
    "Config",
    "CacheData",
    "Scraper",
    "ScheduledTask",
    "TaskHistory",
]