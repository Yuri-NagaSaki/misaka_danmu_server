#!/bin/bash
# 御坂弹幕服务器管理脚本
# Misaka Danmu Server Management Script

PROJECT_NAME="misaka_danmu_server"
WORK_DIR="$HOME/${PROJECT_NAME}"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

print_message() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
}

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "=================================================="
    echo "🎬 Misaka 弹幕服务器 - 服务管理"
    echo "=================================================="
    echo -e "${NC}"
}

# 检查服务状态
check_service_status() {
    if [[ ! -d "$WORK_DIR" ]]; then
        return 1
    fi
    
    cd "$WORK_DIR"
    
    # 检查容器状态
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            if docker-compose -f "$compose_file" ps 2>/dev/null | grep -q "Up"; then
                return 0
            fi
        fi
    done
    
    return 1
}

# 显示服务状态
show_status() {
    print_banner
    
    if check_service_status; then
        cd "$WORK_DIR"
        
        print_message $GREEN "🟢 服务运行状态: 正常运行"
        echo
        
        # 显示服务信息
        if [[ -f ".env" ]]; then
            SERVER_PORT=$(grep "SERVER_PORT=" .env | cut -d'=' -f2)
            DB_TYPE=$(grep "DB_TYPE=" .env | cut -d'=' -f2)
            ADMIN_USERNAME=$(grep "ADMIN_USERNAME=" .env | cut -d'=' -f2)
            ADMIN_PASSWORD=$(grep "ADMIN_PASSWORD=" .env | cut -d'=' -f2)
            
            print_message $WHITE "📋 服务信息:"
            echo "  🌐 Web界面: http://localhost:${SERVER_PORT:-7768}"
            echo "  📖 API文档: http://localhost:${SERVER_PORT:-7768}/docs"
            echo "  📊 数据库: $DB_TYPE"
            echo "  👤 管理员: $ADMIN_USERNAME"
            echo "  🔐 密码: $ADMIN_PASSWORD"
            echo
        fi
        
        # 显示容器状态
        print_message $WHITE "🐳 容器状态:"
        for compose_file in docker-compose.*.yml; do
            if [[ -f "$compose_file" ]]; then
                docker-compose -f "$compose_file" ps
                break
            fi
        done
        
    else
        print_message $RED "🔴 服务运行状态: 未运行或未安装"
        echo
        print_message $YELLOW "使用以下命令部署服务:"
        echo "  ./scripts/deploy.sh"
    fi
    
    echo
}

# 显示日志
show_logs() {
    print_banner
    
    if ! check_service_status; then
        print_message $RED "❌ 服务未运行"
        exit 1
    fi
    
    cd "$WORK_DIR"
    
    print_message $BLUE "📜 显示服务日志 (Ctrl+C 退出):"
    echo
    
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            docker-compose -f "$compose_file" logs -f --tail=50
            break
        fi
    done
}

# 重启服务
restart_service() {
    print_banner
    
    if ! check_service_status; then
        print_message $RED "❌ 服务未运行，无法重启"
        exit 1
    fi
    
    cd "$WORK_DIR"
    
    print_message $BLUE "🔄 重启服务..."
    
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            docker-compose -f "$compose_file" restart
            break
        fi
    done
    
    sleep 5
    
    if check_service_status; then
        print_message $GREEN "✅ 服务重启成功"
    else
        print_message $RED "❌ 服务重启失败"
        exit 1
    fi
}

# 停止服务
stop_service() {
    print_banner
    
    if ! check_service_status; then
        print_message $YELLOW "⚠️  服务已停止"
        exit 0
    fi
    
    cd "$WORK_DIR"
    
    print_message $BLUE "⏹️  停止服务..."
    
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            docker-compose -f "$compose_file" stop
            break
        fi
    done
    
    print_message $GREEN "✅ 服务已停止"
}

# 启动服务
start_service() {
    print_banner
    
    if [[ ! -d "$WORK_DIR" ]]; then
        print_message $RED "❌ 服务未安装，请先运行部署脚本"
        exit 1
    fi
    
    cd "$WORK_DIR"
    
    if check_service_status; then
        print_message $YELLOW "⚠️  服务已在运行中"
        exit 0
    fi
    
    print_message $BLUE "▶️  启动服务..."
    
    for compose_file in docker-compose.*.yml; do
        if [[ -f "$compose_file" ]]; then
            docker-compose -f "$compose_file" start
            break
        fi
    done
    
    sleep 5
    
    if check_service_status; then
        print_message $GREEN "✅ 服务启动成功"
        show_status
    else
        print_message $RED "❌ 服务启动失败"
        exit 1
    fi
}

# 显示帮助
show_help() {
    echo "Misaka 弹幕服务器 - 管理脚本"
    echo
    echo "用法: $0 [命令]"
    echo
    echo "命令:"
    echo "  status      显示服务状态"
    echo "  start       启动服务"
    echo "  stop        停止服务"  
    echo "  restart     重启服务"
    echo "  logs        显示实时日志"
    echo "  --help      显示帮助信息"
    echo
    echo "无参数运行显示服务状态"
}

# 主函数
main() {
    case "${1:-status}" in
        status|"")
            show_status
            ;;
        start)
            start_service
            ;;
        stop)
            stop_service
            ;;
        restart)
            restart_service
            ;;
        logs)
            show_logs
            ;;
        --help|-h)
            show_help
            ;;
        *)
            print_message $RED "❌ 未知命令: $1"
            echo
            show_help
            exit 1
            ;;
    esac
}

main "$@"