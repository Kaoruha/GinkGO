"""TDD for AlertService notification escaping -- #5556

根因：三个通知渠道（钉钉/企业微信 markdown、邮件 HTML）用 f-string 直接插值
content['pattern'/'message'/...]，pattern 来自规则匹配的日志关键词，若日志
含恶意 HTML/JS 则注入。html.escape 在插值点转义。

每个渠道一个 RED：注入恶意 pattern/message → 断言发出的 payload 中已被转义。
"""
from unittest.mock import MagicMock, patch

import pytest

try:
    from ginkgo.services.logging.alert_service import AlertService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="alert_service not importable")
class TestAlertServiceEscaping:
    """#5556: 通知内容必须 HTML 转义，防注入"""

    def _make_svc(self):
        redis = MagicMock()
        redis.get.return_value = None  # 未抑制，允许发送
        with patch("ginkgo.services.logging.alert_service.GCONF"):
            svc = AlertService(redis_client=redis, db_engine=MagicMock())
        return svc

    def _mock_post(self):
        """捕获 requests.post 的 json 参数"""
        captured = {}

        def fake_post(url, json=None, **kw):
            captured["json"] = json
            resp = MagicMock()
            resp.status_code = 200
            resp.json.return_value = {"errcode": 0}
            return resp

        return captured, fake_post

    def test_dingtalk_escapes_html_in_pattern(self):
        """钉钉 markdown：pattern 含 <script> 必须被转义为 &lt;script&gt;。"""
        svc = self._make_svc()
        svc._dingtalk_webhook = "http://hook.example.com/dingtalk"
        captured, fake_post = self._mock_post()

        with patch("ginkgo.services.logging.alert_service.requests.post",
                   side_effect=fake_post):
            svc.send_alert(
                message="normal message",
                rule_id="r1",
                pattern="<script>alert(1)</script>",
                channels=["dingtalk"],
            )

        text = captured["json"]["markdown"]["text"]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    def test_wechat_escapes_html_in_pattern(self):
        """企业微信 markdown：pattern 含 <script> 必须被转义。"""
        svc = self._make_svc()
        svc._wechat_webhook = "http://hook.example.com/wechat"
        captured, fake_post = self._mock_post()

        with patch("ginkgo.services.logging.alert_service.requests.post",
                   side_effect=fake_post):
            svc.send_alert(
                message="normal message",
                rule_id="r1",
                pattern="<script>alert(1)</script>",
                channels=["wechat"],
            )

        text = captured["json"]["markdown"]["content"]
        assert "<script>" not in text
        assert "&lt;script&gt;" in text

    def test_email_escapes_html_in_pattern(self):
        """邮件 HTML body：pattern 含 <script> 必须被转义。"""
        svc = self._make_svc()
        svc._email_smtp_host = "smtp.example.com"
        svc._email_to = ["a@b.com"]
        svc._email_from = "f@b.com"
        svc._email_username = "u"
        svc._email_password = "p"
        captured = {}

        class FakeSMTP:
            def __init__(self, host, port):
                pass

            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def starttls(self):
                pass

            def login(self, u, p):
                pass

            def send_message(self, msg):
                captured["msg"] = msg

        with patch("ginkgo.services.logging.alert_service.smtplib.SMTP", FakeSMTP):
            svc.send_alert(
                message="normal message",
                rule_id="r1",
                pattern="<script>alert(1)</script>",
                channels=["email"],
            )

        html_body = captured["msg"].get_payload()[0].get_payload(decode=True).decode("utf-8")
        assert "<script>" not in html_body
        assert "&lt;script&gt;" in html_body
