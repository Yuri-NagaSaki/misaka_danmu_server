-- MySQL数据库初始化脚本
-- Misaka Danmu Server MySQL Initialization

-- 设置字符集
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS danmaku_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE danmaku_db;

-- 创建用户（如果不存在）
CREATE USER IF NOT EXISTS 'danmaku_user'@'%' IDENTIFIED BY 'danmaku_password';

-- 授权
GRANT ALL PRIVILEGES ON danmaku_db.* TO 'danmaku_user'@'%';

-- 刷新权限
FLUSH PRIVILEGES;

-- 输出初始化完成信息
SELECT 'MySQL数据库初始化完成！Misaka Danmu Server Database Ready!' as status;