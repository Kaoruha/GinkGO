"""
回归 #6223（扩充）：notification_worker.py L647 同款
result.is_success 属性恒真 bug（Pattern A）。

_process_custom_fields_message：send_discord_webhook 失败时必须返回 False。
buggy `if result.is_success:`（方法对象恒真）→ 计成功 → 返回 True（假成功）。
用真实 ServiceResult.error（非 MagicMock auto-truthy）逼出 bug。
"""
from unittest.mock import MagicMock
from types import SimpleNamespace

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.notifier.workers.notification_worker import NotificationWorker


def _bare_worker():
    """绕过重型 __init__，构造仅带 notification_service 的 worker。"""
    w = NotificationWorker.__new__(NotificationWorker)
    w.notification_service = MagicMock()
    return w


class TestProcessCustomFieldsFailurePath:
    """Pattern A：Discord webhook 发送失败时不能假成功。"""

    def test_send_discord_webhook_failure_returns_false(self):
        w = _bare_worker()
        ns = w.notification_service

        # 组存在、有成员、成员有活跃 WEBHOOK 联系方式
        ns.user_group_service.get_group_by_name.return_value = SimpleNamespace(
            success=True, data=MagicMock(uuid="grp-1")
        )
        ns.user_group_service.get_group_member_uuids.return_value = SimpleNamespace(
            success=True, data=["member-1"]
        )
        contact = MagicMock()
        contact.get_contact_type_enum.return_value = SimpleNamespace(name="WEBHOOK")
        contact.is_active = True
        contact.address = "http://hook.example"
        ns.user_service.get_active_contacts.return_value = SimpleNamespace(
            success=True, data=[contact]
        )
        # 发送失败（真实 ServiceResult，is_success() 返回 False）
        ns.send_discord_webhook.return_value = ServiceResult.error("webhook failed")

        message = {
            "content": "hello",
            "fields": [{"name": "x", "value": "y", "inline": True}],
            "group_name": "System",
            "module": "System",
        }

        result = w._process_custom_fields_message(message)

        assert result is False, "send_discord_webhook 失败时不能因 is_success 是方法而恒真报成功"
