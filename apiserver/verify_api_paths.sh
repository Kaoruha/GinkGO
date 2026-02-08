#!/bin/bash

# API 路径验证脚本
# 验证所有API端点都使用了正确的版本前缀和命名规范

echo "=========================================="
echo "API 路径验证脚本"
echo "=========================================="
echo ""

# 检查版本配置文件
echo "1. 检查版本配置文件..."
if [ -f "core/version.py" ]; then
    echo "   ✓ core/version.py 存在"

    # 检查关键常量
    if grep -q "API_VERSION = \"v1\"" core/version.py; then
        echo "   ✓ API_VERSION 正确设置为 v1"
    else
        echo "   ✗ API_VERSION 未正确设置"
    fi

    if grep -q "API_PREFIX = \"/api/v1\"" core/version.py; then
        echo "   ✓ API_PREFIX 正确设置为 /api/v1"
    else
        echo "   ✗ API_PREFIX 未正确设置"
    fi
else
    echo "   ✗ core/version.py 不存在"
fi

echo ""

# 检查 main.py 路由注册
echo "2. 检查 main.py 路由注册..."
if [ -f "main.py" ]; then
    echo "   ✓ main.py 存在"

    # 检查是否使用统一前缀
    if grep -q 'API_PREFIX' main.py; then
        echo "   ✓ main.py 使用 API_PREFIX 常量"
    else
        echo "   ! main.py 未使用 API_PREFIX 常量"
    fi

    # 检查各个路由的前缀
    ROUTES=("auth" "dashboard" "portfolio" "backtest" "components" "data" "arena" "settings" "node-graphs")
    for route in "${ROUTES[@]}"; do
        if grep -q "prefix=f\"{API_PREFIX}/$route\"" main.py; then
            echo "   ✓ $route 路由使用正确前缀"
        elif grep -q "prefix=\"/api/$route\"" main.py; then
            echo "   ! $route 路由使用旧前缀 /api/$route"
        elif grep -q "prefix=\"$route\"" main.py; then
            echo "   ✗ $route 路由缺少前缀"
        fi
    done
else
    echo "   ✗ main.py 不存在"
fi

echo ""

# 检查前端 API 模块
echo "3. 检查前端 API 模块路径..."
FRONTEND_API_DIR="../web-ui/src/api/modules"

if [ -d "$FRONTEND_API_DIR" ]; then
    echo "   ✓ 前端 API 目录存在"

    # 检查各个模块文件
    MODULES=("portfolio.ts" "backtest.ts" "nodeGraph.ts" "components.ts" "auth.ts" "settings.ts")

    for module in "${MODULES[@]}"; do
        FILE="$FRONTEND_API_DIR/$module"
        if [ -f "$FILE" ]; then
            echo "   ✓ $module 存在"

            # 检查是否使用新路径
            if grep -q "'/api/v1/" "$FILE"; then
                echo "     ✓ $module 使用 /api/v1 前缀"
            elif grep -q '"/api/v1/' "$FILE"; then
                echo "     ✓ $module 使用 /api/v1 前缀"
            else
                echo "     ! $module 未使用 /api/v1 前缀"
            fi
        else
            echo "   ✗ $module 不存在"
        fi
    done
else
    echo "   ! 前端 API 目录不存在: $FRONTEND_API_DIR"
fi

echo ""

# 检查后端路由文件
echo "4. 检查后端路由文件..."
API_DIR="api"

if [ -d "$API_DIR" ]; then
    echo "   ✓ 后端 API 目录存在"

    # 检查各个路由文件是否使用正确的路径格式
    ROUTE_FILES=("portfolio.py" "backtest.py" "node_graph.py" "components.py" "dashboard.py")

    for route_file in "${ROUTE_FILES[@]}"; do
        FILE="$API_DIR/$route_file"
        if [ -f "$FILE" ]; then
            echo "   ✓ $route_file 存在"

            # 检查是否使用空字符串路径（在 main.py 中已添加前缀）
            if grep -q '@router.get("")' "$FILE"; then
                echo "     ✓ $route_file 使用正确的路由格式"
            fi
        else
            echo "   ! $route_file 不存在（可选模块）"
        fi
    done
else
    echo "   ✗ 后端 API 目录不存在"
fi

echo ""

# 检查文档
echo "5. 检查文档..."
if [ -f "API_VERSIONING.md" ]; then
    echo "   ✓ API_VERSIONING.md 存在"
else
    echo "   ✗ API_VERSIONING.md 不存在"
fi

echo ""
echo "=========================================="
echo "验证完成"
echo "=========================================="
echo ""
echo "下一步："
echo "1. 运行应用服务器: python start.py"
echo "2. 访问文档: http://localhost:8000/docs"
echo "3. 测试API端点"
echo ""
