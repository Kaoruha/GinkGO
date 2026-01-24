# Upstream: Kafka control commands (ginkgo.live.control.commands)
# Downstream: ClickHouse (bar data storage via BarCRUD), Redis (heartbeat storage)
# Role: Data collection worker - consumes Kafka commands and fetches/updates market data

import threading
import time
import signal
import json
from typing import Optional, Dict, Any, List
from datetime import datetime

from ginkgo.libs.utils.common import retry, time_logger
from ginkgo.interfaces.dtos.control_command_dto import ControlCommandDTO
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
    CONTROL_COMMANDS_TOPIC: str = "ginkgo.live.control.commands"
    DEFAULT_CONSUMER_GROUP: str = "data_worker_group"

    # 心跳配置
    HEARTBEAT_KEY_PREFIX: str = "heartbeat:data_worker"
    HEARTBEAT_TTL: int = 30  # 秒
    HEARTBEAT_INTERVAL: int = 10  # 秒

    def __init__(
        self,
        bar_crud: Any,
        group_id: str = DEFAULT_CONSUMER_GROUP,
        auto_offset_reset: str = "earliest",
        node_id: Optional[str] = None
    ) -> None:
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
        self._bar_crud: Any = bar_crud

        # Kafka配置
        self._group_id: str = group_id
        self._auto_offset_reset: str = auto_offset_reset

        # 节点标识
        self._node_id: str = node_id or f"data_worker_{threading.get_ident()}"

        # 状态管理
        self._status: WORKER_STATUS_TYPES = WORKER_STATUS_TYPES.STOPPED
        self._stop_event: threading.Event = threading.Event()
        self._lock: threading.Lock = threading.Lock()

        # Kafka消费者（延迟初始化）
        self._consumer: Optional[Any] = None

        # 统计信息
        self._stats: Dict[str, Any] = {
            "messages_processed": 0,
            "bars_written": 0,
            "errors": 0,
            "last_heartbeat": None
        }

        # 心跳线程
        self._heartbeat_thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        """检查Worker是否正在运行"""
        with self._lock:
            return self._status == WORKER_STATUS_TYPES.RUNNING

    @property
    def is_healthy(self) -> bool:
        """检查Worker是否健康（用于Docker healthcheck）"""
        return self.is_running and self._stop_event.is_set() == False

    @time_logger
    def start(self) -> bool:
        """
        启动Worker

        Returns:
            bool: 启动是否成功
        """
        with self._lock:
            if self._status != WORKER_STATUS_TYPES.STOPPED:
                print(f"[DataWorker:{self._node_id}] Worker already started or in transition, current status: {self._status}")
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

            print(f"[DataWorker:{self._node_id}] DataWorker started successfully")
            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Failed to start DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR
            return False

    @time_logger
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
                print(f"[DataWorker:{self._node_id}] Worker is not running, current status: {self._status}")
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

            print(f"[DataWorker:{self._node_id}] DataWorker stopped successfully")
            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error stopping DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR
            return False

    def run(self):
        """
        Worker主线程 - 订阅Kafka消息并处理

        这是threading.Thread的入口方法，由start()方法调用
        """
        print(f"[DataWorker:{self._node_id}] Worker thread started")

        try:
            # 使用poll模式，可以定期检查stop_event（适合低频控制命令）
            while not self._stop_event.is_set():
                try:
                    # 从Kafka拉取消息，超时1秒
                    raw_messages = self._consumer.consumer.poll(timeout_ms=1000)

                    if not raw_messages:
                        # 超时无消息，循环继续（此时会检查stop_event）
                        continue

                    # 处理消息（max_poll_records=1，所以只有1条）
                    for tp, messages in raw_messages.items():
                        for message in messages:
                            try:
                                # 获取消息值 - GinkgoConsumer已反序列化
                                message_value = message.value

                                if message_value is not None:
                                    if isinstance(message_value, dict):
                                        self._process_kafka_message_dict(message_value)
                                    else:
                                        print(f"[DataWorker:{self._node_id}] Unexpected message type: {type(message_value)}")
                                        with self._lock:
                                            self._stats["errors"] += 1

                                # 手动提交offset（处理完成后立即提交）
                                self._consumer.commit()

                                # 更新统计
                                with self._lock:
                                    self._stats["messages_processed"] += 1

                            except Exception as e:
                                print(f"[DataWorker:{self._node_id}] Error processing message: {e}")
                                import traceback
                                print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
                                with self._lock:
                                    self._stats["errors"] += 1

                except Exception as e:
                    print(f"[DataWorker:{self._node_id}] Error in worker loop: {e}")
                    import traceback
                    print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
                    with self._lock:
                        self._stats["errors"] += 1
                    # 出错后短暂等待再继续
                    time.sleep(5)

        except KeyboardInterrupt:
            print(f"[DataWorker:{self._node_id}] Worker received keyboard interrupt")
        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Unexpected error in worker thread: {e}")
        finally:
            print(f"[DataWorker:{self._node_id}] Worker thread exiting")

    def wait_for_completion(self):
        """等待Worker完成（阻塞调用）"""
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"[DataWorker:{self._node_id}] Interrupted, stopping worker...")
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
        try:
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoConsumer

            # 创建Kafka消费者
            # 注意：GinkgoConsumer在__init__内部已经处理了订阅
            self._consumer = GinkgoConsumer(
                topic=self.CONTROL_COMMANDS_TOPIC,
                group_id=self._group_id,
                offset=self._auto_offset_reset
            )

            print(f"[DataWorker:{self._node_id}] Kafka consumer initialized: topic={self.CONTROL_COMMANDS_TOPIC}, group_id={self._group_id}")

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Failed to initialize Kafka consumer: {e}")
            raise

    def _get_kafka_bootstrap_servers(self) -> str:
        """获取Kafka bootstrap servers配置"""
        # 从环境变量或GCONF读取
        import os
        host = os.environ.get("GINKGO_KAFKA_HOST", "localhost")
        port = os.environ.get("GINKGO_KAFKA_PORT", "9092")
        return f"{host}:{port}"

    def _process_kafka_message(self, message_value: bytes):
        """
        处理Kafka消息（字节序列）

        Args:
            message_value: Kafka消息值（字节序列）
        """
        try:
            # 解析JSON消息
            message_data = json.loads(message_value.decode('utf-8'))
            self._process_kafka_message_dict(message_data)
        except json.JSONDecodeError as e:
            print(f"[DataWorker:{self._node_id}] Failed to parse Kafka message as JSON: {e}")
            with self._lock:
                self._stats["errors"] += 1
        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error processing Kafka message: {e}")
            with self._lock:
                self._stats["errors"] += 1

    def _process_kafka_message_dict(self, message_data: Dict[str, Any]):
        """
        处理Kafka消息（已解析的字典）

        Args:
            message_data: 已解析的消息数据（字典）
        """
        try:
            # 创建ControlCommandDTO对象
            command_dto = ControlCommandDTO(**message_data)

            print(f"[DataWorker:{self._node_id}] Received control command: {command_dto.command}, source: {command_dto.source}")

            # 处理命令
            success = self._process_command(
                command=command_dto.command,
                payload=command_dto.params
            )

            if success:
                print(f"[DataWorker:{self._node_id}] Command {command_dto.command} processed successfully")
            else:
                print(f"[DataWorker:{self._node_id}] Command {command_dto.command} processing failed")

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error processing Kafka message dict: {e}")
            with self._lock:
                self._stats["errors"] += 1

    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        def heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    # 通过RedisCRUD获取原始Redis客户端
                    from ginkgo.data.crud import RedisCRUD

                    redis_crud = RedisCRUD()
                    redis_client = redis_crud.redis

                    if not redis_client:
                        print(f"[DataWorker:{self._node_id}] Failed to get Redis client")
                        self._stop_event.wait(self.HEARTBEAT_INTERVAL)
                        continue

                    # 构建心跳键
                    heartbeat_key = f"{self.HEARTBEAT_KEY_PREFIX}:{self._node_id}"

                    # 心跳数据
                    heartbeat_data = {
                        "node_id": self._node_id,
                        "status": str(self._status),
                        "timestamp": datetime.now().isoformat(),
                        "stats": self._stats.copy()
                    }

                    # 写入Redis（带TTL）- 使用原始Redis客户端的setex方法
                    import json
                    redis_client.setex(
                        heartbeat_key,
                        self.HEARTBEAT_TTL,
                        json.dumps(heartbeat_data, ensure_ascii=False)
                    )

                    with self._lock:
                        self._stats["last_heartbeat"] = time.time()

                    print(f"[DataWorker:{self._node_id}] Heartbeat sent: {heartbeat_key}")

                except Exception as e:
                    print(f"[DataWorker:{self._node_id}] Error sending heartbeat: {e}")

                # 等待下一次心跳间隔
                self._stop_event.wait(self.HEARTBEAT_INTERVAL)

        self._heartbeat_thread = threading.Thread(
            target=heartbeat_loop,
            daemon=True,
            name=f"Heartbeat-{self._node_id}"
        )
        self._heartbeat_thread.start()

    @time_logger(threshold=1.0)
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
            print(f"[DataWorker:{self._node_id}] Processing command: {command}")

            if command == "bar_snapshot":
                return self._handle_bar_snapshot(payload)
            elif command == "update_selector":
                return self._handle_update_selector(payload)
            elif command == "update_data":
                return self._handle_update_data(payload)
            elif command == "heartbeat_test":
                return self._handle_heartbeat_test(payload)
            else:
                print(f"[DataWorker:{self._node_id}] Unknown command: {command}")
                return False

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error processing command {command}: {e}")
            import traceback
            print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            with self._lock:
                self._stats["errors"] += 1
            return False

    @time_logger(threshold=5.0)
    @retry(max_try=3)
    def _handle_bar_snapshot(self, payload: Dict[str, Any]) -> bool:
        """
        处理bar_snapshot命令 - K线快照采集

        参考GTM的process_task实现，调用bar_service进行数据同步
        """
        try:
            code = payload.get("code")  # 股票代码
            force = payload.get("force", False)  # 是否强制覆盖
            full = payload.get("full", False)  # 是否全量同步

            print(f"[DataWorker:{self._node_id}] Handling bar_snapshot: code={code}, force={force}, full={full}")

            # 使用service_hub获取bar_service
            from ginkgo import service_hub

            bar_service = service_hub.data.services.bar()

            if full:
                # 全量同步：使用sync_range从上市日期开始
                print(f"[DataWorker:{self._node_id}] Starting full sync for {code}")
                result = bar_service.sync_range(code=code, start_date=None, end_date=None)
            else:
                # 增量同步：使用sync_smart
                print(f"[DataWorker:{self._node_id}] Starting incremental sync for {code}")
                result = bar_service.sync_smart(code=code, fast_mode=not force)

            if result.success:
                print(f"[DataWorker:{self._node_id}] Bar sync completed for {code}")
                # 更新统计
                if result.data and hasattr(result.data, 'records_processed'):
                    print(f"[DataWorker:{self._node_id}] Processed {result.data.records_processed} records for {code}")
                    with self._lock:
                        self._stats["bars_written"] += result.data.records_processed
                return True
            else:
                print(f"[DataWorker:{self._node_id}] Bar sync failed for {code}: {result.error}")
                return False

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling bar_snapshot: {e}")
            import traceback
            print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_update_selector(self, payload: Dict[str, Any]) -> bool:
        """
        处理update_selector命令 - 更新选股器

        这个命令主要被ExecutionNode使用，DataWorker只需要确认接收
        """
        try:
            print(f"[DataWorker:{self._node_id}] Handling update_selector command (acknowledged)")

            # update_selector主要由ExecutionNode处理
            # DataWorker只需要记录接收到命令
            # TODO: 如果需要在数据更新后通知Selector更新，可以在这里实现

            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling update_selector: {e}")
            return False

    def _handle_update_data(self, payload: Dict[str, Any]) -> bool:
        """
        处理update_data命令 - 更新数据

        这是bar_snapshot的别名，使用相同的逻辑
        """
        # update_data本质上是bar_snapshot
        return self._handle_bar_snapshot(payload)

    def _handle_heartbeat_test(self, payload: Dict[str, Any]) -> bool:
        """
        处理heartbeat_test命令 - 心跳测试

        用于验证Worker正常运行，发送通知确认心跳正常
        """
        try:
            print(f"[DataWorker:{self._node_id}] Handling heartbeat_test command")

            # 发送心跳测试通知
            # TODO: 通过notification_service发送心跳测试通知
            # 当前为占位实现

            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling heartbeat_test: {e}")
            return False
