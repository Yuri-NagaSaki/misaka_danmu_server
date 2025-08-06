# 御坂弹幕服务 Docker 部署说明

## 快速开始

使用一键部署脚本快速启动服务：

```bash
# 运行部署脚本
./scripts/docker_deploy.sh
```

脚本会：
1. 检查系统依赖（Docker, Docker Compose）
2. 让你选择数据库类型（MySQL/PostgreSQL）
3. 自动生成安全的配置文件
4. 构建Docker镜像并启动服务
5. 运行数据库迁移
6. 进行健康检查

## 手动部署

### 1. 选择数据库类型

**使用MySQL：**
```bash
docker-compose -f docker-compose.mysql.yml up -d
```

**使用PostgreSQL：**
```bash
docker-compose -f docker-compose.postgres.yml up -d
```

### 2. 环境变量配置

复制环境变量模板：
```bash
cp scripts/.env.template .env
```

编辑`.env`文件设置你的配置：
```bash
# 数据库配置
DB_USER=your_db_user
DB_PASSWORD=your_secure_password
DB_NAME=danmaku_db

# JWT密钥
JWT_SECRET_KEY=your_super_secret_jwt_key

# 管理员账户
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_admin_password
```

## 服务管理

### 常用命令

```bash
# 查看服务状态
docker-compose -f docker-compose.mysql.yml ps

# 查看日志
docker-compose -f docker-compose.mysql.yml logs -f

# 停止服务
docker-compose -f docker-compose.mysql.yml down

# 重启服务
docker-compose -f docker-compose.mysql.yml restart

# 清理服务和数据
docker-compose -f docker-compose.mysql.yml down -v
```

### 脚本快捷命令

```bash
# 显示日志
./scripts/docker_deploy.sh --logs

# 停止服务
./scripts/docker_deploy.sh --stop

# 重启服务
./scripts/docker_deploy.sh --restart

# 清理所有数据
./scripts/docker_deploy.sh --clean
```

## 访问服务

部署完成后，可以通过以下地址访问：

- **Web界面**: http://localhost:7768
- **API文档**: http://localhost:7768/docs
- **健康检查**: http://localhost:7768/health

## 数据持久化

- **MySQL**: 数据存储在Docker卷`mysql_data`中
- **PostgreSQL**: 数据存储在Docker卷`postgres_data`中
- **应用日志**: 挂载到本地`./logs`目录

## 故障排除

### 常见问题

1. **端口冲突**: 默认端口7768被占用
   - 修改`.env`文件中的`SERVER_PORT`
   
2. **数据库连接失败**: 
   - 检查数据库容器是否正常启动
   - 确认数据库密码配置正确

3. **权限问题**: 
   - 确保Docker有足够权限访问项目目录

### 查看详细日志

```bash
# 查看应用日志
docker logs danmaku_server

# 查看数据库日志
docker logs danmaku_mysql  # 或 danmaku_postgres
```

## 开发模式

如需在开发模式下运行：

```bash
# 设置开发环境变量
export DEBUG=true
export LOG_LEVEL=DEBUG

# 启动服务
docker-compose -f docker-compose.mysql.yml up
```