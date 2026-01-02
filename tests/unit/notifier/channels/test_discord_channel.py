# Upstream: None
# Downstream: None
# Role: WebhookChannel单元测试验证Webhook通知渠道功能


"""
WebhookChannel Unit Tests

测试覆盖:
- 渠道初始化
- 配置验证
- 消息发送
- 重试机制
- 错误处理
- 便捷方法
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ginkgo.notifier.channels.webhook_channel import WebhookChannel


@pytest.mark.unit
class TestWebhookChannelInit:
    """WebhookChannel 初始化测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_init_basic(self):
        """测试基本初始化"""
        webhook_url = "https://discord.com/api/webhooks/123456/abc123"
        channel = WebhookChannel(webhook_url)

        assert channel.webhook_url == webhook_url
        assert channel.channel_name == "webhook"
        assert channel.max_retries == 3
        assert channel.retry_delay == 1.0

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_init_with_options(self):
        """测试带选项的初始化"""
        webhook_url = "https://discord.com/api/webhooks/123456/abc123"
        channel = WebhookChannel(
            webhook_url,
            username="TestBot",
            avatar_url="https://example.com/avatar.png",
            max_retries=5,
            retry_delay=2.0,
            timeout=30.0
        )

        assert channel.username == "TestBot"
        assert channel.avatar_url == "https://example.com/avatar.png"
        assert channel.max_retries == 5
        assert channel.retry_delay == 2.0
        assert channel.timeout == 30.0


@pytest.mark.unit
class TestWebhookChannelValidation:
    """WebhookChannel 配置验证测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_validate_config_valid(self):
        """测试有效配置"""
        webhook_url = "https://discord.com/api/webhooks/123456/abc123"
        channel = WebhookChannel(webhook_url)

        assert channel.validate_config() is True

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_validate_config_empty_url(self):
        """测试空 URL"""
        channel = WebhookChannel("")

        assert channel.validate_config() is False

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_validate_config_invalid_format(self):
        """测试无效格式"""
        channel = WebhookChannel("https://example.com/webhook")

        assert channel.validate_config() is False

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_validate_config_incomplete_url(self):
        """测试不完整的 URL"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123456")

        assert channel.validate_config() is False

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_is_available(self):
        """测试 is_available"""
        webhook_url = "https://discord.com/api/webhooks/123456/abc123"
        channel = WebhookChannel(webhook_url)

        assert channel.is_available() is True


@pytest.mark.unit
class TestWebhookChannelConfigSummary:
    """WebhookChannel 配置摘要测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_get_config_summary(self):
        """测试获取配置摘要"""
        webhook_url = "https://discord.com/api/webhooks/123456/abc123def"
        channel = WebhookChannel(
            webhook_url,
            username="TestBot",
            max_retries=5
        )

        summary = channel.get_config_summary()

        assert summary["channel"] == "webhook"
        assert summary["webhook_url"] == "https://discord.com/api/webhooks/123456/***"
        assert summary["username"] == "TestBot"
        assert summary["max_retries"] == 5
        assert "timeout" in summary


@pytest.mark.unit
class TestWebhookChannelBuildPayload:
    """WebhookChannel payload 构建测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_build_payload_simple_text(self):
        """测试简单文本 payload"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        payload = channel._build_payload(
            content="Simple text message"
        )

        assert payload["content"] == "Simple text message"
        assert "embeds" not in payload

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_build_payload_with_title(self):
        """测试带标题的 payload"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        payload = channel._build_payload(
            content="Message content",
            title="Test Title"
        )

        assert "embeds" in payload
        assert len(payload["embeds"]) == 1
        assert payload["embeds"][0]["title"] == "Test Title"
        assert payload["embeds"][0]["description"] == "Message content"

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_build_payload_with_color(self):
        """测试带颜色的 payload"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        payload = channel._build_payload(
            content="Colored message",
            color=WebhookChannel.COLOR_SUCCESS
        )

        assert payload["embeds"][0]["color"] == WebhookChannel.COLOR_SUCCESS

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_build_payload_with_custom_embed(self):
        """测试自定义嵌入 payload"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        custom_embed = {
            "title": "Custom Embed",
            "description": "Custom description",
            "fields": [
                {"name": "Field 1", "value": "Value 1", "inline": True}
            ]
        }

        payload = channel._build_payload(
            content="Content",
            embed=custom_embed
        )

        assert payload["embeds"][0]["title"] == "Custom Embed"
        assert payload["embeds"][0]["fields"][0]["name"] == "Field 1"

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_build_payload_with_username_override(self):
        """测试用户名覆盖"""
        channel = WebhookChannel(
            "https://discord.com/api/webhooks/123/abc",
            username="OverrideBot"
        )

        payload = channel._build_payload(content="Test")

        assert payload["username"] == "OverrideBot"


