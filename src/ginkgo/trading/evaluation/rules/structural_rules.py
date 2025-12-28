"""
Structural evaluation rules for strategy validation.

These rules check the basic structure of strategy classes:
- BaseStrategyInheritanceRule: Checks if the class inherits from BaseStrategy
- CalMethodRequiredRule: Checks if the cal() method is implemented
- SuperInitCallRule: Checks if __init__ calls super().__init__()
- CalSignatureValidationRule: Validates the cal() method signature
- AbstractMarkerRule: Checks if __abstract__ = False is set for concrete strategies
"""

import ast
from pathlib import Path
from typing import Optional

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, EvaluationSeverity
from ginkgo.trading.evaluation.rules.base_rule import ASTBasedRule


class BaseStrategyInheritanceRule(ASTBasedRule):
    """
    Rule to check if a class inherits from BaseStrategy.

    Attributes:
        rule_id: UNIQUE-001
        name: Base Strategy Inheritance
        description: Checks that the strategy class inherits from BaseStrategy
    """

    rule_id = "BASE_STRATEGY_INHERITANCE"
    name = "Base Strategy Inheritance"
    description = "Checks that the strategy class inherits from BaseStrategy"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.BASIC

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """
        Check if any class in the file inherits from BaseStrategy.

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if no class inherits from BaseStrategy, None otherwise
        """
        from ginkgo.trading.strategies.base_strategy import BaseStrategy

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class inherits from BaseStrategy
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "BaseStrategy" or base_name == BaseStrategy.__name__:
                        return None  # Found a valid strategy class

        # No class inherits from BaseStrategy
        return self.get_issue(
            message="Strategy class must inherit from BaseStrategy",
            suggestion='Change class definition to: class MyStrategy(BaseStrategy):',
            file_path=file_path,
        )

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class CalMethodRequiredRule(ASTBasedRule):
    """
    Rule to check if the cal() method is implemented.

    Attributes:
        rule_id: UNIQUE-002
        name: cal() Method Required
        description: Checks that the strategy class implements the cal() method
    """

    rule_id = "CAL_METHOD_REQUIRED"
    name = "cal() Method Required"
    description = "Checks that the strategy class implements the cal() method"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.BASIC

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """
        Check if any class in the file implements the cal() method.

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if no class has a cal() method, None otherwise
        """
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            has_cal = False
            for item in class_node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "cal":
                    has_cal = True
                    break

            if not has_cal:
                return self.get_issue(
                    message=f"Strategy class '{class_name}' must implement the cal() method",
                    suggestion="Add: def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:",
                    file_path=file_path,
                    line=class_node.lineno,
                )

        return None

    def _find_strategy_classes(self, tree: ast.Module) -> list:
        """Find all classes that inherit from BaseStrategy."""
        strategy_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "BaseStrategy":
                        strategy_classes.append((node, node.name))
                        break
        return strategy_classes

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class SuperInitCallRule(ASTBasedRule):
    """
    Rule to check if __init__ calls super().__init__().

    Attributes:
        rule_id: UNIQUE-003
        name: Super __init__ Call
        description: Checks that __init__ calls super().__init__()
    """

    rule_id = "SUPER_INIT_CALL"
    name = "Super __init__ Call"
    description = "Checks that __init__ calls super().__init__() to properly initialize the base class"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.BASIC

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """
        Check if __init__ methods call super().__init__().

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if __init__ doesn't call super().__init__(), None otherwise
        """
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            init_method = self._find_method(class_node, "__init__")

            if init_method:
                if not self._has_super_init_call(init_method):
                    return self.get_issue(
                        message=f"__init__ method in '{class_name}' must call super().__init__()",
                        suggestion="Add at the start of __init__: super().__init__(*args, **kwargs)",
                        file_path=file_path,
                        line=init_method.lineno,
                    )
            else:
                # No __init__ method is fine, BaseStrategy will handle it
                pass

        return None

    def _find_strategy_classes(self, tree: ast.Module) -> list:
        """Find all classes that inherit from BaseStrategy."""
        strategy_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "BaseStrategy":
                        strategy_classes.append((node, node.name))
                        break
        return strategy_classes

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method in a class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return item
        return None

    def _has_super_init_call(self, init_method: ast.FunctionDef) -> bool:
        """Check if __init__ contains a call to super().__init__()."""
        for node in ast.walk(init_method):
            if isinstance(node, ast.Call):
                # Check if this is super().__init__()
                if isinstance(node.func, ast.Attribute):
                    if (isinstance(node.func.value, ast.Call) and
                        isinstance(node.func.value.func, ast.Name) and
                        node.func.value.func.id == "super" and
                        node.func.attr == "__init__"):
                        return True
                # Check if this is super().__init__() (simplified form)
                if isinstance(node.func, ast.Name) and node.func.id == "__init__":
                    # Need to check if it's called on super()
                    pass  # Simplified check
        return False

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class CalSignatureValidationRule(ASTBasedRule):
    """
    Rule to validate the cal() method signature.

    Attributes:
        rule_id: UNIQUE-004
        name: cal() Signature Validation
        description: Validates that cal() has the correct signature
    """

    rule_id = "CAL_SIGNATURE_VALIDATION"
    name = "cal() Signature Validation"
    description = "Validates that cal() has the correct signature: cal(self, portfolio_info, event)"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """
        Check if cal() methods have the correct signature.

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if signature is incorrect, None otherwise
        """
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            cal_method = self._find_method(class_node, "cal")

            if cal_method:
                # Check parameter count
                params = cal_method.args
                param_names = [arg.arg for arg in params.args]

                # Should have at least: self, portfolio_info, event
                if len(param_names) < 3:
                    return self.get_issue(
                        message=f"cal() method in '{class_name}' has incorrect signature",
                        suggestion="Expected: def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:",
                        file_path=file_path,
                        line=cal_method.lineno,
                    )

                # Check parameter names
                if param_names[0] != "self":
                    return self.get_issue(
                        message=f"cal() method first parameter must be 'self'",
                        suggestion="Expected: def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:",
                        file_path=file_path,
                        line=cal_method.lineno,
                    )

                if "portfolio_info" not in param_names[1].lower() and "portfolio" not in param_names[1].lower():
                    return self.get_issue(
                        message=f"cal() method second parameter should be 'portfolio_info'",
                        suggestion="Expected: def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:",
                        file_path=file_path,
                        line=cal_method.lineno,
                    )

                if "event" not in param_names[2].lower():
                    return self.get_issue(
                        message=f"cal() method third parameter should be 'event'",
                        suggestion="Expected: def cal(self, portfolio_info: Dict, event: EventBase) -> List[Signal]:",
                        file_path=file_path,
                        line=cal_method.lineno,
                    )

        return None

    def _find_strategy_classes(self, tree: ast.Module) -> list:
        """Find all classes that inherit from BaseStrategy."""
        strategy_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "BaseStrategy":
                        strategy_classes.append((node, node.name))
                        break
        return strategy_classes

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method in a class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == method_name:
                return item
        return None

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None


