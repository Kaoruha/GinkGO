# Upstream: CLI评估命令, 回测引擎
# Downstream: core.enums, core.evaluation_result
# Role: 策略评估模块入口，导出ComponentType/EvaluationLevel/EvaluationSeverity枚举和EvaluationResult/EvaluationIssue结果实体






"""
Ginkgo Strategy Evaluation Module

This module provides static analysis and runtime validation for trading strategies
and other Ginkgo components (Selector, Sizer, RiskManager).

Main Components:
- ComponentEvaluator: Unified evaluator for all component types
- SignalTracer: Runtime signal generation tracking
- SignalVisualizer: Visualization of signals on price charts
- EvaluationPipeline: Flexible evaluation workflow orchestration
"""

from ginkgo.trading.evaluation.core.enums import (
    ComponentType,
    EvaluationLevel,
    EvaluationSeverity,
)
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult, EvaluationIssue

__all__ = [
    # Enums
    "ComponentType",
    "EvaluationLevel",
    "EvaluationSeverity",
    # Core Entities
    "EvaluationResult",
    "EvaluationIssue",
]

