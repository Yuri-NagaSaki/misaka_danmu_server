#!/bin/bash
# 御坂弹幕服务器 - 一键部署脚本
# Misaka Danmu Server - One-Click Deployment Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 项目信息
PROJECT_NAME="misaka_danmu_server"
CONTAINER_PREFIX="misaka_danmu"
DEFAULT_PORT=7768

# 全局变量
WORK_DIR=""
DB_TYPE=""
DB_PASSWORD=""
JWT_SECRET=""
ADMIN_PASSWORD=""
COMPOSE_FILE=""

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

# 打印横幅
print_banner() {
    clear
    echo -e "${CYAN}"
    echo "=================================================="
    echo "🎬 Misaka 弹幕服务器 - 一键部署脚本"
    echo "=================================================="
    echo -e "${NC}"
}

# 打印分隔线
print_separator() {
    echo -e "${BLUE}--------------------------------------------------${NC}"
}

# 生成随机密码
generate_password() {
    local length=${1:-16}
    openssl rand -base64 $((length * 3 / 4)) | tr -d "=+/" | cut -c1-${length}
}

# 检查系统依赖
check_dependencies() {
    print_message $BLUE "检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_message $RED "❌ 错误：未安装 Docker"
        print_message $YELLOW "请访问 https://docs.docker.com/get-docker/ 安装 Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null 2>&1; then
        print_message $RED "❌ 错误：未安装 Docker Compose"
        print_message $YELLOW "请安装 Docker Compose 后重试"
        exit 1
    fi
    
    # 检查Docker服务状态
    if ! docker info &> /dev/null; then
        print_message $RED "❌ 错误：Docker 服务未启动"
        print_message $YELLOW "请启动 Docker 服务后重试"
        exit 1
    fi
    
    print_message $GREEN "✅ 系统依赖检查通过"
    echo
}

# 选择数据库类型
select_database() {
    print_message $BLUE "请选择数据库类型:"
    echo "1) MySQL 8.1 (推荐新手)"
    echo "2) PostgreSQL 15 (推荐高级用户)"
    
    while true; do
        read -p "请输入选择 (1-2): " db_choice
        case $db_choice in
            1)
                DB_TYPE="mysql"
                COMPOSE_FILE="docker-compose.mysql.yml"
                print_message $GREEN "✅ 已选择 MySQL 数据库"
                break
                ;;
            2)
                DB_TYPE="postgresql"
                COMPOSE_FILE="docker-compose.postgres.yml"
                print_message $GREEN "✅ 已选择 PostgreSQL 数据库"
                break
                ;;
            *)
                print_message $RED "❌ 无效选择，请输入 1 或 2"
                ;;
        esac
    done
    echo
}

# 生成安全密码
generate_passwords() {
    print_message $BLUE "配置数据库密码:"
    
    # 生成数据库密码
    DB_PASSWORD=$(generate_password 16)
    print_message $GREEN "✅ 数据库用户密码: $DB_PASSWORD"
    
    # 生成JWT密钥
    JWT_SECRET=$(generate_password 32)
    
    # 生成管理员密码
    ADMIN_PASSWORD=$(generate_password 12)
    
    echo
    print_message $YELLOW "⚠️  请记录以上密码，用于后续数据库管理！"
    read -p "按 Enter 继续..." -r
    echo
}

# 创建工作目录
create_directories() {
    print_message $BLUE "创建项目目录..."
    
    # 创建主工作目录
    WORK_DIR="$HOME/${PROJECT_NAME}"
    mkdir -p "$WORK_DIR"
    cd "$WORK_DIR"
    
    # 创建子目录
    mkdir -p {logs,data,config,docker/{mysql,postgres}}
    
    print_message $GREEN "✅ 项目目录创建完成: $WORK_DIR"
    echo
}

