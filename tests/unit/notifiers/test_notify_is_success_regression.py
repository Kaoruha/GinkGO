"""
回归 #6223：notify() / notify_with_fields() 的 result.is_success 属性恒真 bug。

ServiceResult.is_success 是方法（base_service.py:135，无 @property）。
buggy 代码 `if result.is_success:` 取回绑定方法对象（恒 truthy）→ 发送失败也计成功，
notify/notify_with_fields 返回 True 但实际无人收到。

每个测试用 mock.is_success.return_value=False 强制失败路径，断言返回 False，
才能逼出 bug（MagicMock 的 is_success 属性默认 auto-truthy 会掩盖）。
"""
from unittest.mock import patch, MagicMock
from types import SimpleNamespace

from ginkgo.notifier.core.notify import notify, notify_with_fields


class TestNotifySyncFailurePath:
    """notify() 同步路径：send_to_user 失败时必须返回 False。"""

    def test_sync_send_to_user_failure_returns_false(self):
        fail_result = MagicMock()
        fail_result.is_success.return_value = False  # 方法返回失败

        fake_service = MagicMock()
        fake_service.send_to_user.return_value = fail_result
        # 同步路径后半段会查 contacts 发 discord webhook，置空避免迭代 MagicMock 报错
        fake_service.user_service.get_active_contacts.return_value = SimpleNamespace(
            success=True, data=[]
        )

        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            result = notify("boom", async_mode=False)

        assert result is False, "send_to_user 失败时不能因 is_success 是方法而恒真报成功"


class TestNotifyAsyncFailurePath:
    """notify() 异步路径：send_async 失败时必须返回 False。"""

    def test_async_send_async_failure_returns_false(self):
        fail_result = MagicMock()
        fail_result.is_success.return_value = False

        fake_service = MagicMock()
        fake_service.send_async.return_value = fail_result

        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            result = notify("boom", async_mode=True)

        assert result is False, "send_async 失败时不能因 is_success 是方法而恒真报成功"


class TestNotifyWithFieldsSyncFailurePath:
    """notify_with_fields() 同步路径：send_discord_webhook 失败时必须返回 False。"""

    def test_sync_discord_webhook_failure_returns_false(self):
        fail_result = MagicMock()
        fail_result.is_success.return_value = False

        fake_service = MagicMock()
        fake_service.send_discord_webhook.return_value = fail_result

        contact = MagicMock()
        contact.get_contact_type_enum.return_value = SimpleNamespace(name="WEBHOOK")
        contact.is_active = True
        contact.address = "http://hook.example"
        fake_service.user_service.get_active_contacts.return_value = SimpleNamespace(
            success=True, data=[contact]
        )

        with patch(
            "ginkgo.notifier.core.notify._get_notification_service",
            return_value=fake_service,
        ), patch(
            "ginkgo.notifier.core.notify._get_recipient_user_uuids",
            return_value=["user-1"],
        ):
            result = notify_with_fields(
                "content", [{"name": "x", "value": "y", "inline": True}], async_mode=False
            )

        assert result is False, "send_discord_webhook 失败时不能因 is_success 是方法而恒真报成功"
