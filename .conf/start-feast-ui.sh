#!/bin/bash
set -e  # 遇到错误立即退出

# 切换到工作目录
cd /feast

echo "🌐 Starting Feast Web UI..."
echo "📝 Generating configuration file..."

# 生成配置文件
envsubst < feature_store_template.yaml > feature_store.yaml

echo "✅ Configuration generated"
echo "🖥️  Starting Feast Web UI on ${FEAST_UI_HOST:-0.0.0.0}:${FEAST_UI_PORT:-9999}..."

# 启动Web UI服务
feast ui --host "${FEAST_UI_HOST:-0.0.0.0}" --port "${FEAST_UI_PORT:-9999}"