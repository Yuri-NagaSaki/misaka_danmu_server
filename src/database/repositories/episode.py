"""
分集和弹幕Repository

提供分集和弹幕相关的数据访问方法，包括弹幕查询、分集管理等。
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import select, func, and_, or_, desc, asc, text
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .danmaku_parser import EnhancedCommentStatistics, DanmakuParamsParser
from .base import BaseRepository
from ..models.episode import Episode, Comment
from ..models.anime import AnimeSource


class EpisodeRepository(BaseRepository[Episode]):
    """分集Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Episode)
    
    async def get_by_source_and_episode(
        self, 
        source_id: int, 
        episode_index: int
    ) -> Optional[Episode]:
        """
        根据数据源和分集号获取分集
        
        Args:
            source_id: 数据源ID
            episode_index: 分集序号
            
        Returns:
            分集对象或None
        """
        stmt = select(Episode).where(
            and_(
                Episode.source_id == source_id,
                Episode.episode_index == episode_index
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_episodes_by_source(
        self, 
        source_id: int, 
        limit: Optional[int] = None
    ) -> List[Episode]:
        """
        获取数据源的所有分集
        
        Args:
            source_id: 数据源ID
            limit: 限制返回数量
            
        Returns:
            分集列表
        """
        stmt = select(Episode).where(
            Episode.source_id == source_id
        ).order_by(Episode.episode_index.asc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_episodes_with_danmaku_count(
        self, 
        source_id: int
    ) -> List[Tuple[Episode, int]]:
        """
        获取分集及其弹幕数量
        
        Args:
            source_id: 数据源ID
            
        Returns:
            (分集对象, 弹幕数量) 的元组列表
        """
        stmt = select(
            Episode,
            func.count(Comment.id).label('danmaku_count')
        ).outerjoin(Comment).where(
            Episode.source_id == source_id
        ).group_by(Episode.id).order_by(Episode.episode_index.asc())
        
        result = await self.session.execute(stmt)
        return [(episode, count) for episode, count in result.all()]
    
    async def get_recent_episodes(
        self, 
        days: int = 7, 
        limit: int = 50
    ) -> List[Episode]:
        """
        获取最近添加的分集
        
        Args:
            days: 最近天数
            limit: 返回数量限制
            
        Returns:
            最近添加的分集列表
        """
        since_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(Episode).where(
            Episode.created_at >= since_date
        ).options(
            selectinload(Episode.source)
        ).order_by(
            Episode.created_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_episodes_by_anime(
        self, 
        anime_id: int
    ) -> List[Episode]:
        """
        获取番剧的所有分集（通过数据源关联）
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            分集列表
        """
        stmt = select(Episode).join(AnimeSource).where(
            AnimeSource.anime_id == anime_id
        ).options(
            selectinload(Episode.source)
        ).order_by(
            AnimeSource.provider_name.asc(),
            Episode.episode_index.asc()
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_episode_stats(self, source_id: int) -> Dict[str, Any]:
        """
        获取数据源的分集统计信息
        
        Args:
            source_id: 数据源ID
            
        Returns:
            包含统计数据的字典
        """
        # 总分集数
        total_episodes_stmt = select(func.count(Episode.id)).where(
            Episode.source_id == source_id
        )
        total_result = await self.session.execute(total_episodes_stmt)
        total_episodes = total_result.scalar() or 0
        
        # 总弹幕数
        total_danmaku_stmt = select(func.count(Comment.id)).join(Episode).where(
            Episode.source_id == source_id
        )
        danmaku_result = await self.session.execute(total_danmaku_stmt)
        total_danmaku = danmaku_result.scalar() or 0
        
        # 平均每集弹幕数
        avg_danmaku = total_danmaku / total_episodes if total_episodes > 0 else 0
        
        return {
            "total_episodes": total_episodes,
            "total_danmaku": total_danmaku,
            "avg_danmaku_per_episode": round(avg_danmaku, 2)
        }


class CommentRepository(BaseRepository[Comment]):
    """弹幕Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Comment)
        self.enhanced_stats = EnhancedCommentStatistics(session)
        self.parser = DanmakuParamsParser()
    
    async def get_danmaku_by_episode(
        self, 
        episode_id: int, 
        limit: Optional[int] = None
    ) -> List[Comment]:
        """
        获取分集的所有弹幕
        
        Args:
            episode_id: 分集ID
            limit: 限制返回数量
            
        Returns:
            弹幕列表
        """
        stmt = select(Comment).where(
            Comment.episode_id == episode_id
        ).order_by(Comment.t.asc())
        
        if limit:
            stmt = stmt.limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_danmaku_by_time_range(
        self, 
        episode_id: int, 
        start_time: float, 
        end_time: float
    ) -> List[Comment]:
        """
        获取指定时间段的弹幕
        
        Args:
            episode_id: 分集ID
            start_time: 开始时间（秒）
            end_time: 结束时间（秒）
            
        Returns:
            时间段内的弹幕列表
        """
        stmt = select(Comment).where(
            and_(
                Comment.episode_id == episode_id,
                Comment.t >= start_time,
                Comment.t <= end_time
            )
        ).order_by(Comment.t.asc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_danmaku_by_content(
        self, 
        episode_id: int, 
        keyword: str
    ) -> List[Comment]:
        """
        根据内容搜索弹幕
        
        Args:
            episode_id: 分集ID
            keyword: 搜索关键词
            
        Returns:
            匹配的弹幕列表
        """
        search_term = f"%{keyword}%"
        
        stmt = select(Comment).where(
            and_(
                Comment.episode_id == episode_id,
                Comment.m.ilike(search_term)
            )
        ).order_by(Comment.t.asc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_danmaku_by_user(
        self, 
        user_hash: str, 
        limit: int = 100
    ) -> List[Comment]:
        """
        获取用户的弹幕（通过p字段中的用户哈希匹配）
        
        Args:
            user_hash: 用户哈希
            limit: 返回数量限制
            
        Returns:
            用户的弹幕列表
        """
        # 由于用户哈希在p字段中，需要使用LIKE查询
        # 格式通常为: "时间,模式,字号,颜色,用户ID,弹幕池,弹幕ID,用户哈希"
        stmt = select(Comment).where(
            Comment.p.like(f"%{user_hash}")
        ).options(
            selectinload(Comment.episode)
        ).order_by(
            Comment.id.desc()  # 使用ID排序，因为没有created_at字段
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_popular_danmaku(
        self, 
        episode_id: int, 
        limit: int = 50
    ) -> List[Comment]:
        """
        获取热门弹幕（根据时间聚集度和内容相似度）
        
        Args:
            episode_id: 分集ID
            limit: 返回数量限制
            
        Returns:
            热门弹幕列表
        """
        # 这里使用一个简单的启发式算法：
        # 1. 找出在相近时间点（±5秒）出现的弹幕
        # 2. 按密度排序
        
        stmt = text("""
            SELECT c1.*, COUNT(c2.id) as nearby_count
            FROM comment c1
            LEFT JOIN comment c2 ON c2.episode_id = c1.episode_id 
                AND c2.t BETWEEN c1.t - 5 AND c1.t + 5
                AND c2.id != c1.id
            WHERE c1.episode_id = :episode_id
            GROUP BY c1.id
            ORDER BY nearby_count DESC, c1.t ASC
            LIMIT :limit
        """)
        
        result = await self.session.execute(stmt, {
            "episode_id": episode_id,
            "limit": limit
        })
        
        # 将结果转换为Comment对象
        comment_ids = [row[0] for row in result.all()]  # 假设id是第一列
        
        if comment_ids:
            stmt = select(Comment).where(Comment.id.in_(comment_ids))
            comments_result = await self.session.execute(stmt)
            return list(comments_result.scalars().all())
        
        return []
    
    async def get_danmaku_statistics(
        self, 
        episode_id: int,
        use_enhanced: bool = True,
        use_view: bool = True
    ) -> Dict[str, Any]:
        """
        获取分集弹幕统计信息
        
        Args:
            episode_id: 分集ID
            use_enhanced: 是否使用增强统计（包含颜色、模式分布）
            use_view: 是否使用数据库视图（性能更好）
            
        Returns:
            包含统计数据的字典
        """
        # 基础统计
        total_count_stmt = select(func.count(Comment.id)).where(
            Comment.episode_id == episode_id
        )
        total_result = await self.session.execute(total_count_stmt)
        total_count = total_result.scalar() or 0
        
        # 平均时间偏移
        avg_time_stmt = select(func.avg(Comment.t)).where(
            Comment.episode_id == episode_id
        )
        avg_result = await self.session.execute(avg_time_stmt)
        avg_time = avg_result.scalar() or 0
        
        # 弹幕时间分布（每分钟弹幕数）
        time_distribution_stmt = select(
            func.floor(Comment.t / 60).label('minute'),
            func.count(Comment.id).label('count')
        ).where(
            Comment.episode_id == episode_id
        ).group_by(
            func.floor(Comment.t / 60)
        ).order_by('minute')
        
        distribution_result = await self.session.execute(time_distribution_stmt)
        time_distribution = dict(distribution_result.all())
        
        basic_stats = {
            "total_count": total_count,
            "average_time_offset": round(avg_time, 2),
            "time_distribution": time_distribution,  # 每分钟弹幕数
        }
        
        if use_enhanced:
            try:
                # 获取增强统计信息
                enhanced_stats = await self.enhanced_stats.get_comprehensive_statistics(
                    episode_id, use_view=use_view
                )
                
                # 合并统计结果
                basic_stats.update({
                    "color_distribution": enhanced_stats["color_distribution"],
                    "mode_distribution": enhanced_stats["mode_distribution"], 
                    "font_size_distribution": enhanced_stats["font_size_distribution"],
                    "statistics_method": enhanced_stats["method"]
                })
                
                if "sample_limit" in enhanced_stats:
                    basic_stats["sample_limit"] = enhanced_stats["sample_limit"]
                    
            except Exception as e:
                # 如果增强统计失败，添加空的分布数据
                basic_stats.update({
                    "color_distribution": {},
                    "mode_distribution": {},
                    "font_size_distribution": {},
                    "statistics_method": "basic_only",
                    "enhanced_error": str(e)
                })
        else:
            basic_stats.update({
                "color_distribution": {},
                "mode_distribution": {},
                "font_size_distribution": {},
                "statistics_method": "basic_only"
            })
        
        return basic_stats
    
    async def batch_create_danmaku(
        self, 
        episode_id: int, 
        danmaku_list: List[Dict[str, Any]]
    ) -> List[Comment]:
        """
        批量创建弹幕
        
        Args:
            episode_id: 分集ID
            danmaku_list: 弹幕数据列表
            
        Returns:
            创建的弹幕列表
        """
        # 为每条弹幕添加episode_id
        for danmaku in danmaku_list:
            danmaku['episode_id'] = episode_id
        
        return await self.create_many(danmaku_list)
    
    async def delete_danmaku_by_episode(self, episode_id: int) -> int:
        """
        删除分集的所有弹幕
        
        Args:
            episode_id: 分集ID
            
        Returns:
            删除的弹幕数量
        """
        return await self.update_many(
            {"episode_id": episode_id}, 
            **{}  # 这里实际应该是删除操作
        )
        # TODO: 实现真正的删除操作
    
    async def get_danmaku_export_data(
        self, 
        episode_id: int
    ) -> List[Dict[str, Any]]:
        """
        获取弹幕导出数据
        
        Args:
            episode_id: 分集ID
            
        Returns:
            弹幕导出数据列表
        """
        danmaku_list = await self.get_danmaku_by_episode(episode_id)
        
        export_data = []
        for danmaku in danmaku_list:
            # 使用便捷属性获取解析后的参数
            export_data.append({
                "time": float(danmaku.time_offset),
                "mode": danmaku.mode,
                "size": danmaku.font_size,
                "color": danmaku.color,
                "timestamp": danmaku.timestamp,
                "pool": 0,  # 弹幕池，一般为0
                "user_hash": danmaku.user_hash,
                "content": danmaku.content
            })
        
        return export_data
    
    async def import_danmaku_from_xml(
        self, 
        episode_id: int, 
        xml_data: str
    ) -> int:
        """
        从XML格式导入弹幕
        
        Args:
            episode_id: 分集ID
            xml_data: XML格式的弹幕数据
            
        Returns:
            导入的弹幕数量
        """
        # TODO: 实现XML解析和弹幕导入逻辑
        # 这里需要解析XML格式的弹幕文件（如B站、A站的弹幕格式）
        pass
    
    async def get_top_commenters(
        self, 
        episode_id: int, 
        limit: int = 10
    ) -> List[Tuple[str, int]]:
        """
        获取分集的top评论者（基于p字段中的用户哈希）
        
        Args:
            episode_id: 分集ID
            limit: 返回数量限制
            
        Returns:
            (user_hash, comment_count) 的元组列表
        """
        # 由于用户哈希在p字段中，需要使用复杂查询或在Python中处理
        # 这里提供一个简化实现，仅作示例
        comments = await self.get_danmaku_by_episode(episode_id)
        
        # 在Python中统计用户哈希
        user_stats = {}
        for comment in comments:
            user_hash = comment.user_hash
            if user_hash:
                user_stats[user_hash] = user_stats.get(user_hash, 0) + 1
        
        # 按评论数排序并限制数量
        sorted_users = sorted(user_stats.items(), key=lambda x: x[1], reverse=True)
        return sorted_users[:limit]
    
    async def get_danmaku_color_distribution(self, episode_id: int, use_view: bool = True) -> Dict[str, int]:
        """
        快捷方法：获取弹幕颜色分布
        
        Args:
            episode_id: 分集ID
            use_view: 是否使用数据库视图
            
        Returns:
            颜色分布字典 {颜色: 数量}
        """
        if use_view:
            return await self.enhanced_stats.get_color_distribution_via_view(episode_id)
        else:
            return await self.enhanced_stats.get_color_distribution_via_python(episode_id)
    
    async def get_danmaku_mode_distribution(self, episode_id: int, use_view: bool = True) -> Dict[str, int]:
        """
        快捷方法：获取弹幕模式分布
        
        Args:
            episode_id: 分集ID
            use_view: 是否使用数据库视图
            
        Returns:
            模式分布字典 {模式: 数量}
        """
        if use_view:
            return await self.enhanced_stats.get_mode_distribution_via_view(episode_id)
        else:
            return await self.enhanced_stats.get_mode_distribution_via_python(episode_id)
    
    async def get_parsed_danmaku(self, episode_id: int, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取解析后的弹幕数据
        
        Args:
            episode_id: 分集ID
            limit: 限制返回数量
            
        Returns:
            解析后的弹幕列表，包含所有参数
        """
        danmaku_list = await self.get_danmaku_by_episode(episode_id, limit)
        
        parsed_danmaku = []
        for danmaku in danmaku_list:
            params = self.parser.parse_params_string(danmaku.p)
            parsed_data = {
                "id": danmaku.id,
                "cid": danmaku.cid, 
                "time_offset": float(danmaku.t),
                "content": danmaku.m,
                "raw_params": danmaku.p,
                **params  # 展开解析后的参数
            }
            parsed_danmaku.append(parsed_data)
        
        return parsed_danmaku