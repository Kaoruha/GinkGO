"""偏差检测器 DeviationChecker 单元测试。"""
import pytest
import json
import importlib
import types
from unittest.mock import MagicMock, patch
import sys

from ginkgo.data.services.base_service import ServiceResult


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
        mock_redis.get_cache.return_value = ServiceResult.success(data=json.dumps(baseline))

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        assert result == baseline
        mock_redis.get_cache.assert_called_once_with("deviation:baseline:p-001")

    def test_returns_none_when_no_source_mapping(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get_cache.return_value = ServiceResult.success(data=None)

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        assert result is None


@pytest.mark.tdd
class TestGetDeviationConfig:
    def test_returns_default_config_when_no_redis(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        mock_redis = MagicMock()
        mock_redis.get_cache.return_value = ServiceResult.success(data=None)

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_deviation_config("p-001")

        assert result["auto_takedown"] is False
        assert result["alert_channels"] == ["kafka"]

    def test_returns_config_from_redis(self, _deviation_checker_env):
        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()
        config = {"auto_takedown": True, "check_time": "21:00"}
        mock_redis = MagicMock()
        mock_redis.get_cache.return_value = ServiceResult.success(data=json.dumps(config))

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


# ============================================================================
# #4662: RedisService API contract — get_cache()/set_cache(), not get()/set()
# ============================================================================


@pytest.mark.tdd
class TestDeviationCheckerRedisAPI:
    """#4662: DeviationChecker must use get_cache()/set_cache() returning ServiceResult.

    RedisService exposes:
      - set_cache(key, value, expire_seconds=3600) → ServiceResult
      - get_cache(key) → ServiceResult  (extract .data for the value)

    The methods .get() and .set() do NOT exist on RedisService.
    """

    def test_get_baseline_uses_get_cache_for_cached_value(self, _deviation_checker_env):
        """get_baseline must call get_cache() not get() for baseline lookup."""
        from ginkgo.data.services.base_service import ServiceResult

        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()

        mock_redis = MagicMock()
        mock_redis.get_cache.return_value = ServiceResult.success(
            data=json.dumps({"net_value": {"mean": 1.0, "std": 0.1}})
        )

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        # Must call get_cache, not the non-existent get()
        mock_redis.get_cache.assert_called_once_with("deviation:baseline:p-001")
        mock_redis.get.assert_not_called()
        assert result is not None

    def test_get_baseline_uses_get_cache_for_source_lookup(self, _deviation_checker_env):
        """When baseline not cached, must use get_cache() to find source portfolio."""
        from ginkgo.data.services.base_service import ServiceResult

        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()

        mock_redis = MagicMock()
        # First call: baseline miss (None)
        # Second call: source miss (None)
        mock_redis.get_cache.return_value = ServiceResult.success(data=None)

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_baseline("p-001")

        # get_cache should have been called for both baseline and source
        assert mock_redis.get_cache.call_count >= 1
        mock_redis.get.assert_not_called()
        assert result is None

    def test_get_baseline_uses_set_cache_to_store(self, _deviation_checker_env):
        """When computing baseline, must use set_cache() not set() to store."""
        from ginkgo.data.services.base_service import ServiceResult

        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()

        mock_task = MagicMock()
        mock_task.task_id = "task-123"
        mock_task.engine_id = "engine-456"

        mock_task_svc = MagicMock()
        mock_task_svc.list.return_value = ServiceResult.success(data=[mock_task])

        mock_evaluator_cls = MagicMock()
        mock_evaluator = mock_evaluator_cls.return_value
        mock_evaluator.evaluate_backtest_stability.return_value = {
            "status": "success",
            "monitoring_baseline": {"slice_period_days": 30, "baseline_stats": {}},
        }

        mock_redis = MagicMock()
        # get_cache is called multiple times with different keys:
        # 1st: baseline lookup → miss (None)
        # 2nd: source lookup → hit ("source-789")
        mock_redis.get_cache.side_effect = [
            ServiceResult.success(data=None),
            ServiceResult.success(data="source-789"),
        ]
        mock_redis.set_cache.return_value = ServiceResult.success()

        mock_services.data.redis_service.return_value = mock_redis
        mock_services.data.backtest_task_service.return_value = mock_task_svc

        # Patch the module-level import by injecting into sys.modules
        import types
        evaluator_mod = types.ModuleType("ginkgo.trading.analysis.evaluation.backtest_evaluator")
        evaluator_mod.BacktestEvaluator = mock_evaluator_cls

        import sys
        saved = sys.modules.get("ginkgo.trading.analysis.evaluation.backtest_evaluator")
        sys.modules["ginkgo.trading.analysis.evaluation.backtest_evaluator"] = evaluator_mod
        try:
            result = checker.get_baseline("p-001")
        finally:
            if saved is not None:
                sys.modules["ginkgo.trading.analysis.evaluation.backtest_evaluator"] = saved
            else:
                del sys.modules["ginkgo.trading.analysis.evaluation.backtest_evaluator"]

        # Must call set_cache, not the non-existent set()
        mock_redis.set_cache.assert_called_once()
        mock_redis.set.assert_not_called()
        assert result is not None

    def test_get_deviation_config_uses_get_cache(self, _deviation_checker_env):
        """get_deviation_config must use get_cache() not get()."""
        from ginkgo.data.services.base_service import ServiceResult

        DeviationChecker, mock_services = _deviation_checker_env
        checker = DeviationChecker()

        config = {"auto_takedown": True, "check_time": "21:00"}
        mock_redis = MagicMock()
        mock_redis.get_cache.return_value = ServiceResult.success(data=json.dumps(config))

        _setup_redis_service(mock_services, mock_redis)
        result = checker.get_deviation_config("p-001")

        mock_redis.get_cache.assert_called_once_with("deviation:config:p-001")
        mock_redis.get.assert_not_called()
        assert result["auto_takedown"] is True
