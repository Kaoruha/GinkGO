#!/bin/bash
# Ginkgo 日志清理脚本
# 清理 ClickHouse 和其他服务的旧日志文件

set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOGS_DIR="${PROJECT_ROOT}/.logs"

echo "🧹 开始清理 Ginkgo 日志..."
echo "日志目录: ${LOGS_DIR}"

# 清理 ClickHouse 旧日志（保留最近2个）
clean_clickhouse_logs() {
    local log_dir="$1"
    if [ -d "$log_dir" ]; then
        echo ""
        echo "📁 清理 $(basename "$log_dir")"
        # 删除 .log.3 及更旧的日志
        find "$log_dir" -name "clickhouse-server.log.[3-9].gz" -delete 2>/dev/null || true
        find "$log_dir" -name "clickhouse-server.log.1[0-9].gz" -delete 2>/dev/null || true

        # 清空当前错误日志
        if [ -f "$log_dir/clickhouse-server.err.log" ]; then
            echo "  清空 clickhouse-server.err.log"
            > "$log_dir/clickhouse-server.err.log"
        fi

        # 显示当前大小
        local size=$(du -sh "$log_dir" 2>/dev/null | cut -f1)
        echo "  当前大小: $size"
    fi
}

# 清理所有 ClickHouse 日志
clean_clickhouse_logs "${LOGS_DIR}/clickhouse"
clean_clickhouse_logs "${LOGS_DIR}/clickhouse_test"

# 清理 Python 应用日志（只保留 error.log）
clean_python_logs() {
    for dir in "${LOGS_DIR}"/*; do
        if [ -d "$dir" ]; then
            # 跳过 ClickHouse 和 MySQL 日志（单独处理）
            if [[ "$dir" =~ (clickhouse|mysql) ]]; then
                continue
            fi
            # 删除旧的 .log.1, .log.2 等轮转文件
            find "$dir" -name "*.log.[0-9]" -delete 2>/dev/null || true
        fi
    done
}

clean_python_logs

# 显示最终结果
echo ""
echo "✅ 清理完成！"
echo ""
echo "当前日志目录大小："
du -sh "${LOGS_DIR}"/* 2>/dev/null | sort -hr | head -10
