"""#5567: settings.py 端点 500 响应不泄露 str(e) 内部细节。

收尾切片（#5567 第 4 切片）。接续 PR #6421（components）/ #6422（node_graph）/ #6423（data），
同根因同修复模式：HTTPException(500, detail=f"...{str(e)}") → detail="..."，
异常详情已在 logger.error 记录，诊断不丢。

参考 [[arch_global_error_handler_trace_id]]：FastAPI 默认 HTTPException handler 精确匹配
优先于全局 Exception handler，global_error_handler 的 isinstance(HTTPException) 分支是
死代码，端点须自行脱敏。

覆盖 3 处泄露点：
- 683 test_user_contact WEBHOOK 分支（requests.post 抛异常）
- 1559 create_notification_recipient（service.add_recipient 抛）
- 1784 test_notification_recipient（service.get_recipient_contacts 抛）

688 Unsupported contact type（400，contact_type 用户输入枚举）合法保留不脱敏。
"""
import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

# settings.py 无相对导入，但 worktree/api/ 双层结构（api/api/settings.py），
# 测试用 from api.settings import（包上下文），patch api.settings.xxx。
# 对齐 data 切片（PR #6423）双层约定。
_api_dir = str(Path(__file__).parent.parent.parent / "api")
if _api_dir not in sys.path:
    sys.path.insert(0, _api_dir)

# config.py 全局 Settings() 需合法 SECRET_KEY
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

# 注意：端点函数 test_user_contact / test_notification_recipient 以 test_ 开头，
# 直接导入会被 pytest 误收集成测试函数（报 fixture 'contact_uuid' not found）。
# 别名导入（_xxx_endpoint）使其不以 test_ 开头，规避收集。
from api.settings import (  # noqa: E402
    UserContactTest,
    create_notification_recipient,
    test_notification_recipient as _test_notification_recipient_endpoint,
    test_user_contact as _test_user_contact_endpoint,
)

# 模拟内部异常细节（URL/连接串/内部主机名）——这些绝不应出现在 500 响应里
SENSITIVE = "Connection failed: postgres://u:p@10.0.0.1/db; host=secret-internal-host"


def _raise_sensitive(*_a, **_kw):
    raise RuntimeError(SENSITIVE)


def _assert_sanitized(exc, expected_detail):
    """断言 500 响应不含敏感细节，detail 为 generic。"""
    assert exc.value.status_code == 500
    assert "postgres" not in exc.value.detail
    assert "10.0.0.1" not in exc.value.detail
    assert "secret-internal-host" not in exc.value.detail
    assert exc.value.detail == expected_detail


class TestTestUserContactSanitization:
    """test_user_contact WEBHOOK 分支 500 响应不泄露 requests 异常细节。"""

    def test_webhook_500_detail_excludes_exception_internals(self):
        from ginkgo.enums import CONTACT_TYPES

        # 构造 get_contact 返回 WEBHOOK 类型联系方式
        mock_contact = MagicMock()
        mock_contact.get_contact_type_enum.return_value = CONTACT_TYPES.WEBHOOK
        mock_contact_result = MagicMock()
        mock_contact_result.success = True  # 647 not success → False，跳过 404
        mock_contact_result.data = mock_contact
        mock_user_svc = MagicMock()
        mock_user_svc.get_contact.return_value = mock_contact_result

        with patch("api.settings.get_user_service", return_value=mock_user_svc), \
             patch("requests.post", side_effect=_raise_sensitive):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(_test_user_contact_endpoint(
                    "contact-uuid",
                    UserContactTest(address="https://example.com/webhook")
                ))

        _assert_sanitized(exc, "Webhook test failed")


class TestCreateNotificationRecipientSanitization:
    """create_notification_recipient 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.add_recipient.side_effect = _raise_sensitive
        with patch("api.settings.get_notification_recipient_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(create_notification_recipient(data=MagicMock()))

        _assert_sanitized(exc, "Failed to create notification recipient")


class TestTestNotificationRecipientSanitization:
    """test_notification_recipient 500 响应不泄露。"""

    def test_500_detail_excludes_exception_internals(self):
        mock_svc = MagicMock()
        mock_svc.get_recipient_contacts.side_effect = _raise_sensitive
        with patch("api.settings.get_notification_recipient_service", return_value=mock_svc):
            with pytest.raises(HTTPException) as exc:
                asyncio.run(_test_notification_recipient_endpoint("recipient-uuid"))

        _assert_sanitized(exc, "Failed to test notification recipient")
