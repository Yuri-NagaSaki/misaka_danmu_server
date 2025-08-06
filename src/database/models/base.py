"""
SQLAlchemy 基础模型定义

所有ORM模型的基类和混入类
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import BigInteger, DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    """
    所有ORM模型的基类
    
    继承自 AsyncAttrs 以支持异步属性访问
    """
    pass


class IDMixin:
    """ID混入类 - 为模型提供自增主键"""
    
    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True,
        comment="主键ID"
    )


class TimestampMixin:
    """时间戳混入类 - 为模型提供创建和更新时间"""
    
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        server_default=func.now(),
        comment="创建时间"
    )
    
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )