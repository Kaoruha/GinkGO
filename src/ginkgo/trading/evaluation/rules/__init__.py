"""
Evaluation rules for validating Ginkgo components.

This package contains all validation rules organized by category:
- Structural rules: Inheritance, method signatures, required methods
- Logical rules: Signal fields, time provider usage, parameter validation
- Best practice rules: Decorator usage, exception handling, logging
"""

from ginkgo.trading.evaluation.rules.base_rule import (
    BaseRule,
    ASTBasedRule,
    RuntimeRule,
)
from ginkgo.trading.evaluation.rules.rule_registry import (
    RuleRegistry,
    get_global_registry,
)
from ginkgo.trading.evaluation.rules.structural_rules import (
    BaseStrategyInheritanceRule,
    CalMethodRequiredRule,
    CalSignatureValidationRule,
    SuperInitCallRule,
)
from ginkgo.trading.evaluation.rules.logical_rules import (
    ReturnStatementRule,
    SignalFieldRule,
    SignalParameterRule,
    DirectionValidationRule,
    TimeProviderUsageRule,
    ForbiddenDirectDataAccessRule,
    ForbiddenOperationsRule,
)

__all__ = [
    # Base classes
    "BaseRule",
    "ASTBasedRule",
    "RuntimeRule",
    # Registry
    "RuleRegistry",
    "get_global_registry",
    # Structural rules
    "BaseStrategyInheritanceRule",
    "CalMethodRequiredRule",
    "CalSignatureValidationRule",
    "SuperInitCallRule",
    # Logical rules
    "ReturnStatementRule",
    "SignalFieldRule",
    "SignalParameterRule",
    "DirectionValidationRule",
    "TimeProviderUsageRule",
    "ForbiddenDirectDataAccessRule",
    "ForbiddenOperationsRule",
]
