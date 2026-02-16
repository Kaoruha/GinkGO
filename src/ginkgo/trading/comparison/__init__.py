# Upstream: ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.client
# Role: 回测对比模块 - 多回测结果对比分析

"""
Ginkgo Comparison Module - 回测对比模块

提供回测对比功能:
- BacktestComparator: 回测对比器
"""

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # P0 - 回测对比
    "BacktestComparator",
    # Container
    "ComparisonContainer",
    # Data models
    "ComparisonResult",
]

# 延迟导入
def __getattr__(name: str):
    if name == "BacktestComparator":
        from ginkgo.trading.comparison.backtest_comparator import BacktestComparator
        return BacktestComparator
    elif name == "ComparisonContainer":
        from ginkgo.trading.comparison.containers import ComparisonContainer
        return ComparisonContainer
    elif name == "ComparisonResult":
        from ginkgo.trading.comparison.models import ComparisonResult
        return ComparisonResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
