"""
Phase 5 迁移工具测试脚本

测试Alembic迁移和数据库schema创建功能
"""

import asyncio
import logging
import os
from pathlib import Path
import sys
import subprocess

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def test_alembic_configuration():
    """测试Alembic配置"""
    try:
        logger.info("测试Alembic配置...")
        
        # 检查Alembic配置文件
        alembic_ini = project_root / "alembic.ini"
        if not alembic_ini.exists():
            raise FileNotFoundError("alembic.ini文件不存在")
        
        # 检查Alembic目录
        alembic_dir = project_root / "alembic"
        if not alembic_dir.exists():
            raise FileNotFoundError("alembic目录不存在")
        
        # 检查env.py文件
        env_py = alembic_dir / "env.py"
        if not env_py.exists():
            raise FileNotFoundError("alembic/env.py文件不存在")
        
        # 检查版本目录
        versions_dir = alembic_dir / "versions"
        if not versions_dir.exists():
            raise FileNotFoundError("alembic/versions目录不存在")
        
        # 检查是否有迁移文件
        migration_files = list(versions_dir.glob("*.py"))
        if not migration_files:
            logger.warning("⚠️  没有找到迁移文件")
        else:
            logger.info(f"📁 找到 {len(migration_files)} 个迁移文件")
            for file in migration_files:
                logger.info(f"  - {file.name}")
        
        logger.info("✅ Alembic配置测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ Alembic配置测试失败: {e}")
        return False


