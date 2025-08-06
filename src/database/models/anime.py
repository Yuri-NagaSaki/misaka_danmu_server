"""
番剧相关模型

包含：
- Anime: 番剧主表
- AnimeSource: 番剧数据源关联表
- AnimeMetadata: 番剧元数据表
- AnimeAlias: 番剧别名表
- TMDBEpisodeMapping: TMDB分集映射表
"""

import enum
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Integer, Enum, Text, Boolean, DECIMAL, 
    Index, ForeignKey, UniqueConstraint, BigInteger
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .episode import Episode


class AnimeType(enum.Enum):
    """番剧类型枚举"""
    TV_SERIES = "tv_series"
    MOVIE = "movie" 
    OVA = "ova"
    OTHER = "other"


class Anime(Base, IDMixin, TimestampMixin):
    """
    番剧主表
    
    对应原表：anime
    """
    __tablename__ = "anime"
    
    # 基本信息
    title: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="番剧标题"
    )
    type: Mapped[AnimeType] = mapped_column(
        Enum(AnimeType), 
        nullable=False, 
        default=AnimeType.TV_SERIES,
        comment="番剧类型"
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="封面图片URL"
    )
    season: Mapped[int] = mapped_column(
        Integer, 
        nullable=False, 
        default=1,
        comment="季度"
    )
    episode_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        comment="总集数"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="来源URL"
    )
    
    # 关系定义
    sources: Mapped[List["AnimeSource"]] = relationship(
        "AnimeSource", 
        back_populates="anime",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    anime_metadata: Mapped[Optional["AnimeMetadata"]] = relationship(
        "AnimeMetadata", 
        back_populates="anime",
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    aliases: Mapped[Optional["AnimeAlias"]] = relationship(
        "AnimeAlias",
        back_populates="anime", 
        cascade="all, delete-orphan",
        uselist=False,
        lazy="selectin"
    )
    
    # 索引定义
    __table_args__ = (
        # MySQL FULLTEXT索引（其他数据库会忽略）
        Index('idx_title_fulltext', 'title', mysql_prefix='FULLTEXT'),
        # 标题和季度的复合索引
        Index('idx_title_season', 'title', 'season'),
        # 类型索引
        Index('idx_type', 'type'),
        # 创建时间索引
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self) -> str:
        return f"<Anime(id={self.id}, title='{self.title}', type='{self.type.value}', season={self.season})>"


class AnimeSource(Base, IDMixin, TimestampMixin):
    """
    番剧数据源关联表
    
    对应原表：anime_sources
    """
    __tablename__ = "anime_sources"
    
    # 关联字段
    anime_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("anime.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联的番剧ID"
    )
    provider_name: Mapped[str] = mapped_column(
        String(50), 
        nullable=False,
        comment="数据源提供商名称"
    )
    media_id: Mapped[str] = mapped_column(
        String(255), 
        nullable=False,
        comment="在该数据源中的媒体ID"
    )
    is_favorited: Mapped[bool] = mapped_column(
        Boolean, 
        nullable=False, 
        default=False,
        comment="是否为精确匹配的数据源"
    )
    
    # 关系定义
    anime: Mapped["Anime"] = relationship("Anime", back_populates="sources")
    episodes: Mapped[List["Episode"]] = relationship(
        "Episode",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：同一个番剧不能有相同的数据源
        UniqueConstraint('anime_id', 'provider_name', 'media_id', name='idx_anime_provider_media_unique'),
        # 番剧ID索引
        Index('idx_anime_id', 'anime_id'),
        # 数据源提供商索引
        Index('idx_provider_name', 'provider_name'),
        # 精确匹配索引
        Index('idx_is_favorited', 'is_favorited'),
    )
    
    def __repr__(self) -> str:
        return f"<AnimeSource(id={self.id}, anime_id={self.anime_id}, provider='{self.provider_name}', media_id='{self.media_id}')>"


class AnimeMetadata(Base, IDMixin):
    """
    番剧元数据表
    
    对应原表：anime_metadata
    """
    __tablename__ = "anime_metadata"
    
    # 关联字段
    anime_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("anime.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联的番剧ID"
    )
    
    # 外部API的ID
    tmdb_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="TMDB ID"
    )
    tmdb_episode_group_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="TMDB 剧集组ID"
    )
    imdb_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="IMDb ID"
    )
    tvdb_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="TVDB ID"
    )
    douban_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="豆瓣ID"
    )
    bangumi_id: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="Bangumi ID"
    )
    
    # 关系定义
    anime: Mapped["Anime"] = relationship("Anime", back_populates="anime_metadata")
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：每个番剧只能有一条元数据记录
        UniqueConstraint('anime_id', name='idx_anime_id_unique'),
        # 外部ID索引
        Index('idx_tmdb_id', 'tmdb_id'),
        Index('idx_bangumi_id', 'bangumi_id'),
        Index('idx_imdb_id', 'imdb_id'),
    )
    
    def __repr__(self) -> str:
        return f"<AnimeMetadata(id={self.id}, anime_id={self.anime_id}, tmdb_id='{self.tmdb_id}')>"


class AnimeAlias(Base, IDMixin):
    """
    番剧别名表
    
    对应原表：anime_aliases
    """
    __tablename__ = "anime_aliases"
    
    # 关联字段
    anime_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("anime.id", ondelete="CASCADE"), 
        nullable=False,
        comment="关联的番剧ID"
    )
    
    # 不同语言的名称
    name_en: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="英文名称"
    )
    name_jp: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="日文名称"
    )
    name_romaji: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="罗马音名称"
    )
    
    # 中文别名
    alias_cn_1: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="中文别名1"
    )
    alias_cn_2: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="中文别名2"
    )
    alias_cn_3: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="中文别名3"
    )
    
    # 关系定义
    anime: Mapped["Anime"] = relationship("Anime", back_populates="aliases")
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：每个番剧只能有一条别名记录
        UniqueConstraint('anime_id', name='idx_anime_id_unique'),
    )
    
    def __repr__(self) -> str:
        return f"<AnimeAlias(id={self.id}, anime_id={self.anime_id}, name_en='{self.name_en}')>"


class TMDBEpisodeMapping(Base, IDMixin):
    """
    TMDB分集映射表
    
    对应原表：tmdb_episode_mapping
    """
    __tablename__ = "tmdb_episode_mapping"
    
    # TMDB相关字段
    tmdb_tv_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="TMDB电视剧ID"
    )
    tmdb_episode_group_id: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="TMDB剧集组ID"
    )
    tmdb_episode_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="TMDB分集ID"
    )
    tmdb_season_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="TMDB原始季度号"
    )
    tmdb_episode_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="TMDB原始分集号"
    )
    
    # 自定义映射字段
    custom_season_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="自定义季度号"
    )
    custom_episode_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="自定义分集号"
    )
    absolute_episode_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="绝对分集号"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：同一个剧集组中的TMDB分集ID唯一
        UniqueConstraint('tmdb_episode_group_id', 'tmdb_episode_id', name='idx_group_episode_unique'),
        # 复合索引：支持不同的查询模式
        Index('idx_custom_season_episode', 'tmdb_tv_id', 'tmdb_episode_group_id', 'custom_season_number', 'custom_episode_number'),
        Index('idx_absolute_episode', 'tmdb_tv_id', 'tmdb_episode_group_id', 'absolute_episode_number'),
        Index('idx_tmdb_tv_id', 'tmdb_tv_id'),
    )
    
    def __repr__(self) -> str:
        return f"<TMDBEpisodeMapping(id={self.id}, tmdb_tv_id={self.tmdb_tv_id}, group_id='{self.tmdb_episode_group_id}')>"