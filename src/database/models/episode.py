"""
分集和弹幕相关模型

包含：
- Episode: 分集表
- Comment: 弹幕评论表
"""

from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from decimal import Decimal
from sqlalchemy import (
    String, Integer, Text, DECIMAL, BigInteger,
    Index, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, IDMixin, TimestampMixin

if TYPE_CHECKING:
    from .anime import AnimeSource


class Episode(Base, IDMixin, TimestampMixin):
    """
    分集表
    
    对应原表：episode
    """
    __tablename__ = "episode"
    
    # 关联字段
    source_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("anime_sources.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的数据源ID"
    )
    
    # 分集信息
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="分集标题"
    )
    episode_index: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="分集序号"
    )
    provider_episode_id: Mapped[Optional[str]] = mapped_column(
        String(255),
        comment="数据源中的分集ID"
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        comment="分集源URL"
    )
    fetched_at: Mapped[Optional[datetime]] = mapped_column(
        comment="获取时间"
    )
    comment_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="弹幕数量"
    )
    
    # 关系定义
    source: Mapped["AnimeSource"] = relationship(
        "AnimeSource", 
        back_populates="episodes"
    )
    comments: Mapped[List["Comment"]] = relationship(
        "Comment",
        back_populates="episode",
        cascade="all, delete-orphan"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：同一个数据源中的分集序号唯一
        UniqueConstraint('source_id', 'episode_index', name='idx_source_episode_unique'),
        # 数据源ID索引
        Index('idx_source_id', 'source_id'),
        # 获取时间索引
        Index('idx_fetched_at', 'fetched_at'),
        # 弹幕数量索引
        Index('idx_comment_count', 'comment_count'),
    )
    
    def __repr__(self) -> str:
        return f"<Episode(id={self.id}, source_id={self.source_id}, title='{self.title}', episode_index={self.episode_index})>"


class Comment(Base, IDMixin):
    """
    弹幕评论表
    
    对应原表：comment
    """
    __tablename__ = "comment"
    
    # 关联字段
    episode_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("episode.id", ondelete="CASCADE"),
        nullable=False,
        comment="关联的分集ID"
    )
    
    # 弹幕数据
    cid: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="弹幕唯一标识符"
    )
    p: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="弹幕参数（时间,模式,颜色,用户等）"
    )
    m: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="弹幕内容"
    )
    t: Mapped[Decimal] = mapped_column(
        DECIMAL(10, 2),
        nullable=False,
        comment="弹幕出现时间（秒）"
    )
    
    # 关系定义
    episode: Mapped["Episode"] = relationship(
        "Episode", 
        back_populates="comments"
    )
    
    # 约束和索引
    __table_args__ = (
        # 唯一约束：同一个分集中的弹幕CID唯一（防止重复弹幕）
        UniqueConstraint('episode_id', 'cid', name='idx_episode_cid_unique'),
        # 复合索引：分集ID + 时间（用于按时间顺序获取弹幕）
        Index('idx_episode_time', 'episode_id', 't'),
        # 分集ID索引
        Index('idx_episode_id', 'episode_id'),
        # 时间索引
        Index('idx_time', 't'),
    )
    
    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, episode_id={self.episode_id}, cid='{self.cid}', t={self.t})>"
    
    # 便捷属性，提供更有意义的字段名
    @property
    def time_offset(self) -> Decimal:
        """弹幕出现时间（秒）"""
        return self.t
    
    @property
    def content(self) -> str:
        """弹幕内容"""
        return self.m
    
    @property
    def params(self) -> str:
        """弹幕参数字符串"""
        return self.p
    
    def parse_params(self) -> dict:
        """
        解析弹幕参数
        
        Returns:
            包含弹幕参数的字典
        """
        # 解析格式通常为: "时间,模式,字号,颜色,用户ID,弹幕池,弹幕ID,用户哈希"
        parts = self.p.split(',')
        if len(parts) >= 8:
            return {
                'time': float(parts[0]),
                'mode': int(parts[1]),  # 1-从右至左滚动 4-底端固定 5-顶端固定 
                'font_size': int(parts[2]), # 字号
                'color': int(parts[3]), # 颜色
                'timestamp': int(parts[4]), # 发送时间戳
                'pool': int(parts[5]), # 弹幕池
                'user_id': parts[6], # 用户ID
                'user_hash': parts[7] if len(parts) > 7 else '', # 用户哈希
            }
        return {}
    
    @property  
    def mode(self) -> int:
        """弹幕模式"""
        params = self.parse_params()
        return params.get('mode', 1)
    
    @property
    def color(self) -> int:
        """弹幕颜色"""
        params = self.parse_params()
        return params.get('color', 16777215)  # 默认白色
        
    @property
    def font_size(self) -> int:
        """弹幕字号"""
        params = self.parse_params()
        return params.get('font_size', 25)
    
    @property
    def timestamp(self) -> int:
        """弹幕发送时间戳"""
        params = self.parse_params()
        return params.get('timestamp', 0)
    
    @property  
    def user_hash(self) -> str:
        """用户哈希"""
        params = self.parse_params()
        return params.get('user_hash', '')