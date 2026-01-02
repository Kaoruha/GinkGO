# Upstream: External Applications
# Downstream: Trading Strategies, Analysis Tools
# Role: Notifier通知模块提供消息通知/推送和多渠道通知功能支持交易信号和系统消息推送支持交易系统功能


"""
Notifier Module

Provides notification system functionality including:
- Template engine for message rendering
- Notification channels (Email, Webhook, Kafka)
- Notification services and workers
- Dependency injection container for notification components
"""

# 延迟导入以避免循环依赖
__all__ = [
    "TemplateEngine",
    "INotificationChannel",
    "WebhookChannel",
    "NotificationService",
    "NotificationWorker",
    "container",
]

def __getattr__(name):
    if name == "TemplateEngine":
        from ginkgo.notifier.core.template_engine import TemplateEngine
        return TemplateEngine
    if name == "INotificationChannel":
        from ginkgo.notifier.channels.base_channel import INotificationChannel
        return INotificationChannel
    if name == "WebhookChannel":
        from ginkgo.notifier.channels.webhook_channel import WebhookChannel
        return WebhookChannel
    if name == "NotificationService":
        from ginkgo.notifier.core.notification_service import NotificationService
        return NotificationService
    if name == "NotificationWorker":
        from ginkgo.notifier.workers.notification_worker import NotificationWorker
        return NotificationWorker
    if name == "container":
        from ginkgo.notifier.containers import container
        return container
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
