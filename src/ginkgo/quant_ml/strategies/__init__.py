# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: 机器学习策略模块公共接口，导出MLStrategyBase策略基类（trading域统一）、PredictionStrategy预测策略
# Note: ADR-022 原则6 · ML 策略三变体统一。MLStrategyBase 现归 trading/strategies/ml_strategy_base.py，
#       本模块 re-export 维持 quant_ml 域公共接口兼容；quant_ml 域原同名死类已删。




"""
ML策略模块

提供机器学习策略的实现，将ML模型集成到ginkgo的策略框架中。

注：MLStrategyBase 现统一归 trading 域（ADR-022 原则6）；此处 re-export 维持历史导入路径兼容。
"""

# MLStrategyBase 现统一归 trading 域（ADR-022 原则6 · 命名空间唯一性）
from ginkgo.trading.strategies.ml_strategy_base import MLStrategyBase
from ginkgo.quant_ml.strategies.prediction_strategy import PredictionStrategy

__all__ = [
    "MLStrategyBase",
    "PredictionStrategy"
]
