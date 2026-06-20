"""
Tests for notify_trading_signal (#6150 信号→消息通知链路).

验证交易信号通知的发送行为：收件人解析、内容字段、同步/异步路径。
镜像 notify() 的结构，但不依赖真实 Kafka/DB（注入 fake service + 收件人）。
"""
from unittest.mock import patch, MagicMock

from ginkgo.entities import Signal, Order
from ginkgo.enums import DIRECTION_TYPES
from ginkgo.notifier.core.notify import notify_trading_signal


class TestNotifyTradingSignalSync:
    """同步模式：解析收件人，逐个发送携带信号字段的通知。"""

    def test_sync_sends_to_each_recipient_with_code_and_volume(self):
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,
            reason="golden cross",
        )
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)

        fake_service = MagicMock()
        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1", "user-2"],
        ):
            result = notify_trading_signal(signal, order, async_mode=False)

        assert result is True
        # 每个收件人都收到一条通知
        assert fake_service.send_to_user.call_count == 2
        recipients = [c.kwargs["user_uuid"] for c in fake_service.send_to_user.call_args_list]
        assert set(recipients) == {"user-1", "user-2"}
        # 内容携带信号关键事实：代码 + 数量（对实现格式不敏感）
        for call in fake_service.send_to_user.call_args_list:
            content = call.kwargs["content"]
            assert "000001.SZ" in content, "通知内容必须含股票代码"
            assert "1000" in content, "通知内容必须含数量"

    def test_sync_no_recipients_returns_false(self):
        """无收件人时优雅降级，不抛异常。"""
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)

        fake_service = MagicMock()
        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=[],
        ):
            result = notify_trading_signal(signal, order, async_mode=False)

        assert result is False
        fake_service.send_to_user.assert_not_called()


class TestNotifyTradingSignalAsync:
    """异步模式：走 Kafka（send_async）→ worker 订阅，镜像 notify() 的异步路径。"""

    def test_async_routes_via_send_async_not_send_to_user(self):
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,
            reason="golden cross",
        )
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)

        fake_service = MagicMock()
        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            result = notify_trading_signal(signal, order, async_mode=True)

        assert result is True
        # 异步路径走 send_async（Kafka→worker），不走同步 send_to_user
        fake_service.send_async.assert_called_once()
        fake_service.send_to_user.assert_not_called()
        call = fake_service.send_async.call_args
        assert call.kwargs["user_uuid"] == "user-1"
        assert "000001.SZ" in call.kwargs["content"]
        assert "1000" in call.kwargs["content"]
