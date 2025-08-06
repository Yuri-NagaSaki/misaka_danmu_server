# 数据库分析文档

## 当前数据库架构完整分析

### 核心表结构

#### 1. 主体表 (Core Tables)

**anime (番剧主表)**
```sql
CREATE TABLE `anime` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `title` VARCHAR(255) NOT NULL,
    `type` ENUM('tv_series', 'movie', 'ova', 'other') NOT NULL DEFAULT 'tv_series',
    `image_url` VARCHAR(512) NULL,
    `season` INT NOT NULL DEFAULT 1,
    `episode_count` INT NULL DEFAULT NULL,
    `source_url` VARCHAR(512) NULL,
    `created_at` TIMESTAMP NULL,
    PRIMARY KEY (`id`),
    FULLTEXT INDEX `idx_title_fulltext` (`title`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**anime_sources (数据源关联表)**
```sql
CREATE TABLE `anime_sources` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `anime_id` BIGINT NOT NULL,
    `provider_name` VARCHAR(50) NOT NULL,
    `media_id` VARCHAR(255) NOT NULL,
    `is_favorited` BOOLEAN NOT NULL DEFAULT FALSE,
    `created_at` TIMESTAMP NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_anime_provider_media_unique` (`anime_id`, `provider_name`, `media_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**episode (分集表)**
