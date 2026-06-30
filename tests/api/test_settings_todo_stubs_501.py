"""#5595: settings.py 7 个 TODO 桩——假成功/假数据端点改诚实 501，type 筛选接 channels。

延迟导入（conftest api_modules fixture 临时把 api/ 入 sys.path，见 #3849/#4080）。
"""
import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException


def _make_contact(contact_type):
    """构造 mock 联系方式对象，get_contact_type_enum() 返回指定类型。"""
    contact = Mock()
    contact.get_contact_type_enum.return_value = contact_type
    return contact


# ---------- 1. EMAIL 测试联系方式：应返 501，非假成功 ----------
def test_email_contact_test_returns_501_not_fake_success(api_modules):
    from ginkgo.enums import CONTACT_TYPES
    from api.settings import test_user_contact, UserContactTest

    fake_contact = _make_contact(CONTACT_TYPES.EMAIL)
    user_svc = Mock()
    user_svc.get_contact.return_value = Mock(success=True, data=fake_contact)

    with patch("api.settings.get_user_service", return_value=user_svc):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(test_user_contact(
                "contact-uuid",
                UserContactTest(address="a@b.c"),
            ))
    assert exc.value.status_code == 501
    assert "not implemented" in exc.value.detail.lower()


# ---------- 2. 通知模板测试发送：应返 501 ----------
def test_notification_template_test_returns_501(api_modules):
    from api.settings import test_notification_template

    notif_svc = Mock()
    notif_svc.template_exists.return_value = True

    with patch("api.settings.get_notification_service", return_value=notif_svc):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(test_notification_template("tpl-uuid"))
    assert exc.value.status_code == 501


# ---------- 3. list_api_keys：应返 501，非硬编码假列表 ----------
def test_list_api_keys_returns_501(api_modules):
    from api.settings import list_api_keys

    with pytest.raises(HTTPException) as exc:
        asyncio.run(list_api_keys())
    assert exc.value.status_code == 501


# ---------- 4. create_api_key：应返 501，非假密钥 ----------
def test_create_api_key_returns_501(api_modules):
    from api.settings import create_api_key

    with pytest.raises(HTTPException) as exc:
        asyncio.run(create_api_key({"name": "test"}))
    assert exc.value.status_code == 501


# ---------- 5. get_api_stats：应返 501，非硬编码假统计 ----------
def test_get_api_stats_returns_501(api_modules):
    from api.settings import get_api_stats

    with pytest.raises(HTTPException) as exc:
        asyncio.run(get_api_stats())
    assert exc.value.status_code == 501


# ---------- 6. notification history type 筛选应接入 channels 字段 ----------
def test_notification_history_type_filter_wired_to_channels(api_modules):
    from api.settings import list_notification_history

    captured = {}

    def fake_list_records(filters=None, limit=None, offset=None, sort=None):
        captured["filters"] = filters
        return Mock(success=True, data=[])

    notif_svc = Mock()
    notif_svc.list_records.side_effect = fake_list_records

    with patch("api.settings.get_notification_service", return_value=notif_svc):
        asyncio.run(list_notification_history(type="email", page=1, page_size=20))

    assert captured["filters"].get("channels") == "email"
