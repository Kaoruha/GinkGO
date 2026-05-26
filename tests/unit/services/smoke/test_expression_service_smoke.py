"""Smoke test for ExpressionService -- #3823"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

try:
    from ginkgo.features.services.expression_service import ExpressionService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.features.services.expression_service not importable")
class TestExpressionServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_engine = MagicMock()
        mock_engine.validate_expressions.return_value = MagicMock(success=True, data={})
        mock_engine.parse_expressions.return_value = MagicMock(success=True, data={})
        mock_engine.analyze_dependencies.return_value = MagicMock(success=True, data={})
        mock_engine.execute_expression.return_value = MagicMock(success=True, data=pd.DataFrame())
        mock_engine.get_available_operators.return_value = ["rank", "ts_mean"]
        mock_engine.get_engine_stats.return_value = {}
        mock_engine.operator_registry = MagicMock()
        mock_engine.operator_registry.is_function_registered.return_value = True
        with patch("ginkgo.features.services.expression_service.GLOG"):
            svc = ExpressionService(expression_engine=mock_engine)
        return svc, mock_engine

    def test_instantiation(self):
        svc, _ = self._make_svc()
        assert svc is not None

    def test_validate_expressions_callable(self):
        svc, _ = self._make_svc()
        result = svc.validate_expressions({"alpha1": "rank(close)"})
        assert result is not None

    def test_parse_expressions_callable(self):
        svc, _ = self._make_svc()
        result = svc.parse_expressions({"alpha1": "rank(close)"})
        assert result is not None

    def test_analyze_dependencies_callable(self):
        svc, _ = self._make_svc()
        result = svc.analyze_dependencies({"alpha1": "rank(close)"})
        assert result is not None

    def test_execute_expression_callable(self):
        svc, _ = self._make_svc()
        df = pd.DataFrame({"close": [1.0, 2.0, 3.0]})
        result = svc.execute_expression("rank(close)", data=df)
        assert result is not None

    def test_get_available_operators_callable(self):
        svc, _ = self._make_svc()
        result = svc.get_available_operators()
        assert isinstance(result, list)

    def test_get_service_stats_callable(self):
        svc, _ = self._make_svc()
        result = svc.get_service_stats()
        assert isinstance(result, dict)
