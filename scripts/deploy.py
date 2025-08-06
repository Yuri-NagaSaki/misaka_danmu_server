"""
Misaka Danmu Server 部署和启动脚本

提供新ORM架构版本的部署、配置和启动功能
"""

import asyncio
import logging
import sys
import os
from pathlib import Path
import subprocess
from typing import Dict, Any, Optional
import yaml

# 添加src目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / "src"))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentManager:
    """部署管理器"""
    
    def __init__(self):
        self.project_root = project_root
        self.config_file = self.project_root / "config" / "config.yml"
        self.env_file = self.project_root / ".env"
        
    def check_dependencies(self) -> bool:
        """检查依赖项"""
        try:
            logger.info("检查项目依赖...")
            
            # 检查pyproject.toml文件
            pyproject_file = self.project_root / "pyproject.toml"
            if not pyproject_file.exists():
                logger.error("❌ 找不到pyproject.toml文件")
                return False
            
            # 检查uv是否可用
            try:
                result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
                if result.returncode == 0:
                    logger.info(f"✅ UV版本: {result.stdout.strip()}")
                else:
                    logger.error("❌ UV不可用")
                    return False
            except FileNotFoundError:
                logger.error("❌ 找不到UV包管理器")
                return False
            
            # 检查Python版本
            python_version = sys.version_info
            if python_version < (3, 11):
                logger.warning(f"⚠️  Python版本建议3.11+，当前: {python_version.major}.{python_version.minor}")
            else:
                logger.info(f"✅ Python版本: {python_version.major}.{python_version.minor}")
            
            logger.info("✅ 依赖检查完成")
            return True
            
        except Exception as e:
            logger.error(f"❌ 依赖检查失败: {e}")
            return False
    
    def install_dependencies(self) -> bool:
        """安装项目依赖"""
        try:
            logger.info("安装项目依赖...")
            
            # 使用uv同步依赖
            result = subprocess.run(
                ["uv", "sync"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ 依赖安装完成")
                return True
            else:
                logger.error(f"❌ 依赖安装失败: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 依赖安装异常: {e}")
            return False
    
    def setup_database(self) -> bool:
        """设置数据库"""
        try:
            logger.info("设置数据库...")
            
            # 检查Alembic配置
            alembic_ini = self.project_root / "alembic.ini"
            if not alembic_ini.exists():
                logger.error("❌ 找不到alembic.ini文件")
                return False
            
            # 运行数据库迁移
            logger.info("运行数据库迁移...")
            result = subprocess.run(
                ["uv", "run", "alembic", "upgrade", "head"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ 数据库迁移完成")
            else:
                logger.warning(f"⚠️  数据库迁移可能失败（需要配置数据库连接）: {result.stderr}")
                # 不将此视为致命错误，因为可能数据库还未配置
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 数据库设置异常: {e}")
            return False
    
    def create_config_template(self):
        """创建配置文件模板"""
        try:
            logger.info("创建配置文件模板...")
            
            # 创建config目录
            config_dir = self.project_root / "config"
            config_dir.mkdir(exist_ok=True)
            
            # 配置文件模板
            config_template = {
                "server": {
                    "host": "127.0.0.1",
                    "port": 7768,
                    "reload": False
                },
                "database": {
                    "type": "postgresql",
                    "host": "localhost",
                    "port": 5432,
                    "user": "danmaku_user",
                    "password": "change_me_in_env",
                    "name": "danmaku_db",
                    "echo": False,
                    "pool_size": 10,
                    "max_overflow": 20,
                    "pool_timeout": 30,
                    "pool_recycle": 3600
                },
                "jwt": {
                    "secret_key": "change_me_secret_key",
                    "algorithm": "HS256",
                    "access_token_expire_minutes": 1440
                },
                "admin": {
                    "username": "admin",
                    "password": "change_me_in_env",
                    "create_on_startup": True
                },
                "logging": {
                    "level": "INFO",
                    "file": "logs/danmaku_server.log"
                }
            }
            
            config_file = config_dir / "config.yml"
            if not config_file.exists():
                with open(config_file, "w", encoding="utf-8") as f:
                    yaml.dump(config_template, f, default_flow_style=False, allow_unicode=True)
                logger.info(f"✅ 配置模板已创建: {config_file}")
            else:
                logger.info("配置文件已存在，跳过创建")
            
            # 环境变量模板
            env_template = """# Misaka Danmu Server 环境变量配置

# 数据库配置
DATABASE_URL=postgresql+asyncpg://danmaku_user:change_me@localhost:5432/danmaku_db

# 或者分别配置数据库参数
DB_TYPE=postgresql
DB_HOST=localhost
DB_PORT=5432
DB_USER=danmaku_user
DB_PASSWORD=change_me
DB_NAME=danmaku_db

# JWT配置
JWT_SECRET_KEY=change_me_secret_key

# 服务器配置
SERVER_HOST=127.0.0.1
SERVER_PORT=7768

# 日志级别
LOG_LEVEL=INFO

# 开发模式
DEBUG=false
"""
            
            env_file = self.project_root / ".env.template"
            if not env_file.exists():
                with open(env_file, "w", encoding="utf-8") as f:
                    f.write(env_template)
                logger.info(f"✅ 环境变量模板已创建: {env_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置文件创建失败: {e}")
            return False
    
    def validate_configuration(self) -> bool:
        """验证配置"""
        try:
            logger.info("验证配置...")
            
            # 尝试加载配置
            from src.config import settings
            
            logger.info("✅ 配置加载成功")
            logger.info(f"  - 服务器: {settings.server.host}:{settings.server.port}")
            logger.info(f"  - 数据库类型: {settings.database.type}")
            logger.info(f"  - JWT算法: {settings.jwt.algorithm}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 配置验证失败: {e}")
            return False
    
    def create_startup_scripts(self):
        """创建启动脚本"""
        try:
            logger.info("创建启动脚本...")
            
            # 开发环境启动脚本
            dev_script = """#!/bin/bash
# Misaka Danmu Server 开发环境启动脚本

echo "🚀 启动 Misaka Danmu Server (开发模式)"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    uv sync
fi

# 启动应用
echo "启动应用..."
uv run python -m src.main_new

echo "✅ 应用已启动"
"""
            
            dev_script_file = self.project_root / "start_dev.sh"
            with open(dev_script_file, "w", encoding="utf-8") as f:
                f.write(dev_script)
            dev_script_file.chmod(0o755)
            
            # 生产环境启动脚本
            prod_script = """#!/bin/bash
# Misaka Danmu Server 生产环境启动脚本

echo "🚀 启动 Misaka Danmu Server (生产模式)"

# 检查配置
if [ ! -f ".env" ]; then
    echo "⚠️  警告：未找到.env文件，请配置环境变量"
fi

# 运行数据库迁移
echo "运行数据库迁移..."
uv run alembic upgrade head

# 启动应用（使用uvicorn生产配置）
echo "启动应用..."
uv run uvicorn src.main_new:app \\
    --host 0.0.0.0 \\
    --port ${SERVER_PORT:-7768} \\
    --workers ${WORKERS:-4} \\
    --access-log \\
    --log-level info

echo "✅ 应用已启动"
"""
            
            prod_script_file = self.project_root / "start_prod.sh"
            with open(prod_script_file, "w", encoding="utf-8") as f:
                f.write(prod_script)
            prod_script_file.chmod(0o755)
            
            # Windows启动脚本
            windows_script = """@echo off
REM Misaka Danmu Server Windows启动脚本

echo 🚀 启动 Misaka Danmu Server

REM 检查虚拟环境
if not exist ".venv" (
    echo 创建虚拟环境...
    uv sync
)

REM 启动应用
echo 启动应用...
uv run python -m src.main_new

echo ✅ 应用已启动
pause
"""
            
            windows_script_file = self.project_root / "start.bat"
            with open(windows_script_file, "w", encoding="utf-8") as f:
                f.write(windows_script)
            
            logger.info("✅ 启动脚本已创建")
            logger.info(f"  - 开发环境: {dev_script_file}")
            logger.info(f"  - 生产环境: {prod_script_file}")
            logger.info(f"  - Windows: {windows_script_file}")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 启动脚本创建失败: {e}")
            return False
    
    async def run_health_check(self) -> bool:
        """运行健康检查"""
        try:
            logger.info("运行系统健康检查...")
            
            # 运行集成测试
            result = subprocess.run(
                ["uv", "run", "python", "integration_test.py"],
                cwd=self.project_root,
                capture_output=True,
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ 系统健康检查通过")
                return True
            else:
                logger.warning(f"⚠️  系统健康检查警告: {result.stderr}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 健康检查异常: {e}")
            return False
    
    async def deploy(self):
        """完整部署流程"""
        logger.info("🚀 开始 Misaka Danmu Server 部署")
        logger.info("=" * 60)
        
        steps = [
            ("检查依赖", self.check_dependencies),
            ("安装依赖", self.install_dependencies),
            ("创建配置模板", self.create_config_template),
            ("验证配置", self.validate_configuration),
            ("设置数据库", self.setup_database),
            ("创建启动脚本", self.create_startup_scripts),
            ("系统健康检查", self.run_health_check),
        ]
        
        for step_name, step_func in steps:
            logger.info(f"\\n📝 执行步骤: {step_name}")
            logger.info("-" * 30)
            
            if asyncio.iscoroutinefunction(step_func):
                success = await step_func()
            else:
                success = step_func()
            
            if not success:
                logger.error(f"❌ 步骤失败: {step_name}")
                return False
        
        logger.info("\\n" + "=" * 60)
        logger.info("🎉 部署完成！")
        logger.info("\\n📋 下一步操作:")
        logger.info("  1. 编辑 config/config.yml 配置文件")
        logger.info("  2. 创建 .env 文件（基于.env.template）")
        logger.info("  3. 配置数据库连接")
        logger.info("  4. 运行 ./start_dev.sh（开发环境）或 ./start_prod.sh（生产环境）")
        logger.info("\\n🔧 数据库迁移:")
        logger.info("  - 创建数据库: uv run alembic upgrade head")
        logger.info("\\n🌐 访问地址:")
        logger.info("  - API文档: http://localhost:7768/docs")
        logger.info("  - 健康检查: http://localhost:7768/health")
        
        return True


async def main():
    """主函数"""
    manager = DeploymentManager()
    success = await manager.deploy()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)