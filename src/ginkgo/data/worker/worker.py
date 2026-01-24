# Upstream: Kafka control commands (ginkgo.live.control.commands)
# Downstream: ClickHouse (bar data storage via BarCRUD), Redis (heartbeat storage)
# Role: Data collection worker - consumes Kafka commands and fetches/updates market data

import threading
import time
import signal
from typing import Optional, Dict, Any
from enum import IntEnum

from ginkgo.libs.core.logger import GinkgoLogger
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.enums import WORKER_STATUS_TYPES


class DataWorker(threading.Thread):
    """
    Data Worker - 数据采集Worker

    订阅Kafka控制命令主题 (ginkgo.live.control.commands)，接收数据采集任务，
    通过BarCRUD获取数据并批量写入ClickHouse。

    采用"容器即进程"模式，每个容器运行一个Worker实例，
    通过Kafka consumer group实现多实例负载均衡。
    """

    # Kafka配置
    CONTROL_COMMANDS_TOPIC = "ginkgo.live.control.commands"
    DEFAULT_CONSUMER_GROUP = "data_worker_group"

    # 心跳配置
    HEARTBEAT_KEY_PREFIX = "heartbeat:data_worker"
    HEARTBEAT_TTL = 30  # 秒
    HEARTBEAT_INTERVAL = 10  # 秒

    def __init__(
        self,
        bar_crud,
        group_id: str = DEFAULT_CONSUMER_GROUP,
        auto_offset_reset: str = "earliest",
        node_id: Optional[str] = None
    ):
        """
        初始化DataWorker

        Args:
            bar_crud: BarCRUD实例，用于数据操作
            group_id: Kafka consumer group ID
            auto_offset_reset: Kafka auto.offset.reset策略
            node_id: 节点ID，用于心跳键生成
        """
        super().__init__(daemon=False)

        # 依赖注入
        self._bar_crud = bar_crud

        # Kafka配置
        self._group_id = group_id
        self._auto_offset_reset = auto_offset_reset

        # 节点标识
        self._node_id = node_id or f"data_worker_{threading.get_ident()}"

        # 状态管理
        self._status = WORKER_STATUS_TYPES.STOPPED
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

        # Kafka消费者（延迟初始化）
        self._consumer = None

        # 统计信息
        self._stats = {
            "messages_processed": 0,
            "bars_written": 0,
            "errors": 0,
            "last_heartbeat": None
        }

        # 心跳线程
        self._heartbeat_thread = None

        # 日志
        self._logger = GinkgoLogger().get_logger()

    @property
    def is_running(self) -> bool:
        """检查Worker是否正在运行"""
        with self._lock:
            return self._status == WORKER_STATUS_TYPES.RUNNING

    @property
    def is_healthy(self) -> bool:
        """检查Worker是否健康（用于Docker healthcheck）"""
        return self.is_running and self._stop_event.is_set() == False

    def start(self) -> bool:
        """
        启动Worker

        Returns:
            bool: 启动是否成功
        """
        with self._lock:
            if self._status != WORKER_STATUS_TYPES.STOPPED:
                self._logger.warning(f"Worker already started or in transition, current status: {self._status}")
                return False

            self._status = WORKER_STATUS_TYPES.STARTING

        try:
            # 初始化Kafka消费者
            self._init_consumer()

            # 启动心跳线程
            self._start_heartbeat_thread()

            # 启动消费线程
            self._stop_event.clear()
            super().start()

            # 等待线程启动完成
            time.sleep(0.5)

            with self._lock:
                self._status = WORKER_STATUS_TYPES.RUNNING

            self._logger.info(f"DataWorker started successfully (node_id: {self._node_id})")
            return True

        except Exception as e:
            self._logger.error(f"Failed to start DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR
            return False

    def stop(self, timeout: float = 30.0) -> bool:
        """
        停止Worker

        Args:
            timeout: 超时时间（秒）

        Returns:
            bool: 停止是否成功
        """
        with self._lock:
            if self._status != WORKER_STATUS_TYPES.RUNNING:
                self._logger.warning(f"Worker is not running, current status: {self._status}")
                return False

            self._status = WORKER_STATUS_TYPES.STOPPING

        try:
            # 设置停止事件
            self._stop_event.set()

            # 等待线程结束
            self.join(timeout=timeout)

            # 停止心跳线程
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=5.0)

            # 关闭Kafka消费者
            if self._consumer:
                try:
                    self._consumer.close()
                except:
                    pass

            with self._lock:
                self._status = WORKER_STATUS_TYPES.STOPPED

            self._logger.info(f"DataWorker stopped successfully (node_id: {self._node_id})")
            return True

        except Exception as e:
            self._logger.error(f"Error stopping DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR
            return False

    def run(self):
        """
        Worker主线程 - 订阅Kafka消息并处理

        这是threading.Thread的入口方法，由start()方法调用
        """
        self._logger.info(f"Worker thread started (node_id: {self._node_id})")

        try:
            while not self._stop_event.is_set():
                try:
                    # TODO: 实现Kafka消息消费逻辑
                    # 当前为占位实现，等待Kafka集成完成

                    # 模拟消息处理（临时）
                    time.sleep(1)

                    # 更新统计
                    with self._lock:
                        self._stats["messages_processed"] += 1

                except Exception as e:
                    self._logger.error(f"Error in worker loop: {e}")
                    with self._lock:
                        self._stats["errors"] += 1
                    # 短暂等待后继续
                    time.sleep(5)

        except KeyboardInterrupt:
            self._logger.info("Worker received keyboard interrupt")
        except Exception as e:
            self._logger.error(f"Unexpected error in worker thread: {e}")
        finally:
            self._logger.info(f"Worker thread exiting (node_id: {self._node_id})")

    def wait_for_completion(self):
        """等待Worker完成（阻塞调用）"""
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            self._logger.info("Interrupted, stopping worker...")
            self.stop()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取Worker统计信息

        Returns:
            Dict: 统计信息字典
        """
        with self._lock:
            return self._stats.copy()

    def _init_consumer(self):
        """初始化Kafka消费者"""
        # TODO: 实现Kafka消费者初始化
        # 当前为占位实现
        self._logger.info("Kafka consumer initialization (placeholder)")
        pass

    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        def heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    # TODO: 实现Redis心跳上报
                    # 当前为占位实现
                    with self._lock:
                        self._stats["last_heartbeat"] = time.time()

                    self._logger.debug(f"Heartbeat sent (node_id: {self._node_id})")

                except Exception as e:
                    self._logger.error(f"Error sending heartbeat: {e}")

                # 等待下一次心跳间隔
                self._stop_event.wait(self.HEARTBEAT_INTERVAL)

        self._heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            daemon=True,
            name=f"Heartbeat-{self._node_id}"
        )
        self._heartbeat_thread.start()

    def _process_command(self, command: str, payload: Dict[str, Any]) -> bool:
        """
        处理控制命令

        Args:
            command: 命令类型 (bar_snapshot, update_selector, update_data, heartbeat_test)
            payload: 命令参数

        Returns:
            bool: 处理是否成功
        """
        try:
            self._logger.info(f"Processing command: {command}")

            if command == "bar_snapshot":
                return self._handle_bar_snapshot(payload)
            elif command == "update_selector":
                return self._handle_update_selector(payload)
            elif command == "update_data":
                return self._handle_update_data(payload)
            elif command == "heartbeat_test":
                return self._handle_heartbeat_test(payload)
            else:
                self._logger.warning(f"Unknown command: {command}")
                return False

        except Exception as e:
            self._logger.error(f"Error processing command {command}: {e}")
            with self._lock:
                self._stats["errors"] += 1
            return False

    def _handle_bar_snapshot(self, payload: Dict[str, Any]) -> bool:
        """处理bar_snapshot命令"""
        # TODO: T020 实现
        self._logger.info("Handling bar_snapshot command (placeholder)")
        return True

    def _handle_update_selector(self, payload: Dict[str, Any]) -> bool:
        """处理update_selector命令"""
        # TODO: T021 实现
        self._logger.info("Handling update_selector command (placeholder)")
        return True

    def _handle_update_data(self, payload: Dict[str, Any]) -> bool:
        """处理update_data命令"""
        # TODO: T022 实现
        self._logger.info("Handling update_data command (placeholder)")
        return True

    def _handle_heartbeat_test(self, payload: Dict[str, Any]) -> bool:
        """处理heartbeat_test命令"""
        # TODO: T023 实现
        self._logger.info("Handling heartbeat_test command (placeholder)")
        return True
