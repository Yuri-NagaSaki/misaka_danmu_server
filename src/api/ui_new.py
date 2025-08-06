"""
Web UI API路由 - 新ORM架构适配版本

将现有的UI API适配到新的SQLAlchemy 2.0 ORM服务层架构
"""

import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

# 导入新的依赖系统和服务层
from ..dependencies import (
    get_anime_service,
    get_episode_service, 
    get_danmaku_service,
    get_user_service,
    get_auth_service,
    get_current_user,
    get_optional_current_user,
    with_service_error_handling
)
from ..services.anime import AnimeService
from ..services.episode import EpisodeService, DanmakuService
from ..services.user import UserService, AuthService, AuthContext
from ..services.base import ServiceResult

logger = logging.getLogger(__name__)
router = APIRouter()


# Pydantic模型定义
class AnimeSearchResponse(BaseModel):
    """番剧搜索响应"""
    results: List[Dict[str, Any]]
    total: int
    page: int
    limit: int


class AnimeDetailResponse(BaseModel):
    """番剧详情响应"""
    anime: Dict[str, Any]
    sources: List[Dict[str, Any]]
    episodes_count: int
    danmaku_count: int


class EpisodeListResponse(BaseModel):
    """分集列表响应"""
    episodes: List[Dict[str, Any]]
    total: int
    source_info: Dict[str, Any]


class DanmakuAnalysisResponse(BaseModel):
    """弹幕分析响应"""
    analysis: Dict[str, Any]
    episode_info: Dict[str, Any]


# 搜索相关API
@router.get("/search/anime", response_model=AnimeSearchResponse)
@with_service_error_handling
async def search_anime(
    q: str = Query(..., description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    anime_service: AnimeService = Depends(get_anime_service),
    current_user: Optional[AuthContext] = Depends(get_optional_current_user)
):
    """
    搜索本地数据库中的番剧
    
    适配说明：
    - 使用新的AnimeService.search_anime方法
    - 支持可选用户认证
    - 统一的错误处理
    """
    try:
        # 计算偏移量
        offset = (page - 1) * limit
        
        # 调用服务层搜索
        search_result = await anime_service.search_anime(
            query=q,
            limit=limit,
            offset=offset
        )
        
        if not search_result.success:
            raise HTTPException(status_code=400, detail=search_result.error.message)
        
        return AnimeSearchResponse(
            results=search_result.data,
            total=len(search_result.data),  # 实际应该返回总数
            page=page,
            limit=limit
        )
        
    except Exception as e:
        logger.error(f"搜索番剧失败: {e}")
        raise HTTPException(status_code=500, detail="搜索失败")


@router.get("/search/provider")
@with_service_error_handling
async def search_provider(
    q: str = Query(..., description="搜索关键词"),
    providers: Optional[str] = Query(None, description="指定搜索源，逗号分隔"),
    anime_service: AnimeService = Depends(get_anime_service)
):
    """
    搜索外部数据源
    
    注意：这个API需要与爬虫系统集成，暂时保持原有逻辑
    """
    # 暂时返回模拟数据，实际需要集成爬虫管理器
    return {
        "message": "外部搜索功能需要进一步适配",
        "query": q,
        "providers": providers.split(",") if providers else ["all"]
    }


# 媒体库管理API
@router.get("/library")
@with_service_error_handling
async def get_library(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="排序字段"),
    order: str = Query("desc", description="排序方向"),
    anime_service: AnimeService = Depends(get_anime_service),
    current_user: Optional[AuthContext] = Depends(get_optional_current_user)
):
    """
    获取媒体库内容
    
    适配说明：
    - 使用新的AnimeService获取番剧列表
    - 支持分页和排序
    """
    try:
        offset = (page - 1) * limit
        
        # 调用服务层获取番剧列表
        result = await anime_service.get_anime_library(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error.message)
        
        return {
            "anime_list": result.data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": len(result.data)  # 实际应该返回总数
            }
        }
        
    except Exception as e:
        logger.error(f"获取媒体库失败: {e}")
        raise HTTPException(status_code=500, detail="获取媒体库失败")


