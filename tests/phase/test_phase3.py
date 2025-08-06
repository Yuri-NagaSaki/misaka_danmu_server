"""
Phase 3 Repository模式测试脚本

测试Repository实现是否正确工作
"""

import asyncio
import logging
from pathlib import Path
import sys
from datetime import datetime, timedelta

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_repository_imports():
    """测试Repository导入"""
    try:
        logger.info("测试Repository导入...")
        
        # 测试基础Repository导入
        from src.database.repositories.base import BaseRepository
        
        # 测试番剧Repository导入
        from src.database.repositories.anime import (
            AnimeRepository, AnimeSourceRepository, AnimeMetadataRepository,
            AnimeAliasRepository, TMDBEpisodeMappingRepository
        )
        
        # 测试分集Repository导入
        from src.database.repositories.episode import EpisodeRepository, CommentRepository
        
        # 测试用户Repository导入
        from src.database.repositories.user import (
            UserRepository, APITokenRepository, TokenAccessLogRepository,
            BangumiAuthRepository, OAuthStateRepository, UARulesRepository
        )
        
        # 测试系统Repository导入
        from src.database.repositories.system import (
            ConfigRepository, CacheDataRepository, ScraperRepository,
            ScheduledTaskRepository, TaskHistoryRepository
        )
        
        # 测试工厂导入
        from src.database.repositories.factory import RepositoryFactory, RepositoryManager
        
        # 测试统一导入
        from src.database.repositories import BaseRepository as ReposBase
        assert BaseRepository is ReposBase
        
        logger.info("✅ Repository导入测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository导入测试失败: {e}")
        return False


async def test_repository_factory():
    """测试Repository工厂"""
    try:
        logger.info("测试Repository工厂...")
        
        from src.database.repositories.factory import RepositoryFactory
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # 创建工厂
        factory = RepositoryFactory(mock_session)
        
        # 测试Repository属性访问
        anime_repo = factory.anime
        assert anime_repo is not None
        
        episode_repo = factory.episode
        assert episode_repo is not None
        
        user_repo = factory.user
        assert user_repo is not None
        
        config_repo = factory.config
        assert config_repo is not None
        
        # 测试单例模式
        anime_repo2 = factory.anime
        assert anime_repo is anime_repo2
        
        logger.info("✅ Repository工厂测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ Repository工厂测试失败: {e}")
        return False


async def test_base_repository_methods():
    """测试基础Repository方法"""
    try:
        logger.info("测试基础Repository方法...")
        
        from src.database.repositories.base import BaseRepository
        from src.database.models.anime import Anime
        from unittest.mock import Mock, AsyncMock, MagicMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.flush = AsyncMock()
        mock_session.refresh = AsyncMock()
        mock_session.add = Mock()
        mock_session.add_all = Mock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        # 创建Repository
        repo = BaseRepository(mock_session, Anime)
        
        # 测试方法是否存在
        assert hasattr(repo, 'get_by_id')
        assert hasattr(repo, 'get_by_ids')
        assert hasattr(repo, 'get_all')
        assert hasattr(repo, 'create')
        assert hasattr(repo, 'create_many')
        assert hasattr(repo, 'update')
        assert hasattr(repo, 'delete')
        assert hasattr(repo, 'count')
        assert hasattr(repo, 'exists')
        
        # 测试基础方法调用（不会实际执行SQL）
        result = await repo.get_by_id(1)
        assert result is None  # 模拟返回None
        
        count_result = await repo.count()
        assert count_result == 0  # 模拟返回0
        
        logger.info("✅ 基础Repository方法测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 基础Repository方法测试失败: {e}")
        return False


async def test_anime_repository_methods():
    """测试AnimeRepository特有方法"""
    try:
        logger.info("测试AnimeRepository特有方法...")
        
        from src.database.repositories.anime import AnimeRepository
        from src.database.models.anime import AnimeType
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # 创建Repository
        repo = AnimeRepository(mock_session)
        
        # 测试特有方法是否存在
        assert hasattr(repo, 'search_by_title')
        assert hasattr(repo, 'search_by_multiple_fields')
        assert hasattr(repo, 'get_with_full_details')
        assert hasattr(repo, 'get_by_source')
        assert hasattr(repo, 'get_recent_anime')
        assert hasattr(repo, 'get_anime_by_type')
        assert hasattr(repo, 'get_anime_stats')
        
        # 测试方法调用
        result = await repo.search_by_title("测试", limit=10)
        assert isinstance(result, list)
        
        result = await repo.search_by_multiple_fields(
            title="测试", 
            anime_type=AnimeType.TV_SERIES
        )
        assert isinstance(result, list)
        
        logger.info("✅ AnimeRepository方法测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ AnimeRepository方法测试失败: {e}")
        return False


