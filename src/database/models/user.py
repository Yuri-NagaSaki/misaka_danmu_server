"""
用户和认证相关模型

包含：
- User: 用户表
- APIToken: API令牌表
- TokenAccessLog: 令牌访问日志表
- BangumiAuth: Bangumi授权表
- OAuthState: OAuth状态表
- UARules: UA过滤规则表
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Text, Boolean, BigInteger,
    Index, ForeignKey, UniqueConstraint, DateTime
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin


class User(Base, IDMixin, TimestampMixin):
    """
    用户表
    
    对应原表：users
    """
    __tablename__ = "users"
    
    # 用户信息
    username: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="用户名"
    )
    hashed_password: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="哈希后的密码"
    )
    
    # JWT令牌相关
    token: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="当前JWT令牌"
    )
    token_update: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="令牌更新时间"
    )
    
    # 关系定义
    bangumi_auth: Mapped[Optional["BangumiAuth"]] = relationship(
        "BangumiAuth",
        back_populates="user",
        cascade="all, delete-orphan",
        uselist=False
    )
    oauth_states: Mapped[List["OAuthState"]] = relationship(
        "OAuthState",
        back_populates="user",
        cascade="all, delete-orphan"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：用户名唯一
        UniqueConstraint('username', name='idx_username_unique'),
        # 用户名索引
        Index('idx_username', 'username'),
        # 令牌更新时间索引
        Index('idx_token_update', 'token_update'),
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}')>"


class APIToken(Base, IDMixin, TimestampMixin):
    """
    API令牌表
    
    对应原表：api_tokens
    """
    __tablename__ = "api_tokens"
    
    # 令牌信息
    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="令牌名称"
    )
    token: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="令牌字符串"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="过期时间"
    )
    
    # 关系定义
    access_logs: Mapped[List["TokenAccessLog"]] = relationship(
        "TokenAccessLog",
        back_populates="token",
        cascade="all, delete-orphan"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：令牌字符串唯一
        UniqueConstraint('token', name='idx_token_unique'),
        # 令牌索引
        Index('idx_token', 'token'),
        # 启用状态索引
        Index('idx_is_enabled', 'is_enabled'),
        # 过期时间索引
        Index('idx_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<APIToken(id={self.id}, name='{self.name}', token='{self.token[:10]}...', enabled={self.is_enabled})>"


class TokenAccessLog(Base, IDMixin):
    """
    令牌访问日志表
    
    对应原表：token_access_logs
    """
    __tablename__ = "token_access_logs"
    
    # 关联字段
    token_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("api_tokens.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的令牌ID"
    )
    
    # 访问信息
    ip_address: Mapped[str] = mapped_column(
        String(45),  # 支持IPv6
        nullable=False,
        comment="访问IP地址"
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="用户代理字符串"
    )
    access_time: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="访问时间"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="访问状态"
    )
    path: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="访问路径"
    )
    
    # 关系定义
    token: Mapped["APIToken"] = relationship(
        "APIToken", 
        back_populates="access_logs"
    )
    
    # 约束和索引
    __table_args__ = (
        # 复合索引：令牌ID + 访问时间（用于按时间查询某令牌的访问日志）
        Index('idx_token_id_time', 'token_id', 'access_time'),
        # 访问时间索引
        Index('idx_access_time', 'access_time'),
        # IP地址索引
        Index('idx_ip_address', 'ip_address'),
    )
    
    def __repr__(self) -> str:
        return f"<TokenAccessLog(id={self.id}, token_id={self.token_id}, ip='{self.ip_address}', status='{self.status}')>"


class BangumiAuth(Base):
    """
    Bangumi授权表
    
    对应原表：bangumi_auth
    """
    __tablename__ = "bangumi_auth"
    
    # 关联字段（作为主键）
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        comment="关联的用户ID"
    )
    
    # Bangumi用户信息
    bangumi_user_id: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="Bangumi用户ID"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="Bangumi昵称"
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="头像URL"
    )
    
    # OAuth令牌
    access_token: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="访问令牌"
    )
    refresh_token: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="刷新令牌"
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="令牌过期时间"
    )
    authorized_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="授权时间"
    )
    
    # 关系定义
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="bangumi_auth"
    )
    
    # 索引
    __table_args__ = (
        # Bangumi用户ID索引
        Index('idx_bangumi_user_id', 'bangumi_user_id'),
        # 过期时间索引
        Index('idx_expires_at', 'expires_at'),
    )
    
    def __repr__(self) -> str:
        return f"<BangumiAuth(user_id={self.user_id}, bangumi_user_id={self.bangumi_user_id}, nickname='{self.nickname}')>"


class OAuthState(Base):
    """
    OAuth状态表
    
    对应原表：oauth_states
    """
    __tablename__ = "oauth_states"
    
    # 状态键（作为主键）
    state_key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="OAuth状态键"
    )
    
    # 关联字段
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的用户ID"
    )
    
    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="过期时间"
    )
    
    # 关系定义
    user: Mapped["User"] = relationship(
        "User", 
        back_populates="oauth_states"
    )
    
    # 索引
    __table_args__ = (
        # 过期时间索引（用于清理过期状态）
        Index('idx_oauth_expires_at', 'expires_at'),
        # 用户ID索引
        Index('idx_user_id', 'user_id'),
    )
    
    def __repr__(self) -> str:
        return f"<OAuthState(state_key='{self.state_key}', user_id={self.user_id})>"


class UARules(Base, IDMixin, TimestampMixin):
    """
    UA过滤规则表
    
    对应原表：ua_rules
    """
    __tablename__ = "ua_rules"
    
    # UA字符串
    ua_string: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User-Agent字符串"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：UA字符串唯一
        UniqueConstraint('ua_string', name='idx_ua_string_unique'),
        # UA字符串索引
        Index('idx_ua_string', 'ua_string'),
    )
    
    def __repr__(self) -> str:
        return f"<UARules(id={self.id}, ua_string='{self.ua_string[:50]}...')>"