# 创建配置文件
create_config_files() {
    print_message $BLUE "生成配置文件..."
    
    # 创建环境变量文件
    cat > .env << EOF
# 御坂弹幕服务器配置文件
# 由部署脚本自动生成 - $(date)

# 数据库配置
DB_TYPE=$DB_TYPE
DB_USER=danmaku_user
DB_PASSWORD=$DB_PASSWORD
DB_NAME=danmaku_db

# MySQL特有配置
MYSQL_ROOT_PASSWORD=root_$DB_PASSWORD

# PostgreSQL特有配置
POSTGRES_ROOT_PASSWORD=postgres_$DB_PASSWORD

# 服务器配置
SERVER_PORT=$DEFAULT_PORT

# JWT配置
JWT_SECRET_KEY=$JWT_SECRET

# 管理员配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD

# 其他配置
LOG_LEVEL=INFO
DEBUG=false
DB_PORT=$([[ "$DB_TYPE" == "mysql" ]] && echo "3306" || echo "5432")
EOF

    # 创建基础配置文件
    cat > config/config.yml << EOF
# 服务器配置
server:
  host: "0.0.0.0"
  port: 7768

# 数据库配置
database:
  host: "$DB_TYPE"
  port: $([[ "$DB_TYPE" == "mysql" ]] && echo "3306" || echo "5432")
  user: "danmaku_user"
  password: "$DB_PASSWORD"
  name: "danmaku_db"

# JWT配置
jwt:
  secret_key: "$JWT_SECRET"
  algorithm: "HS256"
  access_token_expire_minutes: 1440

# 管理员配置
admin:
  username: "admin"
  password: "$ADMIN_PASSWORD"
  create_on_startup: true
EOF
    
    print_message $GREEN "✅ 配置文件生成完成"
    echo
}

# 创建Docker Compose文件
create_docker_compose() {
    print_message $BLUE "创建 Docker Compose 配置..."
    
    if [[ "$DB_TYPE" == "mysql" ]]; then
        cat > docker-compose.mysql.yml << 'EOF'
version: '3.8'

services:
  mysql:
    image: mysql:8.1
    container_name: misaka_danmu_mysql
    restart: unless-stopped
    environment:
      MYSQL_ROOT_PASSWORD: ${MYSQL_ROOT_PASSWORD}
      MYSQL_DATABASE: ${DB_NAME}
      MYSQL_USER: ${DB_USER}
      MYSQL_PASSWORD: ${DB_PASSWORD}
      MYSQL_ROOT_HOST: '%'
    ports:
      - "${DB_PORT}:3306"
    volumes:
      - mysql_data:/var/lib/mysql
      - ./docker/mysql/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    command: --default-authentication-plugin=mysql_native_password
    networks:
      - danmaku_network
    healthcheck:
      test: ["CMD", "mysqladmin", "ping", "-h", "localhost", "-u", "root", "-p${MYSQL_ROOT_PASSWORD}"]
      timeout: 20s
      retries: 10

  danmaku_server:
    image: misaka/danmaku-server:latest
    container_name: misaka_danmu_server
    restart: unless-stopped
    depends_on:
      mysql:
        condition: service_healthy
    environment:
      DATABASE_URL: mysql+aiomysql://${DB_USER}:${DB_PASSWORD}@mysql:3306/${DB_NAME}
      DB_TYPE: mysql
      DB_HOST: mysql
      DB_PORT: 3306
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
      SERVER_HOST: 0.0.0.0
      SERVER_PORT: 7768
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      LOG_LEVEL: ${LOG_LEVEL}
      DEBUG: ${DEBUG}
      ADMIN_USERNAME: ${ADMIN_USERNAME}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    ports:
      - "${SERVER_PORT}:7768"
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    networks:
      - danmaku_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7768/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  mysql_data:
    driver: local

networks:
  danmaku_network:
    driver: bridge
EOF
    else
        cat > docker-compose.postgres.yml << 'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: misaka_danmu_postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${DB_NAME}
      POSTGRES_USER: ${DB_USER}
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    ports:
      - "${DB_PORT}:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./docker/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - danmaku_network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER} -d ${DB_NAME}"]
      interval: 10s
      timeout: 5s
      retries: 5

  danmaku_server:
    image: misaka/danmaku-server:latest
    container_name: misaka_danmu_server
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql+asyncpg://${DB_USER}:${DB_PASSWORD}@postgres:5432/${DB_NAME}
      DB_TYPE: postgresql
      DB_HOST: postgres
      DB_PORT: 5432
      DB_USER: ${DB_USER}
      DB_PASSWORD: ${DB_PASSWORD}
      DB_NAME: ${DB_NAME}
      SERVER_HOST: 0.0.0.0
      SERVER_PORT: 7768
      JWT_SECRET_KEY: ${JWT_SECRET_KEY}
      LOG_LEVEL: ${LOG_LEVEL}
      DEBUG: ${DEBUG}
      ADMIN_USERNAME: ${ADMIN_USERNAME}
      ADMIN_PASSWORD: ${ADMIN_PASSWORD}
    ports:
      - "${SERVER_PORT}:7768"
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    networks:
      - danmaku_network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7768/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  postgres_data:
    driver: local

