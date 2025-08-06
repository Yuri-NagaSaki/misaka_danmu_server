"""
业务服务层

提供应用的业务逻辑处理，包括数据验证、业务规则执行、事务管理等。
服务层位于Repository层之上，为控制器层提供高级业务操作接口。
"""

from .base import BaseService, ServiceResult, ServiceError, ValidationError
from .anime import AnimeService
from .episode import EpisodeService, DanmakuService
from .user import UserService, AuthService
from .factory import ServiceFactory

__all__ = [
    # 基础类
    "BaseService",
    "ServiceResult", 
    "ServiceError",
    "ValidationError",
    
    # 业务服务
    "AnimeService",
    "EpisodeService",
    "DanmakuService", 
    "UserService",
    "AuthService",
    
    # 工厂
    "ServiceFactory",
]