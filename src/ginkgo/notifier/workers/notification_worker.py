# Upstream: Kafka Consumer, NotificationService
# Downstream: NotificationService (业务逻辑层)
# Role: NotificationWorker Kafka消费者Worker解析消息并调用NotificationService业务方法


"""
Notification Kafka Worker

Kafka 消费者 Worker，从 `notifications` topic 消费消息并调用 NotificationService。

设计原则：
- Worker 只负责解析消息和路由到 NotificationService
- 所有业务逻辑（查找联系方式、模板渲染、渠道发送）由 NotificationService 处理
- 支持 user_uuid 和 group_name 参数，自动查找联系方式
- 支持多种消息类型（simple, template, trading_signal, system_notification）

功能：
- 消费 Kafka 消息
- 根据 message_type 调用对应的 NotificationService 方法
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
from ginkgo.interfaces.kafka_topics import KafkaTopics


class WorkerStatus(IntEnum):
    """Worker 状态"""
    STOPPED = 0
    STARTING = 1
    RUNNING = 2
    STOPPING = 3
    ERROR = 4


class MessageType(IntEnum):
    """消息类型"""
    SIMPLE = 1              # 简单消息（content + channels）
    TEMPLATE = 2            # 模板消息（template_id + context）
    TRADING_SIGNAL = 3      # 交易信号
    SYSTEM_NOTIFICATION = 4 # 系统通知
    CUSTOM_FIELDS = 5       # 自定义字段消息（支持 Discord fields）


class NotificationWorker:
    """
    通知 Kafka Worker

    从 `ginkgo.notifications` topic 消费消息并调用 NotificationService。
    """

    # Kafka topic 名称
    NOTIFICATIONS_TOPIC = KafkaTopics.NOTIFICATIONS
    WORKER_GROUP_ID = "notification_worker_group"

    # Worker 配置
    POLL_TIMEOUT = 1.0  # Kafka 轮询超时（秒）

    def __init__(
        self,
        notification_service,
        record_crud: NotificationRecordCRUD,
        group_id: Optional[str] = None,
        auto_offset_reset: str = "earliest"
    ):
        """
        初始化 NotificationWorker

        Args:
            notification_service: NotificationService 实例
            record_crud: NotificationRecordCRUD 实例
            group_id: Consumer group ID（可选，默认为 notification_worker_group）
            auto_offset_reset: Offset 重置策略（earliest/latest）
        """
        self.notification_service = notification_service
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
                print(f"[WARN] Worker already running or starting, status: {self._status}")
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

            # 检查 Kafka 连接状态
            if not self._consumer.is_connected:
                print(f"[ERROR] Failed to connect to Kafka for topic '{self.NOTIFICATIONS_TOPIC}'")
                with self._lock:
                    self._status = WorkerStatus.ERROR
                return False

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

            print(f"NotificationWorker started (group_id: {self._group_id})")
            return True

        except Exception as e:
            print(f"[ERROR] Failed to start NotificationWorker: {e}")
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
                print(f"[WARN] Worker not running, status: {self._status}")
                return False

            self._status = WorkerStatus.STOPPING

        # 发送停止信号
        self._stop_event.set()

        # 等待 Worker 线程结束
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

        # 关闭 Kafka Consumer
        if self._consumer:
            try:
                self._consumer.close()
            except Exception as e:
                print(f"[ERROR] Error closing Kafka Consumer: {e}")

        with self._lock:
            if self._worker_thread and self._worker_thread.is_alive():
                print("[WARN] Worker did not stop within timeout")
                self._status = WorkerStatus.ERROR
                return False
            else:
                self._status = WorkerStatus.STOPPED
                print("NotificationWorker stopped")
                return True

    def _run(self):
        """
        Worker 主循环

        在独立线程中运行，持续消费 Kafka 消息并处理。
        """
        print("NotificationWorker thread started")

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
                                success = self._process_message(record.value)

                                if success:
                                    self._consumer.commit()

                                    with self._lock:
                                        self._stats["messages_consumed"] += 1
                                        self._stats["messages_sent"] += 1
                                        self._stats["last_message_time"] = datetime.now()
                                else:
                                    with self._lock:
                                        self._stats["messages_consumed"] += 1
                                        self._stats["messages_failed"] += 1

                            except Exception as e:
                                print(f"[ERROR] Error processing message: {e}")
                                # 不 commit offset，让 Kafka 重试
                                with self._lock:
                                    self._stats["messages_retried"] += 1

                except Exception as e:
                    print(f"[ERROR] Error in worker loop: {e}")
                    time.sleep(1)  # 避免紧密循环

        finally:
            # 清理资源
            if self._consumer:
                try:
                    self._consumer.close()
                except Exception as e:
                    print(f"[ERROR] Error closing consumer: {e}")

            with self._lock:
                if self._status == WorkerStatus.RUNNING:
                    self._status = WorkerStatus.STOPPED

            print("NotificationWorker thread stopped")

    def _process_message(self, message: Dict[str, Any]) -> bool:
        """
        处理单条消息

        根据 message_type 调用对应的 NotificationService 方法。

        Args:
            message: Kafka 消息（已反序列化）

        Returns:
            bool: 是否成功处理
        """
        try:
            # 解析消息
            message_type = message.get("message_type")
            message_id = message.get("message_id")

            if not message_type:
                print(f"[WARN] Missing message_type in {message_id}")
                return False

            print(f"[DEBUG] Processing {message_type} message: {message_id}")

            # 根据 message_type 路由到对应的处理方法
            if message_type == "simple":
                return self._process_simple_message(message)
            elif message_type == "template":
                return self._process_template_message(message)
            elif message_type == "trading_signal":
                return self._process_trading_signal_message(message)
            elif message_type == "system_notification":
                return self._process_system_notification_message(message)
            elif message_type == "custom_fields":
                return self._process_custom_fields_message(message)
            else:
                print(f"[WARN] Unknown message_type: {message_type}")
                return False

        except Exception as e:
            print(f"[ERROR] Error processing message: {e}")
            return False

    def _process_simple_message(self, message: Dict[str, Any]) -> bool:
        """
        处理简单消息

        消息格式：
        {
            "message_type": "simple",
            "user_uuid": "user-123" | "group_name": "traders" | "group_uuid": "group-456",
            "content": "通知内容",
            "title": "标题",
            "channels": ["webhook", "email"]  // 可选，覆盖自动查找
        }

        Args:
            message: Kafka 消息

        Returns:
            bool: 是否成功处理
        """
        user_uuid = message.get("user_uuid")
        group_name = message.get("group_name")
        group_uuid = message.get("group_uuid")
        content = message.get("content")
        title = message.get("title")
        channels = message.get("channels")  # 可选，覆盖自动查找
        priority = message.get("priority", 1)

        if not content:
            print("[ERROR] Simple message missing content")
            return False

        # 调用 NotificationService
        if user_uuid:
            result = self.notification_service.send_to_user(
                user_uuid=user_uuid,
                content=content,
                title=title,
                channels=channels,
                priority=priority
            )
        elif group_name:
            result = self.notification_service.send_to_group(
                group_name=group_name,
                content=content,
                title=title,
                channels=channels,
                priority=priority
            )
        elif group_uuid:
            # 需要先查找 group_name
            result = self.notification_service.send_to_group(
                group_uuid=group_uuid,
                content=content,
                title=title,
                channels=channels,
                priority=priority
            )
        else:
            print("[ERROR] Simple message missing user_uuid/group_name/group_uuid")
            return False

        return result.success

    def _process_template_message(self, message: Dict[str, Any]) -> bool:
        """
        处理模板消息

        消息格式：
        {
            "message_type": "template",
            "user_uuid": "user-123" | "group_name": "traders",
            "template_id": "trading_signal",
            "context": {"symbol": "AAPL", "price": 150.0},
            "priority": 1
        }

        Args:
            message: Kafka 消息

        Returns:
            bool: 是否成功处理
        """
        user_uuid = message.get("user_uuid")
        group_name = message.get("group_name")
        group_uuid = message.get("group_uuid")
        template_id = message.get("template_id")
        context = message.get("context", {})
        priority = message.get("priority", 1)

        if not template_id:
            print("[ERROR] Template message missing template_id")
            return False

        # 调用 NotificationService
        if user_uuid:
            result = self.notification_service.send_template_to_user(
                user_uuid=user_uuid,
                template_id=template_id,
                context=context,
                priority=priority
            )
        elif group_name:
            result = self.notification_service.send_template_to_group(
                group_name=group_name,
                template_id=template_id,
                context=context,
                priority=priority
            )
        elif group_uuid:
            result = self.notification_service.send_template_to_group(
                group_uuid=group_uuid,
                template_id=template_id,
                context=context,
                priority=priority
            )
        else:
            print("[ERROR] Template message missing user_uuid/group_name/group_uuid")
            return False

        return result.success

    def _process_trading_signal_message(self, message: Dict[str, Any]) -> bool:
        """
        处理交易信号消息

        消息格式：
        {
            "message_type": "trading_signal",
            "user_uuid": "user-123" | "group_name": "traders",
            "direction": "LONG" | "SHORT",
            "code": "AAPL",
            "price": 150.0,
            "volume": 100,
            "strategy": "策略名称",
            "reason": "突破原因"
        }

        Args:
            message: Kafka 消息

        Returns:
            bool: 是否成功处理
        """
        user_uuid = message.get("user_uuid")
        group_name = message.get("group_name")
        group_uuid = message.get("group_uuid")
        direction = message.get("direction")
        code = message.get("code")
        price = message.get("price")
        volume = message.get("volume")
        strategy = message.get("strategy")
        reason = message.get("reason")

        if not all([direction, code]):
            print("[ERROR] Trading signal message missing required fields")
            return False

        # 调用 NotificationService
        if user_uuid:
            result = self.notification_service.send_trading_signal(
                user_uuid=user_uuid,
                direction=direction,
                code=code,
                price=price,
                volume=volume,
                strategy=strategy,
                reason=reason
            )
        elif group_name:
            result = self.notification_service.send_trading_signal(
                group_name=group_name,
                direction=direction,
                code=code,
                price=price,
                volume=volume,
                strategy=strategy,
                reason=reason
            )
        elif group_uuid:
            result = self.notification_service.send_trading_signal(
                group_uuid=group_uuid,
                direction=direction,
                code=code,
                price=price,
                volume=volume,
                strategy=strategy,
                reason=reason
            )
        else:
            print("[ERROR] Trading signal message missing user_uuid/group_name/group_uuid")
            return False

        return result.success

    def _process_system_notification_message(self, message: Dict[str, Any]) -> bool:
        """
        处理系统通知消息

        消息格式：
        {
            "message_type": "system_notification",
            "user_uuid": "user-123" | "group_name": "admins",
            "content": "系统告警内容",
            "level": "INFO" | "WARNING" | "ERROR"
        }

        Args:
            message: Kafka 消息

        Returns:
            bool: 是否成功处理
        """
        user_uuid = message.get("user_uuid")
        group_name = message.get("group_name")
        group_uuid = message.get("group_uuid")
        content = message.get("content")
        level = message.get("level", "INFO")

        if not content:
            print("[ERROR] System notification message missing content")
            return False

        # 调用 NotificationService
        if user_uuid:
            result = self.notification_service.send_system_notification(
                user_uuid=user_uuid,
                content=content,
                level=level
            )
        elif group_name:
            result = self.notification_service.send_system_notification(
                group_name=group_name,
                content=content,
                level=level
            )
        elif group_uuid:
            result = self.notification_service.send_system_notification(
                group_uuid=group_uuid,
                content=content,
                level=level
            )
        else:
            print("[ERROR] System notification message missing user_uuid/group_name/group_uuid")
            return False

        return result.success

    def _process_custom_fields_message(self, message: Dict[str, Any]) -> bool:
        """
        处理自定义字段消息（支持 Discord fields）

        消息格式：
        {
            "message_type": "custom_fields",
            "group_name": "System",
            "content": "通知内容",
            "title": "标题",
            "level": "INFO",
            "fields": [{"name": "字段名", "value": "字段值", "inline": False}],
            "module": "System"
        }

        Args:
            message: Kafka 消息

        Returns:
            bool: 是否成功处理
        """
        group_name = message.get("group_name", "System")
        group_uuid = message.get("group_uuid")
        content = message.get("content", "")
        title = message.get("title")
        level = message.get("level", "INFO")
        fields = message.get("fields", [])
        module = message.get("module", "System")

        if not content:
            print("[ERROR] Custom fields message missing content")
            return False

        if not fields:
            print("[ERROR] Custom fields message missing fields")
            return False

        # 等级到颜色的映射
        level_colors = {
            "INFO": 3447003,      # 蓝色
            "WARN": 15844367,     # 黄色
            "ERROR": 15158332,    # 红色
            "ALERT": 15158332,    # 红色
            "SUCCESS": 3066993,   # 绿色
        }
        color = level_colors.get(level.upper(), 3447003)

        # 获取组信息
        if group_uuid:
            group = self.notification_service.group_crud.find(
                filters={"uuid": group_uuid}, page_size=1, as_dataframe=False
            )
        elif group_name:
            group = self.notification_service.group_crud.find(
                filters={"name": group_name}, page_size=1, as_dataframe=False
            )
        else:
            print("[ERROR] Custom fields message missing group_name/group_uuid")
            return False

        if not group:
            print(f"[ERROR] Group not found: {group_name or group_uuid}")
            return False

        group_uuid = group[0].uuid
        mappings = self.notification_service.group_mapping_crud.find_by_group(
            group_uuid, as_dataframe=False
        )

        success_count = 0
        for mapping in mappings:
            contacts = self.notification_service.contact_crud.find_by_user_id(
                mapping.user_uuid, as_dataframe=False
            )
            for contact in contacts:
                contact_type_enum = contact.get_contact_type_enum()
                if contact_type_enum and contact_type_enum.name == "WEBHOOK" and contact.is_active:
                    # 直接发送到 Discord webhook
                    from datetime import datetime
                    result = self.notification_service.send_discord_webhook(
                        webhook_url=contact.address,
                        content=content,
                        title=title,
                        color=color,
                        fields=fields,
                        footer={"text": f"{module} • {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"}
                    )
                    if result.is_success:
                        success_count += 1
                    break  # 每个用户只发送一次

        if success_count > 0:
            print(f"[{module}] Custom fields notification sent to {success_count} users")
            return True
        else:
            print(f"[WARN] [{module}] No custom fields notifications sent")
            return False

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
    notification_service,
    record_crud: NotificationRecordCRUD,
    group_id: Optional[str] = None
) -> NotificationWorker:
    """
    创建 NotificationWorker 实例（便捷函数）

    Args:
        notification_service: NotificationService 实例
        record_crud: NotificationRecordCRUD 实例
        group_id: Consumer group ID（可选）

    Returns:
        NotificationWorker: Worker 实例

    Examples:
        >>> from ginkgo.notifier.core.notification_service import NotificationService
        >>> from ginkgo.data.crud import NotificationRecordCRUD
        >>> from ginkgo.notifier.workers.notification_worker import create_notification_worker
        >>>
        >>> # 创建服务
        >>> service = NotificationService(...)
        >>> record_crud = NotificationRecordCRUD()
        >>>
        >>> # 创建 Worker
        >>> worker = create_notification_worker(
        >>>     notification_service=service,
        >>>     record_crud=record_crud
        >>> )
        >>>
        >>> if worker.start():
        >>>     print("Worker started successfully")
    """
    return NotificationWorker(
        notification_service=notification_service,
        record_crud=record_crud,
        group_id=group_id
    )
