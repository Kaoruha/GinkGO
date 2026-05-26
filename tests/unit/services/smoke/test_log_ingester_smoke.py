"""Smoke test for LogIngester -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.log_ingester import LogIngester, IngestResult
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.log_ingester not importable")
class TestLogIngesterSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        return LogIngester()

    def test_instantiation(self):
        svc = self._make_svc()
        assert svc is not None

    def test_ingest_file_callable(self):
        svc = self._make_svc()
        with patch("ginkgo.services.logging.log_ingester.os.path.exists", return_value=False):
            result = svc.ingest_file("/nonexistent/path.log")
        assert isinstance(result, IngestResult)

    def test_ingest_task_logs_callable(self):
        svc = self._make_svc()
        with patch("ginkgo.services.logging.log_ingester.GCONF") as mock_gconf:
            mock_gconf.LOGGING_PATH = "/nonexistent"
            with patch("ginkgo.services.logging.log_ingester.os.path.exists", return_value=False):
                result = svc.ingest_task_logs("abcd1234-5678-efgh")
        assert isinstance(result, IngestResult)

    def test_ingest_result_defaults(self):
        result = IngestResult()
        assert result.total_lines == 0
        assert result.inserted == 0
        assert result.skipped == 0
        assert result.errors == 0
