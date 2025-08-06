-- Test Generated SQL

CREATE TYPE animetype AS ENUM ('TV_SERIES', 'MOVIE', 'OVA', 'OTHER')


CREATE TABLE anime (
	title VARCHAR(255) NOT NULL, 
	type animetype NOT NULL, 
	image_url VARCHAR(512), 
	season INTEGER NOT NULL, 
	episode_count INTEGER, 
	source_url VARCHAR(512), 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id)
)



CREATE INDEX idx_type ON anime (type)

CREATE INDEX idx_title_fulltext ON anime (title)

CREATE INDEX idx_created_at ON anime (created_at)

CREATE INDEX idx_title_season ON anime (title, season)

COMMENT ON COLUMN anime.title IS '番剧标题'

COMMENT ON COLUMN anime.type IS '番剧类型'

COMMENT ON COLUMN anime.image_url IS '封面图片URL'

COMMENT ON COLUMN anime.season IS '季度'

COMMENT ON COLUMN anime.episode_count IS '总集数'

COMMENT ON COLUMN anime.source_url IS '来源URL'

COMMENT ON COLUMN anime.id IS '主键ID'

COMMENT ON COLUMN anime.created_at IS '创建时间'

COMMENT ON COLUMN anime.updated_at IS '更新时间'


CREATE TABLE tmdb_episode_mapping (
	tmdb_tv_id INTEGER NOT NULL, 
	tmdb_episode_group_id VARCHAR(50) NOT NULL, 
	tmdb_episode_id INTEGER NOT NULL, 
	tmdb_season_number INTEGER NOT NULL, 
	tmdb_episode_number INTEGER NOT NULL, 
	custom_season_number INTEGER NOT NULL, 
	custom_episode_number INTEGER NOT NULL, 
	absolute_episode_number INTEGER NOT NULL, 
	id BIGSERIAL NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT idx_group_episode_unique UNIQUE (tmdb_episode_group_id, tmdb_episode_id)
)



CREATE INDEX idx_absolute_episode ON tmdb_episode_mapping (tmdb_tv_id, tmdb_episode_group_id, absolute_episode_number)

CREATE INDEX idx_custom_season_episode ON tmdb_episode_mapping (tmdb_tv_id, tmdb_episode_group_id, custom_season_number, custom_episode_number)

CREATE INDEX idx_tmdb_tv_id ON tmdb_episode_mapping (tmdb_tv_id)

COMMENT ON COLUMN tmdb_episode_mapping.tmdb_tv_id IS 'TMDB电视剧ID'

COMMENT ON COLUMN tmdb_episode_mapping.tmdb_episode_group_id IS 'TMDB剧集组ID'

COMMENT ON COLUMN tmdb_episode_mapping.tmdb_episode_id IS 'TMDB分集ID'

COMMENT ON COLUMN tmdb_episode_mapping.tmdb_season_number IS 'TMDB原始季度号'

COMMENT ON COLUMN tmdb_episode_mapping.tmdb_episode_number IS 'TMDB原始分集号'

COMMENT ON COLUMN tmdb_episode_mapping.custom_season_number IS '自定义季度号'

COMMENT ON COLUMN tmdb_episode_mapping.custom_episode_number IS '自定义分集号'

COMMENT ON COLUMN tmdb_episode_mapping.absolute_episode_number IS '绝对分集号'

COMMENT ON COLUMN tmdb_episode_mapping.id IS '主键ID'


CREATE TABLE users (
	username VARCHAR(50) NOT NULL, 
	hashed_password VARCHAR(255) NOT NULL, 
	token TEXT, 
	token_update TIMESTAMP WITHOUT TIME ZONE, 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT idx_username_unique UNIQUE (username)
)



CREATE INDEX idx_username ON users (username)

CREATE INDEX idx_token_update ON users (token_update)

COMMENT ON COLUMN users.username IS '用户名'

COMMENT ON COLUMN users.hashed_password IS '哈希后的密码'

COMMENT ON COLUMN users.token IS '当前JWT令牌'

