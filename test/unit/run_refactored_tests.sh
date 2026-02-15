#!/bin/bash
# 运行重构后的测试

set -e

echo "========================================="
echo "运行重构后的测试"
echo "========================================="

# 激活虚拟环境（如果存在）
if [ -d "venv" ]; then
    source venv/bin/activate
elif [ -d ".venv" ]; then
    source .venv/bin/activate
fi

# 确保启用调试模式
echo "启用调试模式..."
python -c "from ginkgo.libs import GCONF; GCONF.set_debug(True); print('调试模式已启用')"

# 运行重构后的测试
echo ""
echo "运行 trading/risk 重构后的测试..."
pytest test/unit/trading/risk/test_loss_limit_risk_refactored.py -v --tb=short

echo ""
echo "运行 backtest 重构后的测试..."
pytest test/unit/backtest/test_order_refactored.py -v --tb=short
pytest test/unit/backtest/test_position_refactored.py -v --tb=short
pytest test/unit/backtest/test_bar_refactored.py -v --tb=short

echo ""
echo "========================================="
echo "测试完成！"
echo "========================================="
