# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 机器学习策略模块公共接口，导出MLStrategyBase策略基类、PredictionStrategy预测策略等ML驱动策略实现






"""
ML策略模块

提供机器学习策略的实现，将ML模型集成到ginkgo的策略框架中。
"""

from ginkgo.quant_ml.strategies.ml_strategy_base import MLBaseStrategy
from ginkgo.quant_ml.strategies.prediction_strategy import PredictionStrategy

__all__ = [
    "MLBaseStrategy",
    "PredictionStrategy"
]