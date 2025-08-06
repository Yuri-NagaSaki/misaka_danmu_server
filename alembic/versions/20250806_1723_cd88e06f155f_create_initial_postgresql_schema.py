"""Create initial PostgreSQL schema

Revision ID: cd88e06f155f
Revises: 
Create Date: 2025-08-06 17:23:56.116181+08:00

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'cd88e06f155f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 创建枚举类型
    sa.Enum('TV_SERIES', 'OVA', 'ONA', 'MOVIE', 'SPECIAL', name='animetype').create(op.get_bind())
    
    # 创建基础配置表
    op.create_table('config',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('key', sa.String(length=100), nullable=False),
        sa.Column('value', sa.Text(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key')
    )
    
    # 创建缓存表
    op.create_table('cache_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('cache_key', sa.String(length=255), nullable=False),
        sa.Column('cache_value', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('cache_key')
    )
    
    # 创建爬虫配置表
    op.create_table('scraper',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('last_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('next_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # 创建定时任务表
    op.create_table('scheduled_task',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('cron_expression', sa.String(length=100), nullable=False),
        sa.Column('function_path', sa.String(length=255), nullable=False),
        sa.Column('parameters', sa.JSON(), nullable=True),
        sa.Column('enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('last_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('next_run', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    
    # 创建任务历史表
    op.create_table('task_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_name', sa.String(length=100), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('start_time', sa.TIMESTAMP(), nullable=False),
        sa.Column('end_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('result', sa.JSON(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建用户表
    op.create_table('user',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(length=50), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('current_token', sa.String(length=512), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    # 创建API令牌表
    op.create_table('api_token',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('token', sa.String(length=255), nullable=False),
        sa.Column('is_enabled', sa.Boolean(), nullable=True, default=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token')
    )
    
    # 创建令牌访问日志表
    op.create_table('token_access_log',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('token_id', sa.Integer(), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('access_time', sa.TIMESTAMP(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('path', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['token_id'], ['api_token.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建UA规则表
    op.create_table('ua_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('user_agent', sa.Text(), nullable=False),
        sa.Column('headers', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建OAuth状态表
    op.create_table('oauth_state',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=255), nullable=False),
        sa.Column('provider', sa.String(length=50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('state')
    )
    
    # 创建Bangumi认证表
    op.create_table('bangumi_auth',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('bangumi_user_id', sa.String(length=50), nullable=False),
        sa.Column('access_token', sa.String(length=512), nullable=False),
        sa.Column('refresh_token', sa.String(length=512), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id')
    )
    
    # 创建番剧表
    op.create_table('anime',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('type', sa.Enum('TV_SERIES', 'OVA', 'ONA', 'MOVIE', 'SPECIAL', name='animetype'), nullable=True),
        sa.Column('season', sa.Integer(), nullable=True),
        sa.Column('year', sa.Integer(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('poster_url', sa.String(length=512), nullable=True),
        sa.Column('banner_url', sa.String(length=512), nullable=True),
        sa.Column('total_episodes', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=True),
        sa.Column('rating', sa.DECIMAL(precision=3, scale=1), nullable=True),
        sa.Column('tags', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建番剧元数据表
    op.create_table('anime_metadata',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anime_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.String(length=100), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['anime_id'], ['anime.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建番剧别名表
    op.create_table('anime_alias',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anime_id', sa.Integer(), nullable=False),
        sa.Column('language', sa.String(length=10), nullable=False),
        sa.Column('alias', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['anime_id'], ['anime.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建番剧数据源表
    op.create_table('anime_source',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anime_id', sa.Integer(), nullable=False),
        sa.Column('provider_name', sa.String(length=50), nullable=False),
        sa.Column('media_id', sa.String(length=100), nullable=False),
        sa.Column('season_id', sa.String(length=100), nullable=True),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.Column('config', sa.JSON(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['anime_id'], ['anime.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建TMDB剧集映射表
    op.create_table('tmdb_episode_mapping',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('anime_id', sa.Integer(), nullable=False),
        sa.Column('tmdb_id', sa.String(length=50), nullable=False),
        sa.Column('season_number', sa.Integer(), nullable=False),
        sa.Column('episode_number', sa.Integer(), nullable=False),
        sa.Column('local_episode_number', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['anime_id'], ['anime.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建分集表
    op.create_table('episode',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('episode_index', sa.Integer(), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('air_date', sa.Date(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=512), nullable=True),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['source_id'], ['anime_source.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建弹幕评论表
    op.create_table('comment',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('episode_id', sa.Integer(), nullable=False),
        sa.Column('cid', sa.String(length=100), nullable=False),
        sa.Column('p', sa.String(length=255), nullable=False),
        sa.Column('m', sa.Text(), nullable=False),
        sa.Column('t', sa.DECIMAL(precision=10, scale=3), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=True),
        sa.ForeignKeyConstraint(['episode_id'], ['episode.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建索引以优化性能
    op.create_index('idx_anime_title', 'anime', ['title'])
    op.create_index('idx_anime_year', 'anime', ['year'])
    op.create_index('idx_anime_type', 'anime', ['type'])
    
    op.create_index('idx_anime_metadata_anime_id', 'anime_metadata', ['anime_id'])
    op.create_index('idx_anime_metadata_source', 'anime_metadata', ['source'])
    
    op.create_index('idx_anime_alias_anime_id', 'anime_alias', ['anime_id'])
    op.create_index('idx_anime_alias_alias', 'anime_alias', ['alias'])
    
    op.create_index('idx_anime_source_anime_id', 'anime_source', ['anime_id'])
    op.create_index('idx_anime_source_provider', 'anime_source', ['provider_name'])
    
    op.create_index('idx_episode_source_id', 'episode', ['source_id'])
    op.create_index('idx_episode_index', 'episode', ['episode_index'])
    
    op.create_index('idx_comment_episode_id', 'comment', ['episode_id'])
    op.create_index('idx_comment_cid', 'comment', ['cid'])
    op.create_index('idx_comment_t', 'comment', ['t'])
    
    op.create_index('idx_task_history_task_name', 'task_history', ['task_name'])
    op.create_index('idx_task_history_status', 'task_history', ['status'])
    op.create_index('idx_task_history_start_time', 'task_history', ['start_time'])
    
    op.create_index('idx_token_access_log_token_id', 'token_access_log', ['token_id'])
    op.create_index('idx_token_access_log_access_time', 'token_access_log', ['access_time'])


def downgrade() -> None:
    # 删除索引
    op.drop_index('idx_token_access_log_access_time')
    op.drop_index('idx_token_access_log_token_id')
    op.drop_index('idx_task_history_start_time')
    op.drop_index('idx_task_history_status')
    op.drop_index('idx_task_history_task_name')
    op.drop_index('idx_comment_t')
    op.drop_index('idx_comment_cid')
    op.drop_index('idx_comment_episode_id')
    op.drop_index('idx_episode_index')
    op.drop_index('idx_episode_source_id')
    op.drop_index('idx_anime_source_provider')
    op.drop_index('idx_anime_source_anime_id')
    op.drop_index('idx_anime_alias_alias')
    op.drop_index('idx_anime_alias_anime_id')
    op.drop_index('idx_anime_metadata_source')
    op.drop_index('idx_anime_metadata_anime_id')
    op.drop_index('idx_anime_type')
    op.drop_index('idx_anime_year')
    op.drop_index('idx_anime_title')
    
    # 删除表（按依赖关系逆序删除）
    op.drop_table('comment')
    op.drop_table('episode')
    op.drop_table('tmdb_episode_mapping')
    op.drop_table('anime_source')
    op.drop_table('anime_alias')
    op.drop_table('anime_metadata')
    op.drop_table('anime')
    op.drop_table('bangumi_auth')
    op.drop_table('oauth_state')
    op.drop_table('ua_rules')
    op.drop_table('token_access_log')
    op.drop_table('api_token')
    op.drop_table('user')
    op.drop_table('task_history')
    op.drop_table('scheduled_task')
    op.drop_table('scraper')
    op.drop_table('cache_data')
    op.drop_table('config')
    
    # 删除枚举类型
    sa.Enum(name='animetype').drop(op.get_bind())