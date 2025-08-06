"""
基础Repository类

提供通用的CRUD操作接口，所有具体的Repository都继承自这个基类。
使用SQLAlchemy 2.0的异步API进行数据库操作。
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Type, Optional, List, Dict, Any, Union, Sequence
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func, and_, or_
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.sql import Select
from contextlib import asynccontextmanager

from ..models.base import Base

# 泛型类型
ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType], ABC):
    """
    基础Repository类
    
    提供通用的CRUD操作和查询方法
    """
    
    def __init__(self, session: AsyncSession, model: Type[ModelType]):
        """
        初始化Repository
        
        Args:
            session: SQLAlchemy异步会话
            model: ORM模型类
        """
        self.session = session
        self.model = model
    
    async def get_by_id(self, id: int) -> Optional[ModelType]:
        """
        根据ID获取单个记录
        
        Args:
            id: 记录ID
            
        Returns:
            找到的记录或None
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_ids(self, ids: List[int]) -> List[ModelType]:
        """
        根据ID列表获取多个记录
        
        Args:
            ids: ID列表
            
        Returns:
            找到的记录列表
        """
        if not ids:
            return []
            
        stmt = select(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_all(
        self, 
        limit: Optional[int] = None, 
        offset: Optional[int] = None,
        order_by: Optional[str] = None
    ) -> List[ModelType]:
        """
        获取所有记录
        
        Args:
            limit: 限制返回条数
            offset: 偏移量
            order_by: 排序字段
            
        Returns:
            记录列表
        """
        stmt = select(self.model)
        
        if order_by:
            if order_by.startswith('-'):
                # 降序排序
                field_name = order_by[1:]
                if hasattr(self.model, field_name):
                    stmt = stmt.order_by(getattr(self.model, field_name).desc())
            else:
                # 升序排序
                if hasattr(self.model, order_by):
                    stmt = stmt.order_by(getattr(self.model, order_by))
        
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
            
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> ModelType:
        """
        创建新记录
        
        Args:
            **kwargs: 字段值
            
        Returns:
            创建的记录
        """
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        await self.session.refresh(instance)
        return instance
    
    async def create_many(self, items: List[Dict[str, Any]]) -> List[ModelType]:
        """
        批量创建记录
        
        Args:
            items: 要创建的记录列表
            
        Returns:
            创建的记录列表
        """
        instances = [self.model(**item) for item in items]
        self.session.add_all(instances)
        await self.session.flush()
        
        # 刷新所有实例以获取生成的ID
        for instance in instances:
            await self.session.refresh(instance)
            
        return instances
    
    async def update(self, id: int, **kwargs) -> Optional[ModelType]:
        """
        更新记录
        
        Args:
            id: 记录ID
            **kwargs: 要更新的字段值
            
        Returns:
            更新后的记录或None
        """
        stmt = update(self.model).where(self.model.id == id).values(**kwargs)
        result = await self.session.execute(stmt)
        
        if result.rowcount > 0:
            # 返回更新后的记录
            return await self.get_by_id(id)
        return None
    
    async def update_many(self, filters: Dict[str, Any], **kwargs) -> int:
        """
        批量更新记录
        
        Args:
            filters: 更新条件
            **kwargs: 要更新的字段值
            
        Returns:
            受影响的行数
        """
        stmt = update(self.model).values(**kwargs)
        
        # 添加过滤条件
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def delete(self, id: int) -> bool:
        """
        删除记录
        
        Args:
            id: 记录ID
            
        Returns:
            是否删除成功
        """
        stmt = delete(self.model).where(self.model.id == id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
    
    async def delete_many(self, ids: List[int]) -> int:
        """
        批量删除记录
        
        Args:
            ids: ID列表
            
        Returns:
            删除的记录数
        """
        if not ids:
            return 0
            
        stmt = delete(self.model).where(self.model.id.in_(ids))
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def count(self, **filters) -> int:
        """
        统计记录数
        
        Args:
            **filters: 过滤条件
            
        Returns:
            记录总数
        """
        stmt = select(func.count(self.model.id))
        
        # 添加过滤条件
        for field, value in filters.items():
            if hasattr(self.model, field):
                stmt = stmt.where(getattr(self.model, field) == value)
        
        result = await self.session.execute(stmt)
        return result.scalar() or 0
    
    async def exists(self, **filters) -> bool:
        """
        检查记录是否存在
        
        Args:
            **filters: 过滤条件
            
        Returns:
            是否存在
        """
        count = await self.count(**filters)
        return count > 0
    
    async def get_by_field(self, field: str, value: Any) -> Optional[ModelType]:
        """
        根据字段值获取单个记录
        
        Args:
            field: 字段名
            value: 字段值
            
        Returns:
            找到的记录或None
        """
        if not hasattr(self.model, field):
            return None
            
        stmt = select(self.model).where(getattr(self.model, field) == value)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_many_by_field(
        self, 
        field: str, 
        value: Any,
        limit: Optional[int] = None,
        offset: Optional[int] = None
    ) -> List[ModelType]:
        """
        根据字段值获取多个记录
        
        Args:
            field: 字段名
            value: 字段值
            limit: 限制返回条数
            offset: 偏移量
            
        Returns:
            记录列表
        """
        if not hasattr(self.model, field):
            return []
            
        stmt = select(self.model).where(getattr(self.model, field) == value)
        
        if offset:
            stmt = stmt.offset(offset)
        if limit:
            stmt = stmt.limit(limit)
            
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    def _build_query(self, **filters) -> Select:
        """
        构建基础查询
        
        Args:
            **filters: 过滤条件
            
        Returns:
            SQLAlchemy Select对象
        """
        stmt = select(self.model)
        
        # 添加过滤条件
        for field, value in filters.items():
            if hasattr(self.model, field):
                if isinstance(value, (list, tuple)):
                    stmt = stmt.where(getattr(self.model, field).in_(value))
                else:
                    stmt = stmt.where(getattr(self.model, field) == value)
        
        return stmt
    
    async def get_with_relationships(
        self, 
        id: int, 
        relationships: List[str]
    ) -> Optional[ModelType]:
        """
        获取记录及其关联数据
        
        Args:
            id: 记录ID
            relationships: 要加载的关系列表
            
        Returns:
            包含关联数据的记录或None
        """
        stmt = select(self.model).where(self.model.id == id)
        
        # 添加关系加载
        for rel_name in relationships:
            if hasattr(self.model, rel_name):
                stmt = stmt.options(selectinload(getattr(self.model, rel_name)))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    @asynccontextmanager
    async def transaction(self):
        """
        事务上下文管理器
        
        使用示例:
            async with repo.transaction():
                await repo.create(...)
                await repo.update(...)
        """
        try:
            yield self.session
            await self.session.commit()
        except Exception:
            await self.session.rollback()
            raise