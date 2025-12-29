# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role:   Init  模块提供EvaluationCore评估核心模块提供评估基础功能支持评估框架功能支持回测评估和代码验证






"""
Core evaluation entities and enums.

This package contains the fundamental data structures for the evaluation module:
- ComponentType: Enum of supported component types (STRATEGY, SELECTOR, SIZER, RISK_MANAGER)
- EvaluationLevel: Enum of evaluation levels (BASIC, STANDARD, STRICT)
- EvaluationSeverity: Enum of issue severities (ERROR, WARNING, INFO)
- EvaluationResult: Result entity containing all issues from evaluation
- EvaluationIssue: Individual issue entity with location and suggestion
"""

from ginkgo.trading.evaluation.core.enums import (
    ComponentType,
    EvaluationLevel,
    EvaluationSeverity,
)
from ginkgo.trading.evaluation.core.evaluation_result import (
    EvaluationResult,
    EvaluationIssue,
)

__all__ = [
    "ComponentType",
    "EvaluationLevel",
    "EvaluationSeverity",
    "EvaluationResult",
    "EvaluationIssue",
]
