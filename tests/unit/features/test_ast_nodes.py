"""Smoke tests for features.engines.expression.ast_nodes -- #3870"""
import pytest
import pandas as pd
import numpy as np

try:
    from ginkgo.features.engines.expression.ast_nodes import (
        ASTNode, FieldNode, NumberNode, BinaryOpNode, FunctionNode, ConditionalNode,
        create_field_node, create_number_node, create_binary_op_node,
        create_function_node, create_conditional_node,
    )
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.fixture
def sample_df():
    return pd.DataFrame({
        'close': [10.0, 11.0, 12.0, 13.0, 14.0],
        'open': [9.5, 10.5, 11.5, 12.5, 13.5],
        'volume': [1000, 1100, 1200, 1300, 1400],
    })


@pytest.mark.skipif(not HAS_MODULE, reason="ast_nodes not available")
class TestFieldNode:
    def test_create(self):
        node = FieldNode("close")
        assert node.field_name == "close"

    def test_execute(self, sample_df):
        node = FieldNode("close")
        result = node.execute(sample_df)
        assert isinstance(result, pd.Series)
        assert len(result) == 5

    def test_factory(self):
        node = create_field_node("open")
        assert isinstance(node, FieldNode)


@pytest.mark.skipif(not HAS_MODULE, reason="ast_nodes not available")
class TestNumberNode:
    def test_create(self):
        node = NumberNode(42.0)
        assert node.value == 42.0

    def test_execute(self, sample_df):
        node = NumberNode(5.0)
        result = node.execute(sample_df)
        assert isinstance(result, pd.Series)
        assert (result == 5.0).all()

    def test_factory(self):
        node = create_number_node(3.14)
        assert isinstance(node, NumberNode)


@pytest.mark.skipif(not HAS_MODULE, reason="ast_nodes not available")
class TestBinaryOpNode:
    def test_add(self, sample_df):
        left = FieldNode("close")
        right = NumberNode(1.0)
        node = BinaryOpNode(left, "+", right)
        result = node.execute(sample_df)
        assert isinstance(result, pd.Series)
        assert list(result) == [11.0, 12.0, 13.0, 14.0, 15.0]

    def test_subtract(self, sample_df):
        left = FieldNode("close")
        right = FieldNode("open")
        node = BinaryOpNode(left, "-", right)
        result = node.execute(sample_df)
        assert isinstance(result, pd.Series)
        assert all(abs(v - 0.5) < 1e-10 for v in result)

    def test_multiply(self, sample_df):
        left = FieldNode("close")
        right = NumberNode(2.0)
        node = BinaryOpNode(left, "*", right)
        result = node.execute(sample_df)
        assert list(result) == [20.0, 22.0, 24.0, 26.0, 28.0]

    def test_divide(self, sample_df):
        left = NumberNode(10.0)
        right = NumberNode(2.0)
        node = BinaryOpNode(left, "/", right)
        result = node.execute(sample_df)
        assert (result == 5.0).all()


@pytest.mark.skipif(not HAS_MODULE, reason="ast_nodes not available")
class TestConditionalNode:
    def test_basic(self, sample_df):
        # If close > 11 then close else 0
        cond = BinaryOpNode(FieldNode("close"), ">", NumberNode(11.0))
        true_val = FieldNode("close")
        false_val = NumberNode(0.0)
        node = ConditionalNode(cond, true_val, false_val)
        result = node.execute(sample_df)
        assert isinstance(result, pd.Series)
