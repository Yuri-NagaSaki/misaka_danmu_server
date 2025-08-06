"""
番剧Repository

提供番剧相关的数据访问方法，包括番剧搜索、数据源管理、元数据操作等。
"""

from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, or_, and_, desc
from sqlalchemy.orm import selectinload, joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from .base import BaseRepository
from ..models.anime import Anime, AnimeSource, AnimeMetadata, AnimeAlias, TMDBEpisodeMapping, AnimeType


class AnimeRepository(BaseRepository[Anime]):
    """番剧Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, Anime)
    
    async def search_by_title(
        self, 
        title: str, 
        limit: int = 20, 
        exact_match: bool = False
    ) -> List[Anime]:
        """
        根据标题搜索番剧
        
        Args:
            title: 搜索标题
            limit: 返回数量限制
            exact_match: 是否精确匹配
            
        Returns:
            匹配的番剧列表
        """
        stmt = select(Anime).options(
            selectinload(Anime.sources),
            selectinload(Anime.anime_metadata),
            selectinload(Anime.aliases)
        )
        
        if exact_match:
            stmt = stmt.where(Anime.title == title)
        else:
            # 模糊搜索
            search_term = f"%{title}%"
            stmt = stmt.where(Anime.title.ilike(search_term))
        
        stmt = stmt.limit(limit).order_by(Anime.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def search_by_multiple_fields(
        self,
        title: Optional[str] = None,
        anime_type: Optional[AnimeType] = None,
        season: Optional[int] = None,
        limit: int = 20
    ) -> List[Anime]:
        """
        多字段搜索番剧
        
        Args:
            title: 标题关键词
            anime_type: 番剧类型
            season: 季度
            limit: 返回数量限制
            
        Returns:
            匹配的番剧列表
        """
        stmt = select(Anime).options(
            selectinload(Anime.sources),
            selectinload(Anime.anime_metadata)
        )
        
        conditions = []
        
        if title:
            conditions.append(Anime.title.ilike(f"%{title}%"))
        
        if anime_type:
            conditions.append(Anime.type == anime_type)
            
        if season:
            conditions.append(Anime.season == season)
        
        if conditions:
            stmt = stmt.where(and_(*conditions))
        
        stmt = stmt.limit(limit).order_by(Anime.created_at.desc())
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_with_full_details(self, anime_id: int) -> Optional[Anime]:
        """
        获取番剧的完整信息（包含所有关联数据）
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            包含完整信息的番剧对象
        """
        stmt = select(Anime).where(Anime.id == anime_id).options(
            selectinload(Anime.sources),
            selectinload(Anime.anime_metadata),
            selectinload(Anime.aliases)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_source(
        self, 
        provider_name: str, 
        media_id: str
    ) -> Optional[Anime]:
        """
        根据数据源信息获取番剧
        
        Args:
            provider_name: 数据源提供商
            media_id: 媒体ID
            
        Returns:
            找到的番剧或None
        """
        stmt = select(Anime).join(AnimeSource).where(
            and_(
                AnimeSource.provider_name == provider_name,
                AnimeSource.media_id == media_id
            )
        ).options(selectinload(Anime.sources))
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_recent_anime(self, days: int = 30, limit: int = 50) -> List[Anime]:
        """
        获取最近添加的番剧
        
        Args:
            days: 最近天数
            limit: 返回数量限制
            
        Returns:
            最近添加的番剧列表
        """
        from datetime import datetime, timedelta
        
        since_date = datetime.utcnow() - timedelta(days=days)
        
        stmt = select(Anime).where(
            Anime.created_at >= since_date
        ).options(
            selectinload(Anime.sources)
        ).order_by(
            Anime.created_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_anime_by_type(
        self, 
        anime_type: AnimeType, 
        limit: int = 50
    ) -> List[Anime]:
        """
        根据类型获取番剧列表
        
        Args:
            anime_type: 番剧类型
            limit: 返回数量限制
            
        Returns:
            指定类型的番剧列表
        """
        stmt = select(Anime).where(
            Anime.type == anime_type
        ).options(
            selectinload(Anime.sources)
        ).order_by(
            Anime.created_at.desc()
        ).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_anime_stats(self) -> Dict[str, Any]:
        """
        获取番剧统计信息
        
        Returns:
            包含各种统计数据的字典
        """
        # 总数统计
        total_count_stmt = select(func.count(Anime.id))
        total_result = await self.session.execute(total_count_stmt)
        total_count = total_result.scalar()
        
        # 按类型统计
        type_stats_stmt = select(
            Anime.type, 
            func.count(Anime.id)
        ).group_by(Anime.type)
        type_result = await self.session.execute(type_stats_stmt)
        type_stats = {str(type_enum.value): count for type_enum, count in type_result.all()}
        
        # 按季度统计
        season_stats_stmt = select(
            Anime.season,
            func.count(Anime.id)
        ).group_by(Anime.season).order_by(Anime.season)
        season_result = await self.session.execute(season_stats_stmt)
        season_stats = dict(season_result.all())
        
        return {
            "total_count": total_count,
            "by_type": type_stats,
            "by_season": season_stats
        }


class AnimeSourceRepository(BaseRepository[AnimeSource]):
    """番剧数据源Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AnimeSource)
    
    async def get_by_anime(self, anime_id: int) -> List[AnimeSource]:
        """
        获取番剧的所有数据源
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            数据源列表
        """
        return await self.get_many_by_field("anime_id", anime_id)
    
    async def get_favorited_sources(self, anime_id: int) -> List[AnimeSource]:
        """
        获取番剧的精确匹配数据源
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            精确匹配的数据源列表
        """
        stmt = select(AnimeSource).where(
            and_(
                AnimeSource.anime_id == anime_id,
                AnimeSource.is_favorited == True
            )
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_provider(self, provider_name: str) -> List[AnimeSource]:
        """
        获取特定提供商的所有数据源
        
        Args:
            provider_name: 提供商名称
            
        Returns:
            数据源列表
        """
        return await self.get_many_by_field("provider_name", provider_name)
    
    async def find_duplicate_sources(self) -> List[Tuple[str, str, int]]:
        """
        查找重复的数据源
        
        Returns:
            (provider_name, media_id, count) 的元组列表
        """
        stmt = select(
            AnimeSource.provider_name,
            AnimeSource.media_id,
            func.count(AnimeSource.id).label('count')
        ).group_by(
            AnimeSource.provider_name,
            AnimeSource.media_id
        ).having(
            func.count(AnimeSource.id) > 1
        )
        
        result = await self.session.execute(stmt)
        return list(result.all())


class AnimeMetadataRepository(BaseRepository[AnimeMetadata]):
    """番剧元数据Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AnimeMetadata)
    
    async def get_by_anime(self, anime_id: int) -> Optional[AnimeMetadata]:
        """
        获取番剧的元数据
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            元数据对象或None
        """
        return await self.get_by_field("anime_id", anime_id)
    
    async def get_by_external_id(
        self, 
        id_type: str, 
        external_id: str
    ) -> Optional[AnimeMetadata]:
        """
        根据外部ID获取元数据
        
        Args:
            id_type: ID类型 (tmdb, imdb, tvdb, douban, bangumi)
            external_id: 外部ID值
            
        Returns:
            元数据对象或None
        """
        field_map = {
            "tmdb": "tmdb_id",
            "imdb": "imdb_id", 
            "tvdb": "tvdb_id",
            "douban": "douban_id",
            "bangumi": "bangumi_id"
        }
        
        if id_type not in field_map:
            return None
            
        field_name = field_map[id_type]
        return await self.get_by_field(field_name, external_id)
    
    async def get_anime_with_metadata(
        self, 
        id_type: str, 
        external_id: str
    ) -> Optional[Anime]:
        """
        根据外部ID获取番剧及其元数据
        
        Args:
            id_type: ID类型
            external_id: 外部ID值
            
        Returns:
            番剧对象或None
        """
        field_map = {
            "tmdb": "tmdb_id",
            "imdb": "imdb_id",
            "tvdb": "tvdb_id", 
            "douban": "douban_id",
            "bangumi": "bangumi_id"
        }
        
        if id_type not in field_map:
            return None
            
        field_name = field_map[id_type]
        
        stmt = select(Anime).join(AnimeMetadata).where(
            getattr(AnimeMetadata, field_name) == external_id
        ).options(
            selectinload(Anime.anime_metadata),
            selectinload(Anime.sources)
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()


class AnimeAliasRepository(BaseRepository[AnimeAlias]):
    """番剧别名Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, AnimeAlias)
    
    async def get_by_anime(self, anime_id: int) -> Optional[AnimeAlias]:
        """
        获取番剧的别名信息
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            别名对象或None
        """
        return await self.get_by_field("anime_id", anime_id)
    
    async def search_by_alias(self, alias: str) -> List[Anime]:
        """
        根据别名搜索番剧
        
        Args:
            alias: 别名关键词
            
        Returns:
            匹配的番剧列表
        """
        search_term = f"%{alias}%"
        
        stmt = select(Anime).join(AnimeAlias).where(
            or_(
                AnimeAlias.name_en.ilike(search_term),
                AnimeAlias.name_jp.ilike(search_term),
                AnimeAlias.name_romaji.ilike(search_term),
                AnimeAlias.alias_cn_1.ilike(search_term),
                AnimeAlias.alias_cn_2.ilike(search_term),
                AnimeAlias.alias_cn_3.ilike(search_term)
            )
        ).options(
            selectinload(Anime.aliases),
            selectinload(Anime.sources)
        )
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())


