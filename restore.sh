#!/bin/bash

# Ginkgo数据库还原脚本
# 用法: ./restore.sh <备份文件路径>
# 示例: ./restore.sh /home/Backup/ginkgo_backup_202408091530.tar.gz

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 显示使用方法
show_usage() {
    echo -e "${BLUE}Ginkgo数据库还原脚本${NC}"
    echo ""
    echo "用法:"
    echo "  $0 <备份文件路径> [选项]"
    echo ""
    echo "选项:"
    echo "  -f, --force     强制还原，不进行确认"
    echo "  -h, --help      显示此帮助信息"
    echo ""
    echo "示例:"
    echo "  $0 /home/Backup/ginkgo_backup_202408091530.tar.gz"
    echo "  $0 /home/Backup/ginkgo_backup_202408091530.tar.gz --force"
    echo ""
}

# 检查Docker容器状态
check_container_status() {
    local container_name=$1
    if docker ps -a --format "table {{.Names}}" | grep -q "^${container_name}$"; then
        return 0
    else
        return 1
    fi
}

# 停止Docker容器
stop_containers() {
    log_step "停止Docker容器..."
    
    # 检查并停止ClickHouse容器
    if check_container_status "clickhouse_master"; then
        log_info "停止ClickHouse容器..."
        docker stop clickhouse_master || log_warn "ClickHouse容器可能已经停止"
    else
        log_warn "未找到clickhouse_master容器"
    fi
    
    # 检查并停止MySQL容器
    if check_container_status "mysql_master"; then
        log_info "停止MySQL容器..."
        docker stop mysql_master || log_warn "MySQL容器可能已经停止"
    else
        log_warn "未找到mysql_master容器"
    fi
    
    # 等待容器完全停止
    sleep 2
}

# 启动Docker容器
start_containers() {
    log_step "启动Docker容器..."
    
    # 启动ClickHouse容器
    if check_container_status "clickhouse_master"; then
        log_info "启动ClickHouse容器..."
        docker start clickhouse_master || log_error "启动ClickHouse容器失败"
    fi
    
    # 启动MySQL容器
    if check_container_status "mysql_master"; then
        log_info "启动MySQL容器..."
        docker start mysql_master || log_error "启动MySQL容器失败"
    fi
    
    # 等待容器完全启动
    log_info "等待容器完全启动..."
    sleep 5
    
    # 验证容器状态
    if check_container_status "clickhouse_master" && docker ps | grep -q "clickhouse_master"; then
        log_info "✅ ClickHouse容器启动成功"
    else
        log_warn "⚠️  ClickHouse容器状态异常"
    fi
    
    if check_container_status "mysql_master" && docker ps | grep -q "mysql_master"; then
        log_info "✅ MySQL容器启动成功"
    else
        log_warn "⚠️  MySQL容器状态异常"
    fi
}

# 还原数据
restore_data() {
    local backup_file=$1
    
    log_step "从备份文件还原数据: ${backup_file}"
    
    # 创建数据目录（如果不存在）
    mkdir -p ./.db
    
    # 删除现有数据（如果存在）
    if [ -d "./.db/mysql" ]; then
        log_info "删除现有MySQL数据..."
        sudo rm -rf ./.db/mysql
    fi
    
    if [ -d "./.db/clickhouse" ]; then
        log_info "删除现有ClickHouse数据..."
        sudo rm -rf ./.db/clickhouse
    fi
    
    # 解压备份文件
    log_info "解压备份文件..."
    tar --use-compress-program=pigz -xvf "$backup_file" --directory="./.db"
    
    # 检查还原结果
    if [ -d "./.db/mysql" ] && [ -d "./.db/clickhouse" ]; then
        log_info "✅ 数据还原成功"
        
        # 显示还原的数据大小
        mysql_size=$(du -sh ./.db/mysql | cut -f1)
        clickhouse_size=$(du -sh ./.db/clickhouse | cut -f1)
        log_info "MySQL数据大小: $mysql_size"
        log_info "ClickHouse数据大小: $clickhouse_size"
    else
        log_error "❌ 数据还原失败，请检查备份文件"
        exit 1
    fi
}

# 主函数
main() {
    local backup_file=""
    local force_restore=false
    
    # 解析命令行参数
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--force)
                force_restore=true
                shift
                ;;
            -h|--help)
                show_usage
                exit 0
                ;;
            -*)
                log_error "未知选项: $1"
                show_usage
                exit 1
                ;;
            *)
                if [ -z "$backup_file" ]; then
                    backup_file=$1
                else
                    log_error "多余的参数: $1"
                    show_usage
                    exit 1
                fi
                shift
                ;;
        esac
    done
    
    # 检查备份文件参数
    if [ -z "$backup_file" ]; then
        log_error "请提供备份文件路径"
        show_usage
        exit 1
    fi
    
    # 检查备份文件是否存在
    if [ ! -f "$backup_file" ]; then
        log_error "备份文件不存在: $backup_file"
        exit 1
    fi
    
    # 检查备份文件是否为tar.gz格式
    if [[ ! "$backup_file" =~ \.tar\.gz$ ]]; then
        log_warn "备份文件可能不是正确的格式 (.tar.gz)"
    fi
    
    # 显示操作信息
    echo -e "${BLUE}===========================================${NC}"
    echo -e "${BLUE}         Ginkgo数据库还原操作${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo -e "备份文件: ${GREEN}$backup_file${NC}"
    echo -e "文件大小: ${GREEN}$(du -sh "$backup_file" | cut -f1)${NC}"
    echo -e "${BLUE}===========================================${NC}"
    echo ""
    
    # 确认操作
    if [ "$force_restore" = false ]; then
        echo -e "${RED}⚠️  警告: 此操作将完全替换当前的数据库数据！${NC}"
        echo -e "${RED}⚠️  所有当前数据将被删除并替换为备份文件中的数据！${NC}"
        echo ""
        read -p "确定要继续吗？(输入 'yes' 确认): " confirm
        if [ "$confirm" != "yes" ]; then
            log_info "操作已取消"
            exit 0
        fi
    fi
    
    # 开始还原流程
    log_info "开始数据库还原流程..."
    
    # 1. 停止容器
    stop_containers
    
    # 2. 还原数据
    restore_data "$backup_file"
    
    # 3. 启动容器
    start_containers
    
    echo ""
    echo -e "${GREEN}===========================================${NC}"
    echo -e "${GREEN}         还原操作完成！${NC}"
    echo -e "${GREEN}===========================================${NC}"
    log_info "数据库已从备份文件成功还原"
    log_info "建议运行 'ginkgo data stats' 确认还原结果"
}

# 脚本入口点
main "$@"