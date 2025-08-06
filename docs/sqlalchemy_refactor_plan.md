# SQLAlchemy 2.0 重构规划文档

## 重构概览

### 目标
将当前基于aiomysql的原生SQL实现迁移到SQLAlchemy 2.0 ORM，实现：
1. **多数据库支持** - MySQL, PostgreSQL, SQLite等
2. **类型安全** - 完整的类型提示支持
3. **维护性** - 更好的代码组织和可读性
4. **兼容性** - 保持现有API接口不变
5. **性能优化** - 利用SQLAlchemy 2.0的性能改进

### 技术栈选择

**核心ORM:**
- SQLAlchemy 2.0 (最新版本，异步支持)
- Alembic (数据库迁移工具)

**数据库驱动:**
- asyncpg (PostgreSQL)
- aiomysql (MySQL，保持现有)
- aiosqlite (SQLite，开发/测试用)

**新增依赖:**
```toml
dependencies = [
    # 现有依赖...
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.12.0", 
    "asyncpg>=0.28.0",
    "aiosqlite>=0.19.0",
]
```

## 项目结构重构

### 新增目录结构
```
src/
├── database/
│   ├── __init__.py          # 数据库初始化
│   ├── engine.py            # 数据库引擎配置
│   ├── models/              # ORM模型
│   │   ├── __init__.py
│   │   ├── base.py          # Base模型类
│   │   ├── anime.py         # 番剧相关模型
│   │   ├── user.py          # 用户相关模型
│   │   ├── system.py        # 系统配置模型
│   │   └── cache.py         # 缓存模型
│   ├── repositories/        # 数据访问层
│   │   ├── __init__.py
│   │   ├── base.py          # 基础Repository
│   │   ├── anime.py         # 番剧Repository
│   │   ├── user.py          # 用户Repository
│   │   └── system.py        # 系统Repository
│   └── migrations/          # Alembic迁移文件
│       ├── env.py
│       ├── script.py.mako
│       └── versions/
├── services/                # 业务服务层
│   ├── __init__.py
│   ├── anime_service.py
│   ├── user_service.py
│   └── external_api_service.py
└── legacy/                  # 保留原有代码
    ├── crud.py              # 重命名保留
    └── database.py          # 重命名保留
```

## 阶段性迁移计划

### Phase 1: 基础架构搭建 (第1周)

#### 1.1 依赖更新
```toml
# pyproject.toml 更新
[project]
dependencies = [
    # 现有依赖保持不变
    "sqlalchemy[asyncio]>=2.0.0",
    "alembic>=1.12.0",
    "asyncpg>=0.28.0", 
    "aiosqlite>=0.19.0",
]
```

#### 1.2 数据库引擎配置
```python
# src/database/engine.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool
from typing import AsyncGenerator

class DatabaseEngine:
    def __init__(self, database_url: str):
        self.engine = create_async_engine(
            database_url,
            echo=False,  # 生产环境关闭SQL日志
            pool_pre_ping=True,
            poolclass=NullPool if "sqlite" in database_url else None,
        )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
    
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
```

#### 1.3 配置系统更新
```python
# src/config.py 更新
class DatabaseConfig(BaseModel):
    # 新增数据库类型字段
    type: str = "mysql"  # mysql, postgresql, sqlite
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root" 
    password: str = "password"
    name: str = "danmaku_db"
    
    @property
    def url(self) -> str:
        """构建数据库URL"""
        if self.type == "mysql":
            return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        elif self.type == "postgresql":
            return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        elif self.type == "sqlite":
            return f"sqlite+aiosqlite:///{self.name}.db"
        else:
            raise ValueError(f"Unsupported database type: {self.type}")
```

### Phase 2: 核心模型定义 (第2周)

#### 2.1 基础模型类
```python
# src/database/models/base.py
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import BigInteger, DateTime, func
from datetime import datetime
from typing import Optional

class Base(AsyncAttrs, DeclarativeBase):
    """所有模型的基类"""
    pass

class TimestampMixin:
    """时间戳混入类"""
    created_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime, 
        server_default=func.now()
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )

class IDMixin:
    """ID混入类"""
    id: Mapped[int] = mapped_column(
        BigInteger, 
        primary_key=True, 
        autoincrement=True
    )
```