@router.get("/library/anime/{anime_id}/details", response_model=AnimeDetailResponse)
@with_service_error_handling
async def get_anime_details(
    anime_id: int,
    anime_service: AnimeService = Depends(get_anime_service),
    current_user: Optional[AuthContext] = Depends(get_optional_current_user)
):
    """
    获取番剧详情
    
    适配说明：
    - 使用新的AnimeService获取详细信息
    - 包含关联的数据源和分集统计
    """
    try:
        # 获取番剧详情
        anime_result = await anime_service.get_anime_with_details(anime_id)
        
        if not anime_result.success:
            if anime_result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="番剧不存在")
            else:
                raise HTTPException(status_code=400, detail=anime_result.error.message)
        
        return AnimeDetailResponse(
            anime=anime_result.data["anime"],
            sources=anime_result.data.get("sources", []),
            episodes_count=anime_result.data.get("episodes_count", 0),
            danmaku_count=anime_result.data.get("danmaku_count", 0)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取番剧详情失败: {e}")
        raise HTTPException(status_code=500, detail="获取番剧详情失败")


@router.put("/library/anime/{anime_id}")
@with_service_error_handling
async def update_anime(
    anime_id: int,
    anime_data: Dict[str, Any],
    anime_service: AnimeService = Depends(get_anime_service),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    编辑番剧信息
    
    适配说明：
    - 需要用户认证
    - 使用服务层的更新方法
    """
    try:
        result = await anime_service.update_anime(anime_id, anime_data)
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="番剧不存在")
            elif result.error.error_code == "VALIDATION_ERROR":
                raise HTTPException(status_code=400, detail=result.error.message)
            else:
                raise HTTPException(status_code=400, detail=result.error.message)
        
        return {
            "message": "番剧信息更新成功",
            "anime": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新番剧信息失败: {e}")
        raise HTTPException(status_code=500, detail="更新番剧信息失败")


@router.delete("/library/anime/{anime_id}")
@with_service_error_handling
async def delete_anime(
    anime_id: int,
    anime_service: AnimeService = Depends(get_anime_service),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    删除番剧
    
    适配说明：
    - 需要用户认证
    - 使用服务层的删除方法，支持级联删除
    """
    try:
        result = await anime_service.delete_anime(anime_id)
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="番剧不存在")
            else:
                raise HTTPException(status_code=400, detail=result.error.message)
        
        return {"message": "番剧删除成功"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除番剧失败: {e}")
        raise HTTPException(status_code=500, detail="删除番剧失败")


# 分集管理API
@router.get("/library/source/{source_id}/episodes", response_model=EpisodeListResponse)
@with_service_error_handling
async def get_source_episodes(
    source_id: int,
    include_danmaku_count: bool = Query(True, description="是否包含弹幕数量统计"),
    episode_service: EpisodeService = Depends(get_episode_service),
    current_user: Optional[AuthContext] = Depends(get_optional_current_user)
):
    """
    获取数据源的分集列表
    
    适配说明：
    - 使用新的EpisodeService获取分集信息
    - 支持弹幕数量统计
    """
    try:
        result = await episode_service.get_episodes_with_stats(
            source_id=source_id,
            include_danmaku_count=include_danmaku_count
        )
        
        if not result.success:
            raise HTTPException(status_code=400, detail=result.error.message)
        
        return EpisodeListResponse(
            episodes=result.data["episodes"],
            total=result.data["total_episodes"],
            source_info=result.data["source"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取分集列表失败: {e}")
        raise HTTPException(status_code=500, detail="获取分集列表失败")


@router.put("/library/episode/{episode_id}")
@with_service_error_handling
async def update_episode(
    episode_id: int,
    episode_data: Dict[str, Any],
    episode_service: EpisodeService = Depends(get_episode_service),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    编辑分集信息
    
    适配说明：
    - 需要用户认证
    - 使用服务层的更新方法
    """
    try:
        result = await episode_service.update_episode(episode_id, episode_data)
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="分集不存在")
            elif result.error.error_code == "VALIDATION_ERROR":
                raise HTTPException(status_code=400, detail=result.error.message)
            else:
                raise HTTPException(status_code=400, detail=result.error.message)
        
        return {
            "message": "分集信息更新成功",
            "episode": result.data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新分集信息失败: {e}")
        raise HTTPException(status_code=500, detail="更新分集信息失败")


# 弹幕相关API
@router.get("/danmaku/episode/{episode_id}/analysis", response_model=DanmakuAnalysisResponse)
@with_service_error_handling
async def analyze_episode_danmaku(
    episode_id: int,
    analysis_type: str = Query("comprehensive", description="分析类型"),
    danmaku_service: DanmakuService = Depends(get_danmaku_service),
    current_user: Optional[AuthContext] = Depends(get_optional_current_user)
):
    """
    分析分集弹幕模式
    
    适配说明：
    - 使用新的DanmakuService分析功能
    - 支持不同分析类型
    """
    try:
        result = await danmaku_service.analyze_danmaku_patterns(
            episode_id=episode_id,
            analysis_type=analysis_type
        )
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="分集不存在")
            else:
                raise HTTPException(status_code=400, detail=result.error.message)
        
        return DanmakuAnalysisResponse(
            analysis=result.data,
            episode_info=result.data["episode"]
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"弹幕分析失败: {e}")
        raise HTTPException(status_code=500, detail="弹幕分析失败")


@router.post("/danmaku/episode/{episode_id}/cleanup")
@with_service_error_handling
async def cleanup_episode_danmaku(
    episode_id: int,
    similarity_threshold: float = Query(0.9, ge=0.1, le=1.0, description="相似度阈值"),
    danmaku_service: DanmakuService = Depends(get_danmaku_service),
    current_user: AuthContext = Depends(get_current_user)
):
    """
    清理重复弹幕
    
    适配说明：
    - 需要用户认证
    - 使用新的DanmakuService清理功能
    """
    try:
        result = await danmaku_service.cleanup_duplicate_danmaku(
            episode_id=episode_id,
            similarity_threshold=similarity_threshold
        )
        
        if not result.success:
            if result.error.error_code == "RESOURCE_NOT_FOUND":
                raise HTTPException(status_code=404, detail="分集不存在")
            else:
                raise HTTPException(status_code=400, detail=result.error.message)
        
        return {
            "message": result.message,
            "cleanup_stats": result.data["cleanup_stats"]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"清理弹幕失败: {e}")
        raise HTTPException(status_code=500, detail="清理弹幕失败")


# 系统管理API（暂时保持原有接口，需要进一步适配）
@router.get("/scrapers")
async def get_scrapers():
    """获取搜索源配置 - 需要适配爬虫管理器"""
    return {"message": "搜索源管理需要进一步适配"}


@router.get("/tasks")
async def get_tasks():
    """获取后台任务状态 - 需要适配任务管理器"""
    return {"message": "任务管理需要进一步适配"}


@router.get("/logs")
async def get_logs():
    """获取服务器日志 - 需要适配日志系统"""
    return {"message": "日志管理需要进一步适配"}