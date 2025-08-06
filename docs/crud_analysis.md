# CRUD操作模式分析文档

## 当前CRUD操作完整分析

### 连接管理模式

#### 连接池模式
```python
# 统一的连接池获取模式
async with pool.acquire() as conn:
    async with conn.cursor(aiomysql.DictCursor) as cursor:
        # 数据库操作
```

#### 事务管理模式
```python
# 手动事务管理
try:
    await conn.begin()
    # 多个操作
    await conn.commit()
except Exception as e:
    await conn.rollback()
    raise
```

### 查询操作模式 (SELECT)

#### 1. 基础查询模式

**简单查询**
```python
async def get_user_by_id(pool: aiomysql.Pool, user_id: int):
    async with pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cursor:
            query = "SELECT id, username FROM users WHERE id = %s"
            await cursor.execute(query, (user_id,))
            return await cursor.fetchone()
```

**批量查询**
```python
async def get_library_anime(pool: aiomysql.Pool):
    query = """
        SELECT a.id as animeId, a.title, 
               COALESCE(a.episode_count, (subquery)) as episodeCount
        FROM anime a
        GROUP BY a.id
        ORDER BY a.created_at DESC
    """
```

#### 2. 复杂联接查询模式

**多表联接 + 子查询**
```python
async def search_episodes_in_library(pool, anime_title: str, episode_number: Optional[int]):
    query_template = f"""
        SELECT a.id AS animeId, e.id AS episodeId,
               CASE WHEN a.type = 'movie' THEN CONCAT(s.provider_name, ' 源')
                    ELSE e.title END AS episodeTitle,
               (SELECT COUNT(DISTINCT e_count.id) 
                FROM anime_sources s_count 
                JOIN episode e_count ON s_count.id = e_count.source_id 
                WHERE s_count.anime_id = a.id) as totalEpisodeCount
        FROM episode e
        JOIN anime_sources s ON e.source_id = s.id
        JOIN anime a ON s.anime_id = a.id
        JOIN scrapers sc ON s.provider_name = sc.provider_name
        LEFT JOIN anime_metadata m ON a.id = m.anime_id
        LEFT JOIN anime_aliases al ON a.id = al.anime_id
        WHERE {{title_condition}} {episode_condition}
        ORDER BY LENGTH(a.title) ASC, sc.display_order ASC
    """
```

#### 3. 搜索模式

**FULLTEXT搜索 + LIKE回退**
```python
# 1. 尝试FULLTEXT搜索
sanitized_for_ft = re.sub(r'[+\-><()~*@"]', ' ', clean_title).strip()
query_ft = "SELECT ... WHERE MATCH(a.title) AGAINST(%s IN BOOLEAN MODE)"
await cursor.execute(query_ft, (sanitized_for_ft + '*',))

# 2. 回退到LIKE搜索多个字段
if not results:
    normalized_like_title = f"%{clean_title.replace('：', ':').replace(' ', '')}%"
    like_conditions = [
        "REPLACE(REPLACE(a.title, '：', ':'), ' ', '') LIKE %s",
        "REPLACE(REPLACE(al.name_en, '：', ':'), ' ', '') LIKE %s",
        # ... 更多别名字段
    ]
```

#### 4. 条件动态构建模式

**动态WHERE子句**
```python
episode_condition = "AND e.episode_index = %s" if episode_number is not None else ""
params_episode = [episode_number] if episode_number is not None else []
season_condition = "AND a.season = %s" if season_number is not None else ""
params_season = [season_number] if season_number is not None else []

query = query_template.format(
    title_condition=title_condition,
    episode_condition=episode_condition,
    season_condition=season_condition
)
await cursor.execute(query, tuple(all_params))
```

### 插入操作模式 (INSERT)

#### 1. 基础插入模式

**简单插入**
```python
await cursor.execute(
    "INSERT INTO users (username, hashed_password, created_at) VALUES (%s, %s, %s)",
    (user.username, hashed_password, datetime.now())
)
return cursor.lastrowid
```

#### 2. 条件插入模式

**INSERT IGNORE模式**
```python
await cursor.execute(
    "INSERT IGNORE INTO anime_sources (anime_id, provider_name, media_id, created_at) VALUES (%s, %s, %s, %s)",
    (anime_id, provider, media_id, datetime.now())
)
```

**UPSERT模式 (ON DUPLICATE KEY UPDATE)**
```python
query = """
    INSERT INTO config (config_key, config_value)
    VALUES (%s, %s)
    AS new_values
    ON DUPLICATE KEY UPDATE config_value = new_values.config_value
"""
await cursor.execute(query, (key, value))
```

#### 3. 批量插入模式

**executemany批量插入**
```python
query = "INSERT IGNORE INTO comment (episode_id, cid, p, m, t) VALUES (%s, %s, %s, %s, %s)"
data_to_insert = [(episode_id, c['cid'], c['p'], c['m'], c['t']) for c in comments]
affected_rows = await cursor.executemany(query, data_to_insert)
```

#### 4. 事务插入模式

**多表关联插入**
```python
try:
    await conn.begin()
    # 插入主表
    await cursor.execute("INSERT INTO anime (...) VALUES (...)")
    anime_id = cursor.lastrowid
    # 插入关联表
    await cursor.execute("INSERT INTO anime_metadata (anime_id) VALUES (%s)", (anime_id,))
    await cursor.execute("INSERT INTO anime_aliases (anime_id) VALUES (%s)", (anime_id,))
    await conn.commit()
    return anime_id
except Exception as e:
    await conn.rollback()
    raise
```

### 更新操作模式 (UPDATE)

#### 1. 基础更新模式

**简单更新**
```python
query = "UPDATE users SET hashed_password = %s WHERE username = %s"
await cursor.execute(query, (new_hashed_password, username))
```

#### 2. 条件更新模式

**动态字段更新**
```python
updates, params = [], []
if not current.get('tmdb_id') and tmdb_id: 
    updates.append("tmdb_id = %s"); params.append(tmdb_id)
if not current.get('imdb_id') and imdb_id: 
    updates.append("imdb_id = %s"); params.append(imdb_id)

if updates:
    query = f"UPDATE anime_metadata SET {', '.join(updates)} WHERE anime_id = %s"
    params.append(anime_id)
    await cursor.execute(query, tuple(params))
```

#### 3. 复杂更新模式

**切换逻辑更新**
```python
# 先重置其他记录
await cursor.execute(
    "UPDATE anime_sources SET is_favorited = FALSE WHERE anime_id = %s AND id != %s", 
    (anime_id, source_id)
)
# 再切换目标记录
await cursor.execute(
    "UPDATE anime_sources SET is_favorited = NOT is_favorited WHERE id = %s", 
    (source_id,)
)
```

### 删除操作模式 (DELETE)

#### 1. 简单删除模式
```python
affected_rows = await cursor.execute("DELETE FROM api_tokens WHERE id = %s", (token_id,))
return affected_rows > 0
```

#### 2. 级联删除模式

**手动级联删除**
```python
# 获取要删除的子记录ID
await cursor.execute("SELECT id FROM episode WHERE source_id = %s", (source_id,))
episode_ids = [row[0] for row in await cursor.fetchall()]

if episode_ids:
    # 删除孙记录
    format_strings = ','.join(['%s'] * len(episode_ids))
    await cursor.execute(
        f"DELETE FROM comment WHERE episode_id IN ({format_strings})", 
        tuple(episode_ids)
    )
    # 删除子记录
    await cursor.execute(
        f"DELETE FROM episode WHERE id IN ({format_strings})", 
        tuple(episode_ids)
    )
```

#### 3. 事务删除模式

**复杂删除操作**
```python
try:
    await conn.begin()
    # 多层级删除
    source_ids = [row[0] for row in await cursor.fetchall()]
    if source_ids:
        episode_ids = [row[0] for row in await cursor.fetchall()]
        if episode_ids:
            await cursor.execute("DELETE FROM comment WHERE episode_id IN (...)")
            await cursor.execute("DELETE FROM episode WHERE id IN (...)")
        await cursor.execute("DELETE FROM anime_sources WHERE id IN (...)")
    await cursor.execute("DELETE FROM anime_metadata WHERE anime_id = %s")
    await cursor.execute("DELETE FROM anime WHERE id = %s")
    await conn.commit()
except Exception as e:
    await conn.rollback()
    raise
```

### 特殊操作模式

#### 1. 缓存操作
```python
# 缓存写入带TTL
await cursor.execute("""
    INSERT INTO cache_data (cache_provider, cache_key, cache_value, expires_at) 
    VALUES (%s, %s, %s, NOW() + INTERVAL %s SECOND) 
    AS new_values
    ON DUPLICATE KEY UPDATE
        cache_provider = new_values.cache_provider,
        cache_value = new_values.cache_value,
        expires_at = new_values.expires_at
""", (provider, key, json_value, ttl_seconds))

# 缓存读取带过期检查
await cursor.execute(
    "SELECT cache_value FROM cache_data WHERE cache_key = %s AND expires_at > NOW()", 
    (key,)
)
```

#### 2. 分页查询模式
```python
query += " ORDER BY created_at DESC LIMIT 100"
```

#### 3. 聚合查询模式
```python
# 统计查询
await cursor.execute("SELECT COUNT(DISTINCT e.id) FROM anime_sources s JOIN episode e ON s.id = e.source_id WHERE s.anime_id = a.id")

# 条件聚合
await cursor.execute("SELECT MAX(display_order) FROM scrapers")
max_order = (await cursor.fetchone())[0] or 0
```

### 错误处理模式

#### 1. 重复键处理
```python
try:
    await cursor.execute("UPDATE anime_sources SET anime_id = %s WHERE id = %s", (target_id, src['id']))
except aiomysql.IntegrityError:
    logging.info(f"处理重复源: 正在删除...")
    await delete_anime_source(pool, src['id'], conn)
```

#### 2. 可选连接处理
```python
_conn = conn or await pool.acquire()
try:
    async with _conn.cursor() as cursor:
        if not conn: await _conn.begin()
        # 操作
        if not conn: await _conn.commit()
except Exception as e:
    if not conn: await _conn.rollback()
    raise
finally:
    if not conn: pool.release(_conn)
```

### 性能优化模式

#### 1. 索引优化查询
- 使用 FULLTEXT 索引进行全文搜索
- 复合索引支持多字段查询
- 避免 SELECT * 只查询需要的字段

#### 2. 批量操作优化
- 使用 executemany 进行批量插入
- 使用 IN 子句进行批量查询/删除
- 事务内批量操作减少提交次数

#### 3. 缓存策略
- 数据库级别缓存而非内存缓存
- 带TTL的缓存过期机制
- 定期清理过期缓存

### 数据一致性保证

1. **事务边界**: 相关操作包装在事务中
2. **外键约束**: 通过应用层逻辑维护引用完整性
3. **唯一约束**: 防止重复数据插入
4. **级联操作**: 手动实现级联删除逻辑
5. **错误回滚**: 异常时自动回滚事务