"""Smoke test for AlertService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.services.logging.alert_service import AlertService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.services.logging.alert_service not importable")
class TestAlertServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        with patch("ginkgo.services.logging.alert_service.GCONF"):
            svc = AlertService(redis_client=MagicMock(), db_engine=MagicMock())
        return svc

    def test_instantiation(self):
        with patch("ginkgo.services.logging.alert_service.GCONF"):
            svc = AlertService(redis_client=MagicMock(), db_engine=MagicMock())
        assert svc is not None

    def test_add_alert_rule_callable(self):
        svc = self._make_svc()
        rule_id = svc.add_alert_rule(name="test_rule", pattern="ERROR.*timeout")
        assert isinstance(rule_id, str)

    def test_remove_alert_rule_callable(self):
        svc = self._make_svc()
        svc.add_alert_rule(name="test_rule", pattern="ERROR.*timeout")
        rules = svc.get_alert_rules()
        rule_id = rules[0]["id"]
        result = svc.remove_alert_rule(rule_id)
        assert isinstance(result, bool)

    def test_get_alert_rules_callable(self):
        svc = self._make_svc()
        result = svc.get_alert_rules()
        assert isinstance(result, list)

    def test_check_error_patterns_callable(self):
        svc = self._make_svc()
        result = svc.check_error_patterns()
        assert isinstance(result, list)

    def test_send_alert_callable(self):
        svc = self._make_svc()
        # No channels configured, so send_alert will return False (no webhook set)
        result = svc.send_alert(
            message="test alert",
            rule_id="rule_test",
            pattern="ERROR.*timeout",
        )
        assert isinstance(result, bool)

    def test_should_send_alert_callable(self):
        svc = self._make_svc()
        result = svc.should_send_alert(rule_id="rule_test", pattern="ERROR")
        assert isinstance(result, bool)
