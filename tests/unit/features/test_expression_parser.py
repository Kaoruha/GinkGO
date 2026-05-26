"""Smoke tests for features.engines.expression.parser -- #3870"""
import pytest

try:
    from ginkgo.features.engines.expression.parser import (
        ExpressionParser, ParseError, Token,
        parse_expression, validate_expression, get_expression_dependencies,
    )
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ExpressionParser not available")
class TestExpressionParser:
    def test_instantiation(self):
        parser = ExpressionParser()
        assert parser is not None

    def test_parse_simple_field(self):
        parser = ExpressionParser()
        ast = parser.parse("$close")
        assert ast is not None

    def test_parse_number(self):
        parser = ExpressionParser()
        ast = parser.parse("42.5")
        assert ast is not None

    def test_parse_binary_op(self):
        parser = ExpressionParser()
        ast = parser.parse("$close + $open")
        assert ast is not None

    def test_parse_function_call(self):
        parser = ExpressionParser()
        ast = parser.parse("Mean($close, 10)")
        assert ast is not None

    def test_parse_complex_expression(self):
        parser = ExpressionParser()
        ast = parser.parse("Mean($close, 10) + Std($close, 20)")
        assert ast is not None

    def test_validate_valid_expression(self):
        parser = ExpressionParser()
        assert parser.validate_expression("$close + $open") is True

    def test_validate_invalid_expression(self):
        parser = ExpressionParser()
        assert parser.validate_expression("") is False

    def test_get_dependencies(self):
        parser = ExpressionParser()
        deps = parser.get_dependencies("$close + $open")
        assert isinstance(deps, list)
        assert len(deps) > 0

    def test_parse_error(self):
        err = ParseError("test error", position=5, expression="test")
        assert str(err)

    def test_module_level_functions(self):
        ast = parse_expression("$close")
        assert ast is not None
        assert validate_expression("$close") is True
        deps = get_expression_dependencies("$close + $open")
        assert len(deps) > 0
