-- PostgreSQL数据库初始化脚本
-- Misaka Danmu Server PostgreSQL Initialization

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建扩展（用于UUID生成）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 创建扩展（用于中文全文搜索，如果需要）
CREATE EXTENSION IF NOT EXISTS "zhparser";

-- 输出初始化完成信息
SELECT 'PostgreSQL数据库初始化完成！Misaka Danmu Server Database Ready!' as status;