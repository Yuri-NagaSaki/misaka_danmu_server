"""
系统配置和缓存Repository

提供系统配置、缓存数据、爬虫管理、任务调度等相关的数据访问方法。
"""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, update, delete, text
from sqlalchemy.ext.asyncio import AsyncSession
import json

from .base import BaseRepository
from ..models.system import Config, CacheData, Scraper, ScheduledTask, TaskHistory


class ConfigRepository(BaseRepository[Config]):
    """系统配置Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Config)
    
    async def get_by_key(self, key: str) -> Optional[Config]:
        """
        根据配置键获取配置
        
        Args:
            key: 配置键
            
        Returns:
            配置对象或None
        """
        return await self.get_by_field("key", key)
    
    async def get_value(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键
            default: 默认值
            
        Returns:
            配置值或默认值
        """
        config = await self.get_by_key(key)
        if config:
            try:
                # 尝试解析JSON值
                return json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，返回原始字符串值
                return config.value
        return default
    
    async def set_value(self, key: str, value: Any, description: Optional[str] = None) -> Config:
        """
        设置配置值
        
        Args:
            key: 配置键
            value: 配置值
            description: 配置描述
            
        Returns:
            配置对象
        """
        # 将值转换为JSON字符串（如果需要）
        if isinstance(value, (dict, list, bool)) or value is None:
            json_value = json.dumps(value, ensure_ascii=False)
        else:
            json_value = str(value)
        
        existing_config = await self.get_by_key(key)
        if existing_config:
            # 更新现有配置
            return await self.update(
                existing_config.id, 
                value=json_value, 
                description=description or existing_config.description
            )
        else:
            # 创建新配置
            return await self.create(
                key=key,
                value=json_value,
                description=description
            )
    
    async def get_configs_by_prefix(self, prefix: str) -> List[Config]:
        """
        根据键前缀获取配置
        
        Args:
            prefix: 键前缀
            
        Returns:
            配置列表
        """
        stmt = select(Config).where(
            Config.key.like(f"{prefix}%")
        ).order_by(Config.key)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_all_configs(self) -> Dict[str, Any]:
        """
        获取所有配置的字典形式
        
        Returns:
            配置字典
        """
        configs = await self.get_all()
        config_dict = {}
        
        for config in configs:
            try:
                # 尝试解析JSON值
                config_dict[config.key] = json.loads(config.value)
            except (json.JSONDecodeError, TypeError):
                # 如果不是JSON，使用原始字符串值
                config_dict[config.key] = config.value
        
        return config_dict


class CacheDataRepository(BaseRepository[CacheData]):
    """缓存数据Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, CacheData)
    
    async def get_by_key(self, cache_key: str) -> Optional[CacheData]:
        """
        根据缓存键获取缓存数据
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存数据对象或None
        """
        return await self.get_by_field("cache_key", cache_key)
    
    async def get_cache_value(self, cache_key: str) -> Optional[Any]:
        """
        获取缓存值
        
        Args:
            cache_key: 缓存键
            
        Returns:
            缓存值或None（如果过期或不存在）
        """
        cache = await self.get_by_key(cache_key)
        if cache:
            # 检查是否过期
            if cache.expires_at is None or cache.expires_at > datetime.utcnow():
                try:
                    return json.loads(cache.cache_value)
                except (json.JSONDecodeError, TypeError):
                    return cache.cache_value
            else:
                # 缓存已过期，删除它
                await self.delete(cache.id)
        return None
    
    async def set_cache_value(
        self, 
        cache_key: str, 
        value: Any, 
        expires_seconds: Optional[int] = None
    ) -> CacheData:
        """
        设置缓存值
        
        Args:
            cache_key: 缓存键
            value: 缓存值
            expires_seconds: 过期时间（秒），None表示永不过期
            
        Returns:
            缓存数据对象
        """
        # 计算过期时间
        expires_at = None
        if expires_seconds:
            expires_at = datetime.utcnow() + timedelta(seconds=expires_seconds)
        
        # 将值转换为JSON字符串
        if isinstance(value, (dict, list, bool)) or value is None:
            json_value = json.dumps(value, ensure_ascii=False)
        else:
            json_value = str(value)
        
        existing_cache = await self.get_by_key(cache_key)
        if existing_cache:
            # 更新现有缓存
            return await self.update(
                existing_cache.id,
                cache_value=json_value,
                expires_at=expires_at
            )
        else:
            # 创建新缓存
            return await self.create(
                cache_key=cache_key,
                cache_value=json_value,
                expires_at=expires_at
            )
    
    async def delete_cache(self, cache_key: str) -> bool:
        """
        删除缓存
        
        Args:
            cache_key: 缓存键
            
        Returns:
            是否删除成功
        """
        cache = await self.get_by_key(cache_key)
        if cache:
            return await self.delete(cache.id)
        return False
    
    async def cleanup_expired_cache(self) -> int:
        """
        清理过期的缓存数据
        
        Returns:
            清理的缓存数量
        """
        now = datetime.utcnow()
        
        stmt = delete(CacheData).where(
            and_(
                CacheData.expires_at.isnot(None),
                CacheData.expires_at <= now
            )
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息
        
        Returns:
            缓存统计数据
        """
        now = datetime.utcnow()
        
        # 总缓存数
        total_count_stmt = select(func.count(CacheData.id))
        total_result = await self.session.execute(total_count_stmt)
        total_count = total_result.scalar() or 0
        
        # 有效缓存数（未过期）
        valid_count_stmt = select(func.count(CacheData.id)).where(
            or_(
                CacheData.expires_at.is_(None),
                CacheData.expires_at > now
            )
        )
        valid_result = await self.session.execute(valid_count_stmt)
        valid_count = valid_result.scalar() or 0
        
        # 过期缓存数
        expired_count = total_count - valid_count
        
        return {
            "total_count": total_count,
            "valid_count": valid_count,
            "expired_count": expired_count
        }


