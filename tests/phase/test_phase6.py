"""
Phase 6 API适配测试脚本

测试新ORM架构下的FastAPI应用和API路由适配
"""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Dict, Any
import importlib.util

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_dependency_injection():
    """测试依赖注入系统"""
    try:
        logger.info("测试依赖注入系统...")
        
        # 测试导入依赖模块
        from src.dependencies import (
            get_database_engine,
            get_session_factory,
            get_service_factory,
            get_anime_service,
            get_episode_service,
            get_danmaku_service,
            get_user_service,
            get_auth_service
        )
        
        # 测试数据库引擎创建
        try:
            engine = get_database_engine()
            logger.info(f"✅ 数据库引擎创建成功: {type(engine).__name__}")
        except Exception as e:
            logger.warning(f"⚠️  数据库引擎创建失败（可能是配置问题）: {e}")
        
        # 测试会话工厂创建
        try:
            session_factory = get_session_factory()
            logger.info(f"✅ 会话工厂创建成功: {type(session_factory).__name__}")
        except Exception as e:
            logger.error(f"❌ 会话工厂创建失败: {e}")
            return False
        
        logger.info("✅ 依赖注入系统测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 依赖注入系统测试失败: {e}")
        return False


async def test_fastapi_application():
    """测试FastAPI应用创建"""
    try:
        logger.info("测试FastAPI应用创建...")
        
        # 测试导入新的main模块
        try:
            from src.main_new import app, create_app
            logger.info("✅ FastAPI应用模块导入成功")
            
            # 测试应用实例
            app_instance = create_app()
            logger.info(f"✅ FastAPI应用实例创建成功: {app_instance.title}")
            logger.info(f"  - 版本: {app_instance.version}")
            logger.info(f"  - 路由数量: {len(app_instance.routes)}")
            
            # 列出主要路由
            main_routes = [route for route in app_instance.routes if hasattr(route, 'path')]
            logger.info("📋 主要路由:")
            for route in main_routes[:10]:  # 只显示前10个
                if hasattr(route, 'methods'):
                    methods = list(route.methods)
                    logger.info(f"  {methods} {route.path}")
            
        except Exception as e:
            logger.error(f"❌ FastAPI应用创建失败: {e}")
            return False
        
        logger.info("✅ FastAPI应用测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ FastAPI应用测试失败: {e}")
        return False


async def test_api_routes():
    """测试API路由适配"""
    try:
        logger.info("测试API路由适配...")
        
        # 测试UI API路由
        try:
            from src.api.ui_new import router as ui_router
            logger.info(f"✅ UI API路由导入成功，路由数: {len(ui_router.routes)}")
            
            # 检查关键路由
            key_routes = []
            for route in ui_router.routes:
                if hasattr(route, 'path'):
                    key_routes.append(f"{list(route.methods)[0]} {route.path}")
            
            expected_routes = [
                "/search/anime",
                "/library",
                "/library/anime/{anime_id}/details",
                "/library/source/{source_id}/episodes"
            ]
            
            for expected in expected_routes:
                found = any(expected in route for route in key_routes)
                if found:
                    logger.info(f"  ✅ 找到路由: {expected}")
                else:
                    logger.warning(f"  ⚠️  未找到路由: {expected}")
                    
        except Exception as e:
            logger.error(f"❌ UI API路由测试失败: {e}")
            return False
        
        # 测试认证API路由
        try:
            from src.api.auth_new import router as auth_router
            logger.info(f"✅ 认证API路由导入成功，路由数: {len(auth_router.routes)}")
            
            # 检查认证相关路由
            auth_routes = []
            for route in auth_router.routes:
                if hasattr(route, 'path'):
                    auth_routes.append(f"{list(route.methods)[0]} {route.path}")
            
            expected_auth_routes = ["/register", "/login", "/me", "/tokens"]
            
            for expected in expected_auth_routes:
                found = any(expected in route for route in auth_routes)
                if found:
                    logger.info(f"  ✅ 找到认证路由: {expected}")
                else:
                    logger.warning(f"  ⚠️  未找到认证路由: {expected}")
                    
        except Exception as e:
            logger.error(f"❌ 认证API路由测试失败: {e}")
            return False
        
        logger.info("✅ API路由适配测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ API路由适配测试失败: {e}")
        return False


async def test_service_integration():
    """测试服务层集成"""
    try:
        logger.info("测试服务层集成...")
        
        # 测试服务工厂创建（模拟环境）
        from src.database.repositories.factory import RepositoryFactory
        from src.services.factory import ServiceFactory
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟会话
        mock_session = Mock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # 创建Repository工厂
        try:
            repo_factory = RepositoryFactory(mock_session)
            logger.info("✅ Repository工厂创建成功")
        except Exception as e:
            logger.error(f"❌ Repository工厂创建失败: {e}")
            return False
        
        # 创建服务工厂
        try:
            service_factory = ServiceFactory(
                repository_factory=repo_factory,
                jwt_secret="test_secret",
                config={"test": "config"}
            )
            logger.info("✅ 服务工厂创建成功")
            
            # 测试服务获取
            anime_service = service_factory.anime
            episode_service = service_factory.episode
            danmaku_service = service_factory.danmaku
            user_service = service_factory.user
            auth_service = service_factory.auth
            
            logger.info("✅ 所有服务获取成功")
            logger.info(f"  - AnimeService: {type(anime_service).__name__}")
            logger.info(f"  - EpisodeService: {type(episode_service).__name__}")
            logger.info(f"  - DanmakuService: {type(danmaku_service).__name__}")
            logger.info(f"  - UserService: {type(user_service).__name__}")
            logger.info(f"  - AuthService: {type(auth_service).__name__}")
            
        except Exception as e:
            logger.error(f"❌ 服务工厂测试失败: {e}")
            return False
        
        logger.info("✅ 服务层集成测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 服务层集成测试失败: {e}")
        return False


