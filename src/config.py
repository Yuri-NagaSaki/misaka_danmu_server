import yaml
from pathlib import Path
from typing import Any, Dict, Tuple, Optional

from pydantic import BaseModel
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, EnvSettingsSource

# 1. 为配置的不同部分创建 Pydantic 模型，提供类型提示和默认值
class ServerConfig(BaseModel):
    host: str = "127.0.0.1"
    port: int = 7768

class DatabaseConfig(BaseModel):
    # 数据库类型：mysql, postgresql, sqlite
    type: str = "mysql"
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = "password"
    name: str = "danmaku_db"
    
    # SQLAlchemy 引擎配置
    echo: bool = False              # 是否输出SQL日志
    pool_size: int = 10            # 连接池大小
    max_overflow: int = 20         # 最大溢出连接
    pool_timeout: int = 30         # 获取连接超时（秒）
    pool_recycle: int = 3600       # 连接回收时间（秒）
    
    @property
    def async_url(self) -> str:
        """构建异步数据库URL"""
        if self.type == "mysql":
            return f"mysql+aiomysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?charset=utf8mb4"
        elif self.type == "postgresql":
            return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        elif self.type == "sqlite":
            # SQLite 不需要用户名密码和主机
            return f"sqlite+aiosqlite:///{self.name}.db"
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")
    
    @property
    def sync_url(self) -> str:
        """构建同步数据库URL（用于Alembic迁移）"""
        if self.type == "mysql":
            return f"mysql+pymysql://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}?charset=utf8mb4"
        elif self.type == "postgresql":
            return f"postgresql+psycopg2://{self.user}:{self.password}@{self.host}:{self.port}/{self.name}"
        elif self.type == "sqlite":
            return f"sqlite:///{self.name}.db"
        else:
            raise ValueError(f"不支持的数据库类型: {self.type}")
    
    def get_engine_config(self) -> Dict[str, Any]:
        """获取SQLAlchemy引擎配置"""
        config = {
            "echo": self.echo,
            "pool_pre_ping": True,
            "pool_recycle": self.pool_recycle,
        }
        
        if self.type == "sqlite":
            # SQLite 特殊配置
            from sqlalchemy.pool import NullPool
            config.update({
                "poolclass": NullPool,
                "connect_args": {"check_same_thread": False},
            })
        else:
            # MySQL/PostgreSQL 异步配置 - 不指定poolclass让SQLAlchemy自动选择
            config.update({
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_timeout": self.pool_timeout,
            })
        
        return config

class JWTConfig(BaseModel):
    secret_key: str = "a_very_secret_key_that_should_be_changed"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 1440 # 1 day

# 4. (新增) 初始管理员配置
class AdminConfig(BaseModel):
    initial_user: Optional[str] = None
    initial_password: Optional[str] = None

# 5. (新增) Bangumi OAuth 配置
class BangumiConfig(BaseModel):
    client_id: str = "bgm4222688b7532ef439"
    client_secret: str = "379c426b8f26b561642334445761361f"

# 2. 创建一个自定义的配置源，用于从 YAML 文件加载设置
class YamlConfigSettingsSource(PydanticBaseSettingsSource):
    def __init__(self, settings_cls: type[BaseSettings]):
        super().__init__(settings_cls)
        # 在项目根目录的 config/ 文件夹下查找 config.yml
        self.yaml_file = Path(__file__).parent.parent / "config" / "config.yml"

    def get_field_value(self, field, field_name):
        return None, None, False

    def __call__(self) -> Dict[str, Any]:
        if not self.yaml_file.is_file():
            return {}
        with open(self.yaml_file, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}


# (新增) 豆瓣配置
class DoubanConfig(BaseModel):
    cookie: Optional[str] = None


# 3. 定义主设置类，它将聚合所有配置
class Settings(BaseSettings):
    server: ServerConfig = ServerConfig()
    database: DatabaseConfig = DatabaseConfig()
    jwt: JWTConfig = JWTConfig()
    admin: AdminConfig = AdminConfig()
    bangumi: BangumiConfig = BangumiConfig()
    douban: DoubanConfig = DoubanConfig()
    class Config:
        # 为环境变量设置前缀，避免与系统变量冲突
        # 例如，在容器中设置环境变量 DANMUAPI_SERVER__PORT=8080
        env_prefix = "DANMUAPI_"
        case_sensitive = False
        env_nested_delimiter = '__'

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # 定义加载源的优先级:
        # 1. 环境变量 (最高)
        # 2. .env 文件
        # 3. YAML 文件
        # 4. 文件密钥
        # 5. Pydantic 模型中的默认值 (最低)
        return (
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
            init_settings,
        )


settings = Settings()