async def test_episode_repository_methods():
    """测试EpisodeRepository特有方法"""
    try:
        logger.info("测试EpisodeRepository特有方法...")
        
        from src.database.repositories.episode import EpisodeRepository, CommentRepository
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        mock_session.execute.return_value = mock_result
        
        # 创建Repository
        episode_repo = EpisodeRepository(mock_session)
        comment_repo = CommentRepository(mock_session)
        
        # 测试分集Repository方法
        assert hasattr(episode_repo, 'get_by_source_and_episode')
        assert hasattr(episode_repo, 'get_episodes_by_source')
        assert hasattr(episode_repo, 'get_episodes_with_danmaku_count')
        assert hasattr(episode_repo, 'get_recent_episodes')
        assert hasattr(episode_repo, 'get_episode_stats')
        
        # 测试弹幕Repository方法
        assert hasattr(comment_repo, 'get_danmaku_by_episode')
        assert hasattr(comment_repo, 'get_danmaku_by_time_range')
        assert hasattr(comment_repo, 'search_danmaku_by_content')
        assert hasattr(comment_repo, 'get_danmaku_statistics')
        assert hasattr(comment_repo, 'batch_create_danmaku')
        
        # 测试方法调用
        episode = await episode_repo.get_by_source_and_episode(1, 1)
        assert episode is None  # 模拟返回
        
        danmaku_list = await comment_repo.get_danmaku_by_episode(1, limit=10)
        assert isinstance(danmaku_list, list)
        
        logger.info("✅ EpisodeRepository方法测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ EpisodeRepository方法测试失败: {e}")
        return False


async def test_user_repository_methods():
    """测试UserRepository特有方法"""
    try:
        logger.info("测试UserRepository特有方法...")
        
        from src.database.repositories.user import (
            UserRepository, APITokenRepository, BangumiAuthRepository
        )
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.rowcount = 0
        mock_session.execute.return_value = mock_result
        
        # 创建Repository
        user_repo = UserRepository(mock_session)
        token_repo = APITokenRepository(mock_session)
        bangumi_repo = BangumiAuthRepository(mock_session)
        
        # 测试用户Repository方法
        assert hasattr(user_repo, 'get_by_username')
        assert hasattr(user_repo, 'get_with_auth_info')
        assert hasattr(user_repo, 'verify_password')
        assert hasattr(user_repo, 'update_token')
        
        # 测试API令牌Repository方法
        assert hasattr(token_repo, 'get_by_token')
        assert hasattr(token_repo, 'get_active_tokens')
        assert hasattr(token_repo, 'validate_token')
        assert hasattr(token_repo, 'disable_token')
        
        # 测试Bangumi认证Repository方法
        assert hasattr(bangumi_repo, 'get_by_user_id')
        assert hasattr(bangumi_repo, 'get_by_bangumi_user_id')
        assert hasattr(bangumi_repo, 'refresh_token')
        
        # 测试方法调用
        user = await user_repo.get_by_username("test_user")
        assert user is None  # 模拟返回
        
        token = await token_repo.validate_token("test_token")
        assert token is None  # 模拟返回
        
        logger.info("✅ UserRepository方法测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ UserRepository方法测试失败: {e}")
        return False


async def test_system_repository_methods():
    """测试SystemRepository特有方法"""
    try:
        logger.info("测试SystemRepository特有方法...")
        
        from src.database.repositories.system import (
            ConfigRepository, CacheDataRepository, ScraperRepository
        )
        from unittest.mock import Mock, AsyncMock
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.scalar.return_value = 0
        mock_session.execute.return_value = mock_result
        
        # 创建Repository
        config_repo = ConfigRepository(mock_session)
        cache_repo = CacheDataRepository(mock_session)
        scraper_repo = ScraperRepository(mock_session)
        
        # 测试配置Repository方法
        assert hasattr(config_repo, 'get_by_key')
        assert hasattr(config_repo, 'get_value')
        assert hasattr(config_repo, 'set_value')
        assert hasattr(config_repo, 'get_configs_by_prefix')
        assert hasattr(config_repo, 'get_all_configs')
        
        # 测试缓存Repository方法
        assert hasattr(cache_repo, 'get_by_key')
        assert hasattr(cache_repo, 'get_cache_value')
        assert hasattr(cache_repo, 'set_cache_value')
        assert hasattr(cache_repo, 'delete_cache')
        assert hasattr(cache_repo, 'cleanup_expired_cache')
        
        # 测试爬虫Repository方法
        assert hasattr(scraper_repo, 'get_by_name')
        assert hasattr(scraper_repo, 'get_active_scrapers')
        assert hasattr(scraper_repo, 'update_scraper_status')
        
        # 测试方法调用
        config_value = await config_repo.get_value("test_key", default="default")
        assert config_value == "default"  # 返回默认值
        
        cache_value = await cache_repo.get_cache_value("test_cache_key")
        assert cache_value is None  # 模拟未找到
        
        logger.info("✅ SystemRepository方法测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ SystemRepository方法测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 Phase 3 Repository模式测试")
    logger.info("=" * 50)
    
    tests = [
        ("Repository导入", test_repository_imports),
        ("Repository工厂", test_repository_factory), 
        ("基础Repository方法", test_base_repository_methods),
        ("AnimeRepository方法", test_anime_repository_methods),
        ("EpisodeRepository方法", test_episode_repository_methods),
        ("UserRepository方法", test_user_repository_methods),
        ("SystemRepository方法", test_system_repository_methods),
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
        logger.info("🎉 Phase 3 Repository模式实现完成！")
        logger.info("\n已完成的工作:")
        logger.info("  ✅ 基础Repository类（通用CRUD操作）")
        logger.info("  ✅ AnimeRepository（番剧相关查询）")
        logger.info("  ✅ EpisodeRepository（分集和弹幕操作）")
        logger.info("  ✅ UserRepository（用户和认证管理）")
        logger.info("  ✅ SystemRepository（系统配置和缓存）")
        logger.info("  ✅ Repository工厂和依赖注入")
        logger.info("\n下一步可以进行:")
        logger.info("  1. Phase 4: 业务服务层实现")
        logger.info("  2. 创建数据迁移脚本")
        logger.info("  3. 集成到FastAPI应用")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())