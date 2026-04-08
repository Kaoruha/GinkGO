import pytest
import json
import importlib
import types
from unittest.mock import MagicMock, patch
import sys


@pytest.fixture()
def _deviation_checker_env(monkeypatch):
    """Fixture that sets up the sys.modules mocks for DeviationChecker and
    restores them afterwards, preventing global state pollution."""
    mock_services = MagicMock()

    # Build the mock ginkgo module tree
    ginkgo_mock = types.ModuleType("ginkgo")
    ginkgo_mock.services = mock_services

    kafka_mock = types.ModuleType("ginkgo.interfaces.kafka_topics")
    KafkaTopics_cls = MagicMock()
    KafkaTopics_cls.SYSTEM_EVENTS = "ginkgo.live.system.events"
    kafka_mock.KafkaTopics = KafkaTopics_cls

    glog_mock = types.ModuleType("ginkgo.libs")
    glog_mock.GLOG = MagicMock()

    # Use monkeypatch.setitem for safe sys.modules overrides
    monkeypatch.setitem(sys.modules, "ginkgo.interfaces", types.ModuleType("ginkgo.interfaces"))
    monkeypatch.setitem(sys.modules, "ginkgo.interfaces.kafka_topics", kafka_mock)
    monkeypatch.setitem(sys.modules, "ginkgo.libs", glog_mock)
    monkeypatch.setitem(sys.modules, "ginkgo", ginkgo_mock)

    # Load the target module via spec
    mod_key = "ginkgo.trading.analysis.evaluation.deviation_checker"
    spec = importlib.util.spec_from_file_location(
        mod_key,
        "src/ginkgo/trading/analysis/evaluation/deviation_checker.py",
    )
    mod = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, mod_key, mod)
    spec.loader.exec_module(mod)

    return mod.DeviationChecker, mock_services


def _setup_redis_service(mock_services, mock_redis):
    """Helper to configure the mock services for redis access."""
    mock_services.reset_mock()
    mock_services.data.redis_service.return_value = mock_redis


@pytest.mark.tdd
class TestGetBaseline:
    def test_returns_cached_baseline_from_redis(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        baseline = {"net_value": {"mean": 1.0, "std": 0.1}}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(baseline)

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        assert result == baseline
        mock_redis.get.assert_called_once_with("deviation:baseline:p-001")

    def test_returns_none_when_no_source_mapping(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        assert result is None


@pytest.mark.tdd
class TestGetDeviationConfig:
    def test_returns_default_config_when_no_redis(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is False
        assert result["alert_channels"] == ["kafka"]

    def test_returns_config_from_redis(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        config = {"auto_takedown": True, "check_time": "21:00"}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(config)

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is True
        assert result["check_time"] == "21:00"


@pytest.mark.tdd
class TestHandleDeviationResult:
    def test_normal_is_silent(self, _deviation_checker_env):
        DeviationChecker, _ = _deviation_checker_env
        checker = DeviationChecker()
        result = {"overall_level": "NORMAL", "deviations": {}}
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_not_called()

    def test_moderate_sends_alert(self, _deviation_checker_env):
        DeviationChecker, _ = _deviation_checker_env
        checker = DeviationChecker()
        result = {
            "overall_level": "MODERATE",
            "deviations": {"sharpe_ratio": {"z_score": 2.1, "level": "MODERATE"}}
        }
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_called_once()

    def test_severe_auto_takedown(self, _deviation_checker_env):
        DeviationChecker, _ = _deviation_checker_env
        checker = DeviationChecker()
        mock_takedown = MagicMock()
        checker._takedown_callback = mock_takedown
        result = {
            "overall_level": "SEVERE",
            "deviations": {"max_drawdown": {"z_score": 3.5, "level": "SEVERE"}}
        }
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=True)
        mock_takedown.assert_called_once_with("p-001")


@pytest.mark.tdd
class TestSendDeviationAlert:
    def test_sends_multi_metric_to_system_events(self, _deviation_checker_env):
        DeviationChecker, _ = _deviation_checker_env
        checker = DeviationChecker()
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker._source = "test-source"
        result = {
            "overall_level": "MODERATE",
            "deviations": {
                "sharpe_ratio": {"z_score": 2.1, "level": "MODERATE"},
                "max_drawdown": {"z_score": 1.8, "level": "MODERATE"},
            },
            "risk_score": 0.5,
        }
        checker.send_deviation_alert("p-001", "MODERATE", result)
        call_args = mock_producer.send.call_args
        msg = call_args[0][1]
        assert isinstance(msg["deviation_details"], list)
        assert len(msg["deviation_details"]) == 2

    def test_noop_without_producer(self, _deviation_checker_env):
        DeviationChecker, _ = _deviation_checker_env
        checker = DeviationChecker()
        checker._producer = None
        checker.send_deviation_alert("p-001", "MODERATE", {})
