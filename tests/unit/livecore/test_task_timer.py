"""Smoke tests for livecore.task_timer -- #3870"""
import pytest
from unittest.mock import patch, MagicMock, PropertyMock

try:
    from ginkgo.livecore.task_timer import TaskTimer
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="TaskTimer not available")
class TestTaskTimer:
    def test_instantiation(self):
        timer = TaskTimer()
        assert timer is not None

    def test_instantiation_custom(self):
        timer = TaskTimer(node_id="test_node")
        assert timer is not None

    def test_get_jobs_status(self):
        timer = TaskTimer()
        status = timer.get_jobs_status()
        assert isinstance(status, dict)

    def test_validate_config(self):
        timer = TaskTimer()
        result = timer.validate_config()
        assert isinstance(result, bool)


@pytest.mark.skipif(not HAS_MODULE, reason="TaskTimer not available")
class TestTaskTimerKafkaPublishing:
    """#4667: TaskTimer must pass dict (not str) to Kafka Producer.

    The GinkgoProducer.value_serializer does json.dumps(v).encode().
    If v is already a JSON string, the result is double-encoded.
    If v is a dict, serialization is correct (single pass).
    """

    def _make_timer_with_mock_producer(self):
        """Create a TaskTimer with a mocked producer that captures send() calls."""
        timer = TaskTimer()
        mock_producer = MagicMock()
        mock_producer.send = MagicMock()
        timer._producer = mock_producer
        return timer, mock_producer

    def test_paper_trading_job_sends_dict_not_str(self):
        """Paper trading command must be sent as dict, not JSON string."""
        timer, mock_producer = self._make_timer_with_mock_producer()

        timer._paper_trading_job()

        mock_producer.send.assert_called_once()
        call_kwargs = mock_producer.send.call_args
        msg = call_kwargs.kwargs.get("msg") or call_kwargs[1].get("msg") or call_kwargs[0][1]
        assert isinstance(msg, dict), (
            f"Expected dict but got {type(msg).__name__}. "
            f"This causes double encoding via value_serializer=json.dumps(v). "
            f"Use model_dump() instead of model_dump_json()."
        )

    def test_stockinfo_job_sends_dict_not_str(self):
        """Stockinfo command must be sent as dict to data.commands topic."""
        timer, mock_producer = self._make_timer_with_mock_producer()

        timer._stockinfo_job()

        mock_producer.send.assert_called_once()
        msg = mock_producer.send.call_args.kwargs.get("msg") or mock_producer.send.call_args[0][1]
        assert isinstance(msg, dict), f"Expected dict but got {type(msg).__name__}"

    def test_publish_to_kafka_routes_by_command_type(self):
        """_publish_to_kafka should read command from dict to route to correct topic."""
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        timer, mock_producer = self._make_timer_with_mock_producer()

        message = {"command": "paper_trading", "params": {}, "source": "test"}
        timer._publish_to_kafka(message)

        mock_producer.send.assert_called_once()
        topic = mock_producer.send.call_args.kwargs.get("topic") or mock_producer.send.call_args[0][0]
        assert topic == KafkaTopics.CONTROL_COMMANDS

    def test_publish_to_kafka_routes_data_commands(self):
        """Data commands (bar_snapshot, stockinfo, etc.) must route to DATA_COMMANDS topic."""
        from ginkgo.interfaces.kafka_topics import KafkaTopics
        timer, mock_producer = self._make_timer_with_mock_producer()

        for cmd in ("bar_snapshot", "stockinfo", "adjustfactor", "tick"):
            mock_producer.send.reset_mock()
            message = {"command": cmd, "params": {}, "source": "test"}
            timer._publish_to_kafka(message)

            topic = mock_producer.send.call_args.kwargs.get("topic") or mock_producer.send.call_args[0][0]
            assert topic == KafkaTopics.DATA_COMMANDS, f"Command '{cmd}' should route to DATA_COMMANDS"


@pytest.mark.skipif(not HAS_MODULE, reason="TaskTimer not available")
class TestGetAllStockCodes:
    """#6182: _get_all_stock_codes 必须实例化 service（带 ()）并从 ServiceResult 取 .data。

    旧实现把 dependency_injector 的 Singleton provider 对象当实例（漏调 ()），
    且把 get_stockinfos() 返回的 ServiceResult 当 list 迭代，导致定时数据作业
    永远 "No stocks found, skipping"，定时数据更新变空操作。
    """

    @patch("ginkgo.service_hub")
    def test_returns_codes_from_service_result_data(self, mock_hub):
        """ServiceResult.success(data=[StockInfo...]) -> 返回 [code...]，且 provider 必须被实例化。"""
        from ginkgo.data.services.base_service import ServiceResult

        timer = TaskTimer()
        mock_stocks = [MagicMock(code="000001.SZ"), MagicMock(code="600000.SH")]
        mock_service = MagicMock()
        mock_service.get_stockinfos.return_value = ServiceResult.success(data=mock_stocks)
        mock_hub.data.stockinfo_service.return_value = mock_service

        codes = timer._get_all_stock_codes()

        assert codes == ["000001.SZ", "600000.SH"]
        # provider 必须被实例化（带 ()），否则拿到的是 provider 对象非实例
        mock_hub.data.stockinfo_service.assert_called_once()
        mock_service.get_stockinfos.assert_called_once()

    @patch("ginkgo.service_hub")
    def test_returns_empty_when_no_data(self, mock_hub):
        """ServiceResult 空 data -> 返回 []（不抛异常、不误返 ServiceResult 对象）。"""
        from ginkgo.data.services.base_service import ServiceResult

        timer = TaskTimer()
        mock_service = MagicMock()
        mock_service.get_stockinfos.return_value = ServiceResult.success(data=[])
        mock_hub.data.stockinfo_service.return_value = mock_service

        assert timer._get_all_stock_codes() == []

    @patch("ginkgo.service_hub")
    def test_returns_empty_on_service_failure(self, mock_hub):
        """ServiceResult.failure -> 返回 []。"""
        from ginkgo.data.services.base_service import ServiceResult

        timer = TaskTimer()
        mock_service = MagicMock()
        mock_service.get_stockinfos.return_value = ServiceResult.failure(message="db down")
        mock_hub.data.stockinfo_service.return_value = mock_service

        assert timer._get_all_stock_codes() == []
