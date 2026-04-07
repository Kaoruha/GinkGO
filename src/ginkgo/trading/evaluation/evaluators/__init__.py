# Upstream: evaluation顶层包, validators子包
# Downstream: evaluators.base_evaluator (BaseEvaluator, SimpleEvaluator)
# Role: 评估器子包入口，导出BaseEvaluator抽象基类和SimpleEvaluator简化评估器实现






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