class AbstractMarkerRule(ASTBasedRule):
    """
    Rule to check if concrete strategy classes have __abstract__ = False marker.

    In Ginkgo, concrete strategy classes should set __abstract__ = False
    to distinguish them from abstract base strategies.

    Attributes:
        rule_id: ABSTRACT_MARKER
        name: Abstract Marker
        description: Checks that concrete strategies have __abstract__ = False
    """

    rule_id = "ABSTRACT_MARKER"
    name = "Abstract Marker"
    description = "Checks that concrete strategy classes have __abstract__ = False to mark them as non-abstract"
    severity = EvaluationSeverity.WARNING
    level = EvaluationLevel.BASIC

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """
        Check if strategy classes have the __abstract__ = False marker.

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if __abstract__ = False is missing, None otherwise
        """
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            # Skip if class appears to be abstract (has abstract methods)
            if self._is_abstract_class(class_node):
                continue

            # Check if __abstract__ = False is set
            if not self._has_abstract_false_marker(class_node):
                return self.get_issue(
                    message=f"Strategy class '{class_name}' should set __abstract__ = False",
                    suggestion="Add at class level: __abstract__ = False",
                    file_path=file_path,
                    line=class_node.lineno,
                )

        return None

    def _find_strategy_classes(self, tree: ast.Module) -> list:
        """Find all classes that inherit from BaseStrategy."""
        strategy_classes = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                for base in node.bases:
                    base_name = self._get_name(base)
                    if base_name == "BaseStrategy":
                        strategy_classes.append((node, node.name))
                        break
        return strategy_classes

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if a class appears to be abstract."""
        # Check for ABC inheritance
        for base in class_node.bases:
            base_name = self._get_name(base)
            if "ABC" in base_name or "abc.ABC" in base_name:
                return True

        # Check for abstractmethod decorators
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                for decorator in item.decorator_list:
                    dec_name = self._get_name(decorator) if isinstance(decorator, (ast.Name, ast.Attribute)) else None
                    if dec_name and "abstractmethod" in dec_name:
                        return True

        # Check for __abstract__ = True (Ginkgo pattern)
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__abstract__":
                        # Check if assigned value is True
                        if isinstance(item.value, (ast.Name, ast.Constant)):
                            value = None
                            if isinstance(item.value, ast.Name):
                                value = item.value.id
                            elif isinstance(item.value, ast.Constant):
                                value = item.value.value

                            if value is True or value == "True":
                                return True

        return False

    def _has_abstract_false_marker(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False."""
        for item in class_node.body:
            if isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name) and target.id == "__abstract__":
                        # Check if assigned value is False
                        if isinstance(item.value, (ast.Name, ast.Constant)):
                            value = None
                            if isinstance(item.value, ast.Name):
                                value = item.value.id
                            elif isinstance(item.value, ast.Constant):
                                value = item.value.value

                            if value is False or value == "False":
                                return True

        return False

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None
