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
