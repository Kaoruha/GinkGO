#!/bin/bash
set -e  # 遇到错误立即退出

# 切换到工作目录
cd /feast

echo "🚀 Starting Feast Server..."
echo "📝 Generating configuration file..."

# 生成配置文件
envsubst < feature_store_template.yaml > feature_store.yaml

echo "✅ Configuration generated"
echo "🌐 Starting Feast server on ${FEAST_SERVE_HOST:-0.0.0.0}:${FEAST_SERVE_PORT:-6566}..."

# 启动服务
feast serve --host "${FEAST_SERVE_HOST:-0.0.0.0}" --port "${FEAST_SERVE_PORT:-6566}"