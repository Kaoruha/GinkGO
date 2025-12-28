"""
Base evaluator abstract class for component evaluation.

Evaluators orchestrate the application of rules and generate evaluation results.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Type

from ginkgo.libs import GLOG, time_logger
from ginkgo.trading.evaluation.core.enums import ComponentType, EvaluationLevel
from ginkgo.trading.evaluation.core.evaluation_result import EvaluationResult
from ginkgo.trading.evaluation.rules.base_rule import BaseRule
from ginkgo.trading.evaluation.rules.rule_registry import RuleRegistry, get_global_registry


class BaseEvaluator(ABC):
    """
    Abstract base class for component evaluators.

    Evaluators are responsible for:
    - Loading the component file
    - Applying registered evaluation rules
    - Collecting and reporting issues
    - Generating evaluation results

    Attributes:
        component_type: The type of component this evaluator handles
        registry: The rule registry to use (defaults to global registry)
    """

    def __init__(
        self,
        component_type: ComponentType,
        registry: Optional[RuleRegistry] = None,
    ) -> None:
        """
        Initialize the evaluator.

        Args:
            component_type: The type of component to evaluate
            registry: The rule registry to use (defaults to global registry)
        """
        self.component_type = component_type
        self.registry = registry or get_global_registry()

    @abstractmethod
    def evaluate(
        self,
        file_path: Path,
        level: EvaluationLevel = EvaluationLevel.STANDARD,
        **kwargs,
    ) -> EvaluationResult:
        """
        Evaluate a component file.

        Args:
            file_path: Path to the component file to evaluate
            level: Evaluation level to use
            **kwargs: Additional evaluation options

        Returns:
            EvaluationResult containing all issues found
        """
        pass

    def _load_component_class(self, file_path: Path) -> Optional[Type]:
        """
        Dynamically load a component class from a file.

        Args:
            file_path: Path to the component file

        Returns:
            The loaded component class, or None if loading failed
        """
        import importlib.util
        import sys
        from pathlib import Path as StdPath

        try:
            # Convert to stdlib Path for compatibility
            file_path_std = StdPath(str(file_path))

            # Create module name from file path
            module_name = file_path_std.stem

            # Load the module
            spec = importlib.util.spec_from_file_location(module_name, file_path_std)
            if spec is None or spec.loader is None:
                return None

            module = importlib.util.module_from_spec(spec)
            sys.modules[module_name] = module
            spec.loader.exec_module(module)

            # Find the component class (first class that matches component type)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if isinstance(attr, type) and self._is_component_class(attr):
                    return attr

            return None
        except Exception:
            return None

    def _is_component_class(self, cls: Type) -> bool:
        """
        Check if a class is a component class of the expected type.

        Args:
            cls: The class to check

        Returns:
            True if this is a component class of the expected type
        """
        # This is a basic check - subclasses should override for specific logic
        from ginkgo.trading.strategies.base_strategy import BaseStrategy

        if self.component_type == ComponentType.STRATEGY:
            try:
                return issubclass(cls, BaseStrategy) and cls is not BaseStrategy
            except TypeError:
                return False
        return False

    def _create_result(
        self,
        file_path: Path,
        level: EvaluationLevel,
        issues: Optional[list] = None,
        duration_seconds: Optional[float] = None,
    ) -> EvaluationResult:
        """
        Create an evaluation result.

        Args:
            file_path: Path to the evaluated file
            level: Evaluation level used
            issues: List of issues found (optional)
            duration_seconds: Time taken for evaluation (optional)

        Returns:
            EvaluationResult instance
        """
        return EvaluationResult(
            file_path=file_path,
            component_type=self.component_type.value,
            level=level,
            issues=issues or [],
            duration_seconds=duration_seconds,
        )

    def _parse_ast_once(self, file_path: Path) -> Optional[dict]:
        """
        Parse AST once and cache it for all AST-based rules (T091).

        Args:
            file_path: Path to the file to parse

        Returns:
            Dict with 'ast_context' and 'source_code', or None if parsing fails
        """
        import ast

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                source_code = f.read()
            tree = ast.parse(source_code, filename=str(file_path))
            return {
                "ast_context": tree,
                "source_code": source_code,
            }
        except Exception as e:
            GLOG.WARN(f"Failed to parse AST for caching: {e}")
            return None

    @staticmethod
    def _get_ast_base_rule_class() -> type:
        """
        Get the ASTBasedRule class for isinstance checks (T091).

        Returns:
            The ASTBasedRule class
        """
        from ginkgo.trading.evaluation.rules.base_rule import ASTBasedRule
        return ASTBasedRule

    @staticmethod
    def _get_runtime_rule_class() -> type:
        """
        Get the RuntimeRule class for isinstance checks (T093).

        Returns:
            The RuntimeRule class
        """
        from ginkgo.trading.evaluation.rules.base_rule import RuntimeRule
        return RuntimeRule


class SimpleEvaluator(BaseEvaluator):
    """
    Simple evaluator that applies rules without complex orchestration.

    This evaluator:
    1. Validates input parameters
    2. Loads the component class (optional)
    3. Retrieves applicable rules from the registry
    4. Applies each rule and collects issues
    5. Returns the result with comprehensive error handling
    """

    @time_logger
    def evaluate(
        self,
        file_path: Path,
        level: EvaluationLevel = EvaluationLevel.STANDARD,
        load_component: bool = True,
        **kwargs,
    ) -> EvaluationResult:
        """
        Evaluate a component file.

        Args:
            file_path: Path to the component file to evaluate
            level: Evaluation level to use
            load_component: Whether to load the component class for runtime checks
            **kwargs: Additional evaluation options

        Returns:
            EvaluationResult containing all issues found

        Raises:
            ValueError: If file_path is invalid
            FileNotFoundError: If file doesn't exist
        """
        import time

        # Input validation (T034)
        if not file_path:
            raise ValueError("file_path cannot be None or empty")

        file_path = Path(file_path)

        # Check file exists
        if not file_path.exists():
            GLOG.ERROR(f"File not found: {file_path}")
            raise FileNotFoundError(f"Strategy file not found: {file_path}")

        # Check file extension
        if file_path.suffix != ".py":
            GLOG.WARN(f"File does not have .py extension: {file_path}")

        # Log evaluation start (T033)
        GLOG.INFO(f"Evaluating {self.component_type.value}: {file_path.name}")

        start_time = time.time()
        issues = []

        try:
            # T091: Parse AST once for all AST-based rules (performance optimization)
            ast_context = self._parse_ast_once(file_path)

            # Get applicable rules first
            rules = self.registry.get_rules(self.component_type)
            GLOG.DEBUG(f"Applying {len(rules)} rules")

            # T093: Lazy loading - only load component class if RuntimeRule exists
            component_class = None
            has_runtime_rule = any(isinstance(r, self._get_runtime_rule_class()) for r in rules)

            if load_component and has_runtime_rule:
                try:
                    component_class = self._load_component_class(file_path)
                    if component_class:
                        GLOG.DEBUG(f"Loaded component class: {component_class.__name__}")
                except Exception as e:
                    # Log error but continue with static analysis only
                    GLOG.WARN(f"Failed to load component class: {e}")
                    issues.append(self._create_load_error_issue(file_path, str(e)))
            elif not has_runtime_rule:
                GLOG.DEBUG("Skipping component class loading - no RuntimeRule registered")

            # Apply each rule with error handling (T032)
            for rule in rules:
                try:
                    # Pass cached AST context to AST-based rules (T091)
                    if isinstance(rule, self._get_ast_base_rule_class()):
                        check_target = ast_context if ast_context else component_class
                    else:
                        check_target = component_class

                    issue = rule.check(file_path, check_target)
                    if issue:
                        issues.append(issue)
                        GLOG.DEBUG(f"Rule {rule.rule_id} found issue: {issue.message}")
                except Exception as e:
                    # Log rule execution error but continue with other rules
                    GLOG.ERROR(f"Rule {rule.rule_id} failed: {e}")
                    # Create an error issue for the failed rule
                    issues.append(self._create_rule_error_issue(file_path, rule, str(e)))

            duration = time.time() - start_time

            # Log completion (T033)
            result = self._create_result(
                file_path=file_path,
                level=level,
                issues=issues,
                duration_seconds=duration,
            )

            if result.passed:
                GLOG.INFO(f"Evaluation passed: {file_path.name} ({duration:.2f}s)")
            else:
                GLOG.WARN(f"Evaluation failed: {file_path.name} - {result.error_count} errors ({duration:.2f}s)")

            return result

        except Exception as e:
            # Catch-all error handling (T032)
            GLOG.ERROR(f"Evaluation failed for {file_path}: {e}")
            duration = time.time() - start_time

            # Return result with error information
            return self._create_result(
                file_path=file_path,
                level=level,
                issues=[],
                duration_seconds=duration,
            )

    def _create_load_error_issue(self, file_path: Path, error_msg: str) -> "EvaluationIssue":
        """Create an issue for component loading errors."""
        from ginkgo.trading.evaluation.core.evaluation_result import EvaluationIssue
        from ginkgo.trading.evaluation.core.enums import EvaluationSeverity

        return EvaluationIssue(
            severity=EvaluationSeverity.WARNING,
            code="COMPONENT_LOAD_ERROR",
            message=f"Failed to load component class: {error_msg}",
            suggestion="Check for import errors or missing dependencies. Static analysis will still be performed.",
            file_path=file_path,
        )

    def _create_rule_error_issue(self, file_path: Path, rule: BaseRule, error_msg: str) -> "EvaluationIssue":
        """Create an issue for rule execution errors."""
        from ginkgo.trading.evaluation.core.evaluation_result import EvaluationIssue
        from ginkgo.trading.evaluation.core.enums import EvaluationSeverity

        return EvaluationIssue(
            severity=EvaluationSeverity.WARNING,
            code="RULE_EXECUTION_ERROR",
            message=f"Rule {rule.rule_id} failed during execution: {error_msg}",
            suggestion="This may indicate a bug in the evaluation rule. Please report this issue.",
            file_path=file_path,
        )
