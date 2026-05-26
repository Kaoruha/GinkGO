"""Smoke test for AnalyzerService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.analyzer_service import AnalyzerService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.analyzer_service not importable")
class TestAnalyzerServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_crud = MagicMock()
        return AnalyzerService(analyzer_crud=mock_crud), mock_crud

    def test_instantiation(self):
        mock_crud = MagicMock()
        svc = AnalyzerService(analyzer_crud=mock_crud)
        assert svc is not None

    def test_add_record_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.create.return_value = MagicMock()
        result = svc.add_record(
            portfolio_id="p1",
            engine_id="e1",
            task_id="t1",
            timestamp="2025-01-01",
            value=1.0,
            name="test_analyzer",
        )
        assert result is not None
        mock_crud.create.assert_called_once()

    def test_get_by_task_id_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.get_by_task_id.return_value = []
        result = svc.get_by_task_id(task_id="t1")
        assert result is not None
        mock_crud.get_by_task_id.assert_called_once()

    def test_get_latest_by_portfolio_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.find.return_value = []
        result = svc.get_latest_by_portfolio(portfolio_id="p1")
        assert result is not None
        mock_crud.find.assert_called_once()
