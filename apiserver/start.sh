#!/bin/bash
# API Server 启动脚本 - 支持热重载和日志记录

cd "$(dirname "$0")"

# 日志文件
LOG_FILE="/tmp/apiserver-dev.log"

# 启动 API Server（使用 uvicorn --reload 支持热重载）
uv run uvicorn main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    --log-level info 2>&1 | tee "$LOG_FILE"