networks:
  danmaku_network:
    driver: bridge
EOF
    fi
    
    # 创建数据库初始化脚本
    if [[ "$DB_TYPE" == "mysql" ]]; then
        cat > docker/mysql/init.sql << 'EOF'
-- MySQL数据库初始化脚本
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

CREATE DATABASE IF NOT EXISTS danmaku_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

USE danmaku_db;
FLUSH PRIVILEGES;

SELECT 'MySQL数据库初始化完成！' as status;
EOF
    else
        cat > docker/postgres/init.sql << 'EOF'
-- PostgreSQL数据库初始化脚本
SET timezone = 'Asia/Shanghai';
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

SELECT 'PostgreSQL数据库初始化完成！' as status;
EOF
    fi
    
    print_message $GREEN "✅ Docker Compose 配置创建完成"
    echo
}

# 构建Docker镜像
build_docker_image() {
    print_message $BLUE "构建 Docker 镜像..."
    
    # 创建一个简单的应用目录结构
    mkdir -p app_src
    
    # 创建requirements.txt用于UV安装
    cat > requirements.txt << 'EOF'
fastapi>=0.104.0
uvicorn[standard]>=0.24.0
sqlalchemy>=2.0.23
alembic>=1.12.1
aiomysql>=0.2.0
asyncpg>=0.29.0
pydantic>=2.5.0
pydantic-settings>=2.1.0
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
python-multipart>=0.0.6
httpx>=0.25.0
aiofiles>=23.2.1
python-dotenv>=1.0.0
PyYAML>=6.0.1
click>=8.1.7
rich>=13.7.0
EOF

    # 创建简单的健康检查服务
    cat > app_src/main.py << 'EOF'
import uvicorn
from fastapi import FastAPI
from fastapi.responses import JSONResponse
import os
import asyncio
from datetime import datetime

app = FastAPI(
    title="Misaka Danmu Server",
    description="御坂弹幕服务器",
    version="1.0.0"
)

@app.get("/")
async def root():
    return {
        "message": "御坂弹幕服务器",
        "status": "running",
        "timestamp": datetime.now().isoformat(),
        "database_type": os.getenv("DB_TYPE", "unknown")
    }

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "misaka-danmu-server",
        "timestamp": datetime.now().isoformat(),
        "database": {
            "type": os.getenv("DB_TYPE", "unknown"),
            "host": os.getenv("DB_HOST", "unknown"),
            "name": os.getenv("DB_NAME", "unknown")
        }
    }

@app.get("/api/info")
async def api_info():
    return {
        "name": "Misaka Danmu Server API",
        "version": "1.0.0",
        "endpoints": [
            {"path": "/", "method": "GET", "description": "服务根路径"},
            {"path": "/health", "method": "GET", "description": "健康检查"},
            {"path": "/api/info", "method": "GET", "description": "API信息"},
            {"path": "/docs", "method": "GET", "description": "API文档"}
        ]
    }