```sql
CREATE TABLE `episode` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `source_id` BIGINT NOT NULL,
    `title` VARCHAR(255) NOT NULL,
    `episode_index` INT NOT NULL,
    `provider_episode_id` VARCHAR(255) NULL,
    `source_url` VARCHAR(512) NULL,
    `fetched_at` TIMESTAMP NULL,
    `comment_count` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_source_episode_unique` (`source_id`, `episode_index`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**comment (弹幕评论表)**
```sql
CREATE TABLE `comment` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `cid` VARCHAR(255) NOT NULL,
    `episode_id` BIGINT NOT NULL,
    `p` VARCHAR(255) NOT NULL,
    `m` TEXT NOT NULL,
    `t` DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_episode_cid_unique` (`episode_id`, `cid`),
    INDEX `idx_episode_time` (`episode_id`, `t`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 2. 元数据表 (Metadata Tables)

**anime_metadata (番剧元数据)**
```sql
CREATE TABLE `anime_metadata` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `anime_id` BIGINT NOT NULL,
    `tmdb_id` VARCHAR(50) NULL,
    `tmdb_episode_group_id` VARCHAR(50) NULL,
    `imdb_id` VARCHAR(50) NULL,
    `tvdb_id` VARCHAR(50) NULL,
    `douban_id` VARCHAR(50) NULL,
    `bangumi_id` VARCHAR(50) NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_anime_id_unique` (`anime_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**anime_aliases (番剧别名)**
```sql
CREATE TABLE `anime_aliases` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `anime_id` BIGINT NOT NULL,
    `name_en` VARCHAR(255) NULL,
    `name_jp` VARCHAR(255) NULL,
    `name_romaji` VARCHAR(255) NULL,
    `alias_cn_1` VARCHAR(255) NULL,
    `alias_cn_2` VARCHAR(255) NULL,
    `alias_cn_3` VARCHAR(255) NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_anime_id_unique` (`anime_id`),
    CONSTRAINT `fk_aliases_anime` FOREIGN KEY (`anime_id`) REFERENCES `anime`(`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**tmdb_episode_mapping (TMDB分集映射)**
```sql
CREATE TABLE `tmdb_episode_mapping` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `tmdb_tv_id` INT NOT NULL,
    `tmdb_episode_group_id` VARCHAR(50) NOT NULL,
    `tmdb_episode_id` INT NOT NULL,
    `tmdb_season_number` INT NOT NULL,
    `tmdb_episode_number` INT NOT NULL,
    `custom_season_number` INT NOT NULL,
    `custom_episode_number` INT NOT NULL,
    `absolute_episode_number` INT NOT NULL,
    PRIMARY KEY (`id`),
    UNIQUE KEY `idx_group_episode_unique` (`tmdb_episode_group_id`, `tmdb_episode_id`),
    INDEX `idx_custom_season_episode` (`tmdb_tv_id`, `tmdb_episode_group_id`, `custom_season_number`, `custom_episode_number`),
    INDEX `idx_absolute_episode` (`tmdb_tv_id`, `tmdb_episode_group_id`, `absolute_episode_number`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 3. 用户认证表 (Authentication Tables)

**users (用户表)**
```sql
CREATE TABLE `users` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `username` VARCHAR(50) NOT NULL,
    `hashed_password` VARCHAR(255) NOT NULL,
    `token` TEXT NULL,
    `token_update` TIMESTAMP NULL,
    `created_at` TIMESTAMP NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_username_unique` (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**api_tokens (API令牌表)**
```sql
CREATE TABLE `api_tokens` (
    `id` INT NOT NULL AUTO_INCREMENT,
    `name` VARCHAR(100) NOT NULL,
    `token` VARCHAR(50) NOT NULL,
    `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE,
    `created_at` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `expires_at` TIMESTAMP NULL DEFAULT NULL,
    PRIMARY KEY (`id`),
    UNIQUE INDEX `idx_token_unique` (`token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**token_access_logs (令牌访问日志)**
```sql
CREATE TABLE `token_access_logs` (
    `id` BIGINT NOT NULL AUTO_INCREMENT,
    `token_id` INT NOT NULL,
    `ip_address` VARCHAR(45) NOT NULL,
    `user_agent` TEXT NULL,
    `access_time` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    `status` VARCHAR(50) NOT NULL,
    `path` VARCHAR(512) NULL,
    PRIMARY KEY (`id`),
    INDEX `idx_token_id_time` (`token_id`, `access_time` DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

#### 4. 系统配置表 (System Tables)

**scrapers (爬虫配置)**
```sql
CREATE TABLE `scrapers` (
    `provider_name` VARCHAR(50) NOT NULL,
    `is_enabled` BOOLEAN NOT NULL DEFAULT TRUE,
    `display_order` INT NOT NULL DEFAULT 0,
    PRIMARY KEY (`provider_name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**config (系统配置)**
```sql
CREATE TABLE `config` (
    `config_key` VARCHAR(100) NOT NULL,
    `config_value` VARCHAR(255) NOT NULL,
    `description` TEXT NULL,
    PRIMARY KEY (`config_key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

**cache_data (缓存数据)**
```sql
CREATE TABLE `cache_data` (
    `cache_provider` VARCHAR(50) NULL,
    `cache_key` VARCHAR(255) NOT NULL,
    `cache_value` LONGTEXT NOT NULL,
    `expires_at` TIMESTAMP NOT NULL,
    PRIMARY KEY (`cache_key`),
    INDEX `idx_expires_at` (`expires_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### 数据库关系图

```
anime (1) ---> (N) anime_sources ---> (N) episode ---> (N) comment
  |                                        ^
  |                                        |
  +--> anime_metadata                      |
  |                                        |
  +--> anime_aliases                       |
  |                                        |
  +--> tmdb_episode_mapping ---------------+
  
users (1) ---> (N) api_tokens ---> (N) token_access_logs
  |
  +--> bangumi_auth
  |
  +--> oauth_states

scrapers (配置表)
config (配置表) 
cache_data (缓存表)
```

### 外键约束

1. **anime_aliases.anime_id** → **anime.id** (CASCADE DELETE)
2. **anime_sources.anime_id** → **anime.id** (隐式，通过应用层维护)
3. **episode.source_id** → **anime_sources.id** (隐式)
4. **comment.episode_id** → **episode.id** (隐式)

### 索引策略

#### FULLTEXT 索引
- `anime.title` - 用于番剧标题全文搜索

#### 唯一索引
- `anime_sources(anime_id, provider_name, media_id)` - 防止重复数据源
- `episode(source_id, episode_index)` - 防止重复分集
- `comment(episode_id, cid)` - 防止重复弹幕

#### 复合索引
- `comment(episode_id, t)` - 按分集和时间查询弹幕
- `tmdb_episode_mapping` - 多个复合索引支持不同查询模式

### 数据类型选择

1. **字符集**: 全部使用 `utf8mb4` 支持完整Unicode
2. **时间类型**: 使用 `TIMESTAMP` 而非 `DATETIME`
3. **大整数**: 主键使用 `BIGINT` 应对大数据量
4. **枚举类型**: `anime.type` 使用 ENUM 限制值范围
5. **文本类型**: 弹幕内容使用 `TEXT`，URL使用 `VARCHAR(512)`

### 特殊设计考虑

1. **软外键**: 大部分外键关系通过应用层维护，提高性能
2. **缓存策略**: 专门的缓存表而非Redis，简化部署
3. **分集映射**: 复杂的TMDB映射表支持自定义季度/集数
4. **搜索优化**: 结合FULLTEXT和LIKE搜索的回退机制
5. **事务安全**: 关键操作使用事务保证数据一致性