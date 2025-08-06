"""
FastAPI应用主入口 - 新ORM架构版本

集成新的SQLAlchemy 2.0 ORM服务层，提供完整的API服务
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# 导入新的依赖系统
from .dependencies import (
    lifespan_manager,
    get_service_factory,
    get_health_check_info,
    handle_service_error
)
from .config import settings
from .services.base import ServiceError

# 导入API路由（需要适配）
from .api.ui_new import router as ui_router
from .api.auth_new import router as auth_router
# 其他路由将在适配后导入

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("🚀 启动 Misaka Danmu Server (新ORM版本)")
    
    try:
        # 初始化新的ORM服务层
        async with lifespan_manager():
            logger.info("✅ 应用启动完成")
            yield
            
    except Exception as e:
        logger.error(f"❌ 应用启动失败: {e}")
        raise
    finally:
        logger.info("🛑 应用关闭")


# 创建FastAPI应用
app = FastAPI(
    title="Misaka Danmu Server",
    description="弹幕聚合服务器 - 新ORM架构版本",
    version="2.0.0",
    lifespan=app_lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 全局异常处理器
@app.exception_handler(ServiceError)
async def service_error_handler(request: Request, exc: ServiceError):
    """处理服务层异常"""
    http_exc = handle_service_error(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "timestamp": exc.timestamp.isoformat()
        }
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc):
    """处理内部服务器错误"""
    logger.error(f"内部服务器错误: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "服务器内部错误",
            "path": str(request.url.path)
        }
    )


# 基础API端点
@app.get("/", tags=["基础"])
async def root():
    """根端点"""
    return {
        "message": "Misaka Danmu Server - 新ORM架构版本",
        "version": "2.0.0",
        "status": "running"
    }


@app.get("/health", tags=["监控"])
async def health_check(health_info: dict = get_health_check_info):
    """健康检查端点"""
    if health_info.get("overall_status") == "healthy":
        return health_info
    else:
        raise HTTPException(status_code=503, detail=health_info)


@app.get("/api/version", tags=["基础"])
async def api_version():
    """API版本信息"""
    return {
        "api_version": "v2",
        "orm_version": "sqlalchemy-2.0",
        "database_support": ["mysql", "postgresql", "sqlite"],
        "features": [
            "新ORM架构",
            "Repository模式",
            "Service层封装",
            "统一异常处理",
            "异步事务管理"
        ]
    }


# 包含API路由
# 注意：这些路由已经适配到新的依赖注入系统
app.include_router(ui_router, prefix="/api/ui", tags=["Web UI API"])
app.include_router(auth_router, prefix="/api/ui/auth", tags=["Auth"])

# 其他路由将在适配完成后添加
# app.include_router(auth_router, prefix="/api/ui/auth", tags=["Auth"])
# app.include_router(dandan_router, prefix="/api", tags=["DanDanPlay Compatible"])
# app.include_router(bangumi_router, prefix="/api/bgm", tags=["Bangumi"])
# app.include_router(tmdb_router, prefix="/api/tmdb", tags=["TMDB"])
# app.include_router(douban_router, prefix="/api/douban", tags=["Douban"])
# app.include_router(imdb_router, prefix="/api/imdb", tags=["IMDb"])
# app.include_router(tvdb_router, prefix="/api/tvdb", tags=["TVDB"])
# app.include_router(webhook_router, prefix="/api/webhook", tags=["Webhook"])


# 静态文件服务
static_path = Path(__file__).parent.parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


# 404处理中间件
@app.middleware("http")
async def log_404_requests(request: Request, call_next):
    """记录404请求的详细信息"""
    response = await call_next(request)
    
    if response.status_code == 404:
        logger.warning(
            f"404 请求: {request.method} {request.url.path} "
            f"来源: {request.client.host if request.client else 'unknown'} "
            f"User-Agent: {request.headers.get('user-agent', 'unknown')}"
        )
    
    return response


# 性能监控中间件
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加响应时间监控"""
    import time
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


def create_app() -> FastAPI:
    """创建应用实例（用于测试和部署）"""
    return app


if __name__ == "__main__":
    # 开发环境启动
    uvicorn.run(
        "main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        log_level="info"
    )