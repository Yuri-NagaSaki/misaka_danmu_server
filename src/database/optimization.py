"""
数据库优化配置

包含数据库特定的优化设置和约束
"""

from typing import Dict, Any
from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlalchemy.pool import Pool

from .models.base import Base


class DatabaseOptimizer:
    """数据库优化器"""
    
    @staticmethod
    def configure_mysql_optimizations(engine: Engine) -> None:
        """MySQL特定优化"""
        
        @event.listens_for(engine, "connect")
        def set_mysql_pragmas(dbapi_connection, connection_record):
            """设置MySQL连接参数"""
            with dbapi_connection.cursor() as cursor:
                # 设置字符集
                cursor.execute("SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci")
                # 设置时区
                cursor.execute("SET time_zone = '+00:00'")
                # 设置SQL模式
                cursor.execute("SET sql_mode = 'STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO'")
                # 设置隔离级别
                cursor.execute("SET SESSION TRANSACTION ISOLATION LEVEL READ COMMITTED")
    
    @staticmethod
    def configure_postgresql_optimizations(engine: Engine) -> None:
        """PostgreSQL特定优化"""
        
        @event.listens_for(engine, "connect") 
        def set_postgresql_pragmas(dbapi_connection, connection_record):
            """设置PostgreSQL连接参数"""
            with dbapi_connection.cursor() as cursor:
                # 设置时区
                cursor.execute("SET timezone TO 'UTC'")
                # 设置客户端编码
                cursor.execute("SET client_encoding TO 'UTF8'")
    
    @staticmethod
    def configure_sqlite_optimizations(engine: Engine) -> None:
        """SQLite特定优化"""
        
        @event.listens_for(engine, "connect")
        def set_sqlite_pragmas(dbapi_connection, connection_record):
            """设置SQLite PRAGMA"""
            with dbapi_connection.cursor() as cursor:
                # 启用外键约束
                cursor.execute("PRAGMA foreign_keys=ON")
                # 设置日志模式
                cursor.execute("PRAGMA journal_mode=WAL")
                # 设置同步模式
                cursor.execute("PRAGMA synchronous=NORMAL")
                # 设置缓存大小
                cursor.execute("PRAGMA cache_size=10000")
                # 设置临时存储位置
                cursor.execute("PRAGMA temp_store=memory")
    
    @staticmethod
    def get_create_table_kwargs(database_type: str) -> Dict[str, Any]:
        """获取创建表的额外参数"""
        if database_type == "mysql":
            return {
                'mysql_engine': 'InnoDB',
                'mysql_charset': 'utf8mb4',
                'mysql_collate': 'utf8mb4_unicode_ci',
                'mysql_row_format': 'DYNAMIC'
            }
        elif database_type == "postgresql":
            return {}
        elif database_type == "sqlite":
            return {}
        else:
            return {}
    
    @staticmethod
    def configure_connection_pool(database_type: str) -> Dict[str, Any]:
        """配置连接池参数"""
        base_config = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'echo': False,
        }
        
        if database_type == "mysql":
            base_config.update({
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
            })
        elif database_type == "postgresql":
            base_config.update({
                'pool_size': 10,
                'max_overflow': 20,
                'pool_timeout': 30,
            })
        elif database_type == "sqlite":
            # SQLite使用NullPool
            from sqlalchemy.pool import NullPool
            base_config.update({
                'poolclass': NullPool,
                'connect_args': {
                    'check_same_thread': False,
                    'timeout': 20
                }
            })
        
        return base_config


def configure_database_optimizations(engine: Engine, database_type: str) -> None:
    """根据数据库类型配置优化"""
    optimizer = DatabaseOptimizer()
    
    if database_type == "mysql":
        optimizer.configure_mysql_optimizations(engine)
    elif database_type == "postgresql":
        optimizer.configure_postgresql_optimizations(engine)
    elif database_type == "sqlite":
        optimizer.configure_sqlite_optimizations(engine)


# 数据库特定的索引配置
DATABASE_SPECIFIC_INDEXES = {
    "mysql": {
        # MySQL FULLTEXT索引
        "anime": [
            ("idx_title_fulltext", ["title"], {"mysql_prefix": "FULLTEXT"})
        ]
    },
    "postgresql": {
        # PostgreSQL GIN索引用于全文搜索
        "anime": [
            ("idx_title_gin", ["title"], {"postgresql_using": "gin", "postgresql_ops": {"title": "gin_trgm_ops"}})
        ]
    },
    "sqlite": {
        # SQLite不支持FULLTEXT，使用普通索引
        "anime": [
            ("idx_title_like", ["title"], {})
        ]
    }
}


def get_database_specific_indexes(database_type: str) -> Dict[str, list]:
    """获取数据库特定的索引配置"""
    return DATABASE_SPECIFIC_INDEXES.get(database_type, {})