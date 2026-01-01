# Upstream: Kafka Consumer (GinkgoConsumer), NotificationService
# Downstream: INotificationChannel (WebhookChannel, EmailChannel)
# Role: NotificationWorker Kafka消费者Worker消费notifications topic消息并调用相应渠道发送支持通知系统功能


"""
Notification Kafka Worker

Kafka 消费者 Worker，从 `notifications` topic 消费消息并调用相应渠道发送。

功能：
- 消费 Kafka 消息
- 根据消息中的 channels 路由到对应渠道
- 调用 WebhookChannel/EmailChannel 发送通知
- 记录发送结果到 MNotificationRecord
- 失败重试逻辑
"""

import json
import time
import threading
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import IntEnum

from ginkgo.libs import GLOG
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer
from ginkgo.data.crud import NotificationRecordCRUD
from ginkgo.data.models import MNotificationRecord
from ginkgo.enums import NOTIFICATION_STATUS_TYPES
from ginkgo.notifier.channels.webhook_channel import WebhookChannel
from ginkgo.notifier.channels.email_channel import EmailChannel


class WorkerStatus(IntEnum):
    """Worker 状态"""
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4


class NotificationWorker:
    """
    通知 Kafka Worker

    从 `notifications` topic 消费消息并调用相应渠道发送通知。
    """

    # Kafka topic 名称
    NOTIFICATIONS_TOPIC = "notifications"
    WORKER_GROUP_ID = "notification_worker_group"

    # Worker 配置
    MAX_RETRIES = 3  # 最大重试次数
    RETRY_DELAY = 5  # 重试延迟（秒）
    POLL_TIMEOUT = 1.0  # Kafka 轮询超时（秒）

    def __init__(
        self,
        record_crud: NotificationRecordCRUD,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest"
    ):
        """
        初始化 NotificationWorker

        Args:
            record_crud: NotificationRecordCRUD 实例
            group_id: Consumer group ID（可选，默认为 notification_worker_group）
            auto_offset_reset: Offset 重置策略（earliest/latest）
        """
        self.record_crud = record_crud
        self._group_id = group_id or self.WORKER_GROUP_ID
        self._auto_offset_reset = auto_offset_reset

        # Worker 状态
        self._status = WorkerStatus.STOPPED
        self._worker_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._consumer: Optional[GinkgoConsumer] = None

        # 统计信息
        self._stats = {
            "messages_consumed": 0,
            "messages_sent": 0,
            "messages_failed": 0,
            "messages_retried": 0,
            "start_time": None,
            "last_message_time": None
        }

        # 锁保护状态和统计
        self._lock = threading.Lock()

    @property
    def status(self) -> WorkerStatus:
        """获取 Worker 状态"""
        return self._status

    @property
    def is_running(self) -> bool:
        """Worker 是否正在运行"""
        return self._status == WorkerStatus.RUNNING

    @property
    def stats(self) -> Dict[str, Any]:
        """获取统计信息（线程安全）"""
        with self._lock:
            stats_copy = self._stats.copy()
            if stats_copy["start_time"]:
                stats_copy["uptime_seconds"] = (datetime.now() - stats_copy["start_time"]).total_seconds()
            return stats_copy

    def start(self) -> bool:
        """
        启动 Worker

        Returns:
            bool: 是否成功启动
        """
        with self._lock:
            if self._status != WorkerStatus.STOPPED:
                GLOG.WARN(f"Worker already running or starting, status: {self._status}")
                return False

            self._status = WorkerStatus.STARTING
            self._stop_event.clear()

        try:
            # 创建 Kafka Consumer
            self._consumer = GinkgoConsumer(
                topic=self.NOTIFICATIONS_TOPIC,
                group_id=self._group_id,
                offset=self._auto_offset_reset
            )

            # 启动 Worker 线程
            self._worker_thread = threading.Thread(
                target=self._run,
                name="NotificationWorker",
                daemon=True
            )
            self._worker_thread.start()

            with self._lock:
                self._status = WorkerStatus.RUNNING
                self._stats["start_time"] = datetime.now()

            GLOG.INFO(f"NotificationWorker started (group_id: {self._group_id})")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to start NotificationWorker: {e}")
            with self._lock:
                self._status = WorkerStatus.ERROR
            return False

    def stop(self, timeout: float = 30.0) -> bool:
        """
        停止 Worker

        Args:
            timeout: 等待 Worker 线程结束的超时时间（秒）

        Returns:
            bool: 是否成功停止
        """
        with self._lock:
            if self._status != WorkerStatus.RUNNING:
                GLOG.WARN(f"Worker not running, status: {self._status}")
                return False

            self._status = WorkerStatus.STOPPING

        # 发送停止信号
        self._stop_event.set()

        # 等待 Worker 线程结束
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                GLOG.WARN("Worker did not stop within timeout")
                self._status = WorkerStatus.ERROR
                return False
            else:
                self._status = WorkerStatus.STOPPED
                GLOG.INFO("NotificationWorker stopped")
                return True

    def _run(self):
        """
        Worker 主循环

        在独立线程中运行，持续消费 Kafka 消息并处理。
        """
        GLOG.INFO("NotificationWorker thread started")

        try:
            while not self._stop_event.is_set():
                try:
                    # 从 Kafka 拉取消息
                    messages = self._consumer.consumer.poll(
                        timeout_ms=int(self.POLL_TIMEOUT * 1000),
                        max_records=1
                    )

                    if not messages:
                        continue

                    # 处理消息
                    for topic_partition, records in messages.items():
                        for record in records:
                            if self._stop_event.is_set():
                                break

                            try:
                                self._process_message(record.value)
                                self._consumer.commit()

                                with self._lock:
                                    self._stats["messages_consumed"] += 1
                                    self._stats["last_message_time"] = datetime.now()

                            except Exception as e:
                                GLOG.ERROR(f"Error processing message: {e}")
                                # 不 commit offset，让 Kafka 重试
                                with self._lock:
                                    self._stats["messages_retried"] += 1

                except Exception as e:
                    GLOG.ERROR(f"Error in worker loop: {e}")
                    time.sleep(1)  # 避免紧密循环

        finally:
            # 清理资源
            if self._consumer:
                try:
                    self._consumer.consumer.close()
                except Exception as e:
                    GLOG.ERROR(f"Error closing consumer: {e}")

            with self._lock:
                if self._status == WorkerStatus.RUNNING:
                    self._status = WorkerStatus.STOPPED

            GLOG.INFO("NotificationWorker thread stopped")

    def _process_message(self, message: Dict[str, Any]) -> bool:
        """
        处理单条消息

        Args:
            message: Kafka 消息（已反序列化）

        Returns:
            bool: 是否成功处理
        """
        try:
            # 解析消息
            message_id = message.get("message_id")
            content = message.get("content")
            channels = message.get("channels", [])
            metadata = message.get("metadata", {})
            kwargs = message.get("kwargs", {})

            if not content or not channels:
                GLOG.WARN(f"Invalid message: {message_id}, missing content or channels")
                return False

            user_uuid = metadata.get("user_uuid")
            title = metadata.get("title")

            GLOG.DEBUG(f"Processing message {message_id} for channels: {channels}")

            # 发送到各个渠道
            channel_results: Dict[str, Any] = {}
            success_count = 0

            for channel_name in channels:
                try:
                    result = self._send_to_channel(
                        channel_name=channel_name,
                        content=content,
                        user_uuid=user_uuid,
                        title=title,
                        **kwargs
                    )

                    channel_results[channel_name] = result.to_dict()

                    if result.success:
                        success_count += 1
                        GLOG.DEBUG(f"Sent to {channel_name} successfully: {message_id}")
                    else:
                        GLOG.WARN(f"Failed to send to {channel_name}: {result.error}")

                except Exception as e:
                    error_msg = f"Channel error: {str(e)}"
                    channel_results[channel_name] = {
                        "success": False,
                        "error": error_msg
                    }
                    GLOG.ERROR(f"Error sending to {channel_name}: {e}")

            # 更新通知记录状态
            self._update_record_status(
                message_id=message_id,
                channel_results=channel_results,
                success_count=success_count,
                total_channels=len(channels)
            )

            # 更新统计
            with self._lock:
                if success_count == len(channels):
                    self._stats["messages_sent"] += 1
                elif success_count == 0:
                    self._stats["messages_failed"] += 1

            return success_count > 0

        except Exception as e:
            GLOG.ERROR(f"Error processing message: {e}")
            return False

    def _send_to_channel(
        self,
        channel_name: str,
        content: str,
        user_uuid: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> 'ChannelResult':
        """
        发送到指定渠道

        Args:
            channel_name: 渠道名称（webhook/email）
            content: 消息内容
            user_uuid: 用户 UUID（用于获取联系方式）
            title: 消息标题
            **kwargs: 其他参数

        Returns:
            ChannelResult: 发送结果
        """
        # 导入 ChannelResult 避免循环导入
        from ginkgo.notifier.channels.base_channel import ChannelResult

        if channel_name in ("webhook", "discord"):
            return self._send_webhook(content, user_uuid, title, **kwargs)
        elif channel_name == "email":
            return self._send_email(content, user_uuid, title, **kwargs)
        else:
            return ChannelResult(
                success=False,
                error=f"Unknown channel: {channel_name}"
            )

    def _send_webhook(
        self,
        content: str,
        user_uuid: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> 'ChannelResult':
        """
        发送到 Webhook 渠道

        Args:
            content: 消息内容
            user_uuid: 用户 UUID（用于获取 webhook URL）
            title: 消息标题
            **kwargs: 其他参数（color, fields, footer 等）

        Returns:
            ChannelResult: 发送结果
        """
        # 如果提供了 user_uuid，需要从数据库获取 webhook URL
        # 这里暂时简化处理，假设 kwargs 中有 webhook_url
        webhook_url = kwargs.get("webhook_url")

        if not webhook_url:
            return ChannelResult(
                success=False,
                error="Webhook URL not provided"
            )

        channel = WebhookChannel(webhook_url=webhook_url)

        return channel.send(
            content=content,
            title=title,
            **kwargs
        )

    def _send_email(
        self,
        content: str,
        user_uuid: Optional[str] = None,
        title: Optional[str] = None,
        **kwargs
    ) -> 'ChannelResult':
        """
        发送到 Email 渠道

        Args:
            content: 消息内容
            user_uuid: 用户 UUID（用于获取邮箱地址）
            title: 消息标题
            **kwargs: 其他参数（html, to, cc 等）

        Returns:
            ChannelResult: 发送结果
        """
        # 从 kwargs 获取邮箱地址和其他参数
        to = kwargs.pop("to", None)
        html = kwargs.pop("html", False)

        if not to:
            return ChannelResult(
                success=False,
                error="Email 'to' address not provided"
            )

        channel = EmailChannel()

        return channel.send(
            content=content,
            title=title or "Notification",
            to=to,
            html=html,
            **kwargs
        )

    def _update_record_status(
        self,
        message_id: str,
        channel_results: Dict[str, Any],
        success_count: int,
        total_channels: int
    ):
        """
        更新通知记录状态

        Args:
            message_id: 消息 ID
            channel_results: 渠道发送结果
            success_count: 成功数量
            total_channels: 总渠道数量
        """
        try:
            # 根据 channel_results 更新状态
            if success_count == total_channels:
                status = NOTIFICATION_STATUS_TYPES.SENT.value
            elif success_count == 0:
                status = NOTIFICATION_STATUS_TYPES.FAILED.value
            else:
                status = NOTIFICATION_STATUS_TYPES.SENT.value  # 部分成功也标记为已发送

            # 更新数据库记录
            self.record_crud.update_status(
                message_id=message_id,
                status=status,
                channel_results=channel_results
            )

        except Exception as e:
            GLOG.ERROR(f"Error updating record status for {message_id}: {e}")

    def get_health_status(self) -> Dict[str, Any]:
        """
        获取 Worker 健康状态

        Returns:
            Dict: 健康状态信息
        """
        stats = self.stats

        return {
            "status": self._status.name,
            "group_id": self._group_id,
            "topic": self.NOTIFICATIONS_TOPIC,
            "is_running": self.is_running,
            "messages_consumed": stats["messages_consumed"],
            "messages_sent": stats["messages_sent"],
            "messages_failed": stats["messages_failed"],
            "messages_retried": stats["messages_retried"],
            "uptime_seconds": stats.get("uptime_seconds", 0),
            "last_message_time": stats["last_message_time"].isoformat() if stats.get("last_message_time") else None
        }


# ============================================================================
# 便捷函数
# ============================================================================

def create_notification_worker(
    record_crud: NotificationRecordCRUD,
    group_id: Optional[str] = None
) -> NotificationWorker:
    """
    创建 NotificationWorker 实例（便捷函数）

    Args:
        record_crud: NotificationRecordCRUD 实例
        group_id: Consumer group ID（可选）

    Returns:
        NotificationWorker: Worker 实例

    Examples:
        >>> from ginkgo.data.crud import NotificationRecordCRUD
        >>> from ginkgo.notifier.workers.notification_worker import create_notification_worker
        >>>
        >>> record_crud = NotificationRecordCRUD()
        >>> worker = create_notification_worker(record_crud)
        >>>
        >>> if worker.start():
        ...     print("Worker started successfully")
    """
    return NotificationWorker(
        record_crud=record_crud,
        group_id=group_id
    )
