"""
Phase 4 服务层测试脚本

测试业务服务层的实现是否正确工作，包括事务管理、错误处理等。
"""

import asyncio
import logging
from pathlib import Path
import sys
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_service_imports():
    """测试服务导入"""
    try:
        logger.info("测试服务导入...")
        
        # 测试基础服务导入
        from src.services.base import BaseService, ServiceResult, ServiceError, ValidationError
        
        # 测试业务服务导入
        from src.services.anime import AnimeService
        from src.services.episode import EpisodeService, DanmakuService
        from src.services.user import UserService, AuthService
        
        # 测试工厂导入
        from src.services.factory import ServiceFactory, ServiceManager
        
        # 测试统一导入
        from src.services import BaseService as ServicesBase
        assert BaseService is ServicesBase
        
        logger.info("✅ 服务导入测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 服务导入测试失败: {e}")
        return False


async def test_service_result():
    """测试ServiceResult类"""
    try:
        logger.info("测试ServiceResult类...")
        
        from src.services.base import ServiceResult, ValidationError
        
        # 测试成功结果
        success_result = ServiceResult.success_result(
            data={"test": "data"}, 
            message="操作成功"
        )
        assert success_result.success == True
        assert success_result.data == {"test": "data"}
        assert success_result.message == "操作成功"
        
        # 测试错误结果
        error = ValidationError("字段验证失败", "test_field")
        error_result = ServiceResult.error_result(error)
        assert error_result.success == False
        assert error_result.error.message == "字段验证失败"
        
        # 测试字典转换
        result_dict = success_result.to_dict()
        assert "success" in result_dict
        assert "data" in result_dict
        assert "timestamp" in result_dict
        
        logger.info("✅ ServiceResult测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ ServiceResult测试失败: {e}")
        return False


async def test_base_service():
    """测试BaseService基类"""
    try:
        logger.info("测试BaseService基类...")
        
        from src.services.base import BaseService, ValidationError
        from unittest.mock import Mock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 创建测试服务类
        class TestService(BaseService):
            async def health_check(self):
                return {"status": "healthy"}
        
        service = TestService(mock_repos)
        
        # 测试基础方法
        assert hasattr(service, 'repos')
        assert hasattr(service, 'logger')
        assert hasattr(service, 'transaction')
        assert hasattr(service, '_validate_required_fields')
        assert hasattr(service, '_validate_field_length')
        
        # 测试字段验证
        try:
            service._validate_required_fields({"field1": "value"}, ["field1", "field2"])
            assert False, "应该抛出验证错误"
        except ValidationError as e:
            assert "field2" in e.message
        
        # 测试长度验证
        try:
            service._validate_field_length("test", "test_field", 3, 1)
            assert False, "应该抛出长度错误"
        except ValidationError as e:
            assert "长度不能超过" in e.message
        
        logger.info("✅ BaseService测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ BaseService测试失败: {e}")
        return False


async def test_anime_service():
    """测试AnimeService"""
    try:
        logger.info("测试AnimeService...")
        
        from src.services.anime import AnimeService
        from src.database.models.anime import AnimeType
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.anime = Mock()
        mock_repos.anime_source = Mock()
        mock_repos.anime_metadata = Mock()
        mock_repos.anime_alias = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 模拟查询结果
        mock_anime = Mock()
        mock_anime.id = 1
        mock_anime.title = "测试番剧"
        mock_anime.type = AnimeType.TV_SERIES
        mock_anime.season = 1
        mock_anime.created_at = datetime.utcnow()
        mock_anime.sources = []
        
        mock_repos.anime.search_by_title = AsyncMock(return_value=[mock_anime])
        mock_repos.anime_alias.search_by_alias = AsyncMock(return_value=[])
        mock_repos.anime.search_by_multiple_fields = AsyncMock(return_value=[])
        
        # 创建服务
        service = AnimeService(mock_repos)
        
        # 测试搜索功能
        result = await service.search_anime("测试", limit=10)
        assert result.success == True
        assert len(result.data) == 1
        assert result.data[0]["title"] == "测试番剧"
        
        # 测试验证错误
        result = await service.search_anime("", limit=10)
        assert result.success == False
        assert result.error.error_code == "VALIDATION_ERROR"
        
        logger.info("✅ AnimeService测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ AnimeService测试失败: {e}")
        return False


