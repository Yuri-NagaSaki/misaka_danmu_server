"""
弹幕参数解析和统计功能测试

测试增强的弹幕统计功能，包括颜色、模式分布等。
"""

import asyncio
import logging
from pathlib import Path
import sys
from unittest.mock import Mock, AsyncMock

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_danmaku_parser():
    """测试弹幕参数解析器"""
    try:
        logger.info("测试弹幕参数解析器...")
        
        from src.database.repositories.danmaku_parser import DanmakuParamsParser
        
        parser = DanmakuParamsParser()
        
        # 测试参数解析
        test_params = "23.5,1,25,16777215,1609459200,0,test_id,user_hash_123"
        result = parser.parse_params_string(test_params)
        
        assert result is not None
        assert 'time' in result
        assert 'mode' in result
        assert 'color' in result
        assert result['time'] == 23.5
        assert result['mode'] == 1
        assert result['color'] == 16777215
        
        # 测试工具方法
        mode_name = parser.get_mode_name(1)
        assert mode_name == "从右至左滚动"
        
        color_hex = parser.get_color_hex(16777215)
        assert color_hex == "#FFFFFF"
        
        size_name = parser.get_font_size_name(25)
        assert size_name == "大"
        
        logger.info("✅ 弹幕参数解析器测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 弹幕参数解析器测试失败: {e}")
        return False


async def test_enhanced_comment_statistics():
    """测试增强弹幕统计功能"""
    try:
        logger.info("测试增强弹幕统计功能...")
        
        from src.database.repositories.danmaku_parser import EnhancedCommentStatistics
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟查询结果
        mock_result = Mock()
        mock_result.all.return_value = [
            (16777215, 100),  # 白色
            (255, 50),        # 红色
            (65280, 25)       # 绿色
        ]
        mock_session.execute.return_value = mock_result
        
        stats = EnhancedCommentStatistics(mock_session)
        
        # 测试颜色分布统计（通过视图）
        color_dist = await stats.get_color_distribution_via_view(1)
        assert isinstance(color_dist, dict)
        assert "#FFFFFF" in color_dist  # 白色
        assert "#0000FF" in color_dist  # 红色
        assert "#00FF00" in color_dist  # 绿色
        
        # 测试模式分布统计（通过视图）
        mock_result.all.return_value = [(1, 200), (4, 50), (5, 30)]
        mode_dist = await stats.get_mode_distribution_via_view(1)
        assert isinstance(mode_dist, dict)
        assert "从右至左滚动" in mode_dist
        
        logger.info("✅ 增强弹幕统计功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 增强弹幕统计功能测试失败: {e}")
        return False


async def test_comment_repository_enhanced():
    """测试增强的CommentRepository"""
    try:
        logger.info("测试增强的CommentRepository...")
        
        from src.database.repositories.episode import CommentRepository
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟基础统计查询结果
        mock_result = Mock()
        mock_result.scalar.return_value = 1000  # 总数
        mock_result.all.return_value = [(0, 100), (1, 150), (2, 80)]  # 时间分布
        mock_session.execute.return_value = mock_result
        
        repo = CommentRepository(mock_session)
        
        # 测试Repository初始化时包含增强统计功能
        assert hasattr(repo, 'enhanced_stats')
        assert hasattr(repo, 'parser')
        
        # 测试新增的方法存在
        assert hasattr(repo, 'get_danmaku_color_distribution')
        assert hasattr(repo, 'get_danmaku_mode_distribution') 
        assert hasattr(repo, 'get_parsed_danmaku')
        
        logger.info("✅ 增强CommentRepository测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 增强CommentRepository测试失败: {e}")
        return False


async def test_database_view_creation():
    """测试数据库视图创建功能"""
    try:
        logger.info("测试数据库视图创建功能...")
        
        from src.database.repositories.danmaku_parser import create_comment_params_view
        
        # 创建模拟的AsyncSession
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        
        # 测试MySQL视图创建
        await create_comment_params_view(mock_session, "mysql")
        assert mock_session.execute.called
        assert mock_session.commit.called
        
        # 重置mock
        mock_session.reset_mock()
        
        # 测试PostgreSQL视图创建  
        await create_comment_params_view(mock_session, "postgresql")
        assert mock_session.execute.called
        
        # 重置mock
        mock_session.reset_mock()
        
        # 测试SQLite视图创建
        await create_comment_params_view(mock_session, "sqlite")
        assert mock_session.execute.called
        
        logger.info("✅ 数据库视图创建功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库视图创建功能测试失败: {e}")
        return False


async def test_comprehensive_functionality():
    """综合功能测试"""
    try:
        logger.info("测试综合功能...")
        
        from src.database.repositories.danmaku_parser import EnhancedCommentStatistics
        
        # 创建模拟会话
        mock_session = Mock()
        mock_session.execute = AsyncMock()
        
        # 模拟不同的查询结果
        def mock_execute_side_effect(stmt, params=None):
            mock_result = Mock()
            
            # 根据SQL语句类型返回不同结果
            if hasattr(stmt, 'text') and 'color' in str(stmt.text):
                # 颜色统计查询
                mock_result.all.return_value = [(16777215, 100), (255, 50)]
            elif hasattr(stmt, 'text') and 'mode' in str(stmt.text):
                # 模式统计查询  
                mock_result.all.return_value = [(1, 200), (4, 50)]
            elif hasattr(stmt, 'text') and 'font_size' in str(stmt.text):
                # 字号统计查询
                mock_result.all.return_value = [(25, 150), (18, 100)]
            else:
                mock_result.all.return_value = []
                
            return mock_result
        
        mock_session.execute.side_effect = mock_execute_side_effect
        
        stats = EnhancedCommentStatistics(mock_session)
        
        # 测试综合统计功能
        comprehensive = await stats.get_comprehensive_statistics(
            episode_id=1, 
            use_view=True
        )
        
        assert isinstance(comprehensive, dict)
        assert "color_distribution" in comprehensive
        assert "mode_distribution" in comprehensive
        assert "font_size_distribution" in comprehensive
        assert "method" in comprehensive
        
        # 验证结果内容
        assert "#FFFFFF" in comprehensive["color_distribution"]
        assert "从右至左滚动" in comprehensive["mode_distribution"]
        assert "大" in comprehensive["font_size_distribution"]
        
        logger.info("✅ 综合功能测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 综合功能测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始弹幕参数解析和统计功能测试")
    logger.info("=" * 50)
    
    tests = [
        ("弹幕参数解析器", test_danmaku_parser),
        ("增强弹幕统计功能", test_enhanced_comment_statistics),
        ("增强CommentRepository", test_comment_repository_enhanced),
        ("数据库视图创建", test_database_view_creation),
        ("综合功能", test_comprehensive_functionality),
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
        logger.info("🎉 弹幕参数解析和统计功能实现完成！")
        logger.info("\n新增功能:")
        logger.info("  ✅ 弹幕参数解析器（支持颜色、模式、字号等）")
        logger.info("  ✅ 数据库视图支持（MySQL、PostgreSQL、SQLite）")
        logger.info("  ✅ 增强的统计功能（颜色/模式分布）")
        logger.info("  ✅ Python解析备用方案（视图不可用时）")
        logger.info("  ✅ CommentRepository集成增强统计")
        logger.info("\n使用方式:")
        logger.info("  1. 创建数据库视图（推荐，性能更好）")
        logger.info("  2. 使用增强统计API获取详细分布信息")
        logger.info("  3. 支持视图和Python解析两种模式")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())