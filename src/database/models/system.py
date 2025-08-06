"""
系统配置和缓存相关模型

包含：
- Config: 系统配置表
- CacheData: 缓存数据表
- Scraper: 爬虫配置表
- ScheduledTask: 定时任务表
- TaskHistory: 任务历史表
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    String, Integer, Text, Boolean, DateTime, LargeBinary,
    Index, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, IDMixin, TimestampMixin


class Config(Base):
    """
    系统配置表
    
    对应原表：config
    """
    __tablename__ = "config"
    
    # 配置键（作为主键）
    config_key: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="配置键"
    )
    
    # 配置值
    config_value: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="配置值"
    )
    
    # 配置描述
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="配置描述"
    )
    
    def __repr__(self) -> str:
        return f"<Config(key='{self.config_key}', value='{self.config_value}')>"


class CacheData(Base):
    """
    缓存数据表
    
    对应原表：cache_data
    """
    __tablename__ = "cache_data"
    
    # 缓存键（作为主键）
    cache_key: Mapped[str] = mapped_column(
        String(255),
        primary_key=True,
        comment="缓存键"
    )
    
    # 缓存提供商
    cache_provider: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="缓存提供商"
    )
    
    # 缓存值
    cache_value: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="缓存值（JSON格式）"
    )
    
    # 过期时间
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="过期时间"
    )
    
    # 索引
    __table_args__ = (
        # 过期时间索引（用于清理过期缓存）
        Index('idx_expires_at', 'expires_at'),
        # 缓存提供商索引
        Index('idx_cache_provider', 'cache_provider'),
    )
    
    def __repr__(self) -> str:
        return f"<CacheData(key='{self.cache_key}', provider='{self.cache_provider}')>"


class Scraper(Base):
    """
    爬虫配置表
    
    对应原表：scrapers
    """
    __tablename__ = "scrapers"
    
    # 提供商名称（作为主键）
    provider_name: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="数据源提供商名称"
    )
    
    # 是否启用
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )
    
    # 显示顺序
    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="显示顺序"
    )
    
    # 索引
    __table_args__ = (
        # 显示顺序索引
        Index('idx_display_order', 'display_order'),
        # 启用状态索引
        Index('idx_is_enabled', 'is_enabled'),
    )
    
    def __repr__(self) -> str:
        return f"<Scraper(provider='{self.provider_name}', enabled={self.is_enabled}, order={self.display_order})>"


class ScheduledTask(Base):
    """
    定时任务表
    
    对应原表：scheduled_tasks
    """
    __tablename__ = "scheduled_tasks"
    
    # 任务ID（作为主键）
    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="任务ID"
    )
    
    # 任务信息
    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="任务名称"
    )
    job_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="任务类型"
    )
    cron_expression: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Cron表达式"
    )
    is_enabled: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="是否启用"
    )
    
    # 执行时间
    last_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="上次执行时间"
    )
    next_run_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="下次执行时间"
    )
    
    # 索引
    __table_args__ = (
        # 任务名称索引
        Index('idx_name', 'name'),
        # 任务类型索引
        Index('idx_job_type', 'job_type'),
        # 启用状态索引
        Index('idx_is_enabled', 'is_enabled'),
        # 下次执行时间索引
        Index('idx_next_run_at', 'next_run_at'),
    )
    
    def __repr__(self) -> str:
        return f"<ScheduledTask(id='{self.id}', name='{self.name}', enabled={self.is_enabled})>"


class TaskHistory(Base):
    """
    任务历史表
    
    对应原表：task_history
    """
    __tablename__ = "task_history"
    
    # 任务ID（作为主键）
    id: Mapped[str] = mapped_column(
        String(100),
        primary_key=True,
        comment="任务ID"
    )
    
    # 任务信息
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="任务标题"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="任务状态"
    )
    progress: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="任务进度(0-100)"
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        comment="任务描述"
    )
    
    # 时间字段
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        server_default="CURRENT_TIMESTAMP",
        server_onupdate="CURRENT_TIMESTAMP",
        comment="更新时间"
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        comment="完成时间"
    )
    
    # 索引
    __table_args__ = (
        # 创建时间索引（倒序，用于获取最新任务）
        Index('idx_created_at', 'created_at'),
        # 状态索引
        Index('idx_status', 'status'),
        # 标题索引（用于搜索）
        Index('idx_title', 'title'),
        # 完成时间索引
        Index('idx_finished_at', 'finished_at'),
    )
    
    def __repr__(self) -> str:
        return f"<TaskHistory(id='{self.id}', title='{self.title}', status='{self.status}', progress={self.progress})>"