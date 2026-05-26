"""Smoke test for LokiClient -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.clients.loki_client import LokiClient
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.clients.loki_client not importable")
class TestLokiClientSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        return LokiClient(base_url="http://loki:3100")

    def test_instantiation(self):
        svc = self._make_svc()
        assert svc is not None
        assert svc.base_url == "http://loki:3100"

    def test_query_callable(self):
        svc = self._make_svc()
        with patch("ginkgo.services.logging.clients.loki_client.requests.get") as mock_get:
            mock_response = MagicMock()
            mock_response.json.return_value = {"data": {"result": []}}
            mock_response.raise_for_status.return_value = None
            mock_get.return_value = mock_response
            result = svc.query('{level="ERROR"}', limit=10)
        assert isinstance(result, list)

    def test_query_handles_connection_error(self):
        svc = self._make_svc()
        import requests as real_requests
        with patch("ginkgo.services.logging.clients.loki_client.requests.get", side_effect=real_requests.exceptions.ConnectionError):
            result = svc.query('{level="ERROR"}')
        assert isinstance(result, list)
        assert len(result) == 0

    def test_build_logql_callable(self):
        svc = self._make_svc()
        result = svc.build_logql(portfolio_id="p1", level="ERROR")
        assert isinstance(result, str)
        assert 'portfolio_id="p1"' in result
        assert 'level="ERROR"' in result

    def test_build_logql_empty(self):
        svc = self._make_svc()
        result = svc.build_logql()
        assert result == "{}"
