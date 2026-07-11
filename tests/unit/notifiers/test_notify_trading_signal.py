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


class TestSendFailureHandling:
    """回归（PR#6215 review Issue 1+2）：send 失败时不能报成功。

    ServiceResult.is_success 是方法非属性；渠道必须用生产可解析的 webhook。
    两者叠加曾导致生产全程静默失败却返回 True。
    """

    def test_sync_send_failure_returns_false(self):
        """send 返回失败(is_success()==False)时，notify 必须返回 False。

        回归锚点：buggy `getattr(result, "is_success", False)` 取回绑定方法
        （恒 truthy）会把失败计为成功→返回 True。本测试用 is_success() 返回
        False 的 mock 逼出该 bug。
        """
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100)

        fake_service = MagicMock()
        fail_result = MagicMock()
        fail_result.is_success.return_value = False  # 方法返回失败
        fake_service.send_to_user.return_value = fail_result

        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            result = notify_trading_signal(signal, order, async_mode=False)

        assert result is False, "send 失败时不能因 is_success 是方法而恒真报成功"

    def test_uses_webhook_channel_dynamically_resolvable_not_email(self):
        """渠道必须用 webhook（动态从 user contact 解析，无需预注册），
        而非 email（生产运行时从未 register_channel → 必 Channel not found）。

        回归锚点（#6086 AC2）：notify_trading_signal 早期硬编码 ``["email"]``，
        但 EmailChannel 在 API/worker 启动时从不注册
        （NotificationDeliveryService.__init__ self._channels={}，全仓仅
        notify_cli.py:251 注册过 ConsoleChannel），导致交易信号通知全程
        ``Channel not found: email`` 静默失败。webhook 是 send 链路特判动态
        解析的唯一渠道（notification_service.py:220 ``_get_webhook_channel_for_user``），
        必须与 notify() 对齐用 webhook。
        """
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)

        fake_service = MagicMock()
        ok_result = MagicMock()
        ok_result.is_success.return_value = True
        fake_service.send_async.return_value = ok_result

        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            notify_trading_signal(signal, order, async_mode=True)

        channels = fake_service.send_async.call_args.kwargs["channels"]
        assert "webhook" in channels, "必须用 webhook（动态可解析），与 notify() 对齐"
        assert "email" not in channels, "email 生产从未注册，会导致 Channel not found"
