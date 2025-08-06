"""
Phase 1 基础架构测试脚本

测试SQLAlchemy 2.0集成是否正常工作
"""

import asyncio
import logging
from pathlib import Path
import sys

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_database_configuration():
    """测试数据库配置"""
    try:
        from src.config import settings
        
        logger.info("测试数据库配置...")
        
        # 测试配置属性
        logger.info(f"数据库类型: {settings.database.type}")
        logger.info(f"异步URL: {settings.database.async_url}")
        logger.info(f"同步URL: {settings.database.sync_url}")
        
        # 测试引擎配置
        engine_config = settings.database.get_engine_config()
        logger.info(f"引擎配置: {engine_config}")
        
        logger.info("✅ 数据库配置测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库配置测试失败: {e}")
        return False


async def test_database_engine():
    """测试数据库引擎"""
    try:
        from src.database.engine import DatabaseEngine
        from src.config import settings
        
        logger.info("测试数据库引擎...")
        
        # 创建引擎实例
        database_url = settings.database.async_url
        engine_config = settings.database.get_engine_config()
        
        engine = DatabaseEngine(database_url, **engine_config)
        
        logger.info(f"引擎创建成功: {engine}")
        logger.info(f"数据库类型: {engine.database_type}")
        
        # 关闭引擎
        await engine.close()
        
        logger.info("✅ 数据库引擎测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库引擎测试失败: {e}")
        return False


async def test_base_models():
    """测试基础模型"""
    try:
        from src.database.models.base import Base, IDMixin, TimestampMixin
        
        logger.info("测试基础模型...")
        
        # 测试基础类
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, 'registry')
        
        # 测试混入类
        assert hasattr(IDMixin, 'id')
        assert hasattr(TimestampMixin, 'created_at')
        assert hasattr(TimestampMixin, 'updated_at')
        
        logger.info("✅ 基础模型测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 基础模型测试失败: {e}")
        return False


async def test_database_initialization():
    """测试数据库初始化模块"""
    try:
        from src.database import initialize_database, shutdown_database
        
        logger.info("测试数据库初始化模块...")
        
        # 这些函数应该可以导入而不出错
        assert callable(initialize_database)
        assert callable(shutdown_database)
        
        logger.info("✅ 数据库初始化模块测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库初始化模块测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 Phase 1 基础架构测试")
    logger.info("=" * 50)
    
    tests = [
        ("配置系统", test_database_configuration),
        ("数据库引擎", test_database_engine),
        ("基础模型", test_base_models),
        ("初始化模块", test_database_initialization),
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
        logger.info("🎉 Phase 1 基础架构搭建完成！")
        logger.info("\n下一步可以进行:")
        logger.info("  1. Phase 2: 核心模型定义")
        logger.info("  2. 初始化Alembic迁移")
        logger.info("  3. 创建第一个ORM模型")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())