COMMENT ON COLUMN users.token_update IS '令牌更新时间'

COMMENT ON COLUMN users.id IS '主键ID'

COMMENT ON COLUMN users.created_at IS '创建时间'

COMMENT ON COLUMN users.updated_at IS '更新时间'


CREATE TABLE api_tokens (
	name VARCHAR(100) NOT NULL, 
	token VARCHAR(50) NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT idx_token_unique UNIQUE (token)
)



CREATE INDEX idx_is_enabled ON api_tokens (is_enabled)

CREATE INDEX idx_token ON api_tokens (token)

CREATE INDEX idx_expires_at ON api_tokens (expires_at)

COMMENT ON COLUMN api_tokens.name IS '令牌名称'

COMMENT ON COLUMN api_tokens.token IS '令牌字符串'

COMMENT ON COLUMN api_tokens.is_enabled IS '是否启用'

COMMENT ON COLUMN api_tokens.expires_at IS '过期时间'

COMMENT ON COLUMN api_tokens.id IS '主键ID'

COMMENT ON COLUMN api_tokens.created_at IS '创建时间'

COMMENT ON COLUMN api_tokens.updated_at IS '更新时间'


CREATE TABLE ua_rules (
	ua_string VARCHAR(255) NOT NULL, 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT idx_ua_string_unique UNIQUE (ua_string)
)



CREATE INDEX idx_ua_string ON ua_rules (ua_string)

COMMENT ON COLUMN ua_rules.ua_string IS 'User-Agent字符串'

COMMENT ON COLUMN ua_rules.id IS '主键ID'

COMMENT ON COLUMN ua_rules.created_at IS '创建时间'

COMMENT ON COLUMN ua_rules.updated_at IS '更新时间'


CREATE TABLE config (
	config_key VARCHAR(100) NOT NULL, 
	config_value VARCHAR(255) NOT NULL, 
	description TEXT, 
	PRIMARY KEY (config_key)
)



COMMENT ON COLUMN config.config_key IS '配置键'

COMMENT ON COLUMN config.config_value IS '配置值'

COMMENT ON COLUMN config.description IS '配置描述'


CREATE TABLE cache_data (
	cache_key VARCHAR(255) NOT NULL, 
	cache_provider VARCHAR(50), 
	cache_value TEXT NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (cache_key)
)



CREATE INDEX idx_expires_at ON cache_data (expires_at)

CREATE INDEX idx_cache_provider ON cache_data (cache_provider)

COMMENT ON COLUMN cache_data.cache_key IS '缓存键'

COMMENT ON COLUMN cache_data.cache_provider IS '缓存提供商'

COMMENT ON COLUMN cache_data.cache_value IS '缓存值（JSON格式）'

COMMENT ON COLUMN cache_data.expires_at IS '过期时间'


CREATE TABLE scrapers (
	provider_name VARCHAR(50) NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	display_order INTEGER NOT NULL, 
	PRIMARY KEY (provider_name)
)



CREATE INDEX idx_display_order ON scrapers (display_order)

CREATE INDEX idx_is_enabled ON scrapers (is_enabled)

COMMENT ON COLUMN scrapers.provider_name IS '数据源提供商名称'

COMMENT ON COLUMN scrapers.is_enabled IS '是否启用'

COMMENT ON COLUMN scrapers.display_order IS '显示顺序'


CREATE TABLE scheduled_tasks (
	id VARCHAR(100) NOT NULL, 
	name VARCHAR(255) NOT NULL, 
	job_type VARCHAR(50) NOT NULL, 
	cron_expression VARCHAR(100) NOT NULL, 
	is_enabled BOOLEAN NOT NULL, 
	last_run_at TIMESTAMP WITHOUT TIME ZONE, 
	next_run_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)



CREATE INDEX idx_job_type ON scheduled_tasks (job_type)

CREATE INDEX idx_name ON scheduled_tasks (name)

CREATE INDEX idx_is_enabled ON scheduled_tasks (is_enabled)

