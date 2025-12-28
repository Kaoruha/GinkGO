"""
Unit tests for structural evaluation rules.

Tests for:
- BaseStrategyInheritanceRule
- CalMethodRequiredRule
- SuperInitCallRule
- CalSignatureValidationRule
"""

import ast
import tempfile
from pathlib import Path

import pytest

from ginkgo.trading.evaluation.core.enums import EvaluationLevel, EvaluationSeverity
from ginkgo.trading.evaluation.rules.structural_rules import (
    BaseStrategyInheritanceRule,
    CalMethodRequiredRule,
    CalSignatureValidationRule,
    SuperInitCallRule,
)


@pytest.mark.unit
@pytest.mark.tdd
class TestBaseStrategyInheritanceRule:
    """Test cases for BaseStrategyInheritanceRule."""

    def test_rule_initialization(self):
        """Test rule has correct properties."""
        rule = BaseStrategyInheritanceRule()
        assert rule.rule_id == "BASE_STRATEGY_INHERITANCE"
        assert rule.severity == EvaluationSeverity.ERROR
        assert rule.level == EvaluationLevel.BASIC

    def test_valid_strategy_with_base_strategy_inheritance(self):
        """Test that valid strategy with BaseStrategy inheritance passes."""
        # Create a valid strategy file
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            assert result is None, "Valid strategy should pass inheritance check"
        finally:
            file_path.unlink()

    def test_invalid_class_without_base_strategy(self):
        """Test specific scenario"""
        code = """
class MyStrategy:
    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            assert result is not None, "Should detect missing BaseStrategy inheritance"
            assert result.code == "BASE_STRATEGY_INHERITANCE"
        finally:
            file_path.unlink()



@pytest.mark.unit
@pytest.mark.tdd
class TestCalMethodRequiredRule:
    """Test cases for CalMethodRequiredRule."""

    def test_rule_initialization(self):
        """Test specific scenario"""
        rule = CalMethodRequiredRule()
        assert rule.rule_id == "CAL_METHOD_REQUIRED"
        assert rule.severity == EvaluationSeverity.ERROR
        assert rule.level == EvaluationLevel.BASIC


    def test_valid_strategy_with_cal_method(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalMethodRequiredRule()
            result = rule.check(file_path)
            assert result is None, "Valid strategy should pass cal() check"
        finally:
            file_path.unlink()


    def test_invalid_strategy_without_cal_method(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False
    pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalMethodRequiredRule()
            result = rule.check(file_path)
            assert result is not None, "Should detect missing cal() method"
            assert result.code == "CAL_METHOD_REQUIRED"
            assert "cal()" in result.message
        finally:
            file_path.unlink()



@pytest.mark.unit
@pytest.mark.tdd
class TestSuperInitCallRule:
    """Test cases for SuperInitCallRule."""

    def test_rule_initialization(self):
        """Test specific scenario"""
        rule = SuperInitCallRule()
        assert rule.rule_id == "SUPER_INIT_CALL"
        assert rule.severity == EvaluationSeverity.ERROR
        assert rule.level == EvaluationLevel.BASIC


    def test_valid_strategy_with_super_init(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def __init__(self):
        super().__init__()

    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = SuperInitCallRule()
            result = rule.check(file_path)
            assert result is None, "Valid strategy should pass super().__init__() check"
        finally:
            file_path.unlink()


    def test_invalid_strategy_without_super_init(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def __init__(self):
        pass

    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = SuperInitCallRule()
            result = rule.check(file_path)
            assert result is not None, "Should detect missing super().__init__() call"
            assert result.code == "SUPER_INIT_CALL"
        finally:
            file_path.unlink()



@pytest.mark.unit
@pytest.mark.tdd
class TestCalSignatureValidationRule:
    """Test cases for CalSignatureValidationRule."""

    def test_rule_initialization(self):
        """Test specific scenario"""
        rule = CalSignatureValidationRule()
        assert rule.rule_id == "CAL_SIGNATURE_VALIDATION"
        assert rule.severity == EvaluationSeverity.ERROR
        assert rule.level == EvaluationLevel.STANDARD


    def test_valid_cal_signature(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalSignatureValidationRule()
            result = rule.check(file_path)
            assert result is None, "Valid signature should pass"
        finally:
            file_path.unlink()


    def test_invalid_cal_signature_missing_param(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalSignatureValidationRule()
            result = rule.check(file_path)
            assert result is not None, "Should detect incorrect signature"
            assert result.code == "CAL_SIGNATURE_VALIDATION"
        finally:
            file_path.unlink()


    def test_invalid_cal_signature_wrong_param_names(self):
        """Test specific scenario"""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, a, b, c):
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalSignatureValidationRule()
            result = rule.check(file_path)
            assert result is not None, "Should detect incorrect parameter names"
        finally:
            file_path.unlink()

