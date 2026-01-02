# Upstream: NotificationService (通知服务业务逻辑)
# Downstream: Kafka Producer (GinkgoProducer)、KafkaCRUD (Kafka CRUD操作)
# Role: MessageQueue 消息队列封装封装Kafka发送通知消息支持异步通知处理支持通知系统功能


"""
Notification Message Queue

封装 Kafka 生产者，用于发送通知消息到 Kafka 队列。
支持：
- 发送通知到 `notifications` topic
- 消息序列化
- 错误处理和重试
- 降级模式（Kafka 不可用时同步发送）
"""

import json
from typing import Dict, Any, Optional, List, Union
from datetime import datetime
from enum import IntEnum

from ginkgo.libs import GLOG, retry
from ginkgo.enums import CONTACT_TYPES, NOTIFICATION_STATUS_TYPES


class NotificationPriority(IntEnum):
    """通知优先级（预留，当前按 FIFO 处理）"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class MessageQueue:
    """
    通知消息队列

    封装 Kafka 生产者，用于异步发送通知消息。
    单一 topic: `notifications`
    Worker 根据 contact_type 路由到对应渠道。
    """

    # Kafka topic 名称
    NOTIFICATIONS_TOPIC = "notifications"

    def __init__(self, kafka_crud=None):
        """
        初始化消息队列

        Args:
            kafka_crud: KafkaCRUD 实例（可选，如果为 None 则自动创建）
        """
        if kafka_crud is None:
            from ginkgo.data.crud import KafkaCRUD
            kafka_crud = KafkaCRUD()

        self.kafka_crud = kafka_crud
        self._kafka_available = None  # None = 未检查, True = 可用, False = 不可用

    @property
    def is_available(self) -> bool:
        """
        检查 Kafka 是否可用

        Returns:
            bool: Kafka 是否可用
        """
        if self._kafka_available is None:
            self._check_kafka_availability()
        return self._kafka_available

    def send_notification(
        self,
        content: str,
        channels: List[str],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        **kwargs
    ) -> bool:
        """
        发送通知到 Kafka 队列

        Args:
            content: 通知内容
            channels: 渠道列表（如 ["discord", "email"]）
            user_uuid: 用户 UUID（可选）
            template_id: 模板 ID（可选）
            content_type: 内容类型（text/markdown/html）
            priority: 优先级（0=低, 1=中, 2=高, 3=紧急）
            title: 通知标题（可选）
            **kwargs: 其他参数（如 embeds, fields, footer）

        Returns:
            bool: 是否成功发送到 Kafka
        """
        if not self.is_available:
            GLOG.WARN("Kafka is not available, cannot send notification to queue")
            return False

        try:
            # 构建消息
            message = self._build_message(
                content=content,
                channels=channels,
                user_uuid=user_uuid,
                template_id=template_id,
                content_type=content_type,
                priority=priority,
                title=title,
                **kwargs
            )

            # 发送到 Kafka
            success = self.kafka_crud.send_message(
                topic=self.NOTIFICATIONS_TOPIC,
                message=message,
                key=user_uuid  # 使用 user_uuid 作为分区键，确保同一用户的消息顺序
            )

            if success:
                GLOG.DEBUG(f"Notification queued for user {user_uuid}, channels: {channels}")
            else:
                GLOG.ERROR(f"Failed to queue notification for user {user_uuid}")

            return success

        except Exception as e:
            GLOG.ERROR(f"Error sending notification to queue: {e}")
            return False

    @retry(max_try=3)
    def send_batch(
        self,
        notifications: List[Dict[str, Any]]
    ) -> int:
        """
        批量发送通知

        Args:
            notifications: 通知列表，每个通知是一个字典

        Returns:
            int: 成功发送的数量
        """
        if not self.is_available:
            GLOG.WARN("Kafka is not available, cannot send batch notifications")
            return 0

        try:
            messages = []
            for notif in notifications:
                message = self._build_message(**notif)
                messages.append(message)

            # 批量发送
            success_count = self.kafka_crud.send_batch_messages(
                topic=self.NOTIFICATIONS_TOPIC,
                messages=messages
            )

            GLOG.DEBUG(f"Batch queued {success_count}/{len(notifications)} notifications")
            return success_count

        except Exception as e:
            GLOG.ERROR(f"Error sending batch notifications: {e}")
            return 0

    def _build_message(
        self,
        content: str,
        channels: List[str],
        user_uuid: Optional[str] = None,
        template_id: Optional[str] = None,
        content_type: str = "text",
        priority: int = 1,
        title: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        构建通知消息

        Args:
            content: 通知内容
            channels: 渠道列表
            user_uuid: 用户 UUID
            template_id: 模板 ID
            content_type: 内容类型
            priority: 优先级
            title: 标题
            **kwargs: 其他参数

        Returns:
            Dict: 序列化的消息
        """
        message = {
            "message_id": f"msg_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}",
            "content": content,
            "channels": channels,
            "content_type": content_type,
            "priority": priority,
            "status": NOTIFICATION_STATUS_TYPES.PENDING.value,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": {
                "user_uuid": user_uuid,
                "template_id": template_id,
                "title": title,
            },
            "kwargs": kwargs
        }

        return message

    def _check_kafka_availability(self) -> bool:
        """
        检查 Kafka 可用性

        Returns:
            bool: Kafka 是否可用
        """
        try:
            # 尝试连接 Kafka
            self._kafka_available = self.kafka_crud._test_connection()
            if not self._kafka_available:
                GLOG.WARN("Kafka connection test failed")
            return self._kafka_available
        except Exception as e:
            GLOG.ERROR(f"Kafka availability check failed: {e}")
            self._kafka_available = False
            return False

    def get_queue_status(self) -> Dict[str, Any]:
        """
        获取队列状态

        Returns:
            Dict: 队列状态信息
        """
        try:
            # 获取 topic 信息
            topic_info = self.kafka_crud.get_topic_info(self.NOTIFICATIONS_TOPIC)

            return {
                "topic": self.NOTIFICATIONS_TOPIC,
                "available": self.is_available,
                "topic_exists": topic_info is not None,
                "message_count": self.kafka_crud.get_message_count(self.NOTIFICATIONS_TOPIC) if self.is_available else 0
            }

        except Exception as e:
            GLOG.ERROR(f"Error getting queue status: {e}")
            return {
                "topic": self.NOTIFICATIONS_TOPIC,
                "available": False,
                "error": str(e)
            }


# ============================================================================
# 便捷函数
# ============================================================================

def send_notification_to_queue(
    content: str,
    channels: List[str],
    user_uuid: Optional[str] = None,
    **kwargs
) -> bool:
    """
    发送通知到队列（便捷函数）

    Args:
        content: 通知内容
        channels: 渠道列表
        user_uuid: 用户 UUID
        **kwargs: 其他参数

    Returns:
        bool: 是否成功发送

    Examples:
        >>> from ginkgo.notifier.core.message_queue import send_notification_to_queue
        >>>
        >>> send_notification_to_queue(
        ...     content="Hello World",
        ...     channels=["email", "discord"],
        ...     user_uuid="user-123"
        ... )
    """
    queue = MessageQueue()
    return queue.send_notification(
        content=content,
        channels=channels,
        user_uuid=user_uuid,
        **kwargs
    )
