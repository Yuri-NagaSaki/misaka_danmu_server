#!/bin/bash
# 御坂弹幕服务 Docker 一键部署脚本
# Misaka Danmu Server Docker Deployment Script

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_banner() {
    echo -e "${BLUE}"
    echo "╔════════════════════════════════════════════════════╗"
    echo "║          御坂弹幕服务 Docker 一键部署             ║"
    echo "║        Misaka Danmu Server Docker Deploy          ║"
    echo "╚════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

# 检查依赖
check_dependencies() {
    print_message $BLUE "🔍 检查系统依赖..."
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        print_message $RED "❌ Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    # 检查Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_message $RED "❌ Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    # 检查curl（用于健康检查）
    if ! command -v curl &> /dev/null; then
        print_message $YELLOW "⚠️  curl 未安装，建议安装用于健康检查"
    fi
    
    print_message $GREEN "✅ 系统依赖检查通过"
}

# 选择数据库类型
select_database() {
    print_message $BLUE "📊 请选择数据库类型:"
    echo "1) MySQL 8.0 (推荐)"
    echo "2) PostgreSQL 15"
    echo ""
    
    while true; do
        read -p "请输入选择 (1-2): " db_choice
        case $db_choice in
            1)
                DB_TYPE="mysql"
                COMPOSE_FILE="docker-compose.mysql.yml"
                print_message $GREEN "✅ 已选择: MySQL 8.0"
                break
                ;;
            2)
                DB_TYPE="postgresql"
                COMPOSE_FILE="docker-compose.postgres.yml"
                print_message $GREEN "✅ 已选择: PostgreSQL 15"
                break
                ;;
            *)
                print_message $RED "❌ 无效选择，请输入 1 或 2"
                ;;
        esac
    done
}

# 配置环境变量
configure_environment() {
    print_message $BLUE "⚙️  配置环境变量..."
    
    # 创建.env文件
    ENV_FILE=".env"
    
    # 如果.env文件不存在，则创建
    if [ ! -f "$ENV_FILE" ]; then
        print_message $YELLOW "📝 创建环境变量配置文件..."
        
        # 生成随机密码
        DB_PASSWORD=$(openssl rand -base64 32 | tr -d "=+/" | cut -c1-25)
        JWT_SECRET=$(openssl rand -base64 64 | tr -d "=+/" | cut -c1-50)
        ADMIN_PASSWORD=$(openssl rand -base64 16 | tr -d "=+/" | cut -c1-12)
        
        cat > "$ENV_FILE" << EOF
# 御坂弹幕服务 Docker 部署配置
# Misaka Danmu Server Docker Configuration

# 数据库配置
DB_TYPE=$DB_TYPE
DB_USER=danmaku_user
DB_PASSWORD=$DB_PASSWORD
DB_NAME=danmaku_db

# MySQL特有配置（仅当使用MySQL时）
MYSQL_ROOT_PASSWORD=root_${DB_PASSWORD}

# PostgreSQL特有配置（仅当使用PostgreSQL时）
POSTGRES_ROOT_PASSWORD=postgres_${DB_PASSWORD}

# 服务器配置
SERVER_PORT=7768

# JWT配置
JWT_SECRET_KEY=$JWT_SECRET

# 管理员配置
ADMIN_USERNAME=admin
ADMIN_PASSWORD=$ADMIN_PASSWORD

# 日志配置
LOG_LEVEL=INFO
DEBUG=false

# 端口配置（如果需要修改默认端口）
DB_PORT=${DB_TYPE=="mysql" && "3306" || "5432"}
EOF
        
        print_message $GREEN "✅ 环境变量配置文件已创建: $ENV_FILE"
        print_message $YELLOW "🔐 重要信息："
        print_message $YELLOW "   管理员用户名: admin"
        print_message $YELLOW "   管理员密码: $ADMIN_PASSWORD"
        print_message $YELLOW "   数据库用户名: danmaku_user"
        print_message $YELLOW "   数据库密码: $DB_PASSWORD"
        print_message $YELLOW "   请妥善保存这些信息！"
    else
        print_message $GREEN "✅ 使用现有环境变量配置文件"
    fi
}

# 创建必要的目录
create_directories() {
    print_message $BLUE "📁 创建必要的目录..."
    
    # 创建日志目录
    mkdir -p logs
    
    # 创建Docker相关目录
    mkdir -p docker/${DB_TYPE}
    
    print_message $GREEN "✅ 目录创建完成"
}

