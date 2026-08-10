#!/bin/bash
# Web-UI 启动脚本 - 支持日志记录

cd "$(dirname "$0")"

# 日志文件
LOG_FILE="/tmp/webui-dev.log"

echo "=== Web-UI 启动: $(date) ===" >> "$LOG_FILE"

# 启动 Vite 开发服务器
pnpm dev 2>&1 | tee -a "$LOG_FILE"