#### 2.2 核心业务模型
```python
# src/database/models/anime.py
from sqlalchemy import String, Integer, Enum, Text, Boolean, DECIMAL, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from typing import List, Optional
import enum

class AnimeType(enum.Enum):
    TV_SERIES = "tv_series"
    MOVIE = "movie"
    OVA = "ova"
    OTHER = "other"

class Anime(Base, IDMixin, TimestampMixin):
    __tablename__ = "anime"
    
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[AnimeType] = mapped_column(
        Enum(AnimeType), 
        nullable=False, 
        default=AnimeType.TV_SERIES
    )
    image_url: Mapped[Optional[str]] = mapped_column(String(512))
    season: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    episode_count: Mapped[Optional[int]] = mapped_column(Integer)
    source_url: Mapped[Optional[str]] = mapped_column(String(512))
    
    # 关系定义
    sources: Mapped[List["AnimeSource"]] = relationship(
        "AnimeSource", 
        back_populates="anime",
        cascade="all, delete-orphan"
    )
    metadata: Mapped[Optional["AnimeMetadata"]] = relationship(
        "AnimeMetadata", 
        back_populates="anime",
        cascade="all, delete-orphan",
        uselist=False
    )
    aliases: Mapped[Optional["AnimeAlias"]] = relationship(
        "AnimeAlias",
        back_populates="anime", 
        cascade="all, delete-orphan",
        uselist=False
    )
    
    # 索引定义
    __table_args__ = (
        Index('idx_title_fulltext', 'title', mysql_prefix='FULLTEXT'),
    )

class AnimeSource(Base, IDMixin, TimestampMixin):
    __tablename__ = "anime_sources"
    
    anime_id: Mapped[int] = mapped_column(
        BigInteger, 
        ForeignKey("anime.id", ondelete="CASCADE"), 
        nullable=False
    )
    provider_name: Mapped[str] = mapped_column(String(50), nullable=False)
    media_id: Mapped[str] = mapped_column(String(255), nullable=False)
    is_favorited: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    
    # 关系定义
    anime: Mapped["Anime"] = relationship("Anime", back_populates="sources")
    episodes: Mapped[List["Episode"]] = relationship(
        "Episode",
        back_populates="source",
        cascade="all, delete-orphan"
    )
    
    # 约束定义
    __table_args__ = (
        Index('idx_anime_provider_media_unique', 'anime_id', 'provider_name', 'media_id', unique=True),
    )
```

### Phase 3: Repository模式实现 (第3周)

#### 3.1 基础Repository
```python
# src/database/repositories/base.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update
from sqlalchemy.orm import selectinload
from typing import TypeVar, Generic, List, Optional, Any, Dict
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseRepository(Generic[T], ABC):
    """基础Repository类"""
    
    def __init__(self, session: AsyncSession, model_class: type[T]):
        self.session = session
        self.model_class = model_class
    
    async def get_by_id(self, id: int) -> Optional[T]:
        """通过ID获取单个对象"""
        result = await self.session.execute(
            select(self.model_class).where(self.model_class.id == id)
        )
        return result.scalar_one_or_none()
    
    async def get_all(self, limit: Optional[int] = None) -> List[T]:
        """获取所有对象"""
        query = select(self.model_class)
        if limit:
            query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def create(self, **kwargs) -> T:
        """创建新对象"""
        obj = self.model_class(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        return obj
    
    async def update(self, id: int, **kwargs) -> Optional[T]:
        """更新对象"""
        await self.session.execute(
            update(self.model_class)
            .where(self.model_class.id == id)
            .values(**kwargs)
        )
        return await self.get_by_id(id)
    
    async def delete(self, id: int) -> bool:
        """删除对象"""
        result = await self.session.execute(
            delete(self.model_class).where(self.model_class.id == id)
        )
        return result.rowcount > 0
```

#### 3.2 专业Repository
```python
# src/database/repositories/anime.py
from sqlalchemy import select, func, or_, and_
from sqlalchemy.orm import selectinload, joinedload
from typing import List, Optional
from ..models.anime import Anime, AnimeSource, Episode
from .base import BaseRepository

class AnimeRepository(BaseRepository[Anime]):
    """番剧Repository"""
    
    async def search_by_title(self, keyword: str) -> List[Anime]:
        """通过标题搜索番剧（FULLTEXT + LIKE回退）"""
        # 先尝试FULLTEXT搜索
        sanitized_keyword = self._sanitize_fulltext_keyword(keyword)
        if sanitized_keyword:
            result = await self.session.execute(
                select(Anime)
                .where(func.match(Anime.title).against(f"{sanitized_keyword}*", mysql_boolean=True))
                .options(selectinload(Anime.metadata))
            )
            animes = list(result.scalars().all())
            if animes:
                return animes
        
        # 回退到LIKE搜索
        normalized_title = f"%{keyword.replace('：', ':').replace(' ', '')}%"
        result = await self.session.execute(
            select(Anime)
            .join(Anime.aliases, isouter=True)
            .where(or_(
                func.replace(func.replace(Anime.title, '：', ':'), ' ', '').like(normalized_title),
                func.replace(func.replace(Anime.aliases.name_en, '：', ':'), ' ', '').like(normalized_title),
                # 更多别名字段...
            ))
            .options(selectinload(Anime.metadata))
        )
        return list(result.scalars().all())
    
    async def get_with_sources_and_episodes(self, anime_id: int) -> Optional[Anime]:
        """获取包含数据源和分集的完整番剧信息"""
        result = await self.session.execute(
            select(Anime)
            .where(Anime.id == anime_id)
            .options(
                selectinload(Anime.sources).selectinload(AnimeSource.episodes),
                selectinload(Anime.metadata),
                selectinload(Anime.aliases)
            )
        )
        return result.scalar_one_or_none()
    
    async def get_library_stats(self) -> List[dict]:
        """获取媒体库统计信息"""
        result = await self.session.execute(
            select(
                Anime.id.label('animeId'),
                Anime.title,
                Anime.type,
                Anime.image_url.label('imageUrl'),
                Anime.created_at.label('createdAt'),
                func.coalesce(
                    Anime.episode_count,
                    func.count(Episode.id.distinct())
                ).label('episodeCount'),
                func.count(AnimeSource.id.distinct()).label('sourceCount')
            )
            .select_from(Anime)
            .join(AnimeSource, Anime.id == AnimeSource.anime_id, isouter=True)
            .join(Episode, AnimeSource.id == Episode.source_id, isouter=True)
            .group_by(Anime.id)
            .order_by(Anime.created_at.desc())
        )
        return [dict(row._mapping) for row in result.all()]
    
    def _sanitize_fulltext_keyword(self, keyword: str) -> Optional[str]:
        """清理FULLTEXT搜索关键词"""
        import re
        sanitized = re.sub(r'[+\-><()~*@"]', ' ', keyword).strip()
        return sanitized if sanitized else None
```

### Phase 4: 服务层重构 (第4周)

#### 4.1 业务服务层
```python
# src/services/anime_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict, Any
from ..database.repositories.anime import AnimeRepository
from ..database.models.anime import Anime, AnimeSource, Episode
from .. import models

class AnimeService:
    """番剧业务服务"""
    
    def __init__(self, session: AsyncSession):
        self.session = session
        self.anime_repo = AnimeRepository(session, Anime)
    
    async def get_library_anime(self) -> List[Dict[str, Any]]:
        """获取媒体库中的所有番剧"""
        return await self.anime_repo.get_library_stats()
    
    async def search_anime(self, keyword: str) -> List[models.AnimeInfo]:
        """搜索番剧并转换为API模型"""
        animes = await self.anime_repo.search_by_title(keyword)
        return [
            models.AnimeInfo(
                animeId=anime.id,
                animeTitle=anime.title,
                type=anime.type.value,
                rating=0,
                imageUrl=anime.image_url
            )
            for anime in animes
        ]
    
    async def import_anime_from_provider(
        self, 
        import_request: models.ImportRequest
    ) -> int:
        """从外部数据源导入番剧"""
        # 获取或创建番剧
        anime = await self._get_or_create_anime(
            import_request.anime_title,
            import_request.type,
            import_request.season,
            import_request.image_url
        )
        
        # 链接数据源
        source = await self._link_source_to_anime(
            anime.id,
            import_request.provider,
            import_request.media_id
        )
        
        return anime.id
    
    async def _get_or_create_anime(
        self,
        title: str,
        media_type: str,
        season: int,
        image_url: Optional[str]
    ) -> Anime:
        """获取或创建番剧（事务内处理）"""
        # 尝试查找现有番剧
        existing = await self.session.execute(
            select(Anime).where(
                and_(Anime.title == title, Anime.season == season)
            )
        )
        anime = existing.scalar_one_or_none()
        
        if anime:
            # 如果存在但缺少图片，更新图片
            if not anime.image_url and image_url:
                anime.image_url = image_url
                await self.session.flush()
            return anime
        
        # 创建新番剧及关联表
        anime = Anime(
            title=title,
            type=AnimeType(media_type),
            season=season,
            image_url=image_url
        )
        self.session.add(anime)
        await self.session.flush()  # 获取ID
        
        # 创建关联的元数据和别名表
        from ..database.models.anime import AnimeMetadata, AnimeAlias
        
        metadata = AnimeMetadata(anime_id=anime.id)
        alias = AnimeAlias(anime_id=anime.id)
        
        self.session.add(metadata)
        self.session.add(alias)
        
        return anime
```