# 创建数据库初始化脚本
create_db_init_scripts() {
    print_message $BLUE "🗄️  创建数据库初始化脚本..."
    
    if [ "$DB_TYPE" = "mysql" ]; then
        # MySQL初始化脚本
        cat > "docker/mysql/init.sql" << 'EOF'
-- MySQL数据库初始化脚本
-- 设置字符集
SET NAMES utf8mb4;
SET character_set_client = utf8mb4;

-- 创建数据库（如果不存在）
CREATE DATABASE IF NOT EXISTS danmaku_db 
CHARACTER SET utf8mb4 
COLLATE utf8mb4_unicode_ci;

-- 使用数据库
USE danmaku_db;

-- 确保用户权限
FLUSH PRIVILEGES;

-- 输出初始化完成信息
SELECT 'MySQL数据库初始化完成！' as status;
EOF
    else
        # PostgreSQL初始化脚本
        cat > "docker/postgres/init.sql" << 'EOF'
-- PostgreSQL数据库初始化脚本

-- 设置时区
SET timezone = 'Asia/Shanghai';

-- 创建扩展（如果需要）
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 输出初始化完成信息
SELECT 'PostgreSQL数据库初始化完成！' as status;
EOF
    fi
    
    print_message $GREEN "✅ 数据库初始化脚本创建完成"
}

# 构建Docker镜像
build_docker_image() {
    print_message $BLUE "🔨 构建Docker镜像..."
    
    # 检查Dockerfile是否存在
    if [ ! -f "Dockerfile" ]; then
        print_message $YELLOW "📝 创建Dockerfile..."
        create_dockerfile
    fi
    
    # 构建镜像
    docker-compose -f "$COMPOSE_FILE" build --no-cache
    
    print_message $GREEN "✅ Docker镜像构建完成"
}

