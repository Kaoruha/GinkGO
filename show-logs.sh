#!/bin/bash
# 显示服务日志

echo "=========================================="
echo "  API Server 日志 (最新 20 行)"
echo "  文件: /tmp/apiserver.log"
echo "=========================================="
tail -20 /tmp/apiserver.log

echo ""
echo "=========================================="
echo "  Web-UI 日志 (最新 20 行)"
echo "  文件: /tmp/webui-dev.log"
echo "=========================================="
tail -20 /tmp/webui-dev.log

echo ""
echo "=========================================="
echo "  服务状态"
echo "=========================================="
echo "API Server (8000):"
curl -s http://localhost:8000/api/health 2>&1 | head -1
echo ""
echo "Web-UI (5173):"
curl -s http://localhost:5173 2>&1 | head -1
