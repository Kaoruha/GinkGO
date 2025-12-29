# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role:   Init  模块提供EvaluationValidators评估验证器模块提供验证功能支持代码验证功能支持回测评估和代码验证






"""
Validation evaluators package.

This package contains specialized evaluators for different validation aspects:
- LogicalValidator: Business logic validation
- BestPracticeValidator: Code quality best practices
"""

from ginkgo.trading.evaluation.validators.best_practice_evaluator import BestPracticeValidator
from ginkgo.trading.evaluation.validators.logical_evaluator import LogicalEvaluator

__all__ = ["LogicalEvaluator", "BestPracticeValidator"]
