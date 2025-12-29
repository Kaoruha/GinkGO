# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: LogicalEvaluator逻辑评估器继承BaseEvaluator提供代码逻辑检查和错误识别功能






"""
Logical evaluator for strategy business logic validation.

Validates:
- Signal field requirements
- Return statement patterns
- Direction type usage
- Time provider usage
- Forbidden operations
"""

from pathlib import Path
from typing import Optional

from ginkgo.libs import GLOG, time_logger
from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
from ginkgo.trading.evaluation.rules.logical_rules import (
    ReturnStatementRule,
    SignalFieldRule,
    SignalParameterRule,
    DirectionValidationRule,
    TimeProviderUsageRule,
    ForbiddenDirectDataAccessRule,
    ForbiddenOperationsRule,
)
from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry, get_global_registry


class LogicalEvaluator(SimpleEvaluator):
    """
    Evaluator for strategy business logic validation.

    This evaluator applies all logical validation rules to check:
    - Signal objects have required fields (code, direction)
    - cal() method returns List[Signal]
    - Direction uses DIRECTION_TYPES enum
    - Time provider is used correctly
    - No forbidden operations (DB queries, network, file I/O)

    Extends SimpleEvaluator with logical rules pre-registered.
    """

    def __init__(self, registry: Optional[RuleRegistry] = None):
        """
        Initialize the logical evaluator.

        Args:
            registry: Optional rule registry (defaults to global with logical rules)
        """
        # Use provided registry or create new one
        if registry is None:
            registry = RuleRegistry()  # Create new registry to avoid conflicts
            self._register_logical_rules(registry)

        super().__init__(ComponentType.STRATEGY, registry)

    def _register_logical_rules(self, registry: RuleRegistry) -> None:
        """
        Register all logical validation rules.

        Args:
            registry: Rule registry to populate
        """
        # Register all logical rules at STANDARD level
        logical_rules = [
            ReturnStatementRule(),
            SignalFieldRule(),
            SignalParameterRule(),
            DirectionValidationRule(),
            TimeProviderUsageRule(),
            ForbiddenDirectDataAccessRule(),
            ForbiddenOperationsRule(),
        ]

        for rule in logical_rules:
            registry.register(rule, ComponentType.STRATEGY)
            GLOG.DEBUG(f"Registered logical rule: {rule.rule_id}")

    @time_logger
    def evaluate(
        self,
        file_path: Path,
        level: EvaluationLevel = EvaluationLevel.STANDARD,
        load_component: bool = False,
        **kwargs,
    ):
        """
        Evaluate strategy business logic.

        Args:
            file_path: Path to the strategy file
            level: Evaluation level (should be STANDARD or STRICT for logical checks)
            load_component: Whether to load component class (not needed for AST-based logical checks)
            **kwargs: Additional options

        Returns:
            EvaluationResult with logical validation issues
        """
        # Logical validation is AST-based, no need to load component
        GLOG.INFO(f"Logical evaluation: {file_path.name} at {level.value} level")

        # Call parent evaluate with load_component=False
        return super().evaluate(
            file_path=file_path,
            level=level,
            load_component=False,
            **kwargs,
        )