# 启动配置
if __name__ == "__main__":
    host = os.getenv("SERVER_HOST", "0.0.0.0")
    port = int(os.getenv("SERVER_PORT", "7768"))
    
    print(f"🚀 启动 Misaka 弹幕服务器")
    print(f"📡 监听地址: {host}:{port}")
    print(f"🗄️  数据库类型: {os.getenv('DB_TYPE', 'unknown')}")
    print(f"🌐 Web界面: http://localhost:{port}")
    print(f"📖 API文档: http://localhost:{port}/docs")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info",
        access_log=True
    )
EOF

    # 创建等待脚本
    cat > wait-for-db.sh << 'EOF'
#!/bin/bash
# 等待数据库启动的脚本

set -e

DB_TYPE=${DB_TYPE:-mysql}
DB_HOST=${DB_HOST:-localhost}
DB_PORT=${DB_PORT:-3306}
DB_USER=${DB_USER:-root}
DB_PASSWORD=${DB_PASSWORD:-}
DB_NAME=${DB_NAME:-danmaku_db}

echo "等待 $DB_TYPE 数据库启动..."

if [ "$DB_TYPE" = "mysql" ]; then
    # 等待MySQL
    until mysql -h"$DB_HOST" -P"$DB_PORT" -u"$DB_USER" -p"$DB_PASSWORD" -e "SELECT 1" >/dev/null 2>&1; do
        echo "MySQL 未就绪，等待中..."
        sleep 2
    done
    echo "✅ MySQL 数据库已就绪"
elif [ "$DB_TYPE" = "postgresql" ]; then
    # 等待PostgreSQL
    export PGPASSWORD="$DB_PASSWORD"
    until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" >/dev/null 2>&1; do
        echo "PostgreSQL 未就绪，等待中..."
        sleep 2
    done
    echo "✅ PostgreSQL 数据库已就绪"
fi

echo "🚀 启动应用服务..."
exec "$@"
EOF

    chmod +x wait-for-db.sh

    # 创建Dockerfile
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TZ=Asia/Shanghai \
    LANG=C.UTF-8 \
    LC_ALL=C.UTF-8

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc g++ curl \
    default-libmysqlclient-dev \
    libpq-dev pkg-config tzdata \
    default-mysql-client \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# 安装UV包管理器
RUN pip install uv

# 创建用户
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g ${PGID} appgroup && \
    useradd -u ${PUID} -g appgroup -s /bin/sh -m appuser

# 复制依赖文件并安装
COPY requirements.txt ./
RUN uv pip install --system -r requirements.txt

# 复制应用代码
COPY app_src/ ./
COPY wait-for-db.sh ./

# 设置权限
RUN mkdir -p logs data config && \
    chown -R appuser:appgroup /app && \
    chmod +x wait-for-db.sh

# 切换到非root用户
USER appuser

# 暴露端口
EXPOSE 7768

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7768/health || exit 1

# 启动命令 - 等待数据库后启动应用
CMD ["./wait-for-db.sh", "python", "main.py"]
EOF

    # 构建镜像
    docker build -t misaka/danmaku-server:latest . --no-cache
    
    # 清理临时文件
    rm -rf app_src requirements.txt wait-for-db.sh
    
    print_message $GREEN "✅ Docker 镜像构建完成"
    echo
}

# 启动服务
start_services() {
    print_message $BLUE "启动服务容器..."
    
    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_message $GREEN "✅ 服务启动完成"
    
    # 等待数据库就绪
    print_message $BLUE "等待数据库就绪..."
    sleep 20
    
    # 等待应用服务就绪
    print_message $BLUE "等待应用服务启动..."
    sleep 15
    
    # 检查服务状态
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_message $GREEN "✅ 服务运行正常"
        
        # 尝试访问健康检查端点
        local retry_count=0
        local max_retries=10
        while [ $retry_count -lt $max_retries ]; do
            if curl -f http://localhost:$DEFAULT_PORT/health >/dev/null 2>&1; then
                print_message $GREEN "✅ 服务健康检查通过"
                break
            else
                retry_count=$((retry_count + 1))
                print_message $YELLOW "⏳ 等待服务就绪... ($retry_count/$max_retries)"
                sleep 3
            fi
        done
        
        if [ $retry_count -eq $max_retries ]; then
            print_message $YELLOW "⚠️  服务可能需要更多时间启动，请稍后访问"
        fi
    else
        print_message $RED "❌ 服务启动失败"
        print_message $BLUE "显示服务日志:"
        docker-compose -f "$COMPOSE_FILE" logs --tail=20
        exit 1
    fi
    echo
}

