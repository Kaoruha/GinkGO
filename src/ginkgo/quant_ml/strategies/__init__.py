"""
ML策略模块

提供机器学习策略的实现，将ML模型集成到ginkgo的策略框架中。
"""

from .ml_strategy_base import MLStrategyBase
from .prediction_strategy import PredictionStrategy

__all__ = [
    "MLStrategyBase",
    "PredictionStrategy"
]