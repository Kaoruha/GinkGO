#!/bin/bash

# Ginkgo WebUI E2E测试运行脚本
# 连接到远程Chrome CDP实例并执行测试

echo "🚀 开始Ginkgo WebUI E2E测试..."

# 检查WebUI是否运行
echo "📡 检查WebUI服务状态..."
if ! curl -s http://127.0.0.1:8080 > /dev/null; then
    echo "❌ WebUI服务未运行，请先启动服务"
    exit 1
fi

echo "✅ WebUI服务正常运行"

# 检查远程Chrome实例连接
echo "🔗 检查远程Chrome实例连接..."
if ! curl -s http://50.10:9222/json/version > /dev/null; then
    echo "❌ 无法连接到远程Chrome实例 (50.10:9222)"
    echo "请确保远程Chrome实例正在运行并且可以访问"
    exit 1
fi

echo "✅ 远程Chrome实例连接正常"

# 安装Playwright浏览器（如果需要）
echo "📦 检查Playwright浏览器..."
if [ ! -d "$HOME/.cache/ms-playwright" ]; then
    echo "安装Playwright浏览器..."
    npx playwright install chromium
fi

# 设置环境变量
export NODE_ENV=test
export CI=true

# 运行测试
echo "🧪 开始执行E2E测试..."
npx playwright test ginkgo-e2e-test.spec.js --config=playwright.config.cjs --reporter=json,list

# 检查测试结果
if [ $? -eq 0 ]; then
    echo "✅ E2E测试完成"
    echo "📊 测试报告已生成"
    echo "查看HTML报告: npx playwright show-report"
else
    echo "❌ E2E测试失败"
    exit 1
fi