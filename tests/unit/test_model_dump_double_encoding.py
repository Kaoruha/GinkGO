"""Tests for model_dump_json() double encoding -- PR review Issue 2.

GinkgoProducer.value_serializer does json.dumps(v).encode("utf-8").
When v is a str (from model_dump_json()), it gets double-encoded.
When v is a dict (from model_dump()), it serializes correctly.

All producer.send() calls must pass dict, not str.
"""
import pytest
import sys
import types
from unittest.mock import MagicMock, patch
from datetime import datetime


# ============================================================================
# trade_gateway_adapter.py — 实盘订单反馈 (production-critical)
# ============================================================================


@pytest.mark.tdd
class TestTradeGatewayAdapterPublishFillEvent:
    """_publish_fill_event must send dict to producer, not JSON string."""

    def test_publish_fill_sends_dict_not_str(self):
        """#4667: feedback_dto.model_dump_json() causes double encoding."""
        from ginkgo.livecore.trade_gateway_adapter import TradeGatewayAdapter

        adapter = TradeGatewayAdapter.__new__(TradeGatewayAdapter)
        mock_producer = MagicMock()
        adapter.kafka_producer = mock_producer

        mock_order = MagicMock()
        mock_order.uuid = "order-uuid-12345678"
        mock_order.code = "000001.SZ"
        mock_order.direction = MagicMock()
        mock_order.direction.value = "LONG"

        fill_event = MagicMock()
        fill_event.order = mock_order
        fill_event.portfolio_id = "portfolio-123"
        fill_event.engine_id = "engine-456"
        fill_event.task_id = "task-789"
        fill_event.filled_quantity = 100
        fill_event.fill_price = 10.5
        fill_event.timestamp = datetime(2026, 1, 1, 10, 0, 0)

        with patch("ginkgo.livecore.trade_gateway_adapter.GLOG"):
            adapter._publish_fill_event(fill_event)

        mock_producer.send.assert_called_once()
        value = mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )


# ============================================================================
# publisher.py — 实时调度指令 (production-critical)
# ============================================================================


@pytest.mark.tdd
class TestPublisherPublishScheduleChange:
    """send_schedule_command must send dict to producer, not JSON string."""

    def test_publish_schedule_sends_dict_not_str(self):
        """publisher: command_dto.model_dump_json() causes double encoding."""
        from ginkgo.livecore.scheduler.publisher import SchedulePublisher

        publisher = SchedulePublisher.__new__(SchedulePublisher)
        mock_producer = MagicMock()
        publisher.kafka_producer = mock_producer

        change = {
            "portfolio_id": "portfolio-1234567890",
            "from_node": "node-A",
            "to_node": "node-B",
        }

        # ScheduleUpdateDTO is imported inside the function body
        with patch("ginkgo.interfaces.dtos.ScheduleUpdateDTO") as MockDTO:
            mock_dto = MagicMock()
            mock_dto.model_dump.return_value = {"command": "migrate", "portfolio_id": "portfolio-123"}
            mock_dto.model_dump_json.return_value = '{"command": "migrate"}'
            MockDTO.Commands = MagicMock()
            MockDTO.Commands.PORTFOLIO_MIGRATE = "migrate"
            MockDTO.return_value = mock_dto

            publisher.send_schedule_command(change)

        # send(topic=..., msg=...)  — msg is the second positional arg
        mock_producer.send.assert_called_once()
        value = mock_producer.send.call_args.kwargs.get("msg") or mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )


# ============================================================================
# ginkgo_notifier.py — 通知 fallback 路径
# Import chain: ginkgo_notifier → notifier_telegram → ResultPlot → matplotlib
# Must mock notifier_telegram before importing ginkgo_notifier.
# ============================================================================


def _make_notifier():
    """Create a GinkgoNotifier with mocked producer, avoiding matplotlib import."""
    # Mock the telegram module (which pulls in matplotlib via ResultPlot)
    if "ginkgo.notifier.notifier_telegram" not in sys.modules:
        tel_mock = types.ModuleType("ginkgo.notifier.notifier_telegram")
        tel_mock.echo = MagicMock()
        tel_mock.run_telebot = MagicMock()
        sys.modules["ginkgo.notifier.notifier_telegram"] = tel_mock

    from ginkgo.notifier.ginkgo_notifier import GinkgoNotifier
    notifier = GinkgoNotifier.__new__(GinkgoNotifier)
    notifier._producer = MagicMock()
    notifier._kafka_service = None  # Force fallback path
    return notifier


