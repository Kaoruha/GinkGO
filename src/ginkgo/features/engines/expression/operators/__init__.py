# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role:   Init  引擎提供Operators操作符模块提供表达式操作符公共导出支持数学/统计/技术操作计算和处理






"""
Operators Module - 操作符实现

提供各种类型的操作符实现：
- basic: 基础运算符 (+, -, *, /)
- statistical: 统计函数 (Mean, Std, Max, Min)
- temporal: 时序操作 (Ref, Delta, Rolling)
- technical: 技术指标 (RSI, MACD, BOLL)
"""

# 导入所有操作符模块，确保它们被注册到OperatorRegistry
from ginkgo.features.engines.expression.operators import basic
from ginkgo.features.engines.expression.operators import statistical
from ginkgo.features.engines.expression.operators import temporal
from ginkgo.features.engines.expression.operators import technical

__all__ = ["basic", "statistical", "temporal", "technical"]