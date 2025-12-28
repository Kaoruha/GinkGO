"""
Logical validation rules for strategy evaluation.

This module provides AST-based rules for validating strategy business logic,
including Signal field requirements, return statements, time provider usage,
and forbidden operations.
"""

import ast
from pathlib import Path
from typing import Optional, List

from ginkgo.trading.evaluation.core.enums import EvaluationSeverity, EvaluationLevel
from ginkgo.trading.evaluation.rules.base_rule import ASTBasedRule


class ReturnStatementRule(ASTBasedRule):
    """
    Validates that cal() method returns List[Signal].

    Checks:
    - cal() has a return statement
    - Returns empty list [] or list of Signals
    - Does not return None or single Signal
    """

    rule_id = "RETURN_STATEMENT"
    name = "Return Statement Validation"
    description = "Validates cal() method returns List[Signal]"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check return statements in cal() method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    issue = self._check_cal_method(cal_method, file_path)
                    if issue:
                        return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_cal_method(self, method: ast.FunctionDef, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check cal() method return statement."""
        return_stmts = self._find_return_statements(method)

        if not return_stmts:
            return self.get_issue(
                message="cal() method must have a return statement",
                suggestion="Add 'return []' or 'return [Signal(...)]' to cal() method",
                file_path=file_path,
                line=method.lineno,
            )

        # Check each return statement
        for ret in return_stmts:
            if ret.value is None:
                return self.get_issue(
                    message="cal() method should not return None",
                    suggestion="Return empty list 'return []' or list of Signals",
                    file_path=file_path,
                    line=ret.lineno,
                )
            elif isinstance(ret.value, ast.Call):
                # Check if it's Signal() call (single signal, not in list)
                func_name = None
                if isinstance(ret.value.func, ast.Name):
                    func_name = ret.value.func.id
                elif isinstance(ret.value.func, ast.Attribute):
                    func_name = ret.value.func.attr

                if func_name == "Signal":
                    return self.get_issue(
                        message="cal() must return List[Signal], not single Signal",
                        suggestion="Wrap Signal in list: 'return [Signal(...)]'",
                        file_path=file_path,
                        line=ret.lineno,
                    )

        return None

    def _find_return_statements(self, node: ast.AST) -> List[ast.Return]:
        """Recursively find all return statements in a node."""
        returns = []
        for child in ast.walk(node):
            if isinstance(child, ast.Return):
                returns.append(child)
        return returns


class SignalFieldRule(ASTBasedRule):
    """
    Validates Signal constructor calls have required fields.

    Required fields:
    - code: str
    - direction: DIRECTION_TYPES
    - reason: str (optional but recommended)
    """

    rule_id = "SIGNAL_FIELD"
    name = "Signal Field Validation"
    description = "Validates Signal has required fields (code, direction)"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    def __init__(self):
        super().__init__()
        self._required_fields = {"code", "direction"}

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check Signal() calls in cal() method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    for child in ast.walk(cal_method):
                        if isinstance(child, ast.Call):
                            issue = self._check_signal_call(child, file_path)
                            if issue:
                                return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_signal_call(self, node: ast.Call, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check Signal() call has required fields."""
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name != "Signal":
            return None

        # Extract keyword arguments
        provided_fields = set()
        for kw in node.keywords:
            if kw.arg:
                provided_fields.add(kw.arg)

        # Check for missing required fields
        missing_fields = self._required_fields - provided_fields
        if missing_fields:
            return self.get_issue(
                message=f"Signal() missing required fields: {', '.join(missing_fields)}",
                suggestion="Add missing fields: Signal(code='...', direction=DIRECTION_TYPES.LONG, ...)",
                file_path=file_path,
                line=node.lineno,
            )

        return None


class DirectionValidationRule(ASTBasedRule):
    """
    Validates direction parameter uses DIRECTION_TYPES enum.

    Checks:
    - direction uses DIRECTION_TYPES.LONG or DIRECTION_TYPES.SHORT
    - Not using string values like "LONG" or "SHORT"
    """

    rule_id = "DIRECTION_VALIDATION"
    name = "Direction Type Validation"
    description = "Validates direction uses DIRECTION_TYPES enum"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    def __init__(self):
        super().__init__()
        self._valid_directions = {"LONG", "SHORT"}

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check direction parameter in Signal() calls."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    for child in ast.walk(cal_method):
                        if isinstance(child, ast.Call):
                            issue = self._check_direction_value(child, file_path)
                            if issue:
                                return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_direction_value(self, node: ast.Call, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check direction parameter in Signal() call."""
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name != "Signal":
            return None

        # Find direction argument
        direction_value = None
        for kw in node.keywords:
            if kw.arg == "direction":
                direction_value = kw.value
                break

        if direction_value is None:
            return None  # Will be caught by SignalFieldRule

        # Check if direction is a string (invalid)
        if isinstance(direction_value, ast.Str):
            if direction_value.s in self._valid_directions:
                return self.get_issue(
                    message=f"Use DIRECTION_TYPES.{direction_value.s} instead of string '{direction_value.s}'",
                    suggestion=f"Change direction='{direction_value.s}' to direction=DIRECTION_TYPES.{direction_value.s}",
                    file_path=file_path,
                    line=node.lineno,
                )
        elif isinstance(direction_value, ast.Constant) and isinstance(direction_value.value, str):
            if direction_value.value in self._valid_directions:
                return self.get_issue(
                    message=f"Use DIRECTION_TYPES.{direction_value.value} instead of string '{direction_value.value}'",
                    suggestion=f"Change direction='{direction_value.value}' to direction=DIRECTION_TYPES.{direction_value.value}",
                    file_path=file_path,
                    line=node.lineno,
                )

        return None


class TimeProviderUsageRule(ASTBasedRule):
    """
    Validates proper time retrieval in strategy.

    Forbidden:
    - datetime.now()
    - time.time()
    - Other direct time access

    Allowed:
    - self.get_time_provider()
    - event.timestamp
    """

    rule_id = "TIME_PROVIDER_USAGE"
    name = "Time Provider Usage Validation"
    description = "Validates use of self.get_time_provider() instead of datetime.now()"
    severity = EvaluationSeverity.WARNING
    level = EvaluationLevel.STANDARD

    def __init__(self):
        super().__init__()
        self._forbidden_calls = {
            "datetime.datetime.now",
            "datetime.now",
            "time.time",
            "time.clock",
        }

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check time provider usage in cal() method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    for child in ast.walk(cal_method):
                        if isinstance(child, ast.Call):
                            issue = self._check_time_call(child, file_path)
                            if issue:
                                return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_time_call(self, node: ast.Call, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check for forbidden time retrieval calls."""
        call_str = self._get_call_string(node)
        if call_str in self._forbidden_calls:
            return self.get_issue(
                message=f"Use self.get_time_provider() instead of {call_str}()",
                suggestion="Replace with: tp = self.get_time_provider(); current_time = tp.now()",
                file_path=file_path,
                line=node.lineno,
            )
        return None

    def _get_call_string(self, node: ast.Call) -> Optional[str]:
        """Extract call string."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            elif isinstance(node.func.value, ast.Attribute):
                return f"{node.func.value.value.id}.{node.func.value.attr}.{node.func.attr}"
        return None


class ForbiddenDirectDataAccessRule(ASTBasedRule):
    """
    Detects forbidden direct data imports that bypass datafeeder time control.

    Forbidden:
    - from ginkgo.data import get_bars
    - from ginkgo.data import get_daybar, get_tick, etc.

    Allowed:
    - self.get_bars_cached() - cached data access through datafeeder
    - self.data_feeder.get_bars() - direct datafeeder access

    Why:
    Direct imports bypass time boundary validation in BacktestFeeder,
    allowing strategies to access future data (look-ahead bias).
    Datafeeder enforces time boundaries to prevent temporal violations.
    """

    rule_id = "FORBIDDEN_DIRECT_DATA_ACCESS"
    name = "Forbidden Direct Data Access"
    description = "Detects direct data imports that bypass datafeeder time control"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    # Forbidden data access functions from ginkgo.data
    _forbidden_imports = {
        "get_bars",
        "get_daybar",
        "get_tick",
        "get_ticks",
        "get_bar",
        "add_bars",
        "add_bar",
        "delete_bars",
        "update_bars",
    }

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check for forbidden direct data imports at module level."""
        for node in tree.body:
            if isinstance(node, ast.ImportFrom):
                issue = self._check_data_import(node, file_path)
                if issue:
                    return issue
        return None

    def _check_data_import(self, node: ast.ImportFrom, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check for forbidden imports from ginkgo.data."""
        # Check if importing from ginkgo.data
        if node.module != "ginkgo.data":
            return None

        # Check for forbidden function imports
        forbidden_found = []
        for alias in node.names:
            if alias.name in self._forbidden_imports:
                forbidden_found.append(alias.name)

        if forbidden_found:
            return self.get_issue(
                message=f"Forbidden direct data access: {', '.join(forbidden_found)}",
                suggestion=(
                    "Use self.get_bars_cached() or self.data_feeder.get_bars() instead. "
                    "Direct imports bypass time boundary validation and may cause look-ahead bias."
                ),
                file_path=file_path,
                line=node.lineno,
            )

        return None


class ForbiddenOperationsRule(ASTBasedRule):
    """
    Detects forbidden operations in cal() method.

    Forbidden:
    - Database queries (CRUD operations)
    - Network calls (requests, urllib)
    - File I/O (open, read, write)

    Allowed:
    - self.data_feeder operations
    - Event handling
    - Signal generation
    """

    rule_id = "FORBIDDEN_OPERATIONS"
    name = "Forbidden Operations Detection"
    description = "Detects database queries, network calls, and file I/O in cal()"
    severity = EvaluationSeverity.WARNING
    level = EvaluationLevel.STANDARD

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check for forbidden operations in cal() method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    for child in ast.walk(cal_method):
                        if isinstance(child, (ast.Call, ast.Import, ast.ImportFrom)):
                            issue = self._check_forbidden_operation(child, file_path)
                            if issue:
                                return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_forbidden_operation(self, node: ast.AST, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check for forbidden operations."""
        # Check for forbidden imports in cal()
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in ["requests", "urllib", "httpx", "sqlite3", "pymongo"]:
                    return self.get_issue(
                        message=f"Forbidden import in cal(): {alias.name}",
                        suggestion="Move imports to module level or __init__",
                        file_path=file_path,
                        line=node.lineno,
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module and any(x in node.module for x in ["requests", "urllib", "httpx"]):
                return self.get_issue(
                    message=f"Forbidden import in cal(): {node.module}",
                    suggestion="Move imports to module level or __init__",
                    file_path=file_path,
                    line=node.lineno,
                )
        elif isinstance(node, ast.Call):
            call_str = self._get_call_string(node)
            # Check for forbidden patterns
            forbidden_patterns = [
                ("add_bars", "database"),
                ("get_bars", "database"),
                ("delete_bars", "database"),
                ("cruds.", "database"),
                ("crud.", "database"),
                ("requests.", "network"),
                ("urllib.", "network"),
                ("open(", "file I/O"),
            ]

            if call_str:
                for pattern, desc in forbidden_patterns:
                    if pattern in call_str and "data_feeder" not in call_str:
                        return self.get_issue(
                            message=f"Forbidden operation detected: {desc}",
                            suggestion="Use self.data_feeder for data access, avoid direct DB/network/file operations",
                            file_path=file_path,
                            line=node.lineno,
                        )

        return None

    def _get_call_string(self, node: ast.Call) -> Optional[str]:
        """Extract call string."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name):
                return f"{node.func.value.id}.{node.func.attr}"
            elif isinstance(node.func.value, ast.Attribute):
                return f"{node.func.value.value.id}.{node.func.value.attr}.{node.func.attr}"
        return None


class SignalParameterRule(ASTBasedRule):
    """
    Validates Signal() constructor uses correct parameters.

    Checks:
    - Use business_timestamp instead of timestamp
    - portfolio_id, engine_id, run_id should be from portfolio_info or self
    - business_timestamp should come from portfolio_info.get("now")

    Why:
    Signal's __init__ uses business_timestamp parameter, not timestamp.
    Using timestamp parameter results in signal.business_timestamp being None,
    causing database validation errors when portfolio tries to save signals.

    Correct Example:
        Signal(
            portfolio_id=portfolio_info.get("uuid"),
            engine_id=self.engine_id,
            run_id=self.run_id,
            business_timestamp=portfolio_info.get("now"),
            code=code,
            direction=direction,
            reason=reason
        )

    Incorrect Example:
        Signal(
            timestamp=portfolio_info.get("now"),  # Wrong parameter!
            code=code,
            direction=direction
        )
    """

    rule_id = "SIGNAL_PARAMETER"
    name = "Signal Parameter Validation"
    description = "Validates Signal() uses correct parameter names (business_timestamp, not timestamp)"
    severity = EvaluationSeverity.ERROR
    level = EvaluationLevel.STANDARD

    def check_ast(self, tree: ast.Module, file_path: Path, source_code: str) -> Optional["EvaluationIssue"]:
        """Check Signal() calls in cal() method."""
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                cal_method = self._find_cal_method(node)
                if cal_method:
                    for child in ast.walk(cal_method):
                        if isinstance(child, ast.Call):
                            issue = self._check_signal_call(child, file_path)
                            if issue:
                                return issue
        return None

    def _find_cal_method(self, class_node: ast.ClassDef) -> Optional[ast.FunctionDef]:
        """Find cal() method in class."""
        for item in class_node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "cal":
                return item
        return None

    def _check_signal_call(self, node: ast.Call, file_path: Path) -> Optional["EvaluationIssue"]:
        """Check Signal() call parameters."""
        func_name = None
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name != "Signal":
            return None

        # Extract all keyword arguments
        kwargs = {}
        for kw in node.keywords:
            if kw.arg:
                kwargs[kw.arg] = kw.value

        # Check for incorrect 'timestamp' parameter
        if "timestamp" in kwargs:
            return self.get_issue(
                message="Signal() uses 'timestamp' parameter but should use 'business_timestamp'",
                suggestion=(
                    "Change 'timestamp=...' to 'business_timestamp=...'. "
                    "Signal.__init__ expects business_timestamp, not timestamp. "
                    "Using timestamp will result in signal.business_timestamp=None, "
                    "causing database validation errors."
                ),
                file_path=file_path,
                line=node.lineno,
            )

        # Check if missing recommended context parameters
        recommended_params = {"portfolio_id", "engine_id", "run_id", "business_timestamp"}
        provided_params = set(kwargs.keys())
        missing_recommended = recommended_params - provided_params

        if missing_recommended:
            # Only warn, not error, as some strategies might work without these
            # But still report as warning
            return self.get_issue(
                message=f"Signal() missing recommended parameters: {', '.join(missing_recommended)}",
                suggestion=(
                    f"Add missing parameters: {', '.join(missing_recommended)}. "
                    f"Example: Signal(portfolio_id=portfolio_info.get('uuid'), "
                    f"engine_id=self.engine_id, run_id=self.run_id, "
                    f"business_timestamp=portfolio_info.get('now'), ...)"
                ),
                file_path=file_path,
                line=node.lineno,
            )

        return None
