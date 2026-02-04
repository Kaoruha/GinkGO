# Upstream: Container (依赖注入)、External Applications (直接调用)
# Downstream: NotificationRecipientService (通知接收人服务)
# Role: Notifier Services模块公共接口导出NotificationRecipientService提供通知接收人管理功能


from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService

__all__ = ['NotificationRecipientService']
