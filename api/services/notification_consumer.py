"""Notification Consumer

消费 ginkgo.notifications 并经 WS 推送为前端 toast（ADR-046 全局薄事件通道）。

与 NotificationWorker（独立进程，负责 channels 投递）并行消费同一 topic：
- group_id 必须不同（api-notification-broadcaster），否则同组内互相抢分区
- offset 用 latest：toast 是时效性消息，API 重启不重放历史通知
  （backtest progress consumer 用 earliest 是因为它把状态镜像进 DB，需要补偿）
"""

import asyncio
import json
import uuid
from typing import Optional

from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer
from ginkgo.interfaces.kafka_topics import KafkaTopics
from core.logging import logger
from websocket.events import broadcast_event_to_users

GROUP_ID = "api-notification-broadcaster"


# 在线程池中执行消费者初始化的函数
def _create_consumer_sync(topic: str, group_id: str, offset: str):
    """同步创建 Kafka Consumer（在线程池中运行）"""
    return GinkgoConsumer(topic=topic, group_id=group_id, offset=offset)


# 在线程池中执行 poll 的函数
def _poll_sync(consumer) -> Optional[dict]:
    """同步执行 poll（在线程池中运行）"""
    if consumer and hasattr(consumer, "consumer"):
        return consumer.consumer.poll(timeout_ms=100)
    return None


class NotificationConsumer:
    """通知消费者：Kafka ginkgo.notifications → WS notification 事件"""

    def __init__(self):
        self.consumer: Optional[GinkgoConsumer] = None
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._initialized = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._poll_interval = 1.0  # 轮询间隔（秒）

    async def start(self):
        """启动消费者"""
        if self._running:
            logger.warning("NotificationConsumer already running")
            return

        self._running = True
        self._loop = asyncio.get_event_loop()
        self._task = asyncio.create_task(self._consume_messages())
        logger.info("NotificationConsumer started")

    async def stop(self):
        """停止消费者"""
        self._running = False

        if self.consumer:
            self.consumer.close()

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("NotificationConsumer stopped")

    async def _consume_messages(self):
        """消费消息（结构对齐 BacktestProgressConsumer）"""
        while self._running:
            try:
                if not self._initialized:
                    await self._init_consumer_async()
                    await asyncio.sleep(0.1)
                    continue

                if self.consumer is None or not self.consumer.is_connected:
                    await self._init_consumer_async()
                    await asyncio.sleep(1)
                    continue

                messages = await self._loop.run_in_executor(
                    None, _poll_sync, self.consumer)

                if not messages:
                    await asyncio.sleep(self._poll_interval)
                    continue

                for tp, records in messages.items():
                    for message in records:
                        value = message.value
                        if isinstance(value, str):
                            value = json.loads(value)
                        await self._process_message(value)

            except asyncio.CancelledError:
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error consuming notification message: {e}")
                await asyncio.sleep(1)

    async def _init_consumer_async(self):
        """异步初始化消费者（在线程池中执行，不阻塞事件循环）"""
        try:
            self.consumer = await self._loop.run_in_executor(
                None,
                _create_consumer_sync,
                KafkaTopics.NOTIFICATIONS,
                GROUP_ID,
                "latest",
            )
            self._initialized = True

            if self.consumer and self.consumer.is_connected:
                logger.info("Kafka Consumer for notifications connected successfully")
            else:
                logger.warning("Kafka Consumer for notifications not connected, will retry")

        except Exception as e:
            logger.warning(f"Kafka notification consumer init failed: {e}, will retry later")
            self.consumer = None
            self._initialized = True

    async def _process_message(self, message_value: dict):
        """处理通知消息 → WS 薄事件

        user_uuids 缺失（group-addressed）时 broadcast_to_user 回退全员广播。
        """
        try:
            user_uuids = message_value.get("user_uuids") or (
                [message_value["user_uuid"]] if message_value.get("user_uuid") else []
            )
            await broadcast_event_to_users(
                user_uuids,
                "notification", "notification",
                message_value.get("message_id") or str(uuid.uuid4()),
                data={
                    "title": message_value.get("title"),
                    "content": message_value.get("content"),
                    "level": str(message_value.get("level") or "INFO").lower(),
                    "module": message_value.get("module"),
                    "fields": message_value.get("fields", []),
                },
            )
        except Exception as e:
            logger.error(f"Error processing notification message: {e}")


# 全局消费者实例
_notification_consumer: Optional[NotificationConsumer] = None


def get_notification_consumer() -> NotificationConsumer:
    """获取通知消费者单例"""
    global _notification_consumer
    if _notification_consumer is None:
        _notification_consumer = NotificationConsumer()
    return _notification_consumer