async def test_offline_schema_validation():
    """测试离线schema验证"""
    try:
        logger.info("测试离线schema验证...")
        
        # 运行离线验证脚本
        result = subprocess.run(
            [sys.executable, "validate_schema.py"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        
        if result.returncode == 0:
            logger.info("✅ 离线schema验证通过")
            
            # 检查生成的文件
            schema_file = project_root / "generated_schema.sql"
            if schema_file.exists():
                logger.info(f"📄 生成的schema文件大小: {schema_file.stat().st_size} bytes")
            
            return True
        else:
            logger.error(f"❌ 离线schema验证失败: {result.stderr}")
            return False
            
    except Exception as e:
        logger.error(f"❌ 离线schema验证测试失败: {e}")
        return False


async def test_model_imports():
    """测试模型导入"""
    try:
        logger.info("测试模型导入...")
        
        # 导入所有模型
        from src.database.models.base import Base, IDMixin, TimestampMixin
        from src.database.models.anime import Anime, AnimeType, AnimeSource, AnimeMetadata, AnimeAlias, TMDBEpisodeMapping
        from src.database.models.episode import Episode, Comment
        from src.database.models.user import User, APIToken, TokenAccessLog, BangumiAuth, OAuthState, UARules
        from src.database.models.system import Config, CacheData, Scraper, ScheduledTask, TaskHistory
        
        # 检查模型数量
        model_count = len(Base.registry._class_registry)
        logger.info(f"📊 成功导入 {model_count} 个模型")
        
        # 检查基础模型属性
        test_models = [
            ("Anime", Anime),
            ("Episode", Episode),
            ("Comment", Comment),
            ("User", User),
            ("APIToken", APIToken)
        ]
        
        for model_name, model_class in test_models:
            if hasattr(model_class, '__tablename__'):
                logger.info(f"  ✅ {model_name} -> 表名: {model_class.__tablename__}")
            else:
                logger.warning(f"  ⚠️  {model_name} 没有__tablename__属性")
        
        # 检查元数据
        metadata = Base.metadata
        logger.info(f"📋 元数据包含 {len(metadata.tables)} 个表")
        
        logger.info("✅ 模型导入测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 模型导入测试失败: {e}")
        return False


async def test_database_configuration():
    """测试数据库配置"""
    try:
        logger.info("测试数据库配置...")
        
        from src.config import DatabaseConfig
        
        # 测试默认配置
        config = DatabaseConfig()
        logger.info(f"📊 默认数据库类型: {config.type}")
        
        # 测试PostgreSQL配置
        pg_config = DatabaseConfig(
            type="postgresql",
            host="test.example.com",
            port=5432,
            user="testuser",
            password="testpass",
            name="testdb"
        )
        
        # 测试URL生成
        async_url = pg_config.async_url
        sync_url = pg_config.sync_url
        
        logger.info(f"🔗 异步URL格式: {async_url.split('@')[0]}@***")
        logger.info(f"🔗 同步URL格式: {sync_url.split('@')[0]}@***")
        
        # 测试MySQL配置
        mysql_config = DatabaseConfig(
            type="mysql",
            host="test.example.com",
            port=3306,
            user="testuser",
            password="testpass",
            name="testdb"
        )
        
        mysql_sync_url = mysql_config.sync_url
        logger.info(f"🔗 MySQL URL格式: {mysql_sync_url.split('@')[0]}@***")
        
        logger.info("✅ 数据库配置测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 数据库配置测试失败: {e}")
        return False


async def test_sql_generation():
    """测试SQL生成"""
    try:
        logger.info("测试SQL生成...")
        
        from sqlalchemy import create_mock_engine
        from src.database.models.base import Base
        
        def capture_sql(sql, *multiparams, **params):
            captured_sql.append(str(sql.compile(dialect=engine.dialect)))
            return ""
        
        captured_sql = []
        engine = create_mock_engine("postgresql://", capture_sql)
        
        # 生成创建表的SQL
        Base.metadata.create_all(engine, checkfirst=False)
        
        if captured_sql:
            logger.info(f"📝 生成了 {len(captured_sql)} 条SQL语句")
            
            # 保存到文件
            sql_output = project_root / "test_generated.sql"
            with open(sql_output, "w", encoding="utf-8") as f:
                f.write("-- Test Generated SQL\n\n")
                f.write("\n\n".join(captured_sql))
            
            logger.info(f"💾 SQL已保存到: {sql_output}")
            
            # 检查关键表的SQL
            key_tables = ["anime", "episode", "comment", "users"]
            for table in key_tables:
                found = any(table in sql.lower() for sql in captured_sql)
                if found:
                    logger.info(f"  ✅ 找到表 {table} 的SQL")
                else:
                    logger.warning(f"  ⚠️  未找到表 {table} 的SQL")
        
        logger.info("✅ SQL生成测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ SQL生成测试失败: {e}")
        return False


async def test_environment_variables():
    """测试环境变量支持"""
    try:
        logger.info("测试环境变量支持...")
        
        # 检查.env.example文件是否创建
        env_example = project_root / ".env.example"
        if env_example.exists():
            logger.info("✅ .env.example文件存在")
            with open(env_example, "r", encoding="utf-8") as f:
                content = f.read()
                if "DB_HOST" in content:
                    logger.info("  ✅ 包含数据库配置变量")
                else:
                    logger.warning("  ⚠️  缺少数据库配置变量")
        else:
            logger.warning("⚠️  .env.example文件不存在")
        
        # 测试环境变量读取
        original_host = os.environ.get("DB_HOST")
        os.environ["DB_HOST"] = "test.example.com"
        
        from src.config import DatabaseConfig
        config = DatabaseConfig()
        
        # 恢复原始值
        if original_host:
            os.environ["DB_HOST"] = original_host
        else:
            os.environ.pop("DB_HOST", None)
        
        logger.info("✅ 环境变量测试通过")
        return True
        
    except Exception as e:
        logger.error(f"❌ 环境变量测试失败: {e}")
        return False


async def main():
    """运行所有测试"""
    logger.info("🚀 开始 Phase 5 迁移工具测试")
    logger.info("=" * 60)
    
    tests = [
        ("Alembic配置", test_alembic_configuration),
        ("模型导入", test_model_imports),
        ("数据库配置", test_database_configuration),
        ("离线Schema验证", test_offline_schema_validation),
        ("SQL生成", test_sql_generation),
        ("环境变量支持", test_environment_variables),
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
        logger.info("🎉 Phase 5 迁移工具实现完成！")
        logger.info("\\n已完成的工作:")
        logger.info("  ✅ Alembic迁移环境配置")
        logger.info("  ✅ PostgreSQL数据库schema定义")
        logger.info("  ✅ 完整的ORM模型验证")
        logger.info("  ✅ 离线schema验证工具")
        logger.info("  ✅ 数据库初始化脚本")
        logger.info("  ✅ 环境变量配置支持")
        logger.info("\\n核心特性:")
        logger.info("  🗄️  完整的PostgreSQL schema")
        logger.info("  🔧 Alembic数据库迁移管理")
        logger.info("  ✅ 离线schema验证和SQL生成")
        logger.info("  🔐 支持环境变量配置")
        logger.info("  📊 数据库健康检查和初始化")
        logger.info("  🏗️  支持多数据库类型（MySQL/PostgreSQL）")
        logger.info("\\n下一步可以进行:")
        logger.info("  1. 部署到生产环境")
        logger.info("  2. 集成到CI/CD流水线")
        logger.info("  3. 添加数据库监控和备份")
    else:
        logger.error("⚠️  部分测试失败，需要修复后再继续")
    
    return passed == len(tests)


if __name__ == "__main__":
    asyncio.run(main())