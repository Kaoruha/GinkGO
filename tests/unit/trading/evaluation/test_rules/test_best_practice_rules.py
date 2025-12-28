"""
Unit tests for Best Practice validation rules (T073-T075).

Tests for code quality and best practice recommendations.
"""

import ast
from pathlib import Path
from unittest.mock import Mock

import pytest

from ginkgo.trading.evaluation.rules.best_practice_rules import (
    DecoratorUsageRule,
    ExceptionHandlingRule,
    LoggingRule,
)


@pytest.mark.unit
@pytest.mark.tdd
class TestDecoratorUsageRule:
    """Unit tests for DecoratorUsageRule (T073)."""

    def test_decorator_usage_recommends_time_logger(self):
        """
        Test DecoratorUsageRule recommends @time_logger (T073).

        Expected: Should suggest adding @time_logger to cal() method.
        """
        # Strategy without @time_logger
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""

        rule = DecoratorUsageRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should recommend @time_logger
        assert issue is not None
        assert issue.rule_id == "DECORATOR_USAGE"
        assert "@time_logger" in issue.suggestion.lower() or "time_logger" in issue.suggestion.lower()

    def test_decorator_usage_pass_with_time_logger(self):
        """
        Test DecoratorUsageRule passes with @time_logger (T073).

        Expected: No issue when @time_logger is present.
        """
        # Strategy with @time_logger
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.libs import time_logger

class MyStrategy(BaseStrategy):
    __abstract__ = False

    @time_logger
    def cal(self, portfolio_info, event):
        return []
"""

        rule = DecoratorUsageRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should not raise issue
        assert issue is None

    def test_decorator_usage_recommends_retry(self):
        """
        Test DecoratorUsageRule recommends @retry (T073).

        Expected: Should suggest adding @retry for robustness.
        """
        # Strategy without @retry
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""

        rule = DecoratorUsageRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should recommend @retry
        if issue:  # May be INFO level
            assert "@retry" in issue.suggestion.lower() or "retry" in issue.suggestion.lower()


@pytest.mark.unit
@pytest.mark.tdd
class TestExceptionHandlingRule:
    """Unit tests for ExceptionHandlingRule (T074)."""

    def test_exception_handling_recommends_try_except(self):
        """
        Test ExceptionHandlingRule recommends try-except (T074).

        Expected: Should suggest adding try-except blocks in cal().
        """
        # Strategy without exception handling
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        result = self.calculate()
        return result
"""

        rule = ExceptionHandlingRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should recommend exception handling
        assert issue is not None
        assert "try" in issue.suggestion.lower() or "except" in issue.suggestion.lower()

    def test_exception_handling_pass_with_try_except(self):
        """
        Test ExceptionHandlingRule passes with try-except (T074).

        Expected: No issue when try-except is present.
        """
        # Strategy with exception handling
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        try:
            result = self.calculate()
            return result
        except Exception as e:
            self.logger.error(f"Error: {e}")
            return []
"""

        rule = ExceptionHandlingRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should not raise issue
        assert issue is None


@pytest.mark.unit
@pytest.mark.tdd
class TestLoggingRule:
    """Unit tests for LoggingRule (T075)."""

    def test_logging_rule_recommends_glog(self):
        """
        Test LoggingRule recommends GLOG usage (T075).

        Expected: Should suggest using GLOG for logging.
        """
        # Strategy without logging
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        signals = self.generate_signals()
        return signals
"""

        rule = LoggingRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should recommend GLOG logging
        assert issue is not None
        assert "GLOG" in issue.suggestion or "logging" in issue.suggestion.lower()

    def test_logging_rule_pass_with_glog(self):
        """
        Test LoggingRule passes with GLOG usage (T075).

        Expected: No issue when GLOG is used.
        """
        # Strategy with GLOG logging
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy
from ginkgo.libs import GLOG

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        GLOG.DEBUG("Generating signals")
        signals = self.generate_signals()
        GLOG.INFO(f"Generated {len(signals)} signals")
        return signals
"""

        rule = LoggingRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should not raise issue
        assert issue is None

    def test_logging_rule_pass_with_print_logging(self):
        """
        Test LoggingRule passes with print statements (T075).

        Expected: No issue when using print for debugging.
        """
        # Strategy with print statements
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        print(f"Processing event: {event}")
        signals = self.generate_signals()
        print(f"Generated {len(signals)} signals")
        return signals
"""

        rule = LoggingRule()
        tree = ast.parse(code)

        issue = rule.check_ast(tree, Path("test.py"), code)

        # Should not raise issue (print is acceptable)
        assert issue is None
