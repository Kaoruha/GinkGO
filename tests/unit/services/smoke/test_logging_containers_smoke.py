"""Smoke test for LoggingContainer -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.containers import LoggingContainer
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.containers not importable")
class TestLoggingContainerSmoke:
    """冒烟测试：验证可实例化和容器提供者可访问"""

    def test_instantiation(self):
        with patch("ginkgo.services.logging.containers.get_db_connection", return_value=MagicMock()):
            with patch("ginkgo.services.logging.containers.RedisService"):
                svc = LoggingContainer()
        assert svc is not None

    def test_log_service_provider_exists(self):
        with patch("ginkgo.services.logging.containers.get_db_connection", return_value=MagicMock()):
            with patch("ginkgo.services.logging.containers.RedisService"):
                svc = LoggingContainer()
        assert hasattr(svc, "log_service")

    def test_level_service_provider_exists(self):
        with patch("ginkgo.services.logging.containers.get_db_connection", return_value=MagicMock()):
            with patch("ginkgo.services.logging.containers.RedisService"):
                svc = LoggingContainer()
        assert hasattr(svc, "level_service")

    def test_alert_service_provider_exists(self):
        with patch("ginkgo.services.logging.containers.get_db_connection", return_value=MagicMock()):
            with patch("ginkgo.services.logging.containers.RedisService"):
                svc = LoggingContainer()
        assert hasattr(svc, "alert_service")
