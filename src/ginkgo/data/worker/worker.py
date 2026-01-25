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
    NOTIFICATIONS_TOPIC: str = "ginkgo.notifications"  # 通知主题

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

        # Kafka生产者（用于发送系统事件，延迟初始化）
        self._producer: Optional[Any] = None

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

            # 初始化Kafka生产者（用于系统事件）
            self._init_producer()

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

            # 发送系统事件：启动成功
            self._send_system_event("STARTED")

            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Failed to start DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR

            # 发送系统事件：启动失败
            self._send_system_event("ERROR", {"error": str(e), "phase": "start"})

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

            # 收集最终统计信息
            final_stats = self.get_stats()

            # 发送系统事件：停止成功（在关闭producer之前）
            self._send_system_event("STOPPED", {
                "messages_processed": final_stats.get("messages_processed", 0),
                "bars_written": final_stats.get("bars_written", 0),
                "errors": final_stats.get("errors", 0),
            })

            # 关闭Kafka生产者
            if self._producer:
                try:
                    self._producer.close()
                except:
                    pass

            print(f"[DataWorker:{self._node_id}] DataWorker stopped successfully")
            return True

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error stopping DataWorker: {e}")
            with self._lock:
                self._status = WORKER_STATUS_TYPES.ERROR

            # 发送系统事件：停止失败
            self._send_system_event("ERROR", {"error": str(e), "phase": "stop"})

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
                                        # 已反序列化为dict，直接处理
                                        self._process_kafka_message_dict(message_value)
                                    elif isinstance(message_value, str):
                                        # 仍是字符串，尝试手动解析JSON
                                        try:
                                            message_data = json.loads(message_value)
                                            self._process_kafka_message_dict(message_data)
                                        except json.JSONDecodeError as e:
                                            print(f"[DataWorker:{self._node_id}] Failed to parse message as JSON: {e}")
                                            print(f"[DataWorker:{self._node_id}] Raw message: {message_value[:200]}")
                                            with self._lock:
                                                self._stats["errors"] += 1
                                    else:
                                        print(f"[DataWorker:{self._node_id}] Unexpected message type: {type(message_value)}, value: {message_value}")
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
            # 发送系统事件：严重错误
            self._send_system_event("ERROR", {
                "error": str(e),
                "phase": "run",
                "stats": self.get_stats()
            })
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

    def _init_producer(self):
        """初始化Kafka生产者（用于发送系统事件）"""
        try:
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            self._producer = GinkgoProducer()

            if self._producer.is_connected:
                print(f"[DataWorker:{self._node_id}] Kafka producer initialized for system events")
            else:
                print(f"[DataWorker:{self._node_id}] Warning: Kafka producer not connected, system events will not be sent")

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Failed to initialize Kafka producer: {e}")
            self._producer = None

    def _send_system_event(self, event_type: str, details: Optional[Dict[str, Any]] = None):
        """
        发送系统事件通知

        使用 notify() 函数，与 ExecutionNode 保持一致

        Args:
            event_type: 事件类型 (STARTED, STOPPED, ERROR)
            details: 事件详情
        """
        try:
            from ginkgo.notifier.core.notification_service import notify
            import socket

            # 根据事件类型确定通知等级
            if event_type == "STARTED":
                level = "INFO"
                content = f"DataWorker `{self._node_id}` started on {socket.gethostname()}"
            elif event_type == "STOPPED":
                stats_str = ""
                if details:
                    stats_str = f" (Messages: {details.get('messages_processed', 0)}, Bars: {details.get('bars_written', 0)}, Errors: {details.get('errors', 0)})"
                content = f"DataWorker `{self._node_id}` stopped{stats_str}"
                level = "WARN"
            elif event_type == "ERROR":
                error_info = details.get("error", "Unknown error") if details else "Unknown error"
                phase = details.get("phase", "unknown") if details else "unknown"
                content = f"DataWorker `{self._node_id}` error in {phase}: {error_info}"
                level = "ERROR"
            else:
                content = f"DataWorker `{self._node_id}` event: {event_type}"
                level = "INFO"

            # 构建 details 字典
            notify_details = {
                "node_id": self._node_id,
                "host": socket.gethostname(),
                "group_id": self._group_id,
                "status": str(self._status),
            }
            if details:
                notify_details.update(details)

            # 使用 notify() 发送通知（会自动发送到System组）
            success = notify(
                content=content,
                level=level,
                details=notify_details,
                module="DataWorker",
                async_mode=True  # 异步发送，不阻塞
            )

            if success:
                print(f"[DataWorker:{self._node_id}] System notification sent: {event_type}")
            else:
                print(f"[DataWorker:{self._node_id}] Failed to send system notification: {event_type}")

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Failed to send system event: {e}")

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
            elif command == "stockinfo":
                return self._handle_stockinfo(payload)
            elif command == "adjustfactor":
                return self._handle_adjustfactor(payload)
            elif command == "tick":
                return self._handle_tick(payload)
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

            # 如果没有code参数，忽略此命令（TaskTimer的bar_snapshot是给DataManager用的）
            if not code:
                print(f"[DataWorker:{self._node_id}] Ignoring bar_snapshot without code (for DataManager)")
                return True

            print(f"[DataWorker:{self._node_id}] Handling bar_snapshot: code={code}, force={force}, full={full}")

            # 使用container获取bar_service
            from ginkgo.data.containers import container

            bar_service = container.bar_service()

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

    def _handle_stockinfo(self, payload: Dict[str, Any]) -> bool:
        """
        处理stockinfo命令 - 股票信息更新

        StockinfoService.sync() 同步所有股票信息，不支持单个股票同步
        """
        try:
            code = payload.get("code")  # 参数会被忽略，sync()总是同步所有股票
            print(f"[DataWorker:{self._node_id}] Handling stockinfo: code={code} (will sync all)")

            from ginkgo.data.containers import container
            stockinfo_service = container.stockinfo_service()

            # 同步所有股票信息（StockinfoService.sync() 不接受参数）
            result = stockinfo_service.sync()

            if result.success:
                print(f"[DataWorker:{self._node_id}] Stockinfo sync completed")
            else:
                print(f"[DataWorker:{self._node_id}] Stockinfo sync failed: {result.error}")

            return result.success

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling stockinfo: {e}")
            import traceback
            print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_adjustfactor(self, payload: Dict[str, Any]) -> bool:
        """
        处理adjustfactor命令 - 复权因子更新

        参考GTM的process_task实现
        """
        try:
            code = payload.get("code")  # 股票代码（必需）
            if not code:
                print(f"[DataWorker:{self._node_id}] Adjustfactor requires code parameter")
                return False

            print(f"[DataWorker:{self._node_id}] Handling adjustfactor: code={code}")

            from ginkgo.data.containers import container
            adjustfactor_service = container.adjustfactor_service()

            # 同步复权因子
            result = adjustfactor_service.sync(code)

            if result.success:
                print(f"[DataWorker:{self._node_id}] Adjustfactor sync completed for {code}")
                # 同步完成后计算复权因子
                calc_result = adjustfactor_service.calculate(code)
                if calc_result.success:
                    print(f"[DataWorker:{self._node_id}] Adjustment factor calculation completed for {code}")
            else:
                print(f"[DataWorker:{self._node_id}] Adjustfactor sync failed for {code}: {result.error}")

            return result.success

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling adjustfactor: {e}")
            import traceback
            print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_tick(self, payload: Dict[str, Any]) -> bool:
        """
        处理tick命令 - Tick数据更新

        参考GTM的process_task实现
        """
        try:
            code = payload.get("code")  # 股票代码（必需）
            full = payload.get("full", False)  # 是否全量回填

            if not code:
                print(f"[DataWorker:{self._node_id}] Tick requires code parameter")
                return False

            print(f"[DataWorker:{self._node_id}] Handling tick: code={code}, full={full}")

            from ginkgo.data.containers import container
            tick_service = container.tick_service()

            if full:
                # 全量回填
                print(f"[DataWorker:{self._node_id}] Starting tick backfill for {code}")
                result = tick_service.sync_backfill_by_date(code=code, force_overwrite=True)
            else:
                # 增量更新 (使用 sync_smart)
                print(f"[DataWorker:{self._node_id}] Starting tick incremental update for {code}")
                result = tick_service.sync_smart(code=code, fast_mode=True)

            if result.success:
                print(f"[DataWorker:{self._node_id}] Tick sync completed for {code}")
            else:
                print(f"[DataWorker:{self._node_id}] Tick sync failed for {code}: {result.error}")

            return result.success

        except Exception as e:
            print(f"[DataWorker:{self._node_id}] Error handling tick: {e}")
            import traceback
            print(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False
