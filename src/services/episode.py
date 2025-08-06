"""
分集和弹幕业务服务

提供分集和弹幕相关的复杂业务逻辑，包括弹幕分析、批量操作、导入导出等。
"""

from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime, timedelta
import asyncio
import xml.etree.ElementTree as ET
from io import StringIO
import json

from .base import BaseService, ServiceResult, ServiceError, ValidationError, BusinessLogicError, service_operation
from ..database.models.episode import Episode, Comment
from ..database.models.anime import AnimeSource
from ..database.repositories.factory import RepositoryFactory
from ..database.repositories.danmaku_parser import DanmakuParamsParser, EnhancedCommentStatistics


class EpisodeService(BaseService):
    """分集业务服务"""
    
    def __init__(self, repository_factory: RepositoryFactory):
        super().__init__(repository_factory)
        self.metrics = None
    
    @service_operation("create_episode_with_validation")
    async def create_episode_with_validation(
        self,
        episode_data: Dict[str, Any],
        check_duplicates: bool = True
    ) -> ServiceResult[Dict[str, Any]]:
        """
        创建分集（带验证）
        
        Args:
            episode_data: 分集数据
            check_duplicates: 是否检查重复
            
        Returns:
            创建结果
        """
        try:
            # 验证必需字段
            required_fields = ["source_id", "title", "episode_index"]
            self._validate_required_fields(episode_data, required_fields)
            
            # 验证字段长度
            self._validate_field_length(episode_data["title"], "title", 255, 1)
            
            # 验证episode_index
            episode_index = episode_data["episode_index"]
            if not isinstance(episode_index, int) or episode_index < 1:
                return ServiceResult.validation_error(
                    "分集序号必须是大于0的整数", "episode_index"
                )
            
            # 检查数据源是否存在
            source = await self._check_resource_exists(
                episode_data["source_id"], "AnimeSource", self.repos.anime_source.get_by_id
            )
            
            # 检查重复
            if check_duplicates:
                existing = await self.repos.episode.get_by_source_and_episode(
                    episode_data["source_id"], episode_index
                )
                if existing:
                    return ServiceResult.validation_error(
                        f"数据源 {source.provider_name} 的第 {episode_index} 集已存在",
                        "episode_index"
                    )
            
            # 创建分集
            episode = await self.repos.episode.create(**episode_data)
            
            result_data = {
                "episode": {
                    "id": episode.id,
                    "title": episode.title,
                    "episode_index": episode.episode_index,
                    "source_id": episode.source_id,
                    "created_at": episode.created_at.isoformat() if episode.created_at else None
                },
                "source": {
                    "id": source.id,
                    "provider_name": source.provider_name,
                    "media_id": source.media_id
                }
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"成功创建分集: {episode.title}"
            )
            
        except Exception as e:
            return await self._handle_service_error("create_episode_with_validation", e)
    
    @service_operation("batch_create_episodes")
    async def batch_create_episodes(
        self,
        source_id: int,
        episodes_data: List[Dict[str, Any]],
        skip_duplicates: bool = True
    ) -> ServiceResult[Dict[str, Any]]:
        """
        批量创建分集
        
        Args:
            source_id: 数据源ID
            episodes_data: 分集数据列表
            skip_duplicates: 是否跳过重复项
            
        Returns:
            批量创建结果
        """
        try:
            if not episodes_data:
                return ServiceResult.validation_error("分集数据不能为空", "episodes_data")
            
            # 检查数据源是否存在
            source = await self._check_resource_exists(
                source_id, "AnimeSource", self.repos.anime_source.get_by_id
            )
            
            async with self.transaction():
                created_episodes = []
                skipped_episodes = []
                errors = []
                
                for i, episode_data in enumerate(episodes_data):
                    try:
                        # 添加source_id
                        episode_data["source_id"] = source_id
                        
                        # 验证单个分集数据
                        required_fields = ["title", "episode_index"]
                        self._validate_required_fields(episode_data, required_fields)
                        
                        episode_index = episode_data["episode_index"]
                        
                        # 检查重复
                        if skip_duplicates:
                            existing = await self.repos.episode.get_by_source_and_episode(
                                source_id, episode_index
                            )
                            if existing:
                                skipped_episodes.append({
                                    "index": i,
                                    "episode_index": episode_index,
                                    "reason": "已存在"
                                })
                                continue
                        
                        # 创建分集
                        episode = await self.repos.episode.create(**episode_data)
                        created_episodes.append({
                            "id": episode.id,
                            "title": episode.title,
                            "episode_index": episode.episode_index
                        })
                        
                    except Exception as e:
                        errors.append({
                            "index": i,
                            "episode_data": episode_data,
                            "error": str(e)
                        })
                
                result_data = {
                    "source": {
                        "id": source.id,
                        "provider_name": source.provider_name,
                        "media_id": source.media_id
                    },
                    "total_requested": len(episodes_data),
                    "created_count": len(created_episodes),
                    "skipped_count": len(skipped_episodes),
                    "error_count": len(errors),
                    "created_episodes": created_episodes,
                    "skipped_episodes": skipped_episodes,
                    "errors": errors
                }
                
                return ServiceResult.success_result(
                    data=result_data,
                    message=f"批量创建完成: {len(created_episodes)} 个成功，{len(skipped_episodes)} 个跳过，{len(errors)} 个错误"
                )
                
        except Exception as e:
            return await self._handle_service_error("batch_create_episodes", e)
    
    @service_operation("get_episodes_with_stats")
    async def get_episodes_with_stats(
        self,
        source_id: int,
        include_danmaku_count: bool = True
    ) -> ServiceResult[List[Dict[str, Any]]]:
        """
        获取分集列表及统计信息
        
        Args:
            source_id: 数据源ID
            include_danmaku_count: 是否包含弹幕数量
            
        Returns:
            分集列表及统计
        """
        try:
            # 检查数据源是否存在
            source = await self._check_resource_exists(
                source_id, "AnimeSource", self.repos.anime_source.get_by_id
            )
            
            if include_danmaku_count:
                episodes_with_count = await self.repos.episode.get_episodes_with_danmaku_count(source_id)
                episodes_data = [
                    {
                        "id": episode.id,
                        "title": episode.title,
                        "episode_index": episode.episode_index,
                        "source_id": episode.source_id,
                        "created_at": episode.created_at.isoformat() if episode.created_at else None,
                        "danmaku_count": count
                    }
                    for episode, count in episodes_with_count
                ]
            else:
                episodes = await self.repos.episode.get_episodes_by_source(source_id)
                episodes_data = [
                    {
                        "id": episode.id,
                        "title": episode.title,
                        "episode_index": episode.episode_index,
                        "source_id": episode.source_id,
                        "created_at": episode.created_at.isoformat() if episode.created_at else None
                    }
                    for episode in episodes
                ]
            
            result_data = {
                "source": {
                    "id": source.id,
                    "provider_name": source.provider_name,
                    "media_id": source.media_id
                },
                "episodes": episodes_data,
                "total_episodes": len(episodes_data)
            }
            
            return ServiceResult.success_result(result_data)
            
        except Exception as e:
            return await self._handle_service_error("get_episodes_with_stats", e)
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """分集服务健康检查"""
        try:
            count = await self.repos.episode.count()
            recent = await self.repos.episode.get_recent_episodes(days=1, limit=1)
            
            health_data = {
                "service": "EpisodeService",
                "status": "healthy",
                "total_episodes": count,
                "recent_episodes_today": len(recent),
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(health_data)
            
        except Exception as e:
            return await self._handle_service_error("episode_service_health_check", e)


class DanmakuService(BaseService):
    """弹幕业务服务"""
    
    def __init__(self, repository_factory: RepositoryFactory):
        super().__init__(repository_factory)
        self.metrics = None
        self.parser = DanmakuParamsParser()
    
    @service_operation("import_danmaku_from_xml")
    async def import_danmaku_from_xml(
        self,
        episode_id: int,
        xml_content: str,
        source_format: str = "bilibili",
        batch_size: int = 1000
    ) -> ServiceResult[Dict[str, Any]]:
        """
        从XML格式导入弹幕
        
        Args:
            episode_id: 分集ID
            xml_content: XML内容
            source_format: 源格式 (bilibili, acfun, etc.)
            batch_size: 批处理大小
            
        Returns:
            导入结果
        """
        try:
            # 检查分集是否存在
            episode = await self._check_resource_exists(
                episode_id, "Episode", self.repos.episode.get_by_id
            )
            
            # 解析XML
            try:
                root = ET.fromstring(xml_content)
            except ET.ParseError as e:
                return ServiceResult.validation_error(
                    f"XML格式错误: {str(e)}", "xml_content"
                )
            
            # 解析弹幕数据
            danmaku_list = []
            
            if source_format == "bilibili":
                for d_elem in root.findall(".//d"):
                    p_attr = d_elem.get("p", "")
                    content = d_elem.text or ""
                    
                    if p_attr and content:
                        danmaku_list.append({
                            "episode_id": episode_id,
                            "cid": f"xml_import_{len(danmaku_list)}",
                            "p": p_attr,
                            "m": content.strip(),
                            "t": float(p_attr.split(',')[0]) if p_attr else 0
                        })
            else:
                return ServiceResult.validation_error(
                    f"不支持的格式: {source_format}", "source_format"
                )
            
            if not danmaku_list:
                return ServiceResult.validation_error(
                    "XML中未找到有效的弹幕数据", "xml_content"
                )
            
            # 批量导入
            async with self.transaction():
                total_imported = 0
                errors = []
                
                for i in range(0, len(danmaku_list), batch_size):
                    batch = danmaku_list[i:i + batch_size]
                    
                    try:
                        imported_batch = await self.repos.comment.create_many(batch)
                        total_imported += len(imported_batch)
                    except Exception as e:
                        errors.append({
                            "batch_start": i,
                            "batch_size": len(batch),
                            "error": str(e)
                        })
                
                result_data = {
                    "episode": {
                        "id": episode.id,
                        "title": episode.title,
                        "episode_index": episode.episode_index
                    },
                    "import_stats": {
                        "total_parsed": len(danmaku_list),
                        "total_imported": total_imported,
                        "batch_size": batch_size,
                        "batches_processed": (len(danmaku_list) + batch_size - 1) // batch_size,
                        "errors": errors
                    },
                    "source_format": source_format
                }
                
                return ServiceResult.success_result(
                    data=result_data,
                    message=f"成功导入 {total_imported} 条弹幕"
                )
                
        except Exception as e:
            return await self._handle_service_error("import_danmaku_from_xml", e)
    
    @service_operation("export_danmaku_to_xml")
    async def export_danmaku_to_xml(
        self,
        episode_id: int,
        export_format: str = "bilibili",
        limit: Optional[int] = None
    ) -> ServiceResult[Dict[str, Any]]:
        """
        导出弹幕为XML格式
        
        Args:
            episode_id: 分集ID
            export_format: 导出格式
            limit: 导出数量限制
            
        Returns:
            导出结果（包含XML内容）
        """
        try:
            # 检查分集是否存在
            episode = await self._check_resource_exists(
                episode_id, "Episode", self.repos.episode.get_by_id
            )
            
            # 获取弹幕数据
            danmaku_list = await self.repos.comment.get_danmaku_by_episode(episode_id, limit)
            
            if not danmaku_list:
                return ServiceResult.success_result(
                    data={"xml_content": "", "count": 0},
                    message="该分集暂无弹幕数据"
                )
            
            # 生成XML
            if export_format == "bilibili":
                xml_content = self._generate_bilibili_xml(danmaku_list, episode)
            else:
                return ServiceResult.validation_error(
                    f"不支持的导出格式: {export_format}", "export_format"
                )
            
            result_data = {
                "episode": {
                    "id": episode.id,
                    "title": episode.title,
                    "episode_index": episode.episode_index
                },
                "xml_content": xml_content,
                "export_format": export_format,
                "danmaku_count": len(danmaku_list),
                "exported_at": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"成功导出 {len(danmaku_list)} 条弹幕"
            )
            
        except Exception as e:
            return await self._handle_service_error("export_danmaku_to_xml", e)
    
    def _generate_bilibili_xml(self, danmaku_list: List[Comment], episode: Episode) -> str:
        """生成B站格式的弹幕XML"""
        root = ET.Element("i")
        
        # 添加元数据
        chatserver = ET.SubElement(root, "chatserver")
        chatserver.text = "chat.bilibili.com"
        
        chatid = ET.SubElement(root, "chatid")
        chatid.text = str(episode.id)
        
        mission = ET.SubElement(root, "mission")
        mission.text = "0"
        
        maxlimit = ET.SubElement(root, "maxlimit")
        maxlimit.text = str(len(danmaku_list))
        
        state = ET.SubElement(root, "state")
        state.text = "0"
        
        real_name = ET.SubElement(root, "real_name")
        real_name.text = "0"
        
        source = ET.SubElement(root, "source")
        source.text = "k-v"
        
        # 添加弹幕
        for danmaku in danmaku_list:
            d = ET.SubElement(root, "d")
            d.set("p", danmaku.p)
            d.text = danmaku.m
        
        # 生成XML字符串
        return ET.tostring(root, encoding='unicode', xml_declaration=True)
    
    @service_operation("analyze_danmaku_patterns")
    async def analyze_danmaku_patterns(
        self,
        episode_id: int,
        analysis_type: str = "comprehensive"
    ) -> ServiceResult[Dict[str, Any]]:
        """
        分析弹幕模式和趋势
        
        Args:
            episode_id: 分集ID
            analysis_type: 分析类型 (basic, comprehensive, advanced)
            
        Returns:
            分析结果
        """
        try:
            # 检查分集是否存在
            episode = await self._check_resource_exists(
                episode_id, "Episode", self.repos.episode.get_by_id
            )
            
            # 获取弹幕统计
            stats = await self.repos.comment.get_danmaku_statistics(
                episode_id, 
                use_enhanced=(analysis_type in ["comprehensive", "advanced"])
            )
            
            analysis_result = {
                "episode": {
                    "id": episode.id,
                    "title": episode.title,
                    "episode_index": episode.episode_index
                },
                "basic_stats": {
                    "total_count": stats["total_count"],
                    "average_time_offset": stats["average_time_offset"],
                    "time_distribution": stats["time_distribution"]
                }
            }
            
            if analysis_type in ["comprehensive", "advanced"]:
                analysis_result["enhanced_stats"] = {
                    "color_distribution": stats.get("color_distribution", {}),
                    "mode_distribution": stats.get("mode_distribution", {}),
                    "font_size_distribution": stats.get("font_size_distribution", {}),
                    "statistics_method": stats.get("statistics_method", "basic_only")
                }
                
                # 分析热点时段
                hot_segments = self._analyze_hot_segments(stats["time_distribution"])
                analysis_result["hot_segments"] = hot_segments
            
            if analysis_type == "advanced":
                # 高级分析：获取热门弹幕
                popular_danmaku = await self.repos.comment.get_popular_danmaku(episode_id, limit=10)
                analysis_result["popular_danmaku"] = [
                    {
                        "content": danmaku.m,
                        "time_offset": float(danmaku.t),
                        "params": danmaku.p
                    }
                    for danmaku in popular_danmaku
                ]
                
                # Top评论者
                top_commenters = await self.repos.comment.get_top_commenters(episode_id, limit=5)
                analysis_result["top_commenters"] = [
                    {"user_hash": user_hash, "count": count}
                    for user_hash, count in top_commenters
                ]
            
            return ServiceResult.success_result(
                data=analysis_result,
                message=f"弹幕分析完成 ({analysis_type})"
            )
            
        except Exception as e:
            return await self._handle_service_error("analyze_danmaku_patterns", e)
    
    def _analyze_hot_segments(self, time_distribution: Dict[int, int]) -> List[Dict[str, Any]]:
        """分析热点时段"""
        if not time_distribution:
            return []
        
        # 计算平均值和阈值
        values = list(time_distribution.values())
        avg_count = sum(values) / len(values)
        threshold = avg_count * 1.5  # 高于平均值50%算热点
        
        hot_segments = []
        for minute, count in time_distribution.items():
            if count >= threshold:
                hot_segments.append({
                    "minute": minute,
                    "time_range": f"{minute}:00-{minute+1}:00",
                    "danmaku_count": count,
                    "intensity": round(count / avg_count, 2)
                })
        
        # 按弹幕数量排序
        hot_segments.sort(key=lambda x: x["danmaku_count"], reverse=True)
        return hot_segments[:10]  # 返回前10个热点时段
    
    @service_operation("cleanup_duplicate_danmaku")
    async def cleanup_duplicate_danmaku(
        self,
        episode_id: int,
        similarity_threshold: float = 0.9
    ) -> ServiceResult[Dict[str, Any]]:
        """
        清理重复弹幕
        
        Args:
            episode_id: 分集ID
            similarity_threshold: 相似度阈值
            
        Returns:
            清理结果
        """
        try:
            # 检查分集是否存在
            episode = await self._check_resource_exists(
                episode_id, "Episode", self.repos.episode.get_by_id
            )
            
            # 获取所有弹幕
            all_danmaku = await self.repos.comment.get_danmaku_by_episode(episode_id)
            
            if len(all_danmaku) < 2:
                return ServiceResult.success_result(
                    data={"removed_count": 0, "remaining_count": len(all_danmaku)},
                    message="弹幕数量过少，无需清理"
                )
            
            # 查找重复项
            duplicates = []
            processed = set()
            
            for i, danmaku1 in enumerate(all_danmaku):
                if i in processed:
                    continue
                
                group = [danmaku1]
                for j, danmaku2 in enumerate(all_danmaku[i+1:], i+1):
                    if j in processed:
                        continue
                    
                    # 检查相似度
                    if self._calculate_danmaku_similarity(danmaku1, danmaku2) >= similarity_threshold:
                        group.append(danmaku2)
                        processed.add(j)
                
                if len(group) > 1:
                    duplicates.append(group)
                
                processed.add(i)
            
            # 删除重复项（保留第一个）
            removed_count = 0
            async with self.transaction():
                for group in duplicates:
                    # 保留第一个，删除其他
                    for danmaku in group[1:]:
                        await self.repos.comment.delete(danmaku.id)
                        removed_count += 1
            
            result_data = {
                "episode": {
                    "id": episode.id,
                    "title": episode.title
                },
                "cleanup_stats": {
                    "original_count": len(all_danmaku),
                    "duplicate_groups": len(duplicates),
                    "removed_count": removed_count,
                    "remaining_count": len(all_danmaku) - removed_count,
                    "similarity_threshold": similarity_threshold
                }
            }
            
            return ServiceResult.success_result(
                data=result_data,
                message=f"清理完成，删除了 {removed_count} 条重复弹幕"
            )
            
        except Exception as e:
            return await self._handle_service_error("cleanup_duplicate_danmaku", e)
    
    def _calculate_danmaku_similarity(self, danmaku1: Comment, danmaku2: Comment) -> float:
        """计算弹幕相似度"""
        # 内容相似度（主要因素）
        content_similarity = self._string_similarity(danmaku1.m, danmaku2.m)
        
        # 时间相似度（5秒内认为相似）
        time_diff = abs(float(danmaku1.t) - float(danmaku2.t))
        time_similarity = max(0, 1 - time_diff / 5.0)
        
        # 综合相似度
        return content_similarity * 0.8 + time_similarity * 0.2
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """计算字符串相似度（简单版本）"""
        if s1 == s2:
            return 1.0
        
        # 使用简单的字符匹配
        if not s1 or not s2:
            return 0.0
        
        common_chars = set(s1) & set(s2)
        all_chars = set(s1) | set(s2)
        
        return len(common_chars) / len(all_chars) if all_chars else 0.0
    
    async def health_check(self) -> ServiceResult[Dict[str, Any]]:
        """弹幕服务健康检查"""
        try:
            count = await self.repos.comment.count()
            
            health_data = {
                "service": "DanmakuService",
                "status": "healthy",
                "total_danmaku": count,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            return ServiceResult.success_result(health_data)
            
        except Exception as e:
            return await self._handle_service_error("danmaku_service_health_check", e)