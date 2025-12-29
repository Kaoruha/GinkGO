# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 实现 BaseRule、ASTBasedRule、RuntimeRule 等类的核心功能，封装相关业务逻辑






"""
Base rule abstract class for evaluation rules.

All evaluation rules must inherit from BaseRule and implement the required methods.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, EvaluationSeverity
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationIssue


class BaseRule(ABC):
    """
    Abstract base class for all evaluation rules.

    Each rule is responsible for checking a specific aspect of a component
    and reporting issues if problems are found.

    Attributes:
        rule_id: Unique identifier for this rule (e.g., "BASE_STRATEGY_INHERITANCE")
        name: Human-readable name for the rule
        description: Detailed description of what the rule checks
        severity: Default severity level for issues found by this rule
        level: Minimum evaluation level at which this rule applies
        enabled: Whether this rule is enabled (can be overridden by config)
    """

    rule_id: str = ""
    name: str = ""
    description: str = ""
    severity: EvaluationSeverity = EvaluationSeverity.ERROR
    level: EvaluationLevel = EvaluationLevel.BASIC
    enabled: bool = True

    @abstractmethod
    def check(self, file_path: Path, component_class: Optional[type] = None) -> Optional[EvaluationIssue]:
        """
        Perform the evaluation check.

        Args:
            file_path: Path to the file being evaluated
            component_class: The component class (if already loaded via import)

        Returns:
            EvaluationIssue if a problem is found, None otherwise
        """
        pass

    def get_issue(
        self,
        message: str,
        suggestion: Optional[str] = None,
        file_path: Optional[Path] = None,
        line: Optional[int] = None,
        column: Optional[int] = None,
        context: Optional[str] = None,
    ) -> EvaluationIssue:
        """
        Create an EvaluationIssue with this rule's properties.

        Args:
            message: Human-readable description of the issue
            suggestion: Suggested fix or explanation
            file_path: Path to the file where the issue was found
            line: Line number where the issue occurs
            column: Column number where the issue occurs
            context: Additional context information

        Returns:
            EvaluationIssue with this rule's severity and rule_id
        """
        return EvaluationIssue(
            severity=self.severity,
            code=self.rule_id,
            message=message,
            suggestion=suggestion,
            file_path=file_path,
            line=line,
            column=column,
            context=context,
            rule_id=self.rule_id,
        )

    def is_applicable(self, level: EvaluationLevel) -> bool:
        """
        Check if this rule applies at the given evaluation level.

        Args:
            level: The evaluation level being used

        Returns:
            True if this rule should be applied at this level
        """
        return self.enabled and level.includes(self.level)

    def __repr__(self) -> str:
        """String representation of the rule."""
        return f"{self.__class__.__name__}(id={self.rule_id}, severity={self.severity.value})"


class ASTBasedRule(BaseRule):
    """
    Base class for rules that use AST static analysis.

    Subclasses should implement the `check_ast` method which receives
    the parsed AST tree.

    Supports AST caching: if ast_context is provided in component_class,
    uses cached AST instead of re-parsing.
    """

    def check(self, file_path: Path, component_class: Optional[type] = None) -> Optional[EvaluationIssue]:
        """
        Perform the evaluation check using AST.

        Args:
            file_path: Path to the file being evaluated
            component_class: Can be dict with 'ast_context' for cached AST, or ignored

        Returns:
            EvaluationIssue if a problem is found, None otherwise
        """
        import ast

        try:
            # Check for cached AST (T091 - performance optimization)
            if isinstance(component_class, dict) and "ast_context" in component_class:
                tree = component_class["ast_context"]
                source_code = component_class.get("source_code", "")
                return self.check_ast(tree, file_path, source_code)

            # Parse AST (original behavior)
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=str(file_path))
            return self.check_ast(tree, file_path, source_code)
        except SyntaxError as e:
            return self.get_issue(
                message=f"Syntax error in file: {e.msg}",
                suggestion="Fix the syntax error before evaluation",
                file_path=file_path,
                line=e.lineno,
                column=e.offset,
            )
        except Exception as e:
            return self.get_issue(
                message=f"Error parsing file: {str(e)}",
                suggestion="Ensure the file is a valid Python file",
                file_path=file_path,
            )

    @abstractmethod
    def check_ast(self, tree: "ast.Module", file_path: Path, source_code: str) -> Optional[EvaluationIssue]:
        """
        Perform the check on the parsed AST tree.

        Args:
            tree: The parsed AST tree
            file_path: Path to the file being evaluated
            source_code: Original source code string

        Returns:
            EvaluationIssue if a problem is found, None otherwise
        """
        pass


class RuntimeRule(BaseRule):
    """
    Base class for rules that use runtime inspection.

    Subclasses should implement the `check_runtime` method which receives
    the actual component class object.
    """

    def check(self, file_path: Path, component_class: Optional[type] = None) -> Optional[EvaluationIssue]:
        """
        Perform the evaluation check using runtime inspection.

        Args:
            file_path: Path to the file being evaluated
            component_class: The component class to inspect (must be provided)

        Returns:
            EvaluationIssue if a problem is found, None otherwise
        """
        if component_class is None:
            return self.get_issue(
                message="Cannot perform runtime check: component class not provided",
                suggestion="Ensure the file can be imported successfully",
                file_path=file_path,
            )

        try:
            return self.check_runtime(component_class, file_path)
        except Exception as e:
            return self.get_issue(
                message=f"Error during runtime inspection: {str(e)}",
                suggestion="Ensure the component can be instantiated",
                file_path=file_path,
            )

    @abstractmethod
    def check_runtime(self, component_class: type, file_path: Path) -> Optional[EvaluationIssue]:
        """
        Perform the check on the component class.

        Args:
            component_class: The component class to inspect
            file_path: Path to the file being evaluated

        Returns:
            EvaluationIssue if a problem is found, None otherwise
        """
        pass
