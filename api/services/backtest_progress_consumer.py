"""
Backtest Progress Consumer

消费回测进度消息并更新数据库和Redis缓存
"""

import asyncio
import json
from typing import Optional, Dict, Any
from datetime import datetime

from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer
from ginkgo.interfaces.kafka_topics import KafkaTopics
from core.logging import logger
from core.database import get_db_cursor
from core.redis_client import set_backtest_progress, delete_backtest_progress


# 在线程池中执行消费者初始化的函数
def _create_consumer_sync(topic: str, group_id: str, offset: str):
    """同步创建 Kafka Consumer（在线程池中运行）"""
    return GinkgoConsumer(topic=topic, group_id=group_id, offset=offset)


# 在线程池中执行 poll 的函数
def _poll_sync(consumer) -> Optional[Dict[Any, Any]]:
    """同步执行 poll（在线程池中运行）"""
    if consumer and hasattr(consumer, 'consumer'):
        return consumer.consumer.poll(timeout_ms=100)
    return None


class BacktestProgressConsumer:
    """回测进度消费者"""

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
            logger.warning("BacktestProgressConsumer already running")
            return

        self._running = True
        self._loop = asyncio.get_event_loop()

        # 启动消费任务（消费者初始化在消费循环中进行）
        self._task = asyncio.create_task(self._consume_messages())

        logger.info("BacktestProgressConsumer started")

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

        logger.info("BacktestProgressConsumer stopped")

    async def _consume_messages(self):
        """消费消息"""
        while self._running:
            try:
                # 如果消费者未初始化，尝试初始化
                if not self._initialized:
                    await self._init_consumer_async()
                    await asyncio.sleep(0.1)
                    continue

                # 如果消费者未连接，尝试重连
                if self.consumer is None or not self.consumer.is_connected:
                    await self._init_consumer_async()
                    await asyncio.sleep(1)
                    continue

                # 使用 run_in_executor 在线程池中执行 poll，避免阻塞事件循环
                messages = await self._loop.run_in_executor(
                    None,  # 使用默认线程池
                    _poll_sync,
                    self.consumer
                )

                if not messages:
                    # 没有消息，继续下一轮
                    await asyncio.sleep(self._poll_interval)
                    continue

                # 处理消息 {TopicPartition: [ConsumerRecord]}
                for tp, records in messages.items():
                    for message in records:
                        # message.value 已经反序列化，直接是 dict
                        await self._process_message(message.value)

            except asyncio.CancelledError:
                # 任务被取消，正常退出
                break
            except Exception as e:
                if self._running:
                    logger.error(f"Error consuming progress message: {e}")
                await asyncio.sleep(1)

    async def _init_consumer_async(self):
        """异步初始化消费者（在线程池中执行，不阻塞事件循环）"""
        try:
            # 使用 run_in_executor 在线程池中执行同步操作
            self.consumer = await self._loop.run_in_executor(
                None,  # 使用默认线程池
                _create_consumer_sync,
                KafkaTopics.BACKTEST_PROGRESS,
                "api-server",
                "earliest"
            )
            self._initialized = True

            if self.consumer and self.consumer.is_connected:
                logger.info("Kafka Consumer for backtest progress connected successfully")
            else:
                logger.warning("Kafka Consumer not connected, will retry in consumption loop")

        except Exception as e:
            logger.warning(f"Kafka Consumer initialization failed: {e}, will retry later")
            self.consumer = None
            self._initialized = True  # 标记为已尝试初始化

    async def _process_message(self, message_value: dict):
        """处理进度消息"""
        try:
            message_type = message_value.get("type")
            task_uuid = message_value.get("task_uuid")

            if not task_uuid:
                return

            if message_type == "progress":
                await self._update_progress(
                    task_uuid=task_uuid,
                    progress=message_value.get("progress", 0.0),
                    current_date=message_value.get("current_date"),
                    state=message_value.get("state"),
                )
            elif message_type == "stage":
                await self._update_stage(
                    task_uuid=task_uuid,
                    stage=message_value.get("stage"),
                    message=message_value.get("message"),
                )
            elif message_type == "completed":
                await self._update_completed(
                    task_uuid=task_uuid,
                    result=message_value.get("result"),
                )
            elif message_type == "failed":
                await self._update_failed(
                    task_uuid=task_uuid,
                    error=message_value.get("error"),
                )
            elif message_type == "cancelled":
                await self._update_cancelled(task_uuid)

        except Exception as e:
            logger.error(f"Error processing progress message: {e}")

    async def _update_progress(self, task_uuid: str, progress: float, current_date: Optional[str], state: Optional[str]):
        """更新进度"""
        async with get_db_cursor() as db:
            try:
                # 同时更新state（如果提供了）
                if state:
                    query = """
                        UPDATE backtest_tasks
                        SET progress = %s, state = %s
                        WHERE uuid = %s
                    """
                    await db.execute(query, [progress, state, task_uuid])
                else:
                    query = """
                        UPDATE backtest_tasks
                        SET progress = %s
                        WHERE uuid = %s
                    """
                    await db.execute(query, [progress, task_uuid])

                logger.debug(f"Updated progress for {task_uuid[:8]}: {progress:.1f}%")

                # 写入 Redis（TTL 60秒）
                progress_data = {
                    "progress": progress,
                    "state": state,
                    "current_date": current_date,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await set_backtest_progress(task_uuid, progress_data, ttl=60)

            except Exception as e:
                logger.error(f"Failed to update progress for {task_uuid[:8]}: {e}")

    async def _update_stage(self, task_uuid: str, stage: str, message: Optional[str]):
        """更新阶段"""
        try:
            # 可以记录到日志或单独的阶段表
            logger.info(f"[{task_uuid[:8]}] Stage: {stage} - {message}")
        except Exception as e:
            logger.error(f"Failed to update stage for {task_uuid[:8]}: {e}")

    async def _update_completed(self, task_uuid: str, result: Optional[dict]):
        """更新完成状态"""
        async with get_db_cursor() as db:
            try:
                query = """
                    UPDATE backtest_tasks
                    SET state = %s, progress = 100.0, completed_at = %s, result = %s
                    WHERE uuid = %s
                """
                await db.execute(query, [
                    "COMPLETED",
                    datetime.utcnow(),
                    json.dumps(result) if result else None,
                    task_uuid
                ])

                logger.info(f"[{task_uuid[:8]}] Marked as completed")

                # 写入 Redis（TTL 60秒）
                progress_data = {
                    "progress": 100.0,
                    "state": "COMPLETED",
                    "result": result,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await set_backtest_progress(task_uuid, progress_data, ttl=60)

            except Exception as e:
                logger.error(f"Failed to update completed for {task_uuid[:8]}: {e}")

    async def _update_failed(self, task_uuid: str, error: Optional[str]):
        """更新失败状态"""
        async with get_db_cursor() as db:
            try:
                query = """
                    UPDATE backtest_tasks
                    SET state = %s, completed_at = %s, error = %s
                    WHERE uuid = %s
                """
                await db.execute(query, ["FAILED", datetime.utcnow(), error, task_uuid])

                logger.error(f"[{task_uuid[:8]}] Marked as failed: {error}")

                # 写入 Redis（TTL 60秒）
                progress_data = {
                    "progress": 0.0,
                    "state": "FAILED",
                    "error": error,
                    "updated_at": datetime.utcnow().isoformat()
                }
                await set_backtest_progress(task_uuid, progress_data, ttl=60)

            except Exception as e:
                logger.error(f"Failed to update failed for {task_uuid[:8]}: {e}")

    async def _update_cancelled(self, task_uuid: str):
        """更新取消状态"""
        async with get_db_cursor() as db:
            try:
                query = """
                    UPDATE backtest_tasks
                    SET state = %s, completed_at = %s
                    WHERE uuid = %s
                """
                await db.execute(query, ["CANCELLED", datetime.utcnow(), task_uuid])

                logger.info(f"[{task_uuid[:8]}] Marked as cancelled")

                # 写入 Redis（TTL 60秒）
                progress_data = {
                    "progress": 0.0,
                    "state": "CANCELLED",
                    "updated_at": datetime.utcnow().isoformat()
                }
                await set_backtest_progress(task_uuid, progress_data, ttl=60)

            except Exception as e:
                logger.error(f"Failed to update cancelled for {task_uuid[:8]}: {e}")


# 全局消费者实例
_progress_consumer: Optional[BacktestProgressConsumer] = None


def get_progress_consumer() -> BacktestProgressConsumer:
    """获取进度消费者（单例）"""
    global _progress_consumer
    if _progress_consumer is None:
        _progress_consumer = BacktestProgressConsumer()
    return _progress_consumer
