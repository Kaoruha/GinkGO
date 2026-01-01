# Upstream: Kafka Consumer, NotificationService
# Downstream: INotificationChannel (WebhookChannel, EmailChannel)
# Role: Notifier Workers Module Worker模块提供Kafka消费者Worker支持通知系统功能


"""
Notifier Workers Module

提供 Kafka Worker 组件：
- NotificationWorker: Kafka 消费者 Worker
"""

__all__ = ["NotificationWorker", "WorkerStatus", "create_notification_worker"]


def __getattr__(name):
    if name == "NotificationWorker":
        from ginkgo.notifier.workers.notification_worker import NotificationWorker
        return NotificationWorker
    if name == "WorkerStatus":
        from ginkgo.notifier.workers.notification_worker import WorkerStatus
        return WorkerStatus
    if name == "create_notification_worker":
        from ginkgo.notifier.workers.notification_worker import create_notification_worker
        return create_notification_worker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