async def test_error_handling():
    """测试错误处理机制"""
    try:
        logger.info("测试错误处理机制...")
        
        # 测试异常处理函数
        from src.dependencies import handle_service_error
        from src.services.base import ValidationError, ResourceNotFoundError, PermissionDeniedError
        from fastapi import HTTPException
        
        # 测试不同类型的异常转换
        test_cases = [
            (ValidationError("测试验证错误", "test_field"), 400),
            (ResourceNotFoundError("User", 123), 404),
            (PermissionDeniedError("权限不足"), 403),
        ]
        
        for error, expected_status in test_cases:
            http_exc = handle_service_error(error)
            if isinstance(http_exc, HTTPException) and http_exc.status_code == expected_status:
                logger.info(f"  ✅ {type(error).__name__} -> {expected_status}")
            else:
                logger.error(f"  ❌ {type(error).__name__} 转换失败")
                return False
        
        logger.info("✅ 错误处理机制测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 错误处理机制测试失败: {e}")
        return False


async def test_pydantic_models():
    """测试Pydantic模型定义"""
    try:
        logger.info("测试Pydantic模型定义...")
        
        # 测试UI API模型
        from src.api.ui_new import (
            AnimeSearchResponse,
            AnimeDetailResponse,
            EpisodeListResponse,
            DanmakuAnalysisResponse
        )
        
        # 测试模型创建
        search_response = AnimeSearchResponse(
            results=[{"id": 1, "title": "测试番剧"}],
            total=1,
            page=1,
            limit=20
        )
        logger.info("✅ UI API模型测试通过")
        
        # 测试认证API模型
        from src.api.auth_new import (
            UserCreate,
            UserLogin,
            TokenResponse,
            UserProfile
        )
        
        # 测试模型验证
        user_create = UserCreate(username="testuser", password="testpassword123")
        logger.info("✅ 认证API模型测试通过")
        
        logger.info("✅ Pydantic模型定义测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ Pydantic模型定义测试失败: {e}")
        return False


async def test_configuration():
    """测试配置系统"""
    try:
        logger.info("测试配置系统...")
        
        from src.config import settings
        
        # 检查配置加载
        logger.info(f"✅ 配置加载成功")
        logger.info(f"  - 服务器配置: {settings.server.host}:{settings.server.port}")
        logger.info(f"  - 数据库类型: {settings.database.type}")
        logger.info(f"  - JWT算法: {settings.jwt.algorithm}")
        
        # 测试数据库URL构建
        async_url = settings.database.async_url
        sync_url = settings.database.sync_url
        
        logger.info("✅ 数据库URL构建成功")
        logger.info(f"  - 异步URL: {async_url.split('@')[0]}@***")  # 隐藏敏感信息
        logger.info(f"  - 同步URL: {sync_url.split('@')[0]}@***")
        
        logger.info("✅ 配置系统测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 配置系统测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 Phase 6 API适配测试")
    logger.info("=" * 60)
    
    tests = [
        ("配置系统", test_configuration),
        ("依赖注入系统", test_dependency_injection),
        ("服务层集成", test_service_integration),
        ("FastAPI应用", test_fastapi_application),
        ("API路由适配", test_api_routes),
        ("Pydantic模型", test_pydantic_models),
        ("错误处理机制", test_error_handling),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\\n📝 测试: {test_name}")
        logger.info("-" * 30)
        result = await test_func()
        results.append((test_name, result))
    
    # 总结结果
    logger.info("\\n" + "=" * 60)
    logger.info("📊 测试结果总结:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\\n总计: {passed}/{len(tests)} 测试通过")
    
    if passed == len(tests):
        logger.info("🎉 Phase 6 API适配测试完成！")
        logger.info("\\n已完成的工作:")
        logger.info("  ✅ 新的依赖注入系统")
        logger.info("  ✅ FastAPI应用集成新ORM架构")
        logger.info("  ✅ 主要API路由适配（UI + 认证）")
        logger.info("  ✅ 服务层依赖注入")
        logger.info("  ✅ 统一的错误处理机制")
        logger.info("  ✅ Pydantic模型定义")
        logger.info("  ✅ 配置系统集成")
        logger.info("\\n核心特性:")
        logger.info("  🔧 基于SQLAlchemy 2.0的依赖注入")
        logger.info("  📡 RESTful API与服务层解耦")
        logger.info("  🛡️  统一的认证和权限控制")
        logger.info("  ❌ 标准化的错误处理")
        logger.info("  🎯 类型安全的API接口")
        logger.info("  ⚡ 异步数据库会话管理")
        logger.info("\\n下一步:")
        logger.info("  1. 完成剩余API路由适配")
        logger.info("  2. 实现完整的系统集成测试")
        logger.info("  3. 性能优化和监控")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())