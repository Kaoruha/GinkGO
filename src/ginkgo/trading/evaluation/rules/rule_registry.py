# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Rule Registry模块提供RuleRegistry规则注册表提供规则注册和查找功能支持规则管理功能支持回测评估和代码验证






"""
Rule registry for managing evaluation rules.

The RuleRegistry is responsible for storing, organizing, and retrieving
evaluation rules based on component type.
"""

from typing import Dict, List, Optional, TYPE_CHECKING, Type

from ginkgo.trading.evaluation.core.enums import ComponentType
from ginkgo.trading.evaluation.rules.base_rule import BaseRule

if TYPE_CHECKING:
    from ginkgo.trading.evaluation.core.evaluation_result import EvaluationIssue


class RuleRegistry:
    """
    Registry for managing evaluation rules.

    Rules are organized by component type in a flat structure:
    - ComponentType (e.g., STRATEGY)
      - List of BaseRule instances

    The registry supports:
    - Registering rules dynamically
    - Retrieving rules by component type
    - Enabling/disabling rules
    """

    _instance: Optional["RuleRegistry"] = None
    _initialized: bool = False

    def __new__(cls) -> "RuleRegistry":
        """Singleton pattern to ensure only one registry exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize the registry (only once)."""
        if not self._initialized:
            self._rules: Dict[ComponentType, List[BaseRule]] = {}
            self._rules_by_id: Dict[str, BaseRule] = {}
            RuleRegistry._initialized = True

    def register(
        self,
        rule: BaseRule,
        component_type: ComponentType,
    ) -> None:
        """
        Register a rule for a specific component type.

        Args:
            rule: The rule instance to register
            component_type: The component type this rule applies to
        """
        if component_type not in self._rules:
            self._rules[component_type] = []

        self._rules[component_type].append(rule)
        self._rules_by_id[rule.rule_id] = rule

    def register_rule_class(
        self,
        rule_class: Type[BaseRule],
        component_type: ComponentType,
        **kwargs,
    ) -> BaseRule:
        """
        Register a rule class by instantiating it.

        Args:
            rule_class: The rule class to register
            component_type: The component type this rule applies to
            **kwargs: Additional arguments to pass to the rule constructor

        Returns:
            The instantiated rule
        """
        rule = rule_class(**kwargs)
        self.register(rule, component_type)
        return rule

    def get_rules(
        self,
        component_type: ComponentType,
    ) -> List[BaseRule]:
        """
        Get all rules for a component type.

        Args:
            component_type: The component type

        Returns:
            List of rules for this component type

        Example:
            >>> registry.get_rules(ComponentType.STRATEGY)
            [BaseStrategyInheritanceRule, CalMethodRequiredRule, ...]
        """
        if component_type in self._rules:
            return self._rules[component_type].copy()
        return []

    def get_rule_by_id(self, rule_id: str) -> Optional[BaseRule]:
        """
        Get a rule by its unique ID.

        Args:
            rule_id: The unique rule identifier

        Returns:
            The rule if found, None otherwise
        """
        return self._rules_by_id.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """
        Enable a rule by its ID.

        Args:
            rule_id: The unique rule identifier

        Returns:
            True if the rule was found and enabled, False otherwise
        """
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """
        Disable a rule by its ID.

        Args:
            rule_id: The unique rule identifier

        Returns:
            True if the rule was found and disabled, False otherwise
        """
        rule = self.get_rule_by_id(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def get_registered_component_types(self) -> List[ComponentType]:
        """
        Get all component types that have registered rules.

        Returns:
            List of component types
        """
        return list(self._rules.keys())

    def clear(self) -> None:
        """Clear all registered rules."""
        self._rules.clear()
        self._rules_by_id.clear()

    def count_rules(
        self,
        component_type: Optional[ComponentType] = None,
    ) -> int:
        """
        Count the number of registered rules.

        Args:
            component_type: Filter by component type (None for all)

        Returns:
            Number of rules matching the criteria
        """
        if component_type:
            if component_type in self._rules:
                return len(self._rules[component_type])
            return 0
        else:
            return len(self._rules_by_id)

    def __repr__(self) -> str:
        """String representation of the registry."""
        return f"RuleRegistry(types={len(self._rules)}, total_rules={len(self._rules_by_id)})"


# Global registry instance
_global_registry: Optional[RuleRegistry] = None


def get_global_registry() -> RuleRegistry:
    """
    Get the global rule registry instance.

    Returns:
        The global RuleRegistry singleton
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = RuleRegistry()
    return _global_registry