CREATE INDEX idx_next_run_at ON scheduled_tasks (next_run_at)

COMMENT ON COLUMN scheduled_tasks.id IS '任务ID'

COMMENT ON COLUMN scheduled_tasks.name IS '任务名称'

COMMENT ON COLUMN scheduled_tasks.job_type IS '任务类型'

COMMENT ON COLUMN scheduled_tasks.cron_expression IS 'Cron表达式'

COMMENT ON COLUMN scheduled_tasks.is_enabled IS '是否启用'

COMMENT ON COLUMN scheduled_tasks.last_run_at IS '上次执行时间'

COMMENT ON COLUMN scheduled_tasks.next_run_at IS '下次执行时间'


CREATE TABLE task_history (
	id VARCHAR(100) NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	progress INTEGER NOT NULL, 
	description TEXT, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT 'CURRENT_TIMESTAMP' NOT NULL, 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT 'CURRENT_TIMESTAMP' NOT NULL, 
	finished_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (id)
)



CREATE INDEX idx_title ON task_history (title)

CREATE INDEX idx_created_at ON task_history (created_at)

CREATE INDEX idx_status ON task_history (status)

CREATE INDEX idx_finished_at ON task_history (finished_at)

COMMENT ON COLUMN task_history.id IS '任务ID'

COMMENT ON COLUMN task_history.title IS '任务标题'

COMMENT ON COLUMN task_history.status IS '任务状态'

COMMENT ON COLUMN task_history.progress IS '任务进度(0-100)'

COMMENT ON COLUMN task_history.description IS '任务描述'

COMMENT ON COLUMN task_history.created_at IS '创建时间'

COMMENT ON COLUMN task_history.updated_at IS '更新时间'

COMMENT ON COLUMN task_history.finished_at IS '完成时间'


CREATE TABLE anime_sources (
	anime_id BIGINT NOT NULL, 
	provider_name VARCHAR(50) NOT NULL, 
	media_id VARCHAR(255) NOT NULL, 
	is_favorited BOOLEAN NOT NULL, 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT idx_anime_provider_media_unique UNIQUE (anime_id, provider_name, media_id), 
	FOREIGN KEY(anime_id) REFERENCES anime (id) ON DELETE CASCADE
)



CREATE INDEX idx_is_favorited ON anime_sources (is_favorited)

CREATE INDEX idx_provider_name ON anime_sources (provider_name)

CREATE INDEX idx_anime_id ON anime_sources (anime_id)

COMMENT ON COLUMN anime_sources.anime_id IS '关联的番剧ID'

COMMENT ON COLUMN anime_sources.provider_name IS '数据源提供商名称'

COMMENT ON COLUMN anime_sources.media_id IS '在该数据源中的媒体ID'

COMMENT ON COLUMN anime_sources.is_favorited IS '是否为精确匹配的数据源'

COMMENT ON COLUMN anime_sources.id IS '主键ID'

COMMENT ON COLUMN anime_sources.created_at IS '创建时间'

COMMENT ON COLUMN anime_sources.updated_at IS '更新时间'


CREATE TABLE anime_metadata (
	anime_id BIGINT NOT NULL, 
	tmdb_id VARCHAR(50), 
	tmdb_episode_group_id VARCHAR(50), 
	imdb_id VARCHAR(50), 
	tvdb_id VARCHAR(50), 
	douban_id VARCHAR(50), 
	bangumi_id VARCHAR(50), 
	id BIGSERIAL NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT idx_anime_id_unique UNIQUE (anime_id), 
	FOREIGN KEY(anime_id) REFERENCES anime (id) ON DELETE CASCADE
)



CREATE INDEX idx_imdb_id ON anime_metadata (imdb_id)

CREATE INDEX idx_bangumi_id ON anime_metadata (bangumi_id)

CREATE INDEX idx_tmdb_id ON anime_metadata (tmdb_id)

COMMENT ON COLUMN anime_metadata.anime_id IS '关联的番剧ID'

COMMENT ON COLUMN anime_metadata.tmdb_id IS 'TMDB ID'

