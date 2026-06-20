"""
回归 #6223（扩充）：notification_service.py / notification_worker.py 同款
result.is_success 属性恒真 bug（#6224 自审发现的系统性 9 处）。

三个 pattern：
- A: if result.is_success:        （send_to_users / send_to_group / send_template_to_group / worker）
- B: if not result.is_success:    （_resolve_user_uuid / _resolve_group_uuids）
- C: "success": result.is_success  （结果 dict 存绑定方法，下游恒真）

每个测试用真实 ServiceResult + 显式失败，逼出 bug（勿靠 MagicMock auto-truthy）。
"""
from unittest.mock import MagicMock

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.notifier.core.notification_service import NotificationDeliveryService


def _bare_service():
    """绕过重型 __init__，构造仅带所需属性的服务实例。"""
    return NotificationDeliveryService.__new__(NotificationDeliveryService)


class TestSendToUsersFailurePath:
    """Pattern A + C：send_to_users 批量发送，self.send 失败时不能计成功，
    结果 dict 的 "success" 必须是真实 bool 而非绑定方法。"""

    def test_send_failure_yields_zero_count_and_false_bool(self):
        svc = _bare_service()
        svc.send = MagicMock(return_value=ServiceResult.error("send failed"))

        result = svc.send_to_users(["user-1"], "content", "webhook")

        assert result.is_success()
        data = result.data
        # Pattern A: 失败不能计成功
        assert data["success_count"] == 0, "send 失败时不能因 is_success 是方法而恒真计成功"
        # Pattern C: dict 里 "success" 必须是 False（bool），不是绑定方法
        assert data["results"][0]["success"] is False, (
            '"success" 必须存真实 bool False，不能存绑定方法对象（下游恒 truthy）'
        )


class TestResolveUserUuidFailurePath:
    """Pattern B：fuzzy_search 失败（且 data 泄漏用户）时必须返回 None。

    buggy `not result.is_success` = `not <绑定方法>` = not True = False → 跳过校验，
    继续读 result.data["users"] 返回泄漏的 uuid。固定后 `not result.is_success()`=True → 返回 None。
    """

    def test_failed_search_with_leaked_data_returns_none(self):
        svc = _bare_service()
        svc.user_service = MagicMock()
        # 失败结果，但 data 里塞了用户（模拟泄漏/脏数据）
        svc.user_service.fuzzy_search.return_value = ServiceResult.error(
            "search failed", data={"users": [{"uuid": "LEAKED-UUID"}]}
        )

        uuid = svc._resolve_user_uuid("ghost-user")

        assert uuid is None, "fuzzy_search 失败时不能因 not is_success(方法) 跳过校验返回泄漏 uuid"