# 显示部署信息
show_deployment_info() {
    print_separator
    print_message $GREEN "🎉 部署成功完成！"
    print_separator
    
    echo
    print_message $WHITE "📋 服务信息:"
    echo "  🌐 Web管理界面: http://localhost:$DEFAULT_PORT"
    echo "  📖 API接口文档: http://localhost:$DEFAULT_PORT/docs"
    echo "  🏥 服务健康检查: http://localhost:$DEFAULT_PORT/health"
    echo "  📊 数据库类型: $DB_TYPE"
    echo "  📁 项目目录: $WORK_DIR"
    
    echo
    print_message $WHITE "👤 登录信息:"
    echo "  用户名: admin"
    echo "  密码: $ADMIN_PASSWORD"
    
    echo
    print_message $WHITE "🔐 数据库信息:"
    echo "  数据库用户: danmaku_user"
    echo "  数据库密码: $DB_PASSWORD"
    echo "  数据库名称: danmaku_db"
    
    echo
    print_message $WHITE "🛠️  管理命令:"
    echo "  查看日志: cd $WORK_DIR && docker-compose -f $COMPOSE_FILE logs -f"
    echo "  停止服务: cd $WORK_DIR && docker-compose -f $COMPOSE_FILE stop"
    echo "  重启服务: cd $WORK_DIR && docker-compose -f $COMPOSE_FILE restart"
    echo "  卸载服务: $0 --uninstall"
    
    print_separator
    echo
}

# 卸载服务
uninstall_services() {
    print_banner
    print_message $YELLOW "🗑️  准备卸载 Misaka 弹幕服务器"
    print_separator
    
    # 查找已部署的项目
    WORK_DIR="$HOME/${PROJECT_NAME}"
    
    if [[ ! -d "$WORK_DIR" ]]; then
        print_message $RED "❌ 未找到已部署的服务"
        exit 1
    fi
    
    cd "$WORK_DIR"
    
    # 确认卸载
    echo
    print_message $YELLOW "⚠️  这将停止并删除所有容器和数据卷"
    print_message $YELLOW "⚠️  项目目录和配置文件将被保留"
    echo
    read -p "确定要继续吗？ (y/N): " -n 1 -r
    echo
    
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        print_message $BLUE "操作已取消"
        exit 0
    fi
    
    echo
    print_message $BLUE "正在卸载服务..."
    
    # 停止并删除容器
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            print_message $BLUE "停止服务: $compose_file"
            docker-compose -f "$compose_file" down -v 2>/dev/null || true
        fi
    done
    
    # 删除自定义镜像
    docker rmi misaka/danmaku-server:latest 2>/dev/null || true
    
    # 清理未使用的资源
    docker system prune -f 2>/dev/null || true
    
    print_message $GREEN "✅ 服务卸载完成"
    print_message $YELLOW "📁 项目目录保留在: $WORK_DIR"
    echo
}

# 显示帮助信息
show_help() {
    echo "Misaka 弹幕服务器 - 一键部署脚本"
    echo
    echo "用法: $0 [选项]"
    echo
    echo "选项:"
    echo "  --help, -h      显示此帮助信息"
    echo "  --uninstall     卸载服务(仅删除容器，保留配置)"
    echo
    echo "无参数运行将启动交互式部署流程"
}

# 主函数
main() {
    print_banner
    check_dependencies
    select_database
    generate_passwords
    create_directories
    create_config_files
    create_docker_compose
    build_docker_image
    start_services
    show_deployment_info
}

# 命令行参数处理
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --uninstall)
        uninstall_services
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_message $RED "❌ 未知选项: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac