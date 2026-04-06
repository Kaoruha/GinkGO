import pytest
import json
import importlib
import types
from unittest.mock import MagicMock, patch
import sys

# Direct import to avoid broken __init__.py chain (ginkgo.data.operations missing)
#
# Strategy: force-override sys.modules["ginkgo"] with a mock so that
# `from ginkgo import services` inside DeviationChecker methods resolves
# to our mock at call time.

# Save real ginkgo if present, replace with mock
_real_ginkgo = sys.modules.get("ginkgo")

_mock_services = MagicMock()
_ginkgo_mock = types.ModuleType("ginkgo")
_ginkgo_mock.services = _mock_services

# Mock kafka_topics
_kafka_mock = types.ModuleType("ginkgo.interfaces.kafka_topics")
_KafkaTopics_cls = MagicMock()
_KafkaTopics_cls.SYSTEM_EVENTS = "ginkgo.live.system.events"
_kafka_mock.KafkaTopics = _KafkaTopics_cls
sys.modules["ginkgo.interfaces"] = types.ModuleType("ginkgo.interfaces")
sys.modules["ginkgo.interfaces.kafka_topics"] = _kafka_mock

# Mock GLOG
_glog_mock = types.ModuleType("ginkgo.libs")
_glog_mock.GLOG = MagicMock()
sys.modules["ginkgo.libs"] = _glog_mock

# Force override
sys.modules["ginkgo"] = _ginkgo_mock

# Load the module
_spec = importlib.util.spec_from_file_location(
    "ginkgo.trading.analysis.evaluation.deviation_checker",
    "src/ginkgo/trading/analysis/evaluation/deviation_checker.py",
)
_mod = importlib.util.module_from_spec(_spec)
sys.modules["ginkgo.trading.analysis.evaluation.deviation_checker"] = _mod
_spec.loader.exec_module(_mod)

DeviationChecker = _mod.DeviationChecker


def _setup_redis_service(mock_redis):
    """Helper to configure the mock services for redis access."""
    _mock_services.reset_mock()
    _mock_services.data.redis_service.return_value = mock_redis


@pytest.mark.tdd
class TestGetBaseline:
    def test_returns_cached_baseline_from_redis(self):
        checker = DeviationChecker()
        baseline = {"net_value": {"mean": 1.0, "std": 0.1}}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(baseline)

        _setup_redis_service(mock_redis)
        result = checker.get_baseline("p-001")

        assert result == baseline
        mock_redis.get.assert_called_once_with("deviation:baseline:p-001")

    def test_returns_none_when_no_source_mapping(self):
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        _setup_redis_service(mock_redis)
        result = checker.get_baseline("p-001")

        assert result is None


@pytest.mark.tdd
class TestGetDeviationConfig:
    def test_returns_default_config_when_no_redis(self):
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get.return_value = None

        _setup_redis_service(mock_redis)
        result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is False
        assert result["alert_channels"] == ["kafka"]

    def test_returns_config_from_redis(self):
        checker = DeviationChecker()
        config = {"auto_takedown": True, "check_time": "21:00"}
        mock_redis = MagicMock()
        mock_redis.get.return_value = json.dumps(config)

        _setup_redis_service(mock_redis)
        result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is True
        assert result["check_time"] == "21:00"


@pytest.mark.tdd
class TestHandleDeviationResult:
    def test_normal_is_silent(self):
        checker = DeviationChecker()
        result = {"overall_level": "NORMAL", "deviations": {}}
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_not_called()

    def test_moderate_sends_alert(self):
        checker = DeviationChecker()
        result = {
            "overall_level": "MODERATE",
            "deviations": {"sharpe_ratio": {"z_score": 2.1, "level": "MODERATE"}}
        }
        mock_producer = MagicMock()
        checker._producer = mock_producer
        checker.handle_deviation_result("p-001", result, auto_takedown=False)
        mock_producer.send.assert_called_once()

    def test_severe_auto_takedown(self):
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
    def test_sends_multi_metric_to_system_events(self):
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

    def test_noop_without_producer(self):
        checker = DeviationChecker()
        checker._producer = None
        checker.send_deviation_alert("p-001", "MODERATE", {})