class ScraperRepository(BaseRepository[Scraper]):
    """爬虫Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Scraper)
    
    async def get_by_name(self, name: str) -> Optional[Scraper]:
        """
        根据爬虫名称获取爬虫
        
        Args:
            name: 爬虫名称
            
        Returns:
            爬虫对象或None
        """
        return await self.get_by_field("name", name)
    
    async def get_active_scrapers(self) -> List[Scraper]:
        """
        获取所有活跃的爬虫
        
        Returns:
            活跃爬虫列表
        """
        return await self.get_many_by_field("is_active", True)
    
    async def get_scrapers_by_type(self, scraper_type: str) -> List[Scraper]:
        """
        根据爬虫类型获取爬虫列表
        
        Args:
            scraper_type: 爬虫类型
            
        Returns:
            爬虫列表
        """
        return await self.get_many_by_field("scraper_type", scraper_type)
    
    async def update_scraper_status(
        self, 
        scraper_id: int, 
        is_active: bool,
        last_run_at: Optional[datetime] = None,
        last_error: Optional[str] = None
    ) -> Optional[Scraper]:
        """
        更新爬虫状态
        
        Args:
            scraper_id: 爬虫ID
            is_active: 是否活跃
            last_run_at: 最后运行时间
            last_error: 最后错误信息
            
        Returns:
            更新后的爬虫对象
        """
        update_data = {"is_active": is_active}
        
        if last_run_at:
            update_data["last_run_at"] = last_run_at
        
        if last_error is not None:
            update_data["last_error"] = last_error
        
        return await self.update(scraper_id, **update_data)
    
    async def get_scrapers_due_for_run(self) -> List[Scraper]:
        """
        获取需要运行的爬虫（基于运行间隔）
        
        Returns:
            需要运行的爬虫列表
        """
        now = datetime.utcnow()
        
        # 使用原生SQL查询，因为需要复杂的时间计算
        stmt = text("""
            SELECT * FROM scrapers 
            WHERE is_active = true 
            AND (
                last_run_at IS NULL 
                OR last_run_at + INTERVAL run_interval_minutes MINUTE <= :now
            )
        """)
        
        result = await self.session.execute(stmt, {"now": now})
        
        # 将结果转换为Scraper对象
        scraper_ids = [row[0] for row in result.all()]  # 假设id是第一列
        
        if scraper_ids:
            scrapers = await self.get_by_ids(scraper_ids)
            return scrapers
        
        return []


class ScheduledTaskRepository(BaseRepository[ScheduledTask]):
    """定时任务Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, ScheduledTask)
    
    async def get_by_name(self, task_name: str) -> Optional[ScheduledTask]:
        """
        根据任务名称获取定时任务
        
        Args:
            task_name: 任务名称
            
        Returns:
            定时任务对象或None
        """
        return await self.get_by_field("task_name", task_name)
    
    async def get_active_tasks(self) -> List[ScheduledTask]:
        """
        获取所有活跃的定时任务
        
        Returns:
            活跃任务列表
        """
        return await self.get_many_by_field("is_active", True)
    
    async def get_tasks_due_for_run(self) -> List[ScheduledTask]:
        """
        获取需要运行的定时任务
        
        Returns:
            需要运行的任务列表
        """
        now = datetime.utcnow()
        
        stmt = select(ScheduledTask).where(
            and_(
                ScheduledTask.is_active == True,
                ScheduledTask.next_run_at <= now
            )
        ).order_by(ScheduledTask.next_run_at)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def update_task_schedule(
        self, 
        task_id: int, 
        next_run_at: datetime,
        last_run_at: Optional[datetime] = None
    ) -> Optional[ScheduledTask]:
        """
        更新任务调度信息
        
        Args:
            task_id: 任务ID
            next_run_at: 下次运行时间
            last_run_at: 最后运行时间
            
        Returns:
            更新后的任务对象
        """
        update_data = {"next_run_at": next_run_at}
        
        if last_run_at:
            update_data["last_run_at"] = last_run_at
        
        return await self.update(task_id, **update_data)
    
    async def get_task_stats(self) -> Dict[str, Any]:
        """
        获取任务统计信息
        
        Returns:
            任务统计数据
        """
        # 总任务数
        total_count_stmt = select(func.count(ScheduledTask.id))
        total_result = await self.session.execute(total_count_stmt)
        total_count = total_result.scalar() or 0
        
        # 活跃任务数
        active_count_stmt = select(func.count(ScheduledTask.id)).where(
            ScheduledTask.is_active == True
        )
        active_result = await self.session.execute(active_count_stmt)
        active_count = active_result.scalar() or 0
        
        return {
            "total_count": total_count,
            "active_count": active_count,
            "inactive_count": total_count - active_count
        }