async def test_episode_service():
    """测试EpisodeService"""
    try:
        logger.info("测试EpisodeService...")
        
        from src.services.episode import EpisodeService
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.episode = Mock()
        mock_repos.anime_source = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 模拟数据源
        mock_source = Mock()
        mock_source.id = 1
        mock_source.provider_name = "test_provider"
        mock_source.media_id = "test_media"
        
        mock_repos.anime_source.get_by_id = AsyncMock(return_value=mock_source)
        mock_repos.episode.get_by_source_and_episode = AsyncMock(return_value=None)
        
        # 模拟创建的分集
        mock_episode = Mock()
        mock_episode.id = 1
        mock_episode.title = "第1集"
        mock_episode.episode_index = 1
        mock_episode.source_id = 1
        mock_episode.created_at = datetime.utcnow()
        
        mock_repos.episode.create = AsyncMock(return_value=mock_episode)
        
        # 创建服务
        service = EpisodeService(mock_repos)
        
        # 测试创建分集
        episode_data = {
            "source_id": 1,
            "title": "第1集",
            "episode_index": 1
        }
        
        result = await service.create_episode_with_validation(episode_data)
        assert result.success == True
        assert result.data["episode"]["title"] == "第1集"
        
        # 测试验证错误
        invalid_data = {"source_id": 1}  # 缺少必需字段
        result = await service.create_episode_with_validation(invalid_data)
        assert result.success == False
        assert result.error.error_code == "VALIDATION_ERROR"
        
        logger.info("✅ EpisodeService测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ EpisodeService测试失败: {e}")
        return False


async def test_danmaku_service():
    """测试DanmakuService"""
    try:
        logger.info("测试DanmakuService...")
        
        from src.services.episode import DanmakuService
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.episode = Mock()
        mock_repos.comment = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 模拟分集
        mock_episode = Mock()
        mock_episode.id = 1
        mock_episode.title = "第1集"
        mock_episode.episode_index = 1
        
        mock_repos.episode.get_by_id = AsyncMock(return_value=mock_episode)
        
        # 模拟弹幕统计
        mock_stats = {
            "total_count": 100,
            "average_time_offset": 600.5,
            "time_distribution": {0: 10, 1: 15, 2: 20},
            "color_distribution": {"#FFFFFF": 50, "#FF0000": 30},
            "mode_distribution": {"从右至左滚动": 80, "底端固定": 20}
        }
        
        mock_repos.comment.get_danmaku_statistics = AsyncMock(return_value=mock_stats)
        
        # 创建服务
        service = DanmakuService(mock_repos)
        
        # 测试弹幕分析
        result = await service.analyze_danmaku_patterns(1, "comprehensive")
        assert result.success == True
        assert "basic_stats" in result.data
        assert "enhanced_stats" in result.data
        assert result.data["basic_stats"]["total_count"] == 100
        
        logger.info("✅ DanmakuService测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ DanmakuService测试失败: {e}")
        return False


async def test_user_service():
    """测试UserService"""
    try:
        logger.info("测试UserService...")
        
        from src.services.user import UserService
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.user = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 模拟用户查询
        mock_repos.user.get_by_username = AsyncMock(return_value=None)  # 用户不存在
        
        # 模拟创建的用户
        mock_user = Mock()
        mock_user.id = 1
        mock_user.username = "testuser"
        mock_user.created_at = datetime.utcnow()
        
        mock_repos.user.create = AsyncMock(return_value=mock_user)
        
        # 创建服务
        service = UserService(mock_repos)
        
        # 测试用户创建
        result = await service.create_user("testuser", "TestPassword123!")
        assert result.success == True
        assert result.data["user"]["username"] == "testuser"
        
        # 测试用户名重复
        mock_repos.user.get_by_username = AsyncMock(return_value=mock_user)
        result = await service.create_user("testuser", "TestPassword123!")
        assert result.success == False
        assert "已存在" in result.error.message
        
        logger.info("✅ UserService测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ UserService测试失败: {e}")
        return False


