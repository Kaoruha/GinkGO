"""Smoke tests for features.engines.factor_engine -- #3870"""
import pytest
from unittest.mock import MagicMock

try:
    from ginkgo.features.engines.factor_engine import FactorEngine
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="FactorEngine not available")
class TestFactorEngine:
    def test_instantiation_with_mocks(self):
        mock_factor_service = MagicMock()
        mock_bar_service = MagicMock()
        engine = FactorEngine(mock_factor_service, mock_bar_service)
        assert engine is not None
        assert engine.parser is not None

    def test_get_stats(self):
        engine = FactorEngine(MagicMock(), MagicMock())
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    def test_reset_stats(self):
        engine = FactorEngine(MagicMock(), MagicMock())
        engine.reset_stats()
        stats = engine.get_stats()
        assert isinstance(stats, dict)

    def test_validate_expression(self):
        engine = FactorEngine(MagicMock(), MagicMock())
        result = engine.validate_expression("$close + $open")
        assert isinstance(result, bool)

    def test_get_expression_dependencies(self):
        engine = FactorEngine(MagicMock(), MagicMock())
        deps = engine.get_expression_dependencies("$close + $open")
        assert isinstance(deps, list)