# 创建Dockerfile
create_dockerfile() {
    cat > "Dockerfile" << 'EOF'
# 使用Python 3.11官方镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    default-libmysqlclient-dev \
    libpq-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# 安装UV包管理器
RUN pip install uv

# 复制项目文件
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini ./
COPY config/ ./config/

# 创建非root用户
RUN groupadd -r appgroup && useradd -r -g appgroup -u 1001 appuser

# 创建必要目录并设置权限
RUN mkdir -p logs && chown -R appuser:appgroup /app

# 使用UV安装依赖
RUN uv sync --frozen

# 暴露端口
EXPOSE 7768

# 切换到非root用户
USER appuser

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:7768/health || exit 1

# 启动命令
CMD ["uv", "run", "uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "7768"]
EOF
}

# 启动服务
start_services() {
    print_message $BLUE "🚀 启动服务..."
    
    # 启动服务
    docker-compose -f "$COMPOSE_FILE" up -d
    
    print_message $GREEN "✅ 服务启动完成"
    
    # 等待服务启动
    print_message $BLUE "⏳ 等待服务启动..."
    sleep 10
}

# 运行数据库迁移
run_migrations() {
    print_message $BLUE "🔄 运行数据库迁移..."
    
    # 等待数据库就绪
    print_message $BLUE "⏳ 等待数据库就绪..."
    sleep 15
    
    # 运行迁移
    docker-compose -f "$COMPOSE_FILE" exec -T danmaku_server uv run alembic upgrade head
    
    if [ $? -eq 0 ]; then
        print_message $GREEN "✅ 数据库迁移完成"
    else
        print_message $YELLOW "⚠️  数据库迁移失败，可能需要手动处理"
    fi
}

# 健康检查
health_check() {
    print_message $BLUE "🏥 运行健康检查..."
    
    # 检查服务状态
    if docker-compose -f "$COMPOSE_FILE" ps | grep -q "Up"; then
        print_message $GREEN "✅ 服务运行正常"
        
        # 尝试访问API
        sleep 5
        if curl -f http://localhost:7768/health > /dev/null 2>&1; then
            print_message $GREEN "✅ API健康检查通过"
        else
            print_message $YELLOW "⚠️  API暂时不可用，请稍等片刻后重试"
        fi
    else
        print_message $RED "❌ 服务启动失败"
        show_logs
        exit 1
    fi
}

# 显示日志
show_logs() {
    print_message $BLUE "📜 显示服务日志..."
    docker-compose -f "$COMPOSE_FILE" logs --tail=20
}

# 显示部署信息
show_deployment_info() {
    print_message $GREEN "🎉 部署完成！"
    echo ""
    print_message $BLUE "📋 部署信息："
    echo "  🌐 Web界面: http://localhost:7768"
    echo "  📖 API文档: http://localhost:7768/docs"
    echo "  🏥 健康检查: http://localhost:7768/health"
    echo "  📊 数据库类型: $DB_TYPE"
    echo ""
    
    # 读取管理员信息
    if [ -f ".env" ]; then
        ADMIN_USER=$(grep "ADMIN_USERNAME=" .env | cut -d'=' -f2)
        ADMIN_PASS=$(grep "ADMIN_PASSWORD=" .env | cut -d'=' -f2)
        echo "  👤 管理员用户名: $ADMIN_USER"
        echo "  🔐 管理员密码: $ADMIN_PASS"
        echo ""
    fi
    
    print_message $BLUE "🛠️  常用命令："
    echo "  查看服务状态: docker-compose -f $COMPOSE_FILE ps"
    echo "  查看日志: docker-compose -f $COMPOSE_FILE logs -f"
    echo "  停止服务: docker-compose -f $COMPOSE_FILE down"
    echo "  重启服务: docker-compose -f $COMPOSE_FILE restart"
    echo "  清理数据: docker-compose -f $COMPOSE_FILE down -v"
    echo ""
}

# 主函数
main() {
    print_banner
    
    # 检查是否在项目根目录
    if [ ! -f "pyproject.toml" ]; then
        print_message $RED "❌ 请在项目根目录下运行此脚本"
        exit 1
    fi
    
    # 执行部署步骤
    check_dependencies
    select_database
    configure_environment
    create_directories
    create_db_init_scripts
    build_docker_image
    start_services
    run_migrations
    health_check
    show_deployment_info
    
    print_message $GREEN "🚀 御坂弹幕服务已成功部署！"
}

# 脚本入口
case "${1:-}" in
    --help|-h)
        echo "御坂弹幕服务 Docker 一键部署脚本"
        echo ""
        echo "用法: $0 [选项]"
        echo ""
        echo "选项:"
        echo "  --help, -h     显示帮助信息"
        echo "  --logs         显示服务日志"
        echo "  --stop         停止服务"
        echo "  --restart      重启服务"
        echo "  --clean        清理服务和数据"
        echo ""
        exit 0
        ;;
    --logs)
        if [ -f "docker-compose.mysql.yml" ]; then
            COMPOSE_FILE="docker-compose.mysql.yml"
        else
            COMPOSE_FILE="docker-compose.postgres.yml"
        fi
        docker-compose -f "$COMPOSE_FILE" logs -f
        exit 0
        ;;
    --stop)
        if [ -f "docker-compose.mysql.yml" ]; then
            COMPOSE_FILE="docker-compose.mysql.yml"
        else
            COMPOSE_FILE="docker-compose.postgres.yml"
        fi
        docker-compose -f "$COMPOSE_FILE" down
        print_message $GREEN "✅ 服务已停止"
        exit 0
        ;;
    --restart)
        if [ -f "docker-compose.mysql.yml" ]; then
            COMPOSE_FILE="docker-compose.mysql.yml"
        else
            COMPOSE_FILE="docker-compose.postgres.yml"
        fi
        docker-compose -f "$COMPOSE_FILE" restart
        print_message $GREEN "✅ 服务已重启"
        exit 0
        ;;
    --clean)
        print_message $YELLOW "⚠️  这将删除所有数据，确定要继续吗？ (y/N)"
        read -n 1 -r
        echo ""
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            if [ -f "docker-compose.mysql.yml" ]; then
                COMPOSE_FILE="docker-compose.mysql.yml"
            else
                COMPOSE_FILE="docker-compose.postgres.yml"
            fi
            docker-compose -f "$COMPOSE_FILE" down -v
            docker system prune -f
            print_message $GREEN "✅ 服务和数据已清理"
        else
            print_message $BLUE "操作已取消"
        fi
        exit 0
        ;;
    "")
        # 无参数，执行主部署流程
        main
        ;;
    *)
        print_message $RED "❌ 未知选项: $1"
        echo "使用 --help 查看帮助信息"
        exit 1
        ;;
esac