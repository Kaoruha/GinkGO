"""#5469: webhook test 端点 SSRF 防护——_assert_safe_webhook_url 校验。

服务端 test_user_contact 对用户可控 address 直发 requests.post，可探内网/云元数据
(169.254.169.254)。修复：发送前校验 URL（scheme 白名单 + 解析后 IP 拦私有段 +
getaddrinfo 防 DNS rebinding），不安全则 HTTPException(400)。

延迟导入（conftest api_modules fixture 临时把 api/ 入 sys.path，对齐
test_settings_todo_stubs_501.py 模式）。
"""
import asyncio
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException


def _make_webhook_contact():
    """构造 mock webhook 联系方式对象。"""
    from ginkgo.enums import CONTACT_TYPES

    contact = Mock()
    contact.get_contact_type_enum.return_value = CONTACT_TYPES.WEBHOOK
    return contact


# ---------- 1. tracer：loopback 必拦 ----------
def test_webhook_blocks_loopback(api_modules):
    from api.settings import _assert_safe_webhook_url

    with pytest.raises(HTTPException) as exc:
        _assert_safe_webhook_url("http://127.0.0.1/x")
    assert exc.value.status_code == 400


# ---------- 2. RFC1918 私有段全拦 ----------
@pytest.mark.parametrize("url", [
    "http://10.0.0.1/x",
    "http://172.16.5.4/x",
    "http://172.31.255.255/x",
    "http://192.168.1.1/x",
])
def test_webhook_blocks_rfc1918(api_modules, url):
    from api.settings import _assert_safe_webhook_url

    with pytest.raises(HTTPException) as exc:
        _assert_safe_webhook_url(url)
    assert exc.value.status_code == 400


# ---------- 3. link-local / 云元数据（#5469 头条 AC） ----------
def test_webhook_blocks_cloud_metadata(api_modules):
    from api.settings import _assert_safe_webhook_url

    with pytest.raises(HTTPException) as exc:
        _assert_safe_webhook_url("http://169.254.169.254/latest/meta-data/")
    assert exc.value.status_code == 400


# ---------- 4. 非 http/https scheme 必拦 ----------
@pytest.mark.parametrize("url", ["file:///etc/passwd", "gopher://127.0.0.1/x", "ftp://example.com/x"])
def test_webhook_blocks_bad_scheme(api_modules, url):
    from api.settings import _assert_safe_webhook_url

    with pytest.raises(HTTPException) as exc:
        _assert_safe_webhook_url(url)
    assert exc.value.status_code == 400


# ---------- 5. DNS rebinding：域名解析到私有段亦拦 ----------
def test_webhook_blocks_dns_rebinding(api_modules):
    from api.settings import _assert_safe_webhook_url

    # benign 域名经 mock 解析到 10.0.0.1（私有），应被拦
    fake_info = [(2, 1, 6, "", ("10.0.0.1", 0))]
    with patch("api.settings.socket.getaddrinfo", return_value=fake_info):
        with pytest.raises(HTTPException) as exc:
            _assert_safe_webhook_url("https://internal.evil.example.com/hook")
    assert exc.value.status_code == 400


# ---------- 6. 公网 URL 放行 ----------
def test_webhook_allows_public(api_modules):
    from api.settings import _assert_safe_webhook_url

    # example.com 经 mock 解析到公网 IP（93.184.216.34），应放行不抛
    fake_info = [(2, 1, 6, "", ("93.184.216.34", 0))]
    with patch("api.settings.socket.getaddrinfo", return_value=fake_info):
        _assert_safe_webhook_url("https://example.com/hook")  # 不抛即通过


# ---------- 7. DNS 解析失败 fail-closed ----------
def test_webhook_dns_failure_fail_closed(api_modules):
    from api.settings import _assert_safe_webhook_url
    import socket

    with patch("api.settings.socket.getaddrinfo", side_effect=socket.gaierror("dns fail")):
        with pytest.raises(HTTPException) as exc:
            _assert_safe_webhook_url("https://nonexistent.invalid/x")
    assert exc.value.status_code == 400


# ---------- 8. 端点集成：test_user_contact 拦内网 URL（guard 在 requests 导入前抛 400） ----------
def test_user_contact_blocks_internal_webhook(api_modules):
    from ginkgo.enums import CONTACT_TYPES
    from api.settings import test_user_contact, UserContactTest

    fake_contact = _make_webhook_contact()
    user_svc = Mock()
    user_svc.get_contact.return_value = Mock(success=True, data=fake_contact)

    with patch("api.settings.get_user_service", return_value=user_svc):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(test_user_contact(
                "contact-uuid",
                UserContactTest(address="http://169.254.169.254/latest/meta-data/"),
            ))
    assert exc.value.status_code == 400


# ---------- 9. 第二 sink：test_notification_recipient 内网 webhook block 穿透内层 except ----------
def test_notification_recipient_blocks_internal_webhook(api_modules):
    """#5469: test_notification_recipient 的 DISCORD/WEBHOOK 分支同型 SSRF。

    内层 ``except Exception`` 会吞 HTTPException；修复加 ``except HTTPException: raise``
    使 block 一致返 400（非 200 failed）。
    """
    from api.settings import test_notification_recipient

    svc = Mock()
    contacts_result = Mock()
    contacts_result.is_success.return_value = True
    contacts_result.data = {
        "contacts": [{"type": "WEBHOOK", "address": "http://10.0.0.1/exfil"}],
        "recipient_name": "alice",
        "recipient_type": "USER",
    }
    svc.get_recipient_contacts.return_value = contacts_result

    with patch("api.settings.get_notification_recipient_service", return_value=svc):
        with pytest.raises(HTTPException) as exc:
            asyncio.run(test_notification_recipient("recipient-uuid"))
    assert exc.value.status_code == 400
