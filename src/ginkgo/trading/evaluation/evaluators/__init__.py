# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 评估器模块导出基类/回测评估/实盘偏离检测等评估器实现支持交易系统功能支持回测分析和实盘监控提供策略评估






"""
Evaluator components for orchestrating validation rules.

This package contains evaluator implementations:
- ComponentEvaluator: Unified evaluator supporting all component types
- StructuralEvaluator: Structural validation (inheritance, methods)
- LogicalEvaluator: Logical validation (signals, parameters)
- BestPracticeEvaluator: Best practice validation (decorators, logging)
"""

from ginkgo.trading.evaluation.evaluators.base_evaluator import (
    BaseEvaluator,
    SimpleEvaluator,
)

__all__ = [
    "BaseEvaluator",
    "SimpleEvaluator",
]
