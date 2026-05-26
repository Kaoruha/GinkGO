"""Smoke test for LevelService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.level_service import LevelService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.level_service not importable")
class TestLevelServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_glog = MagicMock()
        with patch("ginkgo.services.logging.level_service.GCONF") as mock_gconf:
            mock_gconf.LOGGING_LEVEL_WHITELIST = ["backtest", "trading", "data"]
            svc = LevelService(glog=mock_glog)
        return svc, mock_glog

    def test_instantiation(self):
        svc, _ = self._make_svc()
        assert svc is not None

    def test_set_level_callable(self):
        svc, _ = self._make_svc()
        result = svc.set_level("backtest", "DEBUG")
        assert result is not None
        assert result.success is True

    def test_get_level_callable(self):
        svc, _ = self._make_svc()
        result = svc.get_level("backtest")
        assert isinstance(result, str)

    def test_get_all_levels_callable(self):
        svc, _ = self._make_svc()
        result = svc.get_all_levels()
        assert isinstance(result, dict)

    def test_reset_levels_callable(self):
        svc, _ = self._make_svc()
        svc.set_level("backtest", "DEBUG")
        result = svc.reset_levels()
        assert result is not None
        assert result.success is True

    def test_get_whitelist_callable(self):
        svc, _ = self._make_svc()
        result = svc.get_whitelist()
        assert isinstance(result, list)

    def test_is_module_allowed_callable(self):
        svc, _ = self._make_svc()
        result = svc.is_module_allowed("backtest")
        assert isinstance(result, bool)
