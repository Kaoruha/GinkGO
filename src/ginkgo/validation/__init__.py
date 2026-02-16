# Upstream: ginkgo.trading.engines, ginkgo.service_hub
# Downstream: ginkgo.trading.strategies
# Role: 策略验证模块 - 走步验证、蒙特卡洛、敏感性分析等

"""
Ginkgo Validation Module - 策略验证模块

提供策略验证和分析功能:
- WalkForwardValidator: 走步验证
- MonteCarloSimulator: 蒙特卡洛模拟
- SensitivityAnalyzer: 敏感性分析
- TimeSeriesCrossValidator: 时间序列交叉验证
"""

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # P2 - 策略验证
    "WalkForwardValidator",
    "MonteCarloSimulator",
    "SensitivityAnalyzer",
    "TimeSeriesCrossValidator",
    # Container
    "ValidationContainer",
    # Data models
    "WalkForwardResult",
    "WalkForwardFold",
    "MonteCarloResult",
    "OptimizationResult",
]

# 延迟导入
def __getattr__(name: str):
    if name == "WalkForwardValidator":
        from ginkgo.validation.walk_forward import WalkForwardValidator
        return WalkForwardValidator
    elif name == "MonteCarloSimulator":
        from ginkgo.validation.monte_carlo import MonteCarloSimulator
        return MonteCarloSimulator
    elif name == "SensitivityAnalyzer":
        from ginkgo.validation.sensitivity import SensitivityAnalyzer
        return SensitivityAnalyzer
    elif name == "TimeSeriesCrossValidator":
        from ginkgo.validation.cross_validation import TimeSeriesCrossValidator
        return TimeSeriesCrossValidator
    elif name == "ValidationContainer":
        from ginkgo.validation.containers import ValidationContainer
        return ValidationContainer
    elif name == "WalkForwardResult":
        from ginkgo.validation.models import WalkForwardResult
        return WalkForwardResult
    elif name == "WalkForwardFold":
        from ginkgo.validation.models import WalkForwardFold
        return WalkForwardFold
    elif name == "MonteCarloResult":
        from ginkgo.validation.models import MonteCarloResult
        return MonteCarloResult
    elif name == "OptimizationResult":
        from ginkgo.validation.models import OptimizationResult
        return OptimizationResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