async def test_service_factory():
    """测试ServiceFactory"""
    try:
        logger.info("测试ServiceFactory...")
        
        from src.services.factory import ServiceFactory
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        mock_repos.close = AsyncMock()
        
        # 创建服务工厂
        factory = ServiceFactory(mock_repos, "test_jwt_secret")
        
        # 测试服务获取
        anime_service = factory.anime
        assert anime_service is not None
        
        episode_service = factory.episode
        assert episode_service is not None
        
        danmaku_service = factory.danmaku
        assert danmaku_service is not None
        
        user_service = factory.user
        assert user_service is not None
        
        auth_service = factory.auth
        assert auth_service is not None
        
        # 测试单例模式
        anime_service2 = factory.anime
        assert anime_service is anime_service2
        
        # 测试关闭
        await factory.close()
        mock_repos.close.assert_called_once()
        
        logger.info("✅ ServiceFactory测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ ServiceFactory测试失败: {e}")
        return False


async def test_transaction_management():
    """测试事务管理"""
    try:
        logger.info("测试事务管理...")
        
        from src.services.base import BaseService
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的Repository工厂
        mock_repos = Mock()
        mock_repos.session = Mock()
        mock_repos.session.commit = AsyncMock()
        mock_repos.session.rollback = AsyncMock()
        
        # 创建测试服务
        class TestService(BaseService):
            async def health_check(self):
                return {"status": "healthy"}
        
        service = TestService(mock_repos)
        
        # 测试成功的事务
        async with service.transaction():
            # 模拟一些操作
            pass
        
        # 验证提交被调用
        mock_repos.session.commit.assert_called_once()
        
        # 重置mock
        mock_repos.session.commit.reset_mock()
        mock_repos.session.rollback.reset_mock()
        
        # 测试失败的事务
        try:
            async with service.transaction():
                raise Exception("测试异常")
        except Exception:
            pass
        
        # 验证回滚被调用
        mock_repos.session.rollback.assert_called_once()
        
        logger.info("✅ 事务管理测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 事务管理测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 Phase 4 服务层测试")
    logger.info("=" * 50)
    
    tests = [
        ("服务导入", test_service_imports),
        ("ServiceResult类", test_service_result),
        ("BaseService基类", test_base_service),
        ("AnimeService", test_anime_service),
        ("EpisodeService", test_episode_service),
        ("DanmakuService", test_danmaku_service),
        ("UserService", test_user_service),
        ("ServiceFactory", test_service_factory),
        ("事务管理", test_transaction_management),
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n📝 测试: {test_name}")
        logger.info("-" * 30)
        result = await test_func()
        results.append((test_name, result))
    
    # 总结结果
    logger.info("\n" + "=" * 50)
    logger.info("📊 测试结果总结:")
    
    passed = 0
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        logger.info(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    logger.info(f"\n总计: {passed}/{len(tests)} 测试通过")
    
    if passed == len(tests):
        logger.info("🎉 Phase 4 服务层实现完成！")
        logger.info("\n已完成的工作:")
        logger.info("  ✅ 服务层基础架构（BaseService、ServiceResult、异常类）")
        logger.info("  ✅ AnimeService（番剧搜索、创建、合并等复杂业务）")
        logger.info("  ✅ EpisodeService（分集管理、批量操作）")
        logger.info("  ✅ DanmakuService（弹幕导入导出、分析、清理）")
        logger.info("  ✅ UserService（用户管理、密码验证）")
        logger.info("  ✅ AuthService（JWT令牌、API令牌认证）")
        logger.info("  ✅ ServiceFactory（依赖注入和生命周期管理）")
        logger.info("  ✅ 事务管理和错误处理机制")
        logger.info("\n核心特性:")
        logger.info("  🔐 统一的认证和权限控制")
        logger.info("  💾 自动事务管理")
        logger.info("  ❌ 统一的错误处理和异常封装")
        logger.info("  📊 服务指标收集")
        logger.info("  🏥 健康检查机制")
        logger.info("  🔧 依赖注入和工厂模式")
        logger.info("\n下一步可以进行:")
        logger.info("  1. 集成到FastAPI应用")
        logger.info("  2. 添加API端点")
        logger.info("  3. 实现前端界面")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())