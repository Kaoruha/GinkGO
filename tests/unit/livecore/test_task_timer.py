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
