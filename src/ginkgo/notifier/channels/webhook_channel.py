# Upstream: NotificationService (通知服务业务逻辑)、INotificationChannel (渠道接口)
# Downstream: Discord Webhook API (外部服务)
# Role: WebhookChannel Webhook通知渠道实现通过Webhook发送消息到Discord/钉钉/企业微信等支持Markdown和嵌入消息支持通知系统功能


"""
Webhook Notification Channel

通过 Webhook 发送通知消息，支持 Discord、钉钉、企业微信等。
"""

import time
from typing import Dict, Any, Optional, List, Union
from datetime import datetime

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False

from ginkgo.notifier.channels.base_channel import INotificationChannel, ChannelResult
from ginkgo.libs import GLOG


class WebhookChannel(INotificationChannel):
    """
    Webhook 通知渠道

    通过 Webhook URL 发送消息到指定平台（Discord、钉钉、企业微信等）。
    支持：
    - 纯文本消息
    - Markdown 格式
    - 嵌入消息（Embeds）
    - 自动重试机制
    """

    # Discord Webhook URL 格式
    WEBHOOK_URL_FORMAT = "https://discord.com/api/webhooks/{user_id}/{token}"

    # 颜色常量（用于嵌入消息）
    COLOR_INFO = 3447003      # 蓝色
    COLOR_SUCCESS = 3066993   # 绿色
    COLOR_WARNING = 15844367  # 黄色
    COLOR_ERROR = 15158332    # 红色

    def __init__(
        self,
        webhook_url: str,
        username: Optional[str] = None,
        avatar_url: Optional[str] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
        timeout: float = 10.0
    ):
        """
        初始化 Webhook 渠道

        Args:
            webhook_url: Webhook URL
            username: 覆盖默认用户名（可选）
            avatar_url: 覆盖默认头像 URL（可选）
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
            timeout: 请求超时（秒）
        """
        if not REQUESTS_AVAILABLE:
            raise ImportError("requests library is required for WebhookChannel")

        self.webhook_url = webhook_url
        self.username = username
        self.avatar_url = avatar_url
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.timeout = timeout

    @property
    def channel_name(self) -> str:
        """获取渠道名称"""
        return "webhook"

    def send(
        self,
        content: str,
        title: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[Union[str, Dict[str, str]]] = None,
        author: Optional[Dict[str, str]] = None,
        url: Optional[str] = None,
        **kwargs
    ) -> ChannelResult:
        """
        发送 Webhook 消息

        Args:
            content: 消息内容（支持 Markdown）
            title: 消息标题（用于嵌入消息）
            embed: 自定义嵌入消息（可选，如果提供则忽略其他参数）
            color: 嵌入消息颜色（可选）
            fields: 嵌入字段数组，格式：[{"name": "字段名", "value": "字段值", "inline": False}]
            footer: 页脚信息，支持直接传字符串 "Text" 或 Dict {"text": "页脚", "icon_url": "URL"}
            author: 作者信息，格式：{"name": "作者名", "url": "链接", "icon_url": "图标URL"}
            url: 标题链接（点击标题跳转的URL）
            **kwargs: 其他参数

        Returns:
            ChannelResult: 发送结果
        """
        if not self.validate_config():
            return ChannelResult(
                success=False,
                error="Invalid webhook configuration"
            )

        # 转换footer为Discord格式
        footer_obj = None
        if footer:
            if isinstance(footer, str):
                footer_obj = {"text": footer}
            else:
                footer_obj = footer

        # 构建消息 payload
        payload = self._build_payload(
            content=content,
            title=title,
            embed=embed,
            color=color,
            fields=fields,
            footer=footer_obj,
            author=author,
            url=url
        )

        # 发送请求（带重试）
        return self._send_with_retry(payload)

    def validate_config(self) -> bool:
        """
        验证 Webhook 配置

        Returns:
            bool: 配置是否有效
        """
        if not self.webhook_url:
            return False

        # 基本格式验证（支持 discord.com 和 discordapp.com）
        valid_prefixes = (
            "https://discord.com/api/webhooks/",
            "https://discordapp.com/api/webhooks/"
        )

        if not any(self.webhook_url.startswith(prefix) for prefix in valid_prefixes):
            return False

        # 检查 URL 格式
        for prefix in valid_prefixes:
            if self.webhook_url.startswith(prefix):
                parts = self.webhook_url.replace(prefix, "").split("/")
                break
        else:
            return False

        if len(parts) < 2:
            return False

        return True

    def get_config_summary(self) -> Dict[str, Any]:
        """
        获取配置摘要

        Returns:
            Dict: 配置摘要（隐藏 Webhook Token）
        """
        # 隐藏 webhook token
        safe_url = self.webhook_url
        if "/" in safe_url:
            parts = safe_url.rstrip("/").split("/")
            if len(parts) >= 2:
                parts[-1] = "***"
                safe_url = "/".join(parts)

        return {
            "channel": self.channel_name,
            "webhook_url": safe_url,
            "username": self.username,
            "max_retries": self.max_retries,
            "timeout": self.timeout
        }

    def _build_payload(
        self,
        content: str,
        title: Optional[str] = None,
        embed: Optional[Dict[str, Any]] = None,
        color: Optional[int] = None,
        fields: Optional[List[Dict[str, Any]]] = None,
        footer: Optional[Dict[str, str]] = None,
        author: Optional[Dict[str, str]] = None,
        url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        构建 Webhook payload

        Args:
            content: 消息内容
            title: 标题
            embed: 自定义嵌入
            color: 颜色
            fields: 嵌入字段数组
            footer: 页脚信息
            author: 作者信息
            url: 标题链接

        Returns:
            Dict: Discord API payload
        """
        payload = {}

        # 添加覆盖选项
        if self.username:
            payload["username"] = self.username
        if self.avatar_url:
            payload["avatar_url"] = self.avatar_url

        # 如果有自定义嵌入，直接使用
        if embed:
            payload["embeds"] = [embed]
            # 如果没有指定 content，使用嵌入的描述
            if not content and "description" not in embed:
                payload["content"] = ""
            elif content:
                payload["content"] = content
        else:
            # 构建标准嵌入
            if title or color is not None or fields or footer or author or url:
                embed_obj = {}

                # 标题和 URL
                if title:
                    embed_obj["title"] = title
                    if url:
                        embed_obj["url"] = url

                # 描述（内容）
                if content:
                    embed_obj["description"] = content

                # 颜色
                if color is not None:
                    embed_obj["color"] = color
                else:
                    embed_obj["color"] = self.COLOR_INFO

                # 时间戳
                embed_obj["timestamp"] = datetime.utcnow().isoformat()

                # 字段（fields）
                if fields:
                    embed_obj["fields"] = fields

                # 页脚（footer）
                if footer:
                    footer_obj = {}
                    if "text" in footer:
                        footer_obj["text"] = footer["text"]
                    if "icon_url" in footer:
                        footer_obj["icon_url"] = footer["icon_url"]
                    embed_obj["footer"] = footer_obj

                # 作者（author）
                if author:
                    author_obj = {}
                    if "name" in author:
                        author_obj["name"] = author["name"]
                    if "url" in author:
                        author_obj["url"] = author["url"]
                    if "icon_url" in author:
                        author_obj["icon_url"] = author["icon_url"]
                    embed_obj["author"] = author_obj

                payload["embeds"] = [embed_obj]
            else:
                # 简单文本消息
                payload["content"] = content

        return payload

    def _send_with_retry(self, payload: Dict[str, Any]) -> ChannelResult:
        """
        发送请求（带重试）

        Args:
            payload: Discord API payload

        Returns:
            ChannelResult: 发送结果
        """
        last_error = None

        for attempt in range(self.max_retries):
            try:
                response = requests.post(
                    self.webhook_url,
                    json=payload,
                    timeout=self.timeout
                )

                if response.status_code in (200, 204):
                    # 成功
                    message_id = self._extract_message_id(response)
                    return ChannelResult(
                        success=True,
                        message_id=message_id,
                        timestamp=datetime.utcnow().timestamp()
                    )
                elif response.status_code == 429:
                    # 速率限制
                    retry_after = response.headers.get("Retry-After", self.retry_delay)
                    GLOG.WARN(f"Discord rate limit, retry after {retry_after}s")
                    time.sleep(float(retry_after))
                    continue
                elif response.status_code >= 500:
                    # 服务器错误，重试
                    last_error = f"Server error: {response.status_code}"
                    if attempt < self.max_retries - 1:
                        time.sleep(self.retry_delay)
                        continue
                else:
                    # 其他错误不重试
                    last_error = f"HTTP {response.status_code}: {response.text}"
                    break

            except requests.Timeout:
                last_error = f"Request timeout after {self.timeout}s"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break

            except requests.RequestException as e:
                last_error = f"Request error: {str(e)}"
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay)
                    continue
                else:
                    break

            except Exception as e:
                last_error = f"Unexpected error: {str(e)}"
                break

        # 所有重试都失败
        GLOG.ERROR(f"Discord send failed after {self.max_retries} attempts: {last_error}")
        return ChannelResult(
            success=False,
            error=last_error,
            timestamp=datetime.utcnow().timestamp()
        )

    def _extract_message_id(self, response: requests.Response) -> Optional[str]:
        """
        从响应中提取消息 ID

        Args:
            response: Discord API 响应

        Returns:
            Optional[str]: 消息 ID（如果有）
        """
        try:
            data = response.json()
            return data.get("id")
        except Exception:
            return None

    # 便捷方法

    def send_info(self, content: str, title: Optional[str] = None) -> ChannelResult:
        """发送信息级别消息（蓝色）"""
        return self.send(content, title=title, color=self.COLOR_INFO)

    def send_success(self, content: str, title: Optional[str] = None) -> ChannelResult:
        """发送成功消息（绿色）"""
        return self.send(content, title=title, color=self.COLOR_SUCCESS)

    def send_warning(self, content: str, title: Optional[str] = None) -> ChannelResult:
        """发送警告消息（黄色）"""
        return self.send(content, title=title, color=self.COLOR_WARNING)

    def send_error(self, content: str, title: Optional[str] = None) -> ChannelResult:
        """发送错误消息（红色）"""
        return self.send(content, title=title, color=self.COLOR_ERROR)


# ============================================================================
# 便捷函数 - 无需实例化即可使用
# ============================================================================

def send_webhook(
    webhook_url: str,
    content: str,
    title: Optional[str] = None,
    color: Optional[int] = None,
    fields: Optional[List[Dict[str, Any]]] = None,
    footer: Optional[Dict[str, str]] = None,
    author: Optional[Dict[str, str]] = None,
    url: Optional[str] = None,
    **kwargs
) -> ChannelResult:
    """
    发送 Webhook 消息（便捷函数）

    无需手动创建 WebhookChannel 实例，直接调用即可发送消息。

    Args:
        webhook_url: Webhook URL
        content: 消息内容
        title: 消息标题
        color: 嵌入消息颜色
        fields: 嵌入字段数组
        footer: 页脚信息
        author: 作者信息
        url: 标题链接
        **kwargs: 其他参数

    Returns:
        ChannelResult: 发送结果

    Examples:
        >>> from ginkgo.notifier.channels import send_webhook
        >>>
        >>> # 简单消息
        >>> send_webhook("https://...", content="Hello World")
        >>>
        >>> # 带标题和颜色
        >>> send_webhook(
        ...     "https://...",
        ...     content="订单已成交",
        ...     title="交易通知",
        ...     color=3066993
        ... )
        >>>
        >>> # 带字段
        >>> send_webhook(
        ...     "https://...",
        ...     content="交易信号",
        ...     title="买入信号",
        ...     fields=[
        ...         {"name": "代码", "value": "000001.SZ", "inline": True},
        ...         {"name": "价格", "value": "12.50", "inline": True}
        ...     ]
        ... )
    """
    channel = WebhookChannel(webhook_url=webhook_url)
    return channel.send(
        content=content,
        title=title,
        color=color,
        fields=fields,
        footer=footer,
        author=author,
        url=url,
        **kwargs
    )


def send_webhook_info(webhook_url: str, content: str, title: Optional[str] = None) -> ChannelResult:
    """发送信息级别消息（蓝色）"""
    return send_webhook(webhook_url, content, title=title, color=WebhookChannel.COLOR_INFO)


def send_webhook_success(webhook_url: str, content: str, title: Optional[str] = None) -> ChannelResult:
    """发送成功消息（绿色）"""
    return send_webhook(webhook_url, content, title=title, color=WebhookChannel.COLOR_SUCCESS)


def send_webhook_warning(webhook_url: str, content: str, title: Optional[str] = None) -> ChannelResult:
    """发送警告消息（黄色）"""
    return send_webhook(webhook_url, content, title=title, color=WebhookChannel.COLOR_WARNING)


def send_webhook_error(webhook_url: str, content: str, title: Optional[str] = None) -> ChannelResult:
    """发送错误消息（红色）"""
    return send_webhook(webhook_url, content, title=title, color=WebhookChannel.COLOR_ERROR)
