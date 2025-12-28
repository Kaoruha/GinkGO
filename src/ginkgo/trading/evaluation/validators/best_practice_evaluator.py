"""
Best practice validator for strategy code quality recommendations.

This evaluator applies all best practice validation rules to provide
recommendations for writing better strategy code.
"""

from pathlib import Path
from typing import Optional

from ginkgo.libs import GLOG, time_logger
from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
from ginkgo.trading.evaluation.rules.best_practice_rules import (
    DecoratorUsageRule,
    ExceptionHandlingRule,
    LoggingRule,
    ResetStateRule,
    ParameterValidationRule,
)
from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry, get_global_registry


class BestPracticeValidator(SimpleEvaluator):
    """
    Evaluator for strategy best practice validation.

    This evaluator applies all best practice validation rules to provide
    recommendations for:
    - Decorator usage (@time_logger, @retry)
    - Exception handling (try-except blocks)
    - Logging (GLOG usage)
    - State reset (super().reset_state() calls)
    - Parameter validation

    Extends SimpleEvaluator with best practice rules pre-registered.
    """

    def __init__(self, registry: Optional[RuleRegistry] = None):
        """
        Initialize the best practice validator.

        Args:
            registry: Optional rule registry (defaults to global with best practice rules)
        """
        # Use provided registry or create new one
        if registry is None:
            registry = RuleRegistry()  # Create new registry to avoid conflicts
            self._register_best_practice_rules(registry)

        super().__init__(ComponentType.STRATEGY, registry)

    def _register_best_practice_rules(self, registry: RuleRegistry) -> None:
        """
        Register all best practice validation rules.

        Args:
            registry: Rule registry to populate
        """
        # Register all best practice rules at STRICT level
        best_practice_rules = [
            DecoratorUsageRule(),
            ExceptionHandlingRule(),
            LoggingRule(),
            ResetStateRule(),
            ParameterValidationRule(),
        ]

        for rule in best_practice_rules:
            registry.register(rule, ComponentType.STRATEGY)
            GLOG.DEBUG(f"Registered best practice rule: {rule.rule_id}")

    @time_logger
    def evaluate(
        self,
        file_path: Path,
        level: EvaluationLevel = EvaluationLevel.STRICT,
        load_component: bool = False,
        **kwargs,
    ):
        """
        Evaluate strategy best practices.

        Args:
            file_path: Path to the strategy file
            level: Evaluation level (should be STRICT for best practice checks)
            load_component: Whether to load component class (not needed for AST-based best practice checks)
            **kwargs: Additional options

        Returns:
            EvaluationResult with best practice recommendations
        """
        # Best practice validation is AST-based, no need to load component
        GLOG.INFO(f"Best practice evaluation: {file_path.name} at {level.value} level")

        # Call parent evaluate with load_component=False
        return super().evaluate(
            file_path=file_path,
            level=level,
            load_component=False,
            **kwargs,
        )