@pytest.mark.unit
class TestWebhookChannelSend:
    """WebhookChannel 发送测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_success(self, mock_post):
        """测试成功发送"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send("Test message")

        assert result.success is True
        assert result.error is None
        mock_post.assert_called_once()

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_with_message_id(self, mock_post):
        """测试获取消息 ID"""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "msg_123456"}
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send("Test message")

        assert result.success is True
        assert result.message_id == "msg_123456"

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_invalid_config(self, mock_post):
        """测试无效配置"""
        channel = WebhookChannel("")  # Invalid URL
        result = channel.send("Test message")

        assert result.success is False
        assert "Invalid webhook" in result.error
        mock_post.assert_not_called()

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_rate_limit_retry(self, mock_post):
        """测试速率限制重试"""
        # 第一次：速率限制
        mock_response_429 = MagicMock()
        mock_response_429.status_code = 429
        mock_response_429.headers = {"Retry-After": "1"}

        # 第二次：成功
        mock_response_204 = MagicMock()
        mock_response_204.status_code = 204

        mock_post.side_effect = [mock_response_429, mock_response_204]

        channel = WebhookChannel(
            "https://discord.com/api/webhooks/123/abc",
            max_retries=3
        )
        result = channel.send("Test message")

        assert result.success is True
        assert mock_post.call_count == 2

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_server_error_retry(self, mock_post):
        """测试服务器错误重试"""
        # 第一次：服务器错误
        mock_response_500 = MagicMock()
        mock_response_500.status_code = 500

        # 第二次：成功
        mock_response_204 = MagicMock()
        mock_response_204.status_code = 204

        mock_post.side_effect = [mock_response_500, mock_response_204]

        channel = WebhookChannel(
            "https://discord.com/api/webhooks/123/abc",
            max_retries=3
        )
        result = channel.send("Test message")

        assert result.success is True
        assert mock_post.call_count == 2

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_timeout_retry(self, mock_post):
        """测试超时重试"""
        # 第一次：超时
        import requests
        mock_post.side_effect = [
            requests.Timeout("Timeout"),
            MagicMock(status_code=204)  # 第二次：成功
        ]

        channel = WebhookChannel(
            "https://discord.com/api/webhooks/123/abc",
            max_retries=3
        )
        result = channel.send("Test message")

        assert result.success is True
        assert mock_post.call_count == 2

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_client_error_no_retry(self, mock_post):
        """测试客户端错误不重试"""
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Bad Request"
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send("Test message")

        assert result.success is False
        assert "HTTP 400" in result.error
        assert mock_post.call_count == 1  # 只调用一次，不重试

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_max_retries_exceeded(self, mock_post):
        """测试超过最大重试次数"""
        import requests
        mock_post.side_effect = requests.Timeout("Timeout")

        channel = WebhookChannel(
            "https://discord.com/api/webhooks/123/abc",
            max_retries=2
        )
        result = channel.send("Test message")

        assert result.success is False
        assert "timeout" in result.error.lower()
        assert mock_post.call_count == 2


@pytest.mark.unit
class TestWebhookChannelConvenienceMethods:
    """WebhookChannel 便捷方法测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_info(self, mock_post):
        """测试发送信息消息"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send_info("Info message", title="Info")

        assert result.success is True

        # 检查 payload 颜色
        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["embeds"][0]["color"] == WebhookChannel.COLOR_INFO

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_success(self, mock_post):
        """测试发送成功消息"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send_success("Success message")

        assert result.success is True

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["embeds"][0]["color"] == WebhookChannel.COLOR_SUCCESS

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_warning(self, mock_post):
        """测试发送警告消息"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send_warning("Warning message")

        assert result.success is True

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["embeds"][0]["color"] == WebhookChannel.COLOR_WARNING

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    @patch('ginkgo.notifier.channels.webhook_channel.requests.post')
    def test_send_error(self, mock_post):
        """测试发送错误消息"""
        mock_response = MagicMock()
        mock_response.status_code = 204
        mock_post.return_value = mock_response

        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")
        result = channel.send_error("Error message")

        assert result.success is True

        call_args = mock_post.call_args
        payload = call_args[1]["json"]
        assert payload["embeds"][0]["color"] == WebhookChannel.COLOR_ERROR


@pytest.mark.unit
class TestWebhookChannelExtractMessageId:
    """WebhookChannel 消息 ID 提取测试"""

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_extract_message_id_success(self):
        """测试成功提取消息 ID"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        mock_response = MagicMock()
        mock_response.json.return_value = {"id": "msg_123456"}

        message_id = channel._extract_message_id(mock_response)

        assert message_id == "msg_123456"

    @pytest.mark.skipif(not REQUESTS_AVAILABLE, reason="requests not available")
    def test_extract_message_id_failure(self):
        """测试提取失败"""
        channel = WebhookChannel("https://discord.com/api/webhooks/123/abc")

        mock_response = MagicMock()
        mock_response.json.side_effect = Exception("No JSON")

        message_id = channel._extract_message_id(mock_response)

        assert message_id is None
