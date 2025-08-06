# 御坂弹幕服务器 - 一键部署指南

## 🚀 快速部署

### 一键部署命令
```bash
# 下载部署脚本
curl -fsSL https://raw.githubusercontent.com/your-repo/misaka_danmu_server/main/scripts/deploy.sh -o deploy.sh

# 给予执行权限
chmod +x deploy.sh

# 运行部署
./deploy.sh
```

### 部署流程

部署脚本将引导您完成以下步骤：

1. **系统检查** - 自动检测Docker和Docker Compose
2. **数据库选择** - 选择MySQL或PostgreSQL
3. **密码生成** - 自动生成安全的随机密码
4. **环境配置** - 自动创建所有必需的配置文件
5. **服务启动** - 自动构建镜像并启动服务

### 部署输出示例

```
==================================================
🎬 Misaka 弹幕服务器 - 一键部署脚本
==================================================
检查系统依赖...
✅ 系统依赖检查通过

请选择数据库类型:
1) MySQL 8.1 (推荐新手)
2) PostgreSQL 15 (推荐高级用户)
请输入选择 (1-2): 2
✅ 已选择 PostgreSQL 数据库

配置数据库密码:
✅ 数据库用户密码: NoRfXaxBesF7X8z1

⚠️  请记录以上密码，用于后续数据库管理！
按 Enter 继续...

--------------------------------------------------
🎉 部署成功完成！
--------------------------------------------------

📋 服务信息:
  🌐 Web管理界面: http://localhost:7768
  📖 API接口文档: http://localhost:7768/docs
  🏥 服务健康检查: http://localhost:7768/health
  📊 数据库类型: postgresql
  📁 项目目录: /home/user/misaka_danmu_server

👤 登录信息:
  用户名: admin
  密码: Abc123DefGhi

🔐 数据库信息:
  数据库用户: danmaku_user
  数据库密码: NoRfXaxBesF7X8z1
  数据库名称: danmaku_db
```

## 🛠️ 服务管理

### 管理命令

```bash
# 查看服务状态
./scripts/manage.sh status

# 启动服务
./scripts/manage.sh start

# 停止服务
./scripts/manage.sh stop

# 重启服务
./scripts/manage.sh restart

# 查看实时日志
./scripts/manage.sh logs
```

### 完整卸载

```bash
# 卸载服务（仅删除容器和镜像，保留配置）
./scripts/deploy.sh --uninstall
```

## 📁 自动目录结构

部署脚本会在用户家目录下创建以下结构：

```
~/misaka_danmu_server/
├── .env                    # 环境变量配置
├── docker-compose.*.yml    # Docker编排文件
├── Dockerfile             # 镜像构建文件
├── config/
│   └── config.yml         # 应用配置文件
├── docker/
│   ├── mysql/
│   │   └── init.sql       # MySQL初始化脚本
│   └── postgres/
│       └── init.sql       # PostgreSQL初始化脚本
├── logs/                  # 应用日志目录
└── data/                  # 数据存储目录
```

## 🔒 安全特性

- **自动密码生成**: 使用OpenSSL生成强随机密码
- **非root运行**: 容器使用非特权用户运行
- **配置隔离**: 敏感配置存储在独立的环境文件中
- **容器隔离**: 服务运行在独立的Docker网络中

## 🔧 自定义配置

### 修改端口

编辑 `~/misaka_danmu_server/.env` 文件：
```bash
SERVER_PORT=8080  # 修改为您想要的端口
```

重启服务：
```bash
cd ~/misaka_danmu_server
docker-compose -f docker-compose.*.yml restart
```

### 修改管理员密码

编辑 `~/misaka_danmu_server/.env` 文件：
```bash
ADMIN_PASSWORD=your_new_password
```

重启服务使配置生效。

## 📊 系统要求

- **操作系统**: Linux / macOS / Windows with WSL2
- **Docker**: 20.10+ 
- **Docker Compose**: 2.0+
- **内存**: 最少512MB可用内存
- **磁盘**: 最少2GB可用空间

## 🆘 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   # 查找占用端口的进程
   sudo lsof -i :7768
   
   # 或修改 .env 文件中的 SERVER_PORT
   ```

2. **Docker权限问题**
   ```bash
   # 将用户加入docker组
   sudo usermod -aG docker $USER
   
   # 重新登录使权限生效
   ```

3. **服务启动失败**
   ```bash
   # 查看详细日志
   ./scripts/manage.sh logs
   
   # 检查容器状态
   docker ps -a
   ```

### 获取帮助

- 查看部署脚本帮助: `./scripts/deploy.sh --help`
- 查看管理脚本帮助: `./scripts/manage.sh --help`
- 查看容器日志: `./scripts/manage.sh logs`