### Phase 5: 迁移工具实现 (第5周)

#### 5.1 Alembic配置
```python
# alembic/env.py
from sqlalchemy import engine_from_config, pool
from sqlalchemy.ext.asyncio import AsyncEngine
from alembic import context
from src.database.models import Base
from src.config import settings

# Alembic配置
config = context.config
config.set_main_option('sqlalchemy.url', settings.database.url)
target_metadata = Base.metadata

async def run_migrations_online():
    """异步迁移运行器"""
    connectable = AsyncEngine(
        engine_from_config(
            config.get_section(config.config_ini_section),
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()
```

#### 5.2 数据迁移脚本
```python
# src/migration_tools/data_migrator.py
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, List
from ..database.engine import DatabaseEngine
from ..legacy import crud as legacy_crud

class DataMigrator:
    """数据迁移工具"""
    
    def __init__(self, legacy_pool, new_engine: DatabaseEngine):
        self.legacy_pool = legacy_pool
        self.new_engine = new_engine
    
    async def migrate_all_data(self):
        """迁移所有数据"""
        print("开始数据迁移...")
        
        async with self.new_engine.get_session() as session:
            # 按依赖顺序迁移
            await self._migrate_anime(session)
            await self._migrate_anime_metadata(session) 
            await self._migrate_anime_aliases(session)
            await self._migrate_anime_sources(session)
            await self._migrate_episodes(session)
            await self._migrate_comments(session)
            await self._migrate_users(session)
            await self._migrate_system_data(session)
            
        print("数据迁移完成!")
    
    async def _migrate_anime(self, session: AsyncSession):
        """迁移番剧数据"""
        print("迁移番剧数据...")
        
        # 从旧系统获取数据
        old_animes = await legacy_crud.get_all_anime(self.legacy_pool)
        
        from ..database.models.anime import Anime
        
        for old_anime in old_animes:
            anime = Anime(
                id=old_anime['id'],
                title=old_anime['title'],
                type=old_anime['type'],
                image_url=old_anime.get('image_url'),
                season=old_anime.get('season', 1),
                episode_count=old_anime.get('episode_count'),
                source_url=old_anime.get('source_url'),
                created_at=old_anime.get('created_at')
            )
            session.add(anime)
        
        await session.flush()
        print(f"迁移了 {len(old_animes)} 个番剧")
    
    async def verify_migration(self) -> Dict[str, Any]:
        """验证迁移结果"""
        print("验证迁移结果...")
        
        # 统计新系统数据
        async with self.new_engine.get_session() as session:
            from ..database.models.anime import Anime, AnimeSource, Episode, Comment
            
            anime_count = await session.scalar(select(func.count(Anime.id)))
            source_count = await session.scalar(select(func.count(AnimeSource.id))) 
            episode_count = await session.scalar(select(func.count(Episode.id)))
            comment_count = await session.scalar(select(func.count(Comment.id)))
        
        # 统计旧系统数据
        old_anime_count = len(await legacy_crud.get_all_anime(self.legacy_pool))
        # ... 其他统计
        
        return {
            "anime": {"old": old_anime_count, "new": anime_count},
            "sources": {"old": old_source_count, "new": source_count},
            "episodes": {"old": old_episode_count, "new": episode_count}, 
            "comments": {"old": old_comment_count, "new": comment_count},
        }
```

### Phase 6: API层适配 (第6周)

#### 6.1 依赖注入更新
```python
# src/database/__init__.py
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from .engine import DatabaseEngine
from ..config import settings

# 全局数据库引擎
db_engine = DatabaseEngine(settings.database.url)

async def get_db_session() -> AsyncSession:
    """FastAPI依赖注入：获取数据库会话"""
    async with db_engine.get_session() as session:
        yield session
```

