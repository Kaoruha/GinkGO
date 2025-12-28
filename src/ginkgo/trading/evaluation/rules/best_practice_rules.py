"""
Best practice validation rules for strategy code quality.

These rules check for code quality best practices and provide recommendations
for writing more robust and maintainable strategy code.
"""

import ast
from pathlib import Path
from typing import Optional

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, EvaluationSeverity
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationIssue
from ginkgo.trading.evaluation.rules.base_rule import ASTBasedRule


class DecoratorUsageRule(ASTBasedRule):
    """
    Rule to check for recommended decorator usage.

    Recommends using @time_logger and @retry decorators for better
    performance monitoring and resilience.
    """

    rule_id = "DECORATOR_USAGE"
    severity = EvaluationSeverity.INFO
    level = EvaluationLevel.STRICT

    def check_ast(
        self,
        tree: ast.Module,
        file_path: Path,
        source_code: str,
    ) -> Optional["EvaluationIssue"]:
        """Check if cal() method has recommended decorators."""
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            if self._is_abstract_class(class_node):
                continue

            cal_method = self._find_method(class_node, "cal")
            if not cal_method:
                continue

            # Check for @time_logger decorator
            has_time_logger = any(
                self._is_decorator_named(dec, "time_logger")
                for dec in cal_method.decorator_list
            )

            # Check for @retry decorator
            has_retry = any(
                self._is_decorator_named(dec, "retry")
                for dec in cal_method.decorator_list
            )

            # Only recommend decorators if neither is present (satisfied if at least one exists)
            if not has_time_logger and not has_retry:
                suggestions = []
                if not has_time_logger:
                    suggestions.append("consider adding @time_logger decorator for performance monitoring")
                if not has_retry:
                    suggestions.append("consider adding @retry decorator for resilience")

                if suggestions:
                    return self.get_issue(
                        message=f"Method cal() in '{class_name}' could benefit from decorators",
                        suggestion="; ".join(suggestions),
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

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False marker."""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__abstract__":
                            if isinstance(stmt.value, ast.Constant):
                                return stmt.value.value is True
        return False

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method by name in the class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == method_name:
                    return item
        return None

    def _is_decorator_named(self, decorator: ast.expr, name: str) -> bool:
        """Check if decorator matches given name."""
        if isinstance(decorator, ast.Name):
            return decorator.id == name
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id == name
        elif isinstance(decorator, ast.Attribute):
            return decorator.attr == name
        return False


class ExceptionHandlingRule(ASTBasedRule):
    """
    Rule to check for proper exception handling.

    Recommends using try-except blocks in cal() method to handle
    potential errors gracefully.
    """

    rule_id = "EXCEPTION_HANDLING"
    severity = EvaluationSeverity.INFO
    level = EvaluationLevel.STRICT

    def check_ast(
        self,
        tree: ast.Module,
        file_path: Path,
        source_code: str,
    ) -> Optional["EvaluationIssue"]:
        """Check if cal() method has exception handling."""
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            if self._is_abstract_class(class_node):
                continue

            cal_method = self._find_method(class_node, "cal")
            if not cal_method:
                continue

            # Check if method body contains try-except
            has_try_except = self._has_try_except(cal_method)

            if not has_try_except:
                return self.get_issue(
                    message=f"Method cal() in '{class_name}' lacks exception handling",
                    suggestion="consider adding try-except block to handle potential errors gracefully",
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

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False marker."""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__abstract__":
                            if isinstance(stmt.value, ast.Constant):
                                return stmt.value.value is True
        return False

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method by name in the class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == method_name:
                    return item
        return None

    def _has_try_except(self, method_node: ast.FunctionDef) -> bool:
        """Check if method contains try-except block."""
        for node in ast.walk(method_node):
            if isinstance(node, ast.Try):
                return True
        return False


class LoggingRule(ASTBasedRule):
    """
    Rule to check for proper logging usage.

    Recommends using GLOG for logging important events and debugging.
    """

    rule_id = "LOGGING_USAGE"
    severity = EvaluationSeverity.INFO
    level = EvaluationLevel.STRICT

    def check_ast(
        self,
        tree: ast.Module,
        file_path: Path,
        source_code: str,
    ) -> Optional["EvaluationIssue"]:
        """Check if cal() method has logging for debugging."""
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            if self._is_abstract_class(class_node):
                continue

            cal_method = self._find_method(class_node, "cal")
            if not cal_method:
                continue

            # Check for GLOG usage or print statements
            has_logging = self._has_logging(cal_method)

            if not has_logging:
                return self.get_issue(
                    message=f"Method cal() in '{class_name}' lacks logging statements",
                    suggestion="consider adding GLOG.INFO/DEBUG for better debugging and monitoring",
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

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False marker."""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__abstract__":
                            if isinstance(stmt.value, ast.Constant):
                                return stmt.value.value is True
        return False

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method by name in the class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == method_name:
                    return item
        return None

    def _has_logging(self, method_node: ast.FunctionDef) -> bool:
        """Check if method contains logging calls."""
        for node in ast.walk(method_node):
            # Check for function calls
            if isinstance(node, ast.Call):
                # Check for GLOG.* calls
                if isinstance(node.func, ast.Attribute):
                    if isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "GLOG":
                            return True
                # Check for print calls
                elif isinstance(node.func, ast.Name):
                    if node.func.id == "print":
                        return True
        return False


class ResetStateRule(ASTBasedRule):
    """
    Rule to check if reset_state() method calls super().reset_state().

    Ensures proper state reset chain in strategy inheritance.
    """

    rule_id = "RESET_STATE_CALL"
    severity = EvaluationSeverity.WARNING
    level = EvaluationLevel.STRICT

    def check_ast(
        self,
        tree: ast.Module,
        file_path: Path,
        source_code: str,
    ) -> Optional["EvaluationIssue"]:
        """Check if reset_state() calls super().reset_state()."""
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            if self._is_abstract_class(class_node):
                continue

            reset_method = self._find_method(class_node, "reset_state")
            if not reset_method:
                continue

            # Check if method calls super().reset_state()
            calls_super = self._calls_super_reset(reset_method)

            if not calls_super:
                return self.get_issue(
                    message=f"Method reset_state() in '{class_name}' does not call super().reset_state()",
                    suggestion="ensure reset_state() calls super().reset_state() to maintain proper state reset chain",
                    file_path=file_path,
                    line=reset_method.lineno,
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

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False marker."""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__abstract__":
                            if isinstance(stmt.value, ast.Constant):
                                return stmt.value.value is True
        return False

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method by name in the class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == method_name:
                    return item
        return None

    def _calls_super_reset(self, method_node: ast.FunctionDef) -> bool:
        """Check if method calls super().reset_state()."""
        for node in ast.walk(method_node):
            if isinstance(node, ast.Call):
                # Check for super().reset_state()
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "reset_state":
                        # Check if it's called on super()
                        if isinstance(node.func.value, ast.Call):
                            if isinstance(node.func.value.func, ast.Name):
                                if node.func.value.func.id == "super":
                                    return True
        return False


class ParameterValidationRule(ASTBasedRule):
    """
    Rule to check for input parameter validation.

    Recommends validating input parameters in cal() method.
    """

    rule_id = "PARAMETER_VALIDATION"
    severity = EvaluationSeverity.INFO
    level = EvaluationLevel.STRICT

    def check_ast(
        self,
        tree: ast.Module,
        file_path: Path,
        source_code: str,
    ) -> Optional["EvaluationIssue"]:
        """Check if cal() method validates input parameters."""
        strategy_classes = self._find_strategy_classes(tree)

        for class_node, class_name in strategy_classes:
            if self._is_abstract_class(class_node):
                continue

            cal_method = self._find_method(class_node, "cal")
            if not cal_method:
                continue

            # Check for parameter validation patterns
            has_validation = self._has_parameter_validation(cal_method)

            if not has_validation:
                return self.get_issue(
                    message=f"Method cal() in '{class_name}' lacks input parameter validation",
                    suggestion="consider validating portfolio_info and event parameters (e.g., None checks, type checks)",
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

    def _get_name(self, node: ast.AST) -> Optional[str]:
        """Extract the name from an AST node."""
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _is_abstract_class(self, class_node: ast.ClassDef) -> bool:
        """Check if class has __abstract__ = False marker."""
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if isinstance(target, ast.Name):
                        if target.id == "__abstract__":
                            if isinstance(stmt.value, ast.Constant):
                                return stmt.value.value is True
        return False

    def _find_method(self, class_node: ast.ClassDef, method_name: str) -> Optional[ast.FunctionDef]:
        """Find a method by name in the class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef):
                if item.name == method_name:
                    return item
        return None

    def _has_parameter_validation(self, method_node: ast.FunctionDef) -> bool:
        """Check if method has parameter validation."""
        # Look for common validation patterns
        validation_keywords = ["if not", "if None", "assert", "isinstance", "raise"]

        for node in ast.walk(method_node):
            # Check early statements (first 10 nodes)
            if isinstance(node, (ast.If, ast.Assert)):
                return True
            # Check for raise statements (validation errors)
            if isinstance(node, ast.Raise):
                return True

        return False