COMMENT ON COLUMN anime_metadata.tmdb_episode_group_id IS 'TMDB 剧集组ID'

COMMENT ON COLUMN anime_metadata.imdb_id IS 'IMDb ID'

COMMENT ON COLUMN anime_metadata.tvdb_id IS 'TVDB ID'

COMMENT ON COLUMN anime_metadata.douban_id IS '豆瓣ID'

COMMENT ON COLUMN anime_metadata.bangumi_id IS 'Bangumi ID'

COMMENT ON COLUMN anime_metadata.id IS '主键ID'


CREATE TABLE anime_aliases (
	anime_id BIGINT NOT NULL, 
	name_en VARCHAR(255), 
	name_jp VARCHAR(255), 
	name_romaji VARCHAR(255), 
	alias_cn_1 VARCHAR(255), 
	alias_cn_2 VARCHAR(255), 
	alias_cn_3 VARCHAR(255), 
	id BIGSERIAL NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT idx_anime_id_unique UNIQUE (anime_id), 
	FOREIGN KEY(anime_id) REFERENCES anime (id) ON DELETE CASCADE
)



COMMENT ON COLUMN anime_aliases.anime_id IS '关联的番剧ID'

COMMENT ON COLUMN anime_aliases.name_en IS '英文名称'

COMMENT ON COLUMN anime_aliases.name_jp IS '日文名称'

COMMENT ON COLUMN anime_aliases.name_romaji IS '罗马音名称'

COMMENT ON COLUMN anime_aliases.alias_cn_1 IS '中文别名1'

COMMENT ON COLUMN anime_aliases.alias_cn_2 IS '中文别名2'

COMMENT ON COLUMN anime_aliases.alias_cn_3 IS '中文别名3'

COMMENT ON COLUMN anime_aliases.id IS '主键ID'


CREATE TABLE token_access_logs (
	token_id INTEGER NOT NULL, 
	ip_address VARCHAR(45) NOT NULL, 
	user_agent TEXT, 
	access_time TIMESTAMP WITHOUT TIME ZONE DEFAULT 'CURRENT_TIMESTAMP' NOT NULL, 
	status VARCHAR(50) NOT NULL, 
	path VARCHAR(512), 
	id BIGSERIAL NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(token_id) REFERENCES api_tokens (id) ON DELETE CASCADE
)



CREATE INDEX idx_token_id_time ON token_access_logs (token_id, access_time)

CREATE INDEX idx_access_time ON token_access_logs (access_time)

CREATE INDEX idx_ip_address ON token_access_logs (ip_address)

COMMENT ON COLUMN token_access_logs.token_id IS '关联的令牌ID'

COMMENT ON COLUMN token_access_logs.ip_address IS '访问IP地址'

COMMENT ON COLUMN token_access_logs.user_agent IS '用户代理字符串'

COMMENT ON COLUMN token_access_logs.access_time IS '访问时间'

COMMENT ON COLUMN token_access_logs.status IS '访问状态'

COMMENT ON COLUMN token_access_logs.path IS '访问路径'

COMMENT ON COLUMN token_access_logs.id IS '主键ID'


CREATE TABLE bangumi_auth (
	user_id BIGINT NOT NULL, 
	bangumi_user_id INTEGER, 
	nickname VARCHAR(255), 
	avatar_url VARCHAR(512), 
	access_token TEXT NOT NULL, 
	refresh_token TEXT, 
	expires_at TIMESTAMP WITHOUT TIME ZONE, 
	authorized_at TIMESTAMP WITHOUT TIME ZONE, 
	PRIMARY KEY (user_id), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)



CREATE INDEX idx_expires_at ON bangumi_auth (expires_at)

CREATE INDEX idx_bangumi_user_id ON bangumi_auth (bangumi_user_id)

COMMENT ON COLUMN bangumi_auth.user_id IS '关联的用户ID'

COMMENT ON COLUMN bangumi_auth.bangumi_user_id IS 'Bangumi用户ID'