#### 6.2 API路由更新
```python
# src/dandan_api.py 更新示例
from sqlalchemy.ext.asyncio import AsyncSession
from .database import get_db_session
from .services.anime_service import AnimeService

@router.get("/search/anime")
async def search_anime(
    keyword: str = Query(...),
    session: AsyncSession = Depends(get_db_session)
):
    service = AnimeService(session)
    animes = await service.search_anime(keyword)
    return models.AnimeSearchResponse(animes=animes)

@router.get("/match")
async def match_episode(
    fileName: str = Query(...),
    session: AsyncSession = Depends(get_db_session)
):
    service = AnimeService(session)
    matches = await service.match_episodes(fileName)
    return models.MatchResponse(
        isMatched=len(matches) > 0,
        matches=matches
    )
```

## 兼容性策略

### 1. 渐进式迁移
- 新旧系统并行运行
- 按模块逐步切换
- 保留原有API接口

### 2. 数据一致性保证
- 事务性迁移
- 数据校验和比对
- 回滚机制

### 3. 性能对比测试
- 基准测试框架
- 关键查询性能对比
- 内存使用监控

## 测试策略

### 1. 单元测试
```python
# tests/test_repositories/test_anime_repository.py
import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.models.anime import Anime
from src.database.repositories.anime import AnimeRepository

@pytest.mark.asyncio
async def test_search_by_title(db_session: AsyncSession):
    repo = AnimeRepository(db_session, Anime)
    
    # 创建测试数据
    anime = await repo.create(
        title="测试番剧",
        type="tv_series",
        season=1
    )
    
    # 测试搜索
    results = await repo.search_by_title("测试")
    assert len(results) == 1
    assert results[0].title == "测试番剧"
```

### 2. 集成测试
```python
# tests/test_services/test_anime_service.py
@pytest.mark.asyncio
async def test_import_anime_flow(db_session: AsyncSession):
    service = AnimeService(db_session)
    
    import_request = models.ImportRequest(
        provider="bilibili",
        media_id="123456",
        anime_title="新番剧",
        type="tv_series"
    )
    
    anime_id = await service.import_anime_from_provider(import_request)
    assert anime_id > 0
    
    # 验证数据创建
    anime = await service.anime_repo.get_by_id(anime_id)
    assert anime.title == "新番剧"
```

## 部署和运维

### 1. 配置管理
```python
# 环境变量支持多种数据库
DANMUAPI_DATABASE__TYPE=postgresql
DANMUAPI_DATABASE__HOST=localhost
DANMUAPI_DATABASE__PORT=5432
DANMUAPI_DATABASE__USER=danmu_user
DANMUAPI_DATABASE__PASSWORD=secure_password
DANMUAPI_DATABASE__NAME=danmu_db
```

### 2. 监控指标
- 查询性能监控
- 连接池状态监控  
- 事务成功率监控
- 数据一致性检查

### 3. 备份策略
- 迁移前完整备份
- 增量备份机制
- 跨数据库备份验证

## 风险评估和缓解

### 1. 技术风险
**风险**: SQLAlchemy学习曲线
**缓解**: 分阶段培训，代码审查，文档完善

**风险**: 性能回归
**缓解**: 基准测试，性能监控，查询优化

### 2. 业务风险  
**风险**: 数据丢失
**缓解**: 完整备份，事务迁移，验证机制

**风险**: 服务中断
**缓解**: 灰度发布，快速回滚，监控告警

### 3. 运维风险
**风险**: 多数据库运维复杂度
**缓解**: 容器化部署，自动化脚本，标准化配置

## 成功指标

### 1. 功能指标
- [ ] 所有现有API功能正常
- [ ] 数据完整性100%
- [ ] 多数据库支持验证

### 2. 性能指标
- [ ] 查询性能≥当前水平
- [ ] 内存使用≤当前水平  
- [ ] 启动时间≤当前水平

### 3. 质量指标
- [ ] 代码覆盖率>80%
- [ ] 类型检查通过率100%
- [ ] 文档完整度100%

## 时间线总结

| 阶段 | 时间 | 主要任务 | 交付物 |
|------|------|---------|--------|
| Phase 1 | 第1周 | 基础架构搭建 | 数据库引擎、配置更新 |
| Phase 2 | 第2周 | 核心模型定义 | SQLAlchemy模型 |
| Phase 3 | 第3周 | Repository实现 | 数据访问层 |
| Phase 4 | 第4周 | 服务层重构 | 业务逻辑层 |
| Phase 5 | 第5周 | 迁移工具 | 数据迁移脚本 |
| Phase 6 | 第6周 | API层适配 | 完整系统集成 |

**总计**: 6周完成完整重构，第7-8周进行测试和优化。