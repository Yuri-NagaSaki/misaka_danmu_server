"""
用户和认证Repository

提供用户管理、认证、API令牌等相关的数据访问方法。
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, update, delete
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.user import (
    User, APIToken, TokenAccessLog, BangumiAuth, 
    OAuthState, UARules
)


class UserRepository(BaseRepository[User]):
    """用户Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)
    
    async def get_by_username(self, username: str) -> Optional[User]:
        """
        根据用户名获取用户
        
        Args:
            username: 用户名
            
        Returns:
            用户对象或None
        """
        return await self.get_by_field("username", username)
    
    async def get_with_auth_info(self, user_id: int) -> Optional[User]:
        """
        获取用户及其认证信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            包含认证信息的用户对象
        """
        stmt = select(User).where(User.id == user_id).options(
            selectinload(User.bangumi_auth),
            selectinload(User.oauth_states)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def verify_password(self, username: str, password_hash: str) -> Optional[User]:
        """
        验证用户密码
        
        Args:
            username: 用户名
            password_hash: 密码哈希值
            
        Returns:
            验证成功返回用户对象，否则返回None
        """
        stmt = select(User).where(
            and_(
                User.username == username,
                User.hashed_password == password_hash
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def update_token(self, user_id: int, token: str) -> bool:
        """
        更新用户JWT令牌
        
        Args:
            user_id: 用户ID
            token: 新的JWT令牌
            
        Returns:
            是否更新成功
        """
        result = await self.update(user_id, token=token, token_update=datetime.utcnow())
        return result is not None
    
    async def get_users_with_active_tokens(self) -> List[User]:
        """
        获取有活跃令牌的用户
        
        Returns:
            用户列表
        """
        # 假设令牌在24小时内更新算作活跃
        since_time = datetime.utcnow() - timedelta(hours=24)
        
        stmt = select(User).where(
            and_(
                User.token.isnot(None),
                User.token_update >= since_time
            )
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class APITokenRepository(BaseRepository[APIToken]):
    """API令牌Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, APIToken)
    
    async def get_by_token(self, token: str) -> Optional[APIToken]:
        """
        根据令牌字符串获取令牌对象
        
        Args:
            token: 令牌字符串
            
        Returns:
            令牌对象或None
        """
        return await self.get_by_field("token", token)
    
    async def get_active_tokens(self) -> List[APIToken]:
        """
        获取所有活跃的API令牌
        
        Returns:
            活跃令牌列表
        """
        now = datetime.utcnow()
        
        stmt = select(APIToken).where(
            and_(
                APIToken.is_enabled == True,
                or_(
                    APIToken.expires_at.is_(None),
                    APIToken.expires_at > now
                )
            )
        ).options(selectinload(APIToken.access_logs))
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_expired_tokens(self) -> List[APIToken]:
        """
        获取所有过期的API令牌
        
        Returns:
            过期令牌列表
        """
        now = datetime.utcnow()
        
        stmt = select(APIToken).where(
            and_(
                APIToken.expires_at.isnot(None),
                APIToken.expires_at <= now
            )
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def validate_token(self, token: str) -> Optional[APIToken]:
        """
        验证API令牌是否有效
        
        Args:
            token: 令牌字符串
            
        Returns:
            有效令牌对象或None
        """
        now = datetime.utcnow()
        
        stmt = select(APIToken).where(
            and_(
                APIToken.token == token,
                APIToken.is_enabled == True,
                or_(
                    APIToken.expires_at.is_(None),
                    APIToken.expires_at > now
                )
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def disable_token(self, token: str) -> bool:
        """
        禁用API令牌
        
        Args:
            token: 令牌字符串
            
        Returns:
            是否禁用成功
        """
        token_obj = await self.get_by_token(token)
        if token_obj:
            result = await self.update(token_obj.id, is_enabled=False)
            return result is not None
        return False


class TokenAccessLogRepository(BaseRepository[TokenAccessLog]):
    """令牌访问日志Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TokenAccessLog)
    
    async def log_access(
        self, 
        token_id: int, 
        ip_address: str, 
        user_agent: Optional[str] = None,
        status: str = "success",
        path: Optional[str] = None
    ) -> TokenAccessLog:
        """
        记录令牌访问日志
        
        Args:
            token_id: 令牌ID
            ip_address: 访问IP地址
            user_agent: 用户代理字符串
            status: 访问状态
            path: 访问路径
            
        Returns:
            访问日志对象
        """
        return await self.create(
            token_id=token_id,
            ip_address=ip_address,
            user_agent=user_agent,
            status=status,
            path=path,
            access_time=datetime.utcnow()
        )
    
    async def get_logs_by_token(
        self, 
        token_id: int, 
        limit: int = 100
    ) -> List[TokenAccessLog]:
        """
        获取令牌的访问日志
        
        Args:
            token_id: 令牌ID
            limit: 返回数量限制
            
        Returns:
            访问日志列表
        """
        stmt = select(TokenAccessLog).where(
            TokenAccessLog.token_id == token_id
        ).order_by(
            TokenAccessLog.access_time.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_recent_logs(self, hours: int = 24) -> List[TokenAccessLog]:
        """
        获取最近的访问日志
        
        Args:
            hours: 最近小时数
            
        Returns:
            最近的访问日志列表
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = select(TokenAccessLog).where(
            TokenAccessLog.access_time >= since_time
        ).options(
            selectinload(TokenAccessLog.token)
        ).order_by(
            TokenAccessLog.access_time.desc()
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_access_stats(
        self, 
        token_id: Optional[int] = None, 
        days: int = 7
    ) -> Dict[str, Any]:
        """
        获取访问统计信息
        
        Args:
            token_id: 令牌ID（可选，不指定则统计所有令牌）
            days: 统计天数
            
        Returns:
            访问统计数据
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 构建基础查询
        base_where = TokenAccessLog.access_time >= since_date
        if token_id:
            base_where = and_(base_where, TokenAccessLog.token_id == token_id)
        
        # 总访问次数
        total_count_stmt = select(func.count(TokenAccessLog.id)).where(base_where)
        total_result = await self.session.execute(total_count_stmt)
        total_count = total_result.scalar() or 0
        
        # 按状态统计
        status_stats_stmt = select(
            TokenAccessLog.status,
            func.count(TokenAccessLog.id)
        ).where(base_where).group_by(TokenAccessLog.status)
        
        status_result = await self.session.execute(status_stats_stmt)
        status_stats = dict(status_result.all())
        
        # 按IP统计（Top 10）
        ip_stats_stmt = select(
            TokenAccessLog.ip_address,
            func.count(TokenAccessLog.id).label('count')
        ).where(base_where).group_by(
            TokenAccessLog.ip_address
        ).order_by(desc('count')).limit(10)
        
        ip_result = await self.session.execute(ip_stats_stmt)
        ip_stats = dict(ip_result.all())
        
        return {
            "total_count": total_count,
            "status_distribution": status_stats,
            "top_ips": ip_stats
        }
    
    async def cleanup_old_logs(self, days: int = 30) -> int:
        """
        清理过期的访问日志
        
        Args:
            days: 保留天数
            
        Returns:
            清理的日志数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(TokenAccessLog).where(
            TokenAccessLog.access_time < cutoff_date
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount


class BangumiAuthRepository(BaseRepository[BangumiAuth]):
    """Bangumi认证Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, BangumiAuth)
    
    async def get_by_user_id(self, user_id: int) -> Optional[BangumiAuth]:
        """
        根据用户ID获取Bangumi认证信息
        
        Args:
            user_id: 用户ID
            
        Returns:
            Bangumi认证对象或None
        """
        return await self.get_by_field("user_id", user_id)
    
    async def get_by_bangumi_user_id(self, bangumi_user_id: int) -> Optional[BangumiAuth]:
        """
        根据Bangumi用户ID获取认证信息
        
        Args:
            bangumi_user_id: Bangumi用户ID
            
        Returns:
            Bangumi认证对象或None
        """
        return await self.get_by_field("bangumi_user_id", bangumi_user_id)
    
    async def get_expired_tokens(self) -> List[BangumiAuth]:
        """
        获取过期的Bangumi认证令牌
        
        Returns:
            过期认证列表
        """
        now = datetime.utcnow()
        
        stmt = select(BangumiAuth).where(
            and_(
                BangumiAuth.expires_at.isnot(None),
                BangumiAuth.expires_at <= now
            )
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def refresh_token(
        self, 
        user_id: int, 
        new_access_token: str, 
        new_refresh_token: str,
        expires_at: datetime
    ) -> bool:
        """
        刷新Bangumi访问令牌
        
        Args:
            user_id: 用户ID
            new_access_token: 新的访问令牌
            new_refresh_token: 新的刷新令牌
            expires_at: 过期时间
            
        Returns:
            是否刷新成功
        """
        stmt = update(BangumiAuth).where(
            BangumiAuth.user_id == user_id
        ).values(
            access_token=new_access_token,
            refresh_token=new_refresh_token,
            expires_at=expires_at
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount > 0


class OAuthStateRepository(BaseRepository[OAuthState]):
    """OAuth状态Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, OAuthState)
    
    async def get_by_state_key(self, state_key: str) -> Optional[OAuthState]:
        """
        根据状态键获取OAuth状态
        
        Args:
            state_key: 状态键
            
        Returns:
            OAuth状态对象或None
        """
        return await self.get_by_field("state_key", state_key)
    
    async def create_state(
        self, 
        user_id: int, 
        state_key: str, 
        expires_minutes: int = 10
    ) -> OAuthState:
        """
        创建OAuth状态
        
        Args:
            user_id: 用户ID
            state_key: 状态键
            expires_minutes: 过期分钟数
            
        Returns:
            OAuth状态对象
        """
        expires_at = datetime.utcnow() + timedelta(minutes=expires_minutes)
        
        return await self.create(
            state_key=state_key,
            user_id=user_id,
            expires_at=expires_at
        )
    
    async def validate_and_consume_state(
        self, 
        state_key: str, 
        user_id: int
    ) -> bool:
        """
        验证并消费OAuth状态
        
        Args:
            state_key: 状态键
            user_id: 用户ID
            
        Returns:
            是否验证成功
        """
        now = datetime.utcnow()
        
        state = await self.get_by_state_key(state_key)
        if state and state.user_id == user_id and state.expires_at > now:
            # 删除已使用的状态
            await self.session.delete(state)
            return True
        
        return False
    
    async def cleanup_expired_states(self) -> int:
        """
        清理过期的OAuth状态
        
        Returns:
            清理的状态数量
        """
        now = datetime.utcnow()
        
        stmt = delete(OAuthState).where(
            OAuthState.expires_at <= now
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount


class UARulesRepository(BaseRepository[UARules]):
    """UA规则Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, UARules)
    
    async def get_by_ua_string(self, ua_string: str) -> Optional[UARules]:
        """
        根据UA字符串获取规则
        
        Args:
            ua_string: UA字符串
            
        Returns:
            UA规则对象或None
        """
        return await self.get_by_field("ua_string", ua_string)
    
    async def search_ua_rules(self, keyword: str) -> List[UARules]:
        """
        搜索UA规则
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            匹配的UA规则列表
        """
        search_term = f"%{keyword}%"
        
        stmt = select(UARules).where(
            UARules.ua_string.ilike(search_term)
        ).order_by(UARules.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def check_ua_blocked(self, ua_string: str) -> bool:
        """
        检查UA字符串是否被阻止
        
        Args:
            ua_string: UA字符串
            
        Returns:
            是否被阻止
        """
        rule = await self.get_by_ua_string(ua_string)
        return rule is not None
    
    async def get_recent_rules(self, days: int = 30) -> List[UARules]:
        """
        获取最近添加的UA规则
        
        Args:
            days: 最近天数
            
        Returns:
            最近的UA规则列表
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(UARules).where(
            UARules.created_at >= since_date
        ).order_by(UARules.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())