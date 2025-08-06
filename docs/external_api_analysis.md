# 外部API集成分析文档

## 外部API集成完整分析

### API集成架构概览

本项目集成了多个外部API服务，主要分为两大类：
1. **视频平台爬虫** (src/scrapers/) - 用于获取弹幕数据
2. **元数据API** (src/api/) - 用于获取影视元数据信息

### 视频平台爬虫集成

#### 1. Bilibili API 集成

**技术特点：**
- 使用 Protobuf 协议解析弹幕数据
- 实现了 WBI 签名算法（Web接口验证）
- 动态生成 Protobuf 消息类

**关键实现：**
```python
class BilibiliScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(headers=headers, timeout=20.0)
        self.base_url = "https://api.bilibili.com/x/web-interface/wbi/search/type"
    
    async def get_wbi_keys(self):
        # 获取WBI签名所需的key
    
    async def search_media(self, keyword: str):
        # 使用WBI签名进行搜索
        signed_params = self._sign_wbi(params, img_key, sub_key)
        url = f"{self.base_url}?{urlencode(signed_params)}"
```

**数据格式：**
- 搜索API: `/x/web-interface/wbi/search/type`
- 弹幕API: 返回 Protobuf 格式数据
- 需要处理反爬机制和签名验证

#### 2. 腾讯视频 API 集成

**技术特点：**
- 标准HTTP JSON API
- 需要处理Cookie和User-Agent

**关键实现：**
```python
class TencentScraper:
    def __init__(self):
        self.base_headers = {
            'User-Agent': '...',
            'Referer': 'https://v.qq.com/'
        }
        self.client = httpx.AsyncClient(
            headers=self.base_headers, 
            cookies=self.cookies, 
            timeout=20.0
        )
```

#### 3. 爱奇艺 API 集成

**技术特点：**
- RESTful JSON API
- 支持重定向跟踪

**关键实现：**
```python
class IqiyiScraper:
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=20.0, 
            follow_redirects=True
        )
```

#### 4. 优酷 API 集成

**技术特点：**
- 标准HTTP请求
- JSON响应格式

### 元数据API集成

#### 1. TMDB (The Movie Database) API

**配置参数：**
```python
default_configs = [
    ('tmdb_api_key', '', '用于访问 The Movie Database API 的密钥'),
    ('tmdb_api_base_url', 'https://api.themoviedb.org', 'TMDB API 的基础域名'),
    ('tmdb_image_base_url', 'https://image.tmdb.org', 'TMDB 图片服务的基础 URL'),
]
```

**客户端创建：**
```python
async def _create_tmdb_client(self) -> httpx.AsyncClient:
    api_key = await crud.get_config_value(self.pool, "tmdb_api_key", "")
    domain = await crud.get_config_value(self.pool, "tmdb_api_base_url", "https://api.themoviedb.org")
    
    base_url = domain if domain.endswith('/3') else f"{domain}/3"
    params = {"api_key": api_key}
    headers = {"Accept": "application/json"}
    
    return httpx.AsyncClient(
        base_url=base_url, 
        params=params, 
        headers=headers, 
        timeout=30.0
    )
```

**主要功能：**
- 影视作品搜索
- 获取详细信息
- 剧集组映射
- 图片资源获取

#### 2. TVDB (TheTVDB) API

**配置：**
```python
('tvdb_api_key', '', '用于访问 TheTVDB API 的密钥')
```

**特点：**
- 电视剧数据库专家
- 分集信息详细
- 需要API密钥认证

#### 3. Bangumi API

**OAuth集成：**
```python
class BangumiConfig(BaseModel):
    client_id: str = "bgm4222688b7532ef439"
    client_secret: str = "379c426b8f26b561642334445761361f"
```

**OAuth流程实现：**
- 授权链接生成
- 授权码交换token
- token刷新机制
- 用户信息获取

**数据库存储：**
```sql
CREATE TABLE `bangumi_auth` (
    `user_id` BIGINT NOT NULL,
    `bangumi_user_id` INT NULL,
    `access_token` TEXT NOT NULL,
    `refresh_token` TEXT NULL,
    `expires_at` TIMESTAMP NULL
) ENGINE=InnoDB;
```

#### 4. 豆瓣 API

**配置：**
```python
('douban_cookie', '', '用于访问豆瓣API的Cookie')
```

**特点：**
- 需要Cookie认证
- 中文影视数据丰富
- 非官方API

#### 5. IMDb API

**客户端配置：**
```python
def get_imdb_client() -> httpx.AsyncClient:
    headers = {
        'User-Agent': 'Mozilla/5.0 ...',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8'
    }
    return httpx.AsyncClient(
        headers=headers, 
        timeout=20.0, 
        follow_redirects=True
    )
```

### HTTP客户端统一模式

#### 1. 客户端初始化模式

**基础配置：**
```python
# 所有爬虫都使用httpx.AsyncClient
self.client = httpx.AsyncClient(
    headers=headers,      # 自定义请求头
    cookies=cookies,      # Cookie支持  
    timeout=20.0,        # 统一超时时间
    follow_redirects=True # 重定向支持
)
```

#### 2. 依赖注入模式

**FastAPI依赖注入：**
```python
async def get_tmdb_client(pool: aiomysql.Pool = Depends(get_db_pool)) -> httpx.AsyncClient:
    # 从数据库获取配置
    api_key = await crud.get_config_value(pool, "tmdb_api_key", "")
    return httpx.AsyncClient(...)

@router.get("/search")
async def search_movies(
    client: httpx.AsyncClient = Depends(get_tmdb_client)
):
    # 使用注入的客户端
```

#### 3. 错误处理模式

**统一异常处理：**
```python
try:
    response = await client.get(url)
    response.raise_for_status()
    return response.json()
except httpx.HTTPError as e:
    logger.error(f"HTTP error: {e}")
    raise HTTPException(status_code=500, detail="API request failed")
except Exception as e:
    logger.error(f"Unexpected error: {e}")
    raise
```

### 缓存策略

#### 1. 数据库缓存
```python
async def get_cached_data(pool: aiomysql.Pool, cache_key: str):
    cached = await crud.get_cache(pool, cache_key)
    if cached:
        return cached
    
    # 获取新数据
    fresh_data = await fetch_from_api()
    
    # 存入缓存
    await crud.set_cache(pool, cache_key, fresh_data, ttl_seconds=3600)
    return fresh_data
```

#### 2. TTL配置
```python
default_configs = [
    ('search_ttl_seconds', '300', '搜索结果的缓存时间（秒）'),
    ('episodes_ttl_seconds', '1800', '分集列表的缓存时间（秒）'),
    ('metadata_search_ttl_seconds', '1800', '元数据搜索结果的缓存时间（秒）'),
]
```

### API配置管理

#### 1. 配置存储
所有API配置都存储在数据库的 `config` 表中：

| config_key | 说明 |
|------------|------|
| tmdb_api_key | TMDB API密钥 |
| tmdb_api_base_url | TMDB API基础域名 |
| tvdb_api_key | TVDB API密钥 |
| douban_cookie | 豆瓣Cookie |
| webhook_api_key | Webhook安全密钥 |

#### 2. 动态配置加载
```python
async def get_config_value(pool: aiomysql.Pool, key: str, default: str) -> str:
    """从数据库获取配置值，支持默认值"""
    async with pool.acquire() as conn:
        async with conn.cursor() as cursor:
            await cursor.execute(
                "SELECT config_value FROM config WHERE config_key = %s", 
                (key,)
            )
            result = await cursor.fetchone()
            return result[0] if result else default
```

### 安全机制

#### 1. API密钥管理
- 所有密钥存储在数据库配置中
- 不在代码中硬编码敏感信息
- 支持运行时动态更新配置

#### 2. 请求限制
- 统一的超时设置 (20-30秒)
- 重试机制（部分API）
- User-Agent 伪装

#### 3. 错误处理
- 详细的日志记录
- 异常类型区分
- 用户友好的错误信息

### Webhook集成

#### 1. Webhook API设计
```python
# URL格式: /api/webhook/{service}?api_key={key}
# 支持的服务: emby, sonarr, radarr
```

#### 2. 安全验证
- API密钥验证
- IP地址记录
- 访问日志记录

#### 3. 自动化流程
- 接收媒体服务器通知
- 自动匹配和导入弹幕
- 后台任务处理

### 性能优化策略

#### 1. 连接复用
- 使用 `httpx.AsyncClient` 复用连接
- 合理设置连接池大小
- 异步并发请求

#### 2. 缓存策略
- 多层缓存：数据库缓存
- 合理的TTL设置
- 缓存键设计

#### 3. 限流保护
- 客户端超时设置
- 请求间隔控制
- 错误重试机制

### API数据流转图

```
外部API请求 → httpx.AsyncClient → 响应解析 → 数据验证 
    ↓
业务逻辑处理 → 数据库存储 → 缓存更新 → 返回结果
    ↓
前端展示 ← JSON响应 ← FastAPI路由 ← 数据格式化
```

### 监控和日志

#### 1. 请求日志
```python
logger.info(f"API request to {url}")
logger.error(f"API error: {response.status_code}")
```

#### 2. 性能监控
- 请求时间记录
- 成功率统计
- 错误类型分析

#### 3. 调试信息
- 详细的异常堆栈
- 请求参数记录
- 响应内容记录（敏感信息脱敏）