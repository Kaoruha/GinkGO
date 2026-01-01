# Upstream: NotificationService (通知服务业务逻辑)
# Downstream: TemplateEngine, MessageQueue, NotificationChannel (渠道实现)
# Role: Notifier Core Module 核心模块提供通知引擎、模板引擎、消息队列支持通知系统功能


"""
Notifier Core Module

提供通知系统的核心组件：
- TemplateEngine: 模板渲染引擎
- MessageQueue: Kafka 消息队列
- NotificationService: 通知服务
- KafkaHealthChecker: Kafka 健康检查器
"""

# 延迟导入以避免循环依赖
__all__ = [
    "TemplateEngine",
    "MessageQueue",
    "KafkaHealthChecker",
]


def __getattr__(name):
    if name == "TemplateEngine":
        from ginkgo.notifier.core.template_engine import TemplateEngine
        return TemplateEngine
    if name == "MessageQueue":
        from ginkgo.notifier.core.message_queue import MessageQueue
        return MessageQueue
    if name == "KafkaHealthChecker":
        from ginkgo.libs.utils.kafka_health_checker import KafkaHealthChecker
        return KafkaHealthChecker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