class TMDBEpisodeMappingRepository(BaseRepository[TMDBEpisodeMapping]):
    """TMDB分集映射Repository"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session, TMDBEpisodeMapping)
    
    async def get_by_tmdb_tv_id(self, tmdb_tv_id: int) -> List[TMDBEpisodeMapping]:
        """
        获取TMDB电视剧的所有分集映射
        
        Args:
            tmdb_tv_id: TMDB电视剧ID
            
        Returns:
            分集映射列表
        """
        return await self.get_many_by_field("tmdb_tv_id", tmdb_tv_id)
    
    async def get_by_episode_group(self, episode_group_id: str) -> List[TMDBEpisodeMapping]:
        """
        获取剧集组的所有分集映射
        
        Args:
            episode_group_id: 剧集组ID
            
        Returns:
            分集映射列表
        """
        return await self.get_many_by_field("tmdb_episode_group_id", episode_group_id)
    
    async def get_episode_mapping(
        self, 
        tmdb_tv_id: int,
        episode_group_id: str,
        season_number: int,
        episode_number: int
    ) -> Optional[TMDBEpisodeMapping]:
        """
        获取特定分集的映射信息
        
        Args:
            tmdb_tv_id: TMDB电视剧ID
            episode_group_id: 剧集组ID
            season_number: 季度号
            episode_number: 分集号
            
        Returns:
            分集映射对象或None
        """
        stmt = select(TMDBEpisodeMapping).where(
            and_(
                TMDBEpisodeMapping.tmdb_tv_id == tmdb_tv_id,
                TMDBEpisodeMapping.tmdb_episode_group_id == episode_group_id,
                TMDBEpisodeMapping.custom_season_number == season_number,
                TMDBEpisodeMapping.custom_episode_number == episode_number
            )
        )
        
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()