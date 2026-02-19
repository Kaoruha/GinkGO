"""
BacktestWorker Node

回测Worker主节点（对应ExecutionNode的node.py）

职责：
- 从Kafka接收回测任务分配
- 管理多个BacktestProcessor并发执行（max_backtests=5）
- 上报心跳到Redis（TTL=30s，10s续约）
- 优雅关闭和资源清理
"""

from typing import Dict, Optional
from threading import Thread, RLock, Event
from datetime import datetime
import time
import logging

from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker
from ginkgo.workers.backtest_worker.metrics import BacktestMetrics
from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestTaskState, AnalyzerConfig
from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer, GinkgoProducer
from ginkgo.data.drivers import create_redis_connection
from ginkgo.libs import GCONF


class BacktestWorker:
    """回测Worker节点"""

    def __init__(self, worker_id: str):
        """
        初始化BacktestWorker

        Args:
            worker_id: Worker唯一标识
        """
        self.worker_id = worker_id

        # 任务管理：{task_uuid: BacktestProcessor}
        self.tasks: Dict[str, BacktestProcessor] = {}
        self.task_lock = RLock()

        # Kafka
        self.task_consumer: Optional[GinkgoConsumer] = None
        self.progress_producer: Optional[GinkgoProducer] = None

        # 进度跟踪和指标
        self.progress_tracker: Optional[ProgressTracker] = None
        self.metrics = BacktestMetrics()

        # 运行状态
        self.is_running = False
        self.should_stop = False

        # 线程
        self.task_consumer_thread: Optional[Thread] = None
        self.heartbeat_thread: Optional[Thread] = None
        self.cleanup_thread: Optional[Thread] = None

        # 心跳配置
        self.heartbeat_interval = 10  # 10秒发送一次心跳
        self.heartbeat_ttl = 30  # 心跳TTL 30秒

        # 节点配置
        self.max_backtests = 5  # 最大并发任务数（对应ExecutionNode的max_portfolios）
        self.started_at: Optional[str] = None

        # Redis客户端
        self._redis = None

        # 任务容量控制：用于阻塞等待空闲槽位
        self._slot_available = Event()
        self._slot_available.set()  # 初始时有空闲槽位

    def start(self):
        """启动BacktestWorker"""
        if self.is_running:
            raise RuntimeError(f"BacktestWorker {self.worker_id} is already running")

        # 检查worker_id是否已被使用
        if self._is_worker_id_in_use():
            raise RuntimeError(f"Worker {self.worker_id} is already in use")

        self.should_stop = False
        self.is_running = True
        self.started_at = datetime.now().isoformat()

        print(f"Starting BacktestWorker {self.worker_id}")

        # 清理旧数据
        self._cleanup_old_heartbeat_data()

        # 获取任务服务（用于写入进度到数据库）
        from ginkgo import services
        task_service = services.data.backtest_task_service()

        # 初始化Kafka Producer（进度上报）
        self.progress_producer = GinkgoProducer()
        self.progress_tracker = ProgressTracker(
            self.worker_id, self.progress_producer, task_service
        )

        # 发送初始心跳
        self._send_heartbeat()

        # 启动心跳线程
        self._start_heartbeat_thread()

        # 启动任务消费线程
        self._start_task_consumer_thread()

        # 启动清理线程
        self._start_cleanup_thread()

        print(f"BacktestWorker {self.worker_id} started")
        print(f"Max concurrent backtests: {self.max_backtests}")
        print(f"Ready to receive tasks from Kafka")

    def stop(self):
        """停止BacktestWorker（优雅关闭）"""
        if not self.is_running:
            print(f"BacktestWorker {self.worker_id} is not running")
            return

        print(f"Stopping BacktestWorker {self.worker_id}")

        # 设置停止标志
        self.should_stop = True
        self.is_running = False

        # 1. 关闭Kafka Consumer
        if self.task_consumer:
            self.task_consumer.close()
            print("Task consumer closed")

        # 2. 等待任务完成或取消
        with self.task_lock:
            if self.tasks:
                print(f"Waiting for {len(self.tasks)} tasks to complete...")
                wait_start = time.time()
                while time.time() - wait_start < 10:  # 最多等10秒
                    for task_uuid, processor in list(self.tasks.items()):
                        if not processor.is_alive():
                            self._remove_task(task_uuid)
                    if not self.tasks:
                        break
                    time.sleep(0.5)

                # 还有未完成的任务，强制取消
                if self.tasks:
                    print(f"Cancelling {len(self.tasks)} remaining tasks...")
                    for processor in self.tasks.values():
                        processor.cancel()

        # 3. 等待线程退出
        for thread in [self.task_consumer_thread, self.heartbeat_thread, self.cleanup_thread]:
            if thread and thread.is_alive():
                thread.join(timeout=5)

        # 4. 清理Redis心跳
        self._clear_heartbeat()

        # 5. 关闭Producer
        if self.progress_producer:
            self.progress_producer.close()

        print(f"BacktestWorker {self.worker_id} stopped")

    def _start_task_consumer_thread(self):
        """启动任务消费线程"""
        if self.task_consumer_thread and self.task_consumer_thread.is_alive():
            return

        def consume_tasks():
            print("Task consumer thread started")
            # 使用独特的 consumer group ID 避免与其他实例冲突
            unique_group_id = f"backtest-workers-{self.worker_id}"
            self.task_consumer = GinkgoConsumer(
                topic="backtest.assignments",
                group_id=unique_group_id,
                offset="earliest",
            )

            while not self.should_stop:
                try:
                    # GinkgoConsumer.consumer 是底层的 KafkaConsumer
                    messages = self.task_consumer.consumer.poll(timeout_ms=1000)

                    if not messages:
                        continue

                    # 处理消息 {TopicPartition: [ConsumerRecord]}
                    for tp, records in messages.items():
                        for message in records:
                            # GinkgoConsumer 已反序列化，message.value 直接是 dict
                            assignment = message.value
                            self._handle_task_assignment(assignment)

                except Exception as e:
                    if not self.should_stop:
                        print(f"Error consuming task: {e}")

        self.task_consumer_thread = Thread(target=consume_tasks, daemon=True)
        self.task_consumer_thread.start()

    def _handle_task_assignment(self, assignment: dict):
        """处理任务分配"""
        task_uuid = assignment.get("task_uuid")
        command = assignment.get("command", "start")

        if command == "start":
            self._start_task(assignment)
        elif command == "cancel":
            self._cancel_task(task_uuid)

    def _start_task(self, assignment: dict):
        """启动新任务（阻塞等待空闲槽位）"""
        task_uuid = assignment.get("task_uuid", "unknown")[:8]

        # 阻塞等待空闲槽位
        while not self._can_accept_task():
            print(f"[{task_uuid}] Worker at full capacity, waiting for slot...")
            # 清除标志，等待任务完成时被设置
            self._slot_available.clear()
            # 等待最多 60 秒，每隔 1 秒检查一次是否应该停止
            for _ in range(60):
                if self.should_stop:
                    print(f"[{task_uuid}] Worker stopping, discarding task")
                    return
                if self._slot_available.wait(timeout=1):
                    break
            else:
                # 60秒后仍然没有槽位，继续等待
                continue

            # 被唤醒后再次检查容量
            if self._can_accept_task():
                print(f"[{task_uuid}] Slot available, proceeding with task")
                break

        # 解析任务配置
        from ginkgo.workers.backtest_worker.models import BacktestConfig

        config_dict = assignment.get("config", {})

        # 转换 analyzers 配置
        analyzers = []
        if "analyzers" in config_dict:
            for analyzer_dict in config_dict["analyzers"]:
                analyzers.append(AnalyzerConfig(**analyzer_dict))

        # 创建 BacktestConfig（包含 analyzers）
        config = BacktestConfig(
            start_date=config_dict.get("start_date"),
            end_date=config_dict.get("end_date"),
            initial_cash=config_dict.get("initial_cash", 100000.0),
            commission_rate=config_dict.get("commission_rate", 0.0003),
            slippage_rate=config_dict.get("slippage_rate", 0.0001),
            benchmark_return=config_dict.get("benchmark_return", 0.0),
            max_position_ratio=config_dict.get("max_position_ratio", 0.3),
            stop_loss_ratio=config_dict.get("stop_loss_ratio", 0.05),
            take_profit_ratio=config_dict.get("take_profit_ratio", 0.15),
            frequency=config_dict.get("frequency", "DAY"),
            analyzers=analyzers,  # Engine 级别的分析器
        )

        task = BacktestTask(
            task_uuid=assignment["task_uuid"],
            portfolio_uuid=assignment["portfolio_uuid"],
            name=assignment["name"],
            config=config,
            state=BacktestTaskState.PENDING,
        )

        print(f"Starting task {task.task_uuid[:8]}: {task.name}")
        if analyzers:
            print(f"  with {len(analyzers)} analyzers: {[a.name for a in analyzers]}")

        # 创建Processor
        processor = BacktestProcessor(task, self.worker_id, self.progress_tracker)

        with self.task_lock:
            self.tasks[task.task_uuid] = processor

        self.metrics.record_task_start(task.task_uuid, task.name)

        # 启动线程
        processor.start()

    def _cancel_task(self, task_uuid: str):
        """取消任务"""
        with self.task_lock:
            if task_uuid not in self.tasks:
                print(f"Task {task_uuid[:8]} not found")
                return

            processor = self.tasks[task_uuid]
            processor.cancel()
            self.metrics.record_task_cancelled(task_uuid)
            print(f"Task {task_uuid[:8]} cancelled")

    def _remove_task(self, task_uuid: str):
        """移除已完成的任务"""
        with self.task_lock:
            if task_uuid in self.tasks:
                processor = self.tasks[task_uuid]
                success = processor.task.state != BacktestTaskState.FAILED
                self.metrics.record_task_complete(task_uuid, success)
                del self.tasks[task_uuid]
                # 通知等待的线程有新槽位可用
                self._slot_available.set()

    def _can_accept_task(self) -> bool:
        """检查是否还能接受任务"""
        with self.task_lock:
            return len(self.tasks) < self.max_backtests

    def _start_cleanup_thread(self):
        """启动清理线程"""
        def cleanup():
            while not self.should_stop:
                try:
                    time.sleep(1)
                    # 收集已完成的任务（不持有锁太久）
                    completed_uuids = []
                    with self.task_lock:
                        for uuid, p in list(self.tasks.items()):
                            if not p.is_alive():
                                completed_uuids.append(uuid)

                    # 移除已完成的任务（_remove_task 会自己获取锁）
                    for uuid in completed_uuids:
                        print(f"[Cleanup] Task {uuid[:8]} thread exited, removing...")
                        self._remove_task(uuid)
                        print(f"[Cleanup] Task {uuid[:8]} removed, slot available")
                except Exception as e:
                    print(f"Error in cleanup: {e}")

        self.cleanup_thread = Thread(target=cleanup, daemon=True)
        self.cleanup_thread.start()

    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            return

        def send_heartbeat():
            while not self.should_stop:
                try:
                    self._send_heartbeat()
                    time.sleep(self.heartbeat_interval)
                except Exception as e:
                    print(f"Error sending heartbeat: {e}")

        self.heartbeat_thread = Thread(target=send_heartbeat, daemon=True)
        self.heartbeat_thread.start()

    def _send_heartbeat(self):
        """发送心跳到Redis"""
        try:
            from ginkgo.data.redis_schema import (
                RedisKeyBuilder, BacktestWorkerHeartbeat, WorkerStatus, RedisTTL
            )

            redis = self._get_redis()
            key = RedisKeyBuilder.backtest_worker_heartbeat(self.worker_id)

            heartbeat = BacktestWorkerHeartbeat.create(
                worker_id=self.worker_id,
                status=WorkerStatus.RUNNING if self.is_running else WorkerStatus.STOPPED,
                running_tasks=len(self.tasks),
                max_tasks=self.max_backtests,
                started_at=self.started_at
            )

            redis.setex(key, RedisTTL.BACKTEST_WORKER_HEARTBEAT, heartbeat.to_json())
            print(f"Heartbeat sent: {len(self.tasks)}/{self.max_backtests} tasks running")

        except Exception as e:
            print(f"Failed to send heartbeat: {e}")

    def _clear_heartbeat(self):
        """清理Redis心跳"""
        try:
            from ginkgo.data.redis_schema import RedisKeyBuilder

            redis = self._get_redis()
            key = RedisKeyBuilder.backtest_worker_heartbeat(self.worker_id)
            redis.delete(key)
            print("Heartbeat cleared")
        except Exception as e:
            print(f"Failed to clear heartbeat: {e}")

    def _cleanup_old_heartbeat_data(self):
        """清理旧的心跳数据"""
        try:
            from ginkgo.data.redis_schema import RedisKeyBuilder

            redis = self._get_redis()
            key = RedisKeyBuilder.backtest_worker_heartbeat(self.worker_id)
            if redis.exists(key):
                print(f"Old heartbeat data found for {self.worker_id}, cleaning up...")
                redis.delete(key)
        except Exception as e:
            print(f"Failed to cleanup old heartbeat: {e}")

    def _is_worker_id_in_use(self) -> bool:
        """检查worker_id是否已被使用"""
        try:
            from ginkgo.data.redis_schema import RedisKeyBuilder
            redis = self._get_redis()
            key = RedisKeyBuilder.backtest_worker_heartbeat(self.worker_id)
            return redis.exists(key)
        except Exception:
            return False

    def _get_redis(self):
        """获取Redis客户端"""
        if self._redis is None:
            self._redis = create_redis_connection()
        return self._redis

    def get_status(self) -> dict:
        """获取Worker状态"""
        with self.task_lock:
            task_statuses = {}
            for uuid, processor in self.tasks.items():
                task_statuses[uuid] = processor.get_status()

        return {
            "worker_id": self.worker_id,
            "status": "running" if self.is_running else "stopped",
            "running_tasks": len(self.tasks),
            "max_tasks": self.max_backtests,
            "started_at": self.started_at,
            "tasks": task_statuses,
            "metrics": self.metrics.get_metrics(),
        }
