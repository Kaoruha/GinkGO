"""Smoke tests for features.engines.expression_engine -- #3870"""
import pytest
import pandas as pd
import numpy as np

try:
    from ginkgo.features.engines.expression_engine import ExpressionEngine
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'close': [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0, 17.0, 18.0, 19.0],
        'open': [9.5, 10.5, 11.5, 12.5, 13.5, 14.5, 15.5, 16.5, 17.5, 18.5],
        'volume': [1000.0] * 10,
    })


@pytest.mark.skipif(not HAS_MODULE, reason="ExpressionEngine not available")
class TestExpressionEngine:
    def test_instantiation(self):
        engine = ExpressionEngine()
        assert engine is not None
        assert engine.parser is not None

    def test_parse_expression(self):
        engine = ExpressionEngine()
        result = engine.parse_expression("$close + $open")
        assert result is not None

    def test_execute_expression(self, sample_df):
        engine = ExpressionEngine()
        result = engine.execute_expression("$close + $open", sample_df)
        assert isinstance(result, pd.Series)
        assert len(result) == 10

    def test_execute_simple_field(self, sample_df):
        engine = ExpressionEngine()
        result = engine.execute_expression("$close", sample_df)
        assert isinstance(result, pd.Series)
        assert list(result) == list(sample_df['close'])

    def test_register_operator(self):
        engine = ExpressionEngine()
        def custom_op(x):
            return x * 2
        engine.register_operator("test_engine_custom", custom_op)

    def test_batch_execute(self, sample_df):
        engine = ExpressionEngine()
        expressions = {
            "sum_price": "$close + $open",
            "double_close": "$close * 2",
        }
        result = engine.batch_execute(expressions, sample_df)
        assert isinstance(result, pd.DataFrame)
        assert "sum_price" in result.columns
        assert "double_close" in result.columns
        assert len(result) == 10