class TaskHistoryRepository(BaseRepository[TaskHistory]):
    """任务历史Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TaskHistory)
    
    async def log_task_execution(
        self, 
        task_id: int, 
        status: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        result: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> TaskHistory:
        """
        记录任务执行历史
        
        Args:
            task_id: 任务ID
            status: 执行状态
            start_time: 开始时间
            end_time: 结束时间
            result: 执行结果
            error_message: 错误信息
            
        Returns:
            任务历史对象
        """
        duration = None
        if end_time and start_time:
            duration = int((end_time - start_time).total_seconds())
        
        return await self.create(
            task_id=task_id,
            status=status,
            start_time=start_time,
            end_time=end_time,
            duration=duration,
            result=result,
            error_message=error_message
        )
    
    async def get_task_history(
        self, 
        task_id: int, 
        limit: int = 50
    ) -> List[TaskHistory]:
        """
        获取任务的执行历史
        
        Args:
            task_id: 任务ID
            limit: 返回数量限制
            
        Returns:
            任务历史列表
        """
        stmt = select(TaskHistory).where(
            TaskHistory.task_id == task_id
        ).order_by(
            TaskHistory.start_time.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_recent_executions(self, hours: int = 24) -> List[TaskHistory]:
        """
        获取最近的任务执行记录
        
        Args:
            hours: 最近小时数
            
        Returns:
            最近的执行记录列表
        """
        since_time = datetime.utcnow() - timedelta(hours=hours)
        
        stmt = select(TaskHistory).where(
            TaskHistory.start_time >= since_time
        ).order_by(
            TaskHistory.start_time.desc()
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_task_performance_stats(
        self, 
        task_id: int, 
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取任务性能统计
        
        Args:
            task_id: 任务ID
            days: 统计天数
            
        Returns:
            性能统计数据
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        # 总执行次数
        total_executions_stmt = select(func.count(TaskHistory.id)).where(
            and_(
                TaskHistory.task_id == task_id,
                TaskHistory.start_time >= since_date
            )
        )
        total_result = await self.session.execute(total_executions_stmt)
        total_executions = total_result.scalar() or 0
        
        # 成功执行次数
        success_executions_stmt = select(func.count(TaskHistory.id)).where(
            and_(
                TaskHistory.task_id == task_id,
                TaskHistory.start_time >= since_date,
                TaskHistory.status == "success"
            )
        )
        success_result = await self.session.execute(success_executions_stmt)
        success_executions = success_result.scalar() or 0
        
        # 平均执行时间
        avg_duration_stmt = select(func.avg(TaskHistory.duration)).where(
            and_(
                TaskHistory.task_id == task_id,
                TaskHistory.start_time >= since_date,
                TaskHistory.duration.isnot(None)
            )
        )
        avg_result = await self.session.execute(avg_duration_stmt)
        avg_duration = avg_result.scalar() or 0
        
        # 成功率
        success_rate = (success_executions / total_executions * 100) if total_executions > 0 else 0
        
        return {
            "total_executions": total_executions,
            "success_executions": success_executions,
            "failed_executions": total_executions - success_executions,
            "success_rate": round(success_rate, 2),
            "average_duration": round(avg_duration, 2)
        }
    
    async def cleanup_old_history(self, days: int = 90) -> int:
        """
        清理过期的任务历史记录
        
        Args:
            days: 保留天数
            
        Returns:
            清理的记录数量
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = delete(TaskHistory).where(
            TaskHistory.start_time < cutoff_date
        )
        
        result = await self.session.execute(stmt)
        return result.rowcount