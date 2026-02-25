# Upstream: ginkgo.trading.strategies, ginkgo.service_hub
# Downstream: ginkgo.client
# Role: 参数优化模块 - 策略参数优化

"""
Ginkgo Optimization Module - 参数优化模块

提供参数优化功能:
- BaseOptimizer: 优化器基类
- GridSearchOptimizer: 网格搜索
- GeneticOptimizer: 遗传算法
- BayesianOptimizer: 贝叶斯优化
"""

__version__ = "0.1.0"
__all__ = [
    "__version__",
    # P2 - 参数优化
    "BaseOptimizer",
    "GridSearchOptimizer",
    "GeneticOptimizer",
    "BayesianOptimizer",
    # Container
    "OptimizationContainer",
    # Data models
    "OptimizationResult",
    "OptimizationRun",
    "ParameterRange",
]

# 延迟导入
def __getattr__(name: str):
    if name == "BaseOptimizer":
        from ginkgo.trading.optimization.base_optimizer import BaseOptimizer
        return BaseOptimizer
    elif name == "GridSearchOptimizer":
        from ginkgo.trading.optimization.grid_search import GridSearchOptimizer
        return GridSearchOptimizer
    elif name == "GeneticOptimizer":
        from ginkgo.trading.optimization.genetic_optimizer import GeneticOptimizer
        return GeneticOptimizer
    elif name == "BayesianOptimizer":
        from ginkgo.trading.optimization.bayesian_optimizer import BayesianOptimizer
        return BayesianOptimizer
    elif name == "OptimizationContainer":
        from ginkgo.trading.optimization.containers import OptimizationContainer
        return OptimizationContainer
    elif name == "OptimizationResult":
        from ginkgo.trading.optimization.models import OptimizationResult
        return OptimizationResult
    elif name == "OptimizationRun":
        from ginkgo.trading.optimization.models import OptimizationRun
        return OptimizationRun
    elif name == "ParameterRange":
        from ginkgo.trading.optimization.models import ParameterRange
        return ParameterRange
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
