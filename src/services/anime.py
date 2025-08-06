"""
番剧业务服务

提供番剧相关的业务逻辑，包括番剧管理、数据源管理、元数据管理等复杂操作。
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime
import asyncio

from .base import BaseService, ServiceResult, ServiceError, ValidationError, BusinessLogicError, service_operation
from ..database.models.anime import Anime, AnimeSource, AnimeMetadata, AnimeAlias, AnimeType
from ..database.repositories.factory import RepositoryFactory


class AnimeService(BaseService):
    """番剧业务服务"""
    
    def __init__(self, repository_factory: RepositoryFactory):
        super().__init__(repository_factory)
        self.metrics = None  # 可选的指标收集
    
    @service_operation("search_anime")
    async def search_anime(
        self, 
        query: str,
        anime_type: Optional[AnimeType] = None,
        season: Optional[int] = None,
        limit: int = 20,
        include_aliases: bool = True
    ) -> ServiceResult[List[Dict[str, Any]]]:
        """
        搜索番剧（支持多种搜索策略）
        
        Args:
            query: 搜索关键词
            anime_type: 番剧类型过滤
            season: 季度过滤
            limit: 返回数量限制
            include_aliases: 是否包含别名搜索
            
        Returns:
            搜索结果
        """
        try:
            # 验证参数
            if not query or not query.strip():
                return ServiceResult.validation_error("搜索关键词不能为空", "query")
            
            query = self._sanitize_search_query(query)
            if len(query) < 2:
                return ServiceResult.validation_error("搜索关键词至少需要2个字符", "query")
            
            if limit < 1 or limit > 100:
                return ServiceResult.validation_error("查询数量限制应在1-100之间", "limit")
            
            # 多策略搜索
            search_results = []
            
            # 1. 精确标题匹配
            exact_matches = await self.repos.anime.search_by_title(
                query, limit=min(limit, 10), exact_match=True
            )
            search_results.extend(exact_matches)
            
            # 2. 模糊标题匹配
            if len(search_results) < limit:
                fuzzy_matches = await self.repos.anime.search_by_title(
                    query, limit=limit - len(search_results), exact_match=False
                )
                # 去除重复
                existing_ids = {anime.id for anime in search_results}
                search_results.extend([anime for anime in fuzzy_matches if anime.id not in existing_ids])
            
            # 3. 别名搜索
            if include_aliases and len(search_results) < limit:
                alias_matches = await self.repos.anime_alias.search_by_alias(query)
                existing_ids = {anime.id for anime in search_results}
                search_results.extend([anime for anime in alias_matches if anime.id not in existing_ids])
            
            # 4. 多字段过滤
            if (anime_type or season) and len(search_results) < limit:
                filtered_matches = await self.repos.anime.search_by_multiple_fields(
                    title=query,
                    anime_type=anime_type,
                    season=season,
                    limit=limit - len(search_results)
                )
                existing_ids = {anime.id for anime in search_results}
                search_results.extend([anime for anime in filtered_matches if anime.id not in existing_ids])
            
            # 限制最终结果数量
            search_results = search_results[:limit]
            
            # 转换为字典格式
            result_data = []
            for anime in search_results:
                anime_dict = {
                    "id": anime.id,
                    "title": anime.title,
                    "type": anime.type.value,
                    "season": anime.season,
                    "episode_count": anime.episode_count,
                    "image_url": anime.image_url,
                    "source_url": anime.source_url,
                    "created_at": anime.created_at.isoformat() if anime.created_at else None,
                    "sources_count": len(anime.sources) if hasattr(anime, 'sources') else 0,
                    "has_metadata": bool(anime.anime_metadata) if hasattr(anime, 'anime_metadata') else False
                }
                result_data.append(anime_dict)
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"找到 {len(result_data)} 个匹配结果"
            )
            
        except Exception as e:
            return await self._handle_service_error("search_anime", e)
    
    @service_operation("get_anime_details")
    async def get_anime_details(self, anime_id: int) -> ServiceResult[Dict[str, Any]]:
        """
        获取番剧详细信息（包含所有关联数据）
        
        Args:
            anime_id: 番剧ID
            
        Returns:
            番剧详细信息
        """
        try:
            # 获取番剧及其关联数据
            anime = await self.repos.anime.get_with_full_details(anime_id)
            if not anime:
                return ServiceResult.not_found_error("Anime", anime_id)
            
            # 获取统计信息
            sources = await self.repos.anime_source.get_by_anime(anime_id)
            episode_stats = {}
            
            for source in sources:
                stats = await self.repos.episode.get_episode_stats(source.id)
                episode_stats[source.id] = stats
            
            # 构建详细信息
            anime_details = {
                "basic_info": {
                    "id": anime.id,
                    "title": anime.title,
                    "type": anime.type.value,
                    "season": anime.season,
                    "episode_count": anime.episode_count,
                    "image_url": anime.image_url,
                    "source_url": anime.source_url,
                    "created_at": anime.created_at.isoformat() if anime.created_at else None,
                    "updated_at": anime.updated_at.isoformat() if anime.updated_at else None
                },
                "sources": [
                    {
                        "id": source.id,
                        "provider_name": source.provider_name,
                        "media_id": source.media_id,
                        "is_favorited": source.is_favorited,
                        "created_at": source.created_at.isoformat() if source.created_at else None,
                        "stats": episode_stats.get(source.id, {})
                    }
                    for source in anime.sources
                ],
                "metadata": None,
                "aliases": None
            }
            
            # 添加元数据信息
            if anime.anime_metadata:
                metadata = anime.anime_metadata
                anime_details["metadata"] = {
                    "tmdb_id": metadata.tmdb_id,
                    "imdb_id": metadata.imdb_id,
                    "tvdb_id": metadata.tvdb_id,
                    "douban_id": metadata.douban_id,
                    "bangumi_id": metadata.bangumi_id,
                    "tmdb_episode_group_id": metadata.tmdb_episode_group_id
                }
            
            # 添加别名信息
            if anime.aliases:
                aliases = anime.aliases
                anime_details["aliases"] = {
                    "name_en": aliases.name_en,
                    "name_jp": aliases.name_jp,
                    "name_romaji": aliases.name_romaji,
                    "alias_cn_1": aliases.alias_cn_1,
                    "alias_cn_2": aliases.alias_cn_2,
                    "alias_cn_3": aliases.alias_cn_3
                }
            
            return ServiceResult.success_result(anime_details)
            
        except Exception as e:
            return await self._handle_service_error("get_anime_details", e)
    
    @service_operation("create_anime_with_sources")
    async def create_anime_with_sources(
        self,
        anime_data: Dict[str, Any],
        sources_data: List[Dict[str, Any]] = None,
        metadata_data: Dict[str, Any] = None,
        aliases_data: Dict[str, Any] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        创建番剧及其关联数据（事务操作）
        
        Args:
            anime_data: 番剧基础数据
            sources_data: 数据源列表
            metadata_data: 元数据
            aliases_data: 别名数据
            
        Returns:
            创建结果
        """
        try:
            # 验证番剧数据
            required_fields = ["title", "type"]
            self._validate_required_fields(anime_data, required_fields)
            self._validate_field_length(anime_data["title"], "title", 255, 1)
            
            # 验证类型
            if anime_data["type"] not in [t.value for t in AnimeType]:
                return ServiceResult.validation_error(
                    f"无效的番剧类型: {anime_data['type']}", "type"
                )
            
            # 检查标题重复
            existing_anime = await self.repos.anime.search_by_title(
                anime_data["title"], exact_match=True, limit=1
            )
            if existing_anime:
                return ServiceResult.validation_error(
                    f"标题为 '{anime_data['title']}' 的番剧已存在", "title"
                )
            
            # 事务创建
            async with self.transaction():
                # 创建番剧
                anime_create_data = {
                    "title": anime_data["title"],
                    "type": AnimeType(anime_data["type"]),
                    "season": anime_data.get("season", 1),
                    "episode_count": anime_data.get("episode_count"),
                    "image_url": anime_data.get("image_url"),
                    "source_url": anime_data.get("source_url")
                }
                
                anime = await self.repos.anime.create(**anime_create_data)
                
                # 创建数据源
                created_sources = []
                if sources_data:
                    for source_data in sources_data:
                        self._validate_required_fields(source_data, ["provider_name", "media_id"])
                        
                        source = await self.repos.anime_source.create(
                            anime_id=anime.id,
                            provider_name=source_data["provider_name"],
                            media_id=source_data["media_id"],
                            is_favorited=source_data.get("is_favorited", False)
                        )
                        created_sources.append(source)
                
                # 创建元数据
                created_metadata = None
                if metadata_data:
                    created_metadata = await self.repos.anime_metadata.create(
                        anime_id=anime.id,
                        **metadata_data
                    )
                
                # 创建别名
                created_aliases = None
                if aliases_data:
                    created_aliases = await self.repos.anime_alias.create(
                        anime_id=anime.id,
                        **aliases_data
                    )
                
                result_data = {
                    "anime": {
                        "id": anime.id,
                        "title": anime.title,
                        "type": anime.type.value,
                        "season": anime.season,
                        "created_at": anime.created_at.isoformat()
                    },
                    "sources": [
                        {
                            "id": source.id,
                            "provider_name": source.provider_name,
                            "media_id": source.media_id,
                            "is_favorited": source.is_favorited
                        }
                        for source in created_sources
                    ],
                    "metadata_created": created_metadata is not None,
                    "aliases_created": created_aliases is not None
                }
                
                return ServiceResult.success_result(
                    data=result_data,
                    message=f"成功创建番剧 '{anime.title}'"
                )
                
        except Exception as e:
            return await self._handle_service_error("create_anime_with_sources", e)
    
    @service_operation("update_anime_metadata")
    async def update_anime_metadata(
        self,
        anime_id: int,
        metadata_updates: Dict[str, Any]
    ) -> ServiceResult[Dict[str, Any]]:
        """
        更新番剧元数据
        
        Args:
            anime_id: 番剧ID
            metadata_updates: 元数据更新
            
        Returns:
            更新结果
        """
        try:
            # 检查番剧是否存在
            anime = await self._check_resource_exists(
                anime_id, "Anime", self.repos.anime.get_by_id
            )
            
            # 获取或创建元数据
            metadata = await self.repos.anime_metadata.get_by_anime(anime_id)
            
            if metadata:
                # 更新现有元数据
                updated_metadata = await self.repos.anime_metadata.update(
                    metadata.id, **metadata_updates
                )
                action = "updated"
            else:
                # 创建新元数据
                updated_metadata = await self.repos.anime_metadata.create(
                    anime_id=anime_id, **metadata_updates
                )
                action = "created"
            
            result_data = {
                "anime_id": anime_id,
                "anime_title": anime.title,
                "metadata": {
                    "tmdb_id": updated_metadata.tmdb_id,
                    "imdb_id": updated_metadata.imdb_id,
                    "tvdb_id": updated_metadata.tvdb_id,
                    "douban_id": updated_metadata.douban_id,
                    "bangumi_id": updated_metadata.bangumi_id,
                    "tmdb_episode_group_id": updated_metadata.tmdb_episode_group_id
                },
                "action": action
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"成功{action}番剧元数据"
            )
            
        except Exception as e:
            return await self._handle_service_error("update_anime_metadata", e)
    
    @service_operation("merge_anime")
    async def merge_anime(
        self,
        target_anime_id: int,
        source_anime_ids: List[int],
        merge_strategy: Dict[str, str] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        合并番剧（复杂事务操作）
        
        Args:
            target_anime_id: 目标番剧ID
            source_anime_ids: 要合并的源番剧ID列表
            merge_strategy: 合并策略配置
            
        Returns:
            合并结果
        """
        try:
            if not source_anime_ids:
                return ServiceResult.validation_error("源番剧列表不能为空", "source_anime_ids")
            
            if target_anime_id in source_anime_ids:
                return ServiceResult.validation_error(
                    "目标番剧不能在源番剧列表中", "target_anime_id"
                )
            
            # 设置默认合并策略
            default_strategy = {
                "title": "keep_target",  # keep_target, use_source, manual
                "metadata": "merge",     # keep_target, use_source, merge
                "sources": "merge",      # merge, replace
                "aliases": "merge"       # merge, replace
            }
            merge_strategy = {**default_strategy, **(merge_strategy or {})}
            
            async with self.transaction():
                # 获取目标番剧
                target_anime = await self._check_resource_exists(
                    target_anime_id, "Anime", self.repos.anime.get_with_full_details
                )
                
                # 获取源番剧
                source_animes = []
                for source_id in source_anime_ids:
                    source_anime = await self._check_resource_exists(
                        source_id, "Anime", self.repos.anime.get_with_full_details
                    )
                    source_animes.append(source_anime)
                
                merge_log = []
                
                # 合并数据源
                if merge_strategy["sources"] == "merge":
                    for source_anime in source_animes:
                        for source in source_anime.sources:
                            # 检查是否已存在相同的数据源
                            existing = await self.repos.anime_source.get_by_anime(target_anime_id)
                            has_duplicate = any(
                                s.provider_name == source.provider_name and s.media_id == source.media_id
                                for s in existing
                            )
                            
                            if not has_duplicate:
                                await self.repos.anime_source.update(
                                    source.id, anime_id=target_anime_id
                                )
                                merge_log.append(f"移动数据源: {source.provider_name}#{source.media_id}")
                
                # 合并元数据
                if merge_strategy["metadata"] == "merge" and any(a.anime_metadata for a in source_animes):
                    target_metadata_data = {}
                    if target_anime.anime_metadata:
                        target_metadata_data = {
                            "tmdb_id": target_anime.anime_metadata.tmdb_id,
                            "imdb_id": target_anime.anime_metadata.imdb_id,
                            "tvdb_id": target_anime.anime_metadata.tvdb_id,
                            "douban_id": target_anime.anime_metadata.douban_id,
                            "bangumi_id": target_anime.anime_metadata.bangumi_id,
                            "tmdb_episode_group_id": target_anime.anime_metadata.tmdb_episode_group_id
                        }
                    
                    # 从源番剧合并元数据
                    for source_anime in source_animes:
                        if source_anime.anime_metadata:
                            metadata = source_anime.anime_metadata
                            fields = ["tmdb_id", "imdb_id", "tvdb_id", "douban_id", "bangumi_id", "tmdb_episode_group_id"]
                            for field in fields:
                                value = getattr(metadata, field)
                                if value and not target_metadata_data.get(field):
                                    target_metadata_data[field] = value
                                    merge_log.append(f"合并元数据: {field} = {value}")
                    
                    # 更新目标元数据
                    await self.update_anime_metadata(target_anime_id, target_metadata_data)
                
                # 删除源番剧
                deleted_count = 0
                for source_anime in source_animes:
                    await self.repos.anime.delete(source_anime.id)
                    deleted_count += 1
                    merge_log.append(f"删除源番剧: {source_anime.title}")
                
                result_data = {
                    "target_anime": {
                        "id": target_anime.id,
                        "title": target_anime.title
                    },
                    "merged_count": len(source_anime_ids),
                    "deleted_count": deleted_count,
                    "merge_strategy": merge_strategy,
                    "merge_log": merge_log
                }
                
                return ServiceResult.success_result(
                    data=result_data,
                    message=f"成功合并 {len(source_anime_ids)} 个番剧到 '{target_anime.title}'"
                )
                
        except Exception as e:
            return await self._handle_service_error("merge_anime", e)
    
    @service_operation("get_anime_statistics")
    async def get_anime_statistics(self) -> ServiceResult[Dict[str, Any]]:
        """
        获取番剧统计信息
        
        Returns:
            统计信息
        """
        try:
            # 并发获取各种统计
            tasks = [
                self.repos.anime.get_anime_stats(),
                self.repos.anime.get_recent_anime(days=30),
                self.repos.anime_source.count(),
                self.repos.anime_metadata.count(),
                self.repos.anime_alias.count()
            ]
            
            basic_stats, recent_anime, sources_count, metadata_count, aliases_count = await asyncio.gather(*tasks)
            
            statistics = {
                "basic_stats": basic_stats,
                "recent_anime_count": len(recent_anime),
                "total_sources": sources_count,
                "with_metadata": metadata_count,
                "with_aliases": aliases_count,
                "metadata_coverage": round(metadata_count / basic_stats["total_count"] * 100, 2) if basic_stats["total_count"] > 0 else 0,
                "aliases_coverage": round(aliases_count / basic_stats["total_count"] * 100, 2) if basic_stats["total_count"] > 0 else 0,
                "avg_sources_per_anime": round(sources_count / basic_stats["total_count"], 2) if basic_stats["total_count"] > 0 else 0,
                "generated_at": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(statistics)
            
        except Exception as e:
            return await self._handle_service_error("get_anime_statistics", e)
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """番剧服务健康检查"""
        try:
            # 检查基础查询
            count = await self.repos.anime.count()
            
            # 检查最近创建
            recent = await self.repos.anime.get_recent_anime(days=1, limit=1)
            
            health_data = {
                "service": "AnimeService",
                "status": "healthy",
                "total_anime": count,
                "recent_anime_today": len(recent),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(health_data)
            
        except Exception as e:
            return await self._handle_service_error("anime_service_health_check", e)