"""Smoke test for LogService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.log_service import LogService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.log_service not importable")
class TestLogServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_engine = MagicMock()
        mock_session = MagicMock()
        mock_engine.get_session.return_value.__enter__ = MagicMock(return_value=mock_session)
        mock_engine.get_session.return_value.__exit__ = MagicMock(return_value=False)
        svc = LogService(engine=mock_engine)
        return svc, mock_engine, mock_session

    def test_instantiation(self):
        svc, _, _ = self._make_svc()
        assert svc is not None

    def test_query_backtest_logs_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.query_backtest_logs(portfolio_id="p1", level="ERROR", limit=50)
        assert isinstance(result, list)

    def test_query_component_logs_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.query_component_logs(component_name="strategy", level="INFO")
        assert isinstance(result, list)

    def test_query_by_trace_id_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.query_by_trace_id("trace-123")
        assert isinstance(result, list)

    def test_get_log_count_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalar.return_value = 0
        result = svc.get_log_count(log_type="backtest")
        assert isinstance(result, int)

    def test_search_logs_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.search_logs(keyword="timeout")
        assert isinstance(result, list)

    def test_get_error_stats_callable(self):
        svc, _, mock_session = self._make_svc()
        mock_session.execute.return_value.scalars.return_value.all.return_value = []
        result = svc.get_error_stats(portfolio_id="p1", hours=24)
        assert isinstance(result, dict)