COMMENT ON COLUMN bangumi_auth.nickname IS 'Bangumi昵称'

COMMENT ON COLUMN bangumi_auth.avatar_url IS '头像URL'

COMMENT ON COLUMN bangumi_auth.access_token IS '访问令牌'

COMMENT ON COLUMN bangumi_auth.refresh_token IS '刷新令牌'

COMMENT ON COLUMN bangumi_auth.expires_at IS '令牌过期时间'

COMMENT ON COLUMN bangumi_auth.authorized_at IS '授权时间'


CREATE TABLE oauth_states (
	state_key VARCHAR(100) NOT NULL, 
	user_id BIGINT NOT NULL, 
	expires_at TIMESTAMP WITHOUT TIME ZONE NOT NULL, 
	PRIMARY KEY (state_key), 
	FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE
)



CREATE INDEX idx_oauth_expires_at ON oauth_states (expires_at)

CREATE INDEX idx_user_id ON oauth_states (user_id)

COMMENT ON COLUMN oauth_states.state_key IS 'OAuth状态键'

COMMENT ON COLUMN oauth_states.user_id IS '关联的用户ID'

COMMENT ON COLUMN oauth_states.expires_at IS '过期时间'


CREATE TABLE episode (
	source_id BIGINT NOT NULL, 
	title VARCHAR(255) NOT NULL, 
	episode_index INTEGER NOT NULL, 
	provider_episode_id VARCHAR(255), 
	source_url VARCHAR(512), 
	fetched_at TIMESTAMP WITHOUT TIME ZONE, 
	comment_count INTEGER NOT NULL, 
	id BIGSERIAL NOT NULL, 
	created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT now(), 
	PRIMARY KEY (id), 
	CONSTRAINT idx_source_episode_unique UNIQUE (source_id, episode_index), 
	FOREIGN KEY(source_id) REFERENCES anime_sources (id) ON DELETE CASCADE
)



CREATE INDEX idx_source_id ON episode (source_id)

CREATE INDEX idx_comment_count ON episode (comment_count)

CREATE INDEX idx_fetched_at ON episode (fetched_at)

COMMENT ON COLUMN episode.source_id IS '关联的数据源ID'

COMMENT ON COLUMN episode.title IS '分集标题'

COMMENT ON COLUMN episode.episode_index IS '分集序号'

COMMENT ON COLUMN episode.provider_episode_id IS '数据源中的分集ID'

COMMENT ON COLUMN episode.source_url IS '分集源URL'

COMMENT ON COLUMN episode.fetched_at IS '获取时间'

COMMENT ON COLUMN episode.comment_count IS '弹幕数量'

COMMENT ON COLUMN episode.id IS '主键ID'

COMMENT ON COLUMN episode.created_at IS '创建时间'

COMMENT ON COLUMN episode.updated_at IS '更新时间'


CREATE TABLE comment (
	episode_id BIGINT NOT NULL, 
	cid VARCHAR(255) NOT NULL, 
	p VARCHAR(255) NOT NULL, 
	m TEXT NOT NULL, 
	t DECIMAL(10, 2) NOT NULL, 
	id BIGSERIAL NOT NULL, 
	PRIMARY KEY (id), 
	CONSTRAINT idx_episode_cid_unique UNIQUE (episode_id, cid), 
	FOREIGN KEY(episode_id) REFERENCES episode (id) ON DELETE CASCADE
)



CREATE INDEX idx_episode_time ON comment (episode_id, t)

CREATE INDEX idx_episode_id ON comment (episode_id)

CREATE INDEX idx_time ON comment (t)

COMMENT ON COLUMN comment.episode_id IS '关联的分集ID'

COMMENT ON COLUMN comment.cid IS '弹幕唯一标识符'

COMMENT ON COLUMN comment.p IS '弹幕参数（时间,模式,颜色,用户等）'

COMMENT ON COLUMN comment.m IS '弹幕内容'

COMMENT ON COLUMN comment.t IS '弹幕出现时间（秒）'

COMMENT ON COLUMN comment.id IS '主键ID'