"""
Edge case tests for strategy validation module (T094).

Tests for:
- Syntax errors
- Import failures
- Multiple classes per file
- Empty files
- Malformed code
"""

import tempfile
from pathlib import Path

import pytest

from ginkgo.trading.evaluation.core.enums import EvaluationSeverity
from ginkgo.trading.evaluation.evaluators.base_evaluator import SimpleEvaluator
from ginkgo.trading.evaluation.rules.structural_rules import (
    BaseStrategyInheritanceRule,
    CalMethodRequiredRule,
)
from ginkgo.trading.evaluation.core.enums import ComponentType


@pytest.mark.unit
@pytest.mark.tdd
class TestSyntaxErrors:
    """Test handling of files with syntax errors."""

    def test_syntax_error_in_strategy_file(self):
        """Test that syntax errors are properly reported."""
        # Create a file with syntax error
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        # Missing closing parenthesis - syntax error
        return [
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should handle syntax error gracefully and return an issue
            # The issue will have the rule's code but mention syntax error in message
            assert result is not None
            assert "Syntax error" in result.message or "syntax" in result.message.lower()
        finally:
            file_path.unlink()

    def test_indentation_error(self):
        """Test that indentation errors are properly reported."""
        # Create actual indentation error
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False
    def cal(self, portfolio_info, event):
    return []
  # This line has wrong indentation after the function
        pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalMethodRequiredRule()
            result = rule.check(file_path)
            # Indentation errors are syntax errors in Python
            # Should return an issue mentioning the error
            assert result is not None
            assert "indentation" in result.message.lower() or "syntax" in result.message.lower() or "unexpected" in result.message.lower()
        finally:
            file_path.unlink()

    def test_invalid_python_version_syntax(self):
        """Test handling of Python version-specific syntax issues."""
        # Using older syntax that should still work
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
            # Should parse successfully
            assert result is None or result.code != "SYNTAX_ERROR"
        finally:
            file_path.unlink()


@pytest.mark.unit
@pytest.mark.tdd
class TestImportFailures:
    """Test handling of files with import issues."""

    def test_missing_base_strategy_import(self):
        """Test AST-based validation doesn't require imports."""
        # AST-based rules only check class names, not actual imports
        # This is expected behavior - AST parsing works without executing code
        code = """
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
            # AST-based check passes because it sees "BaseStrategy" in the class definition
            # The actual import error would only occur at runtime
            assert result is None
        finally:
            file_path.unlink()

    def test_circular_import_attempt(self):
        """Test that circular import patterns are handled."""
        # This file imports from a module that would cause circular import
        code = """
# Simulate a file that might cause import issues
import sys
sys.path.insert(0, '.')

try:
    from ginkgo.trading.strategies.base_strategy import BaseStrategy

    class MyStrategy(BaseStrategy):
        __abstract__ = False

        def cal(self, portfolio_info, event):
            return []
except ImportError:
    pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            # AST-based check should still work even if import would fail
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should parse AST successfully
            assert result is None or result.code != "IMPORT_ERROR"
        finally:
            file_path.unlink()

    def test_nonexistent_module_import(self):
        """Test handling of import from non-existent module."""
        code = """
from nonexistent_module import StrategyBase

class MyStrategy(StrategyBase):
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
            # Should parse AST but detect no BaseStrategy
            assert result is not None
            assert result.code == "BASE_STRATEGY_INHERITANCE"
        finally:
            file_path.unlink()


@pytest.mark.unit
@pytest.mark.tdd
class TestMultipleClassesPerFile:
    """Test handling of files with multiple class definitions."""

    def test_file_with_multiple_strategies(self):
        """Test that first strategy class is validated."""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class FirstStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []

class SecondStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        return []

class HelperClass:
    def helper_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            # Should find at least one valid strategy
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # At least one strategy should exist
            assert result is None  # First class inherits from BaseStrategy
        finally:
            file_path.unlink()

    def test_file_with_no_strategy_classes(self):
        """Test that files without strategy classes are handled."""
        code = """
class HelperClass:
    def helper_method(self):
        pass

class AnotherHelper:
    def another_method(self):
        pass
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should detect no strategy class
            assert result is not None
            assert result.code == "BASE_STRATEGY_INHERITANCE"
        finally:
            file_path.unlink()

    def test_abstract_and_concrete_strategy_mix(self):
        """Test file with both abstract and concrete strategies."""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class AbstractStrategy(BaseStrategy):
    __abstract__ = True  # Abstract strategy

    def cal(self, portfolio_info, event):
        return []

class ConcreteStrategy(BaseStrategy):
    __abstract__ = False  # Concrete strategy

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
            # Should find at least BaseStrategy inheritance
            assert result is None
        finally:
            file_path.unlink()


@pytest.mark.unit
@pytest.mark.tdd
class TestEmptyAndMalformedFiles:
    """Test handling of empty and malformed files."""

    def test_completely_empty_file(self):
        """Test that empty files are handled."""
        code = ""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should report no strategy class found
            assert result is not None
        finally:
            file_path.unlink()

    def test_file_with_only_comments(self):
        """Test that files with only comments are handled."""
        code = """
# This is a comment
# Another comment
# No actual code
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should report no strategy class found
            assert result is not None
        finally:
            file_path.unlink()

    def test_file_with_only_whitespace(self):
        """Test that files with only whitespace are handled."""
        code = "   \n\n\t\t\n   "
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should report no strategy class found
            assert result is not None
        finally:
            file_path.unlink()

    def test_file_with_incomplete_class_definition(self):
        """Test that incomplete class definitions are handled."""
        code = """
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False
    # Missing cal() method
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = CalMethodRequiredRule()
            result = rule.check(file_path)
            # Should detect missing cal() method
            assert result is not None
            assert result.code == "CAL_METHOD_REQUIRED"
        finally:
            file_path.unlink()


@pytest.mark.unit
@pytest.mark.tdd
class TestEvaluatorEdgeCases:
    """Test evaluator behavior with edge cases."""

    def test_evaluator_with_nonexistent_file(self):
        """Test that evaluator handles non-existent files."""
        from pathlib import Path as StdPath

        evaluator = SimpleEvaluator(ComponentType.STRATEGY)
        file_path = StdPath("/nonexistent/path/strategy.py")

        with pytest.raises(FileNotFoundError):
            evaluator.evaluate(file_path)

    def test_evaluator_with_non_python_file(self):
        """Test that evaluator handles non-Python files."""
        import tempfile

        # Create a text file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write("This is not a Python file")
            f.flush()
            file_path = Path(f.name)

        try:
            evaluator = SimpleEvaluator(ComponentType.STRATEGY)
            # Should not raise but handle gracefully
            # The AST parsing will fail or return no issues
            result = evaluator.evaluate(file_path, load_component=False)
            assert result is not None
        finally:
            file_path.unlink()

    def test_evaluator_with_unicode_characters(self):
        """Test that evaluator handles Unicode characters in code."""
        code = """
# Chinese comments
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        # Return signals
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should handle unicode correctly
            assert result is None
        finally:
            file_path.unlink()

    def test_evaluator_with_very_long_line(self):
        """Test that evaluator handles very long lines."""
        # Create a very long line
        long_line = "x = " + ",".join([f"i{i}" for i in range(1000)])
        code = f"""
from ginkgo.trading.strategies.base_strategy import BaseStrategy

class MyStrategy(BaseStrategy):
    __abstract__ = False

    def cal(self, portfolio_info, event):
        {long_line}
        return []
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            f.flush()
            file_path = Path(f.name)

        try:
            rule = BaseStrategyInheritanceRule()
            result = rule.check(file_path)
            # Should handle long lines
            assert result is None
        finally:
            file_path.unlink()