@pytest.mark.tdd
class TestGinkgoNotifierBeepDoubleEncoding:
    """beep()/beep_coin() fallback must send dict, not JSON string."""

    def test_beep_sends_dict_not_str(self):
        """beep() fallback: model_dump_json() causes double encoding."""
        notifier = _make_notifier()

        with patch("ginkgo.notifier.ginkgo_notifier.GCONF") as mock_conf:
            mock_conf.QUIET = False
            with patch("ginkgo.notifier.ginkgo_notifier.GLOG"):
                notifier.beep()

        value = notifier._producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )

    def test_beep_coin_sends_dict_not_str(self):
        """beep_coin() fallback: model_dump_json() causes double encoding."""
        notifier = _make_notifier()

        with patch("ginkgo.notifier.ginkgo_notifier.GCONF") as mock_conf:
            mock_conf.QUIET = False
            with patch("ginkgo.notifier.ginkgo_notifier.GLOG"):
                notifier.beep_coin()

        value = notifier._producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )


# ============================================================================
# scheduler_cli.py — CLI 命令
# GinkgoProducer is imported inside function bodies from
# ginkgo.data.drivers.ginkgo_kafka — patch at the source.
# No GLOG/GCONF at module level — only GinkgoProducer + DTOs inside functions.
# ============================================================================


@pytest.mark.tdd
class TestSchedulerCliSendUsesModelDump:
    """scheduler_cli commands must send dict to producer via GinkgoProducer.

    GinkgoProducer is imported inside function bodies, all DTOs too.
    We test by patching GinkgoProducer at source and invoking via typer.testing.CliRunner.
    """

    def _invoke_and_check(self, app_cmd, args):
        """Helper: invoke a Typer command and assert producer.send got dict."""
        from typer.testing import CliRunner
        runner = CliRunner()
        mock_producer = MagicMock()

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
             patch("ginkgo.data.crud.RedisCRUD"), \
             patch("ginkgo.interfaces.dtos.ScheduleUpdateDTO") as MockDTO, \
             patch("ginkgo.interfaces.dtos.SchedulerCommandDTO") as MockCmdDTO:
            # Configure mock DTOs to have real model_dump/model_dump_json
            mock_dto = MagicMock()
            mock_dto.model_dump.return_value = {"command": "test", "portfolio_id": "pf-001"}
            mock_dto.model_dump_json.return_value = '{"command": "test"}'
            mock_dto.timestamp = "2026-01-01T00:00:00"
            MockDTO.return_value = mock_dto
            MockDTO.Commands = MagicMock()
            MockCmdDTO.return_value = mock_dto
            MockCmdDTO.Commands = MagicMock()

            runner.invoke(app_cmd, args)

        assert mock_producer.send.called, "producer.send() was never called — CLI path not reached"
        value = mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )

    def test_migrate_sends_dict(self):
        """migrate: model_dump_json() causes double encoding."""
        from ginkgo.client.scheduler_cli import app
        self._invoke_and_check(app, ["migrate", "pf-001", "--target", "node-B", "--force"])

    def test_reload_sends_dict(self):
        """reload: model_dump_json() causes double encoding."""
        from ginkgo.client.scheduler_cli import app
        self._invoke_and_check(app, ["reload", "pf-001", "--force"])

    def test_pause_sends_dict(self):
        """pause: model_dump_json() causes double encoding."""
        from ginkgo.client.scheduler_cli import app
        # pause() takes no arguments
        from typer.testing import CliRunner
        runner = CliRunner()
        mock_producer = MagicMock()

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
             patch("ginkgo.interfaces.dtos.SchedulerCommandDTO") as MockCmdDTO:
            mock_dto = MagicMock()
            mock_dto.model_dump.return_value = {"command": "pause", "source": "cli"}
            mock_dto.model_dump_json.return_value = '{"command": "pause"}'
            MockCmdDTO.return_value = mock_dto
            MockCmdDTO.Commands = MagicMock()
            runner.invoke(app, ["pause"])

        assert mock_producer.send.called, "producer.send() was never called — CLI path not reached"
        value = mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )
