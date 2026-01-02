# Upstream: NotificationService (通知服务)
# Downstream: WebhookChannel, EmailChannel, KafkaChannel
# Role: 通知渠道模块提供各类通知渠道实现支持Webhook/Email/Kafka等通知方式支持通知系统功能


"""
Notification Channels Module

提供各种通知渠道的实现：
- INotificationChannel: 通知渠道接口
- WebhookChannel: Webhook 渠道（Discord/钉钉/企业微信等）
- EmailChannel: 邮件渠道
- KafkaChannel: Kafka 消息队列渠道
- ConsoleChannel: 控制台渠道（用于调试）
"""

# 延迟导入以避免循环依赖
__all__ = [
    "INotificationChannel",
    "WebhookChannel",
    "EmailChannel",
    "ConsoleChannel",
]


def __getattr__(name):
    if name == "INotificationChannel":
        from ginkgo.notifier.channels.base_channel import INotificationChannel
        return INotificationChannel
    if name == "WebhookChannel":
        from ginkgo.notifier.channels.webhook_channel import WebhookChannel
        return WebhookChannel
    if name == "EmailChannel":
        from ginkgo.notifier.channels.email_channel import EmailChannel
        return EmailChannel
    if name == "ConsoleChannel":
        from ginkgo.notifier.channels.console_channel import ConsoleChannel
        return ConsoleChannel
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
