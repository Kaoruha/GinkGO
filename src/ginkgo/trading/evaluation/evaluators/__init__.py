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
