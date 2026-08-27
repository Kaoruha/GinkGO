# Upstream: Kafka data commands (ginkgo.data.commands)
# Downstream: ClickHouse (bar data storage via BarCRUD), Redis (heartbeat storage)
# Role: Data Worker - 数据采集Worker

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
from ginkgo.libs import GLOG


class DataWorker(threading.Thread):
    """
    Data Worker - 数据采集Worker

    订阅Kafka数据采集命令主题 (ginkgo.data.commands)，接收数据采集任务，
    通过BarCRUD获取数据并批量写入ClickHouse。

    采用"容器即进程"模式，每个容器运行一个Worker实例，
    通过Kafka consumer group实现多实例负载均衡。
    """

    # Kafka配置
    CONTROL_COMMANDS_TOPIC: str = KafkaTopics.DATA_COMMANDS  # 数据采集命令专用
    DEFAULT_CONSUMER_GROUP: str = "data_worker_group"
    NOTIFICATIONS_TOPIC: str = "ginkgo.notifications"  # 通知主题

    # 心跳配置 (从统一schema获取)
    HEARTBEAT_KEY_PREFIX: str = "heartbeat:data_worker"  # 保持向后兼容，实际使用从redis_schema获取
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

        # 设置日志类别（用于Vector路由）
        GLOG.set_log_category("component")

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
                GLOG.WARN(f"[DataWorker:{self._node_id}] Worker already started or in transition, current status: {self._status}")
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

            GLOG.INFO(f"[DataWorker:{self._node_id}] DataWorker started successfully")

            # 发送系统事件：启动成功
            self._send_system_event("STARTED")

            return True

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to start DataWorker: {e}")
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
                GLOG.WARN(f"[DataWorker:{self._node_id}] Worker is not running, current status: {self._status}")
                return False

            self._status = WORKER_STATUS_TYPES.STOPPING

        try:
            # 1. 先取消Kafka订阅，避免接收新消息
            if self._consumer and self._consumer.consumer:
                try:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Unsubscribing from Kafka topic...")
                    self._consumer.consumer.unsubscribe()
                except Exception as e:
                    GLOG.WARN(f"[DataWorker:{self._node_id}] Error unsubscribing: {e}")

            # 2. 设置停止事件
            self._stop_event.set()

            # 3. 等待线程结束
            self.join(timeout=timeout)

            # 4. 停止心跳线程
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                self._heartbeat_thread.join(timeout=5.0)

            # 5. 关闭Kafka消费者
            if self._consumer:
                try:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Closing Kafka consumer...")
                    self._consumer.close()
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Kafka consumer closed")
                except Exception as e:
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Error closing consumer: {e}")
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
                except Exception as e:
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to close Kafka producer: {e}")

            GLOG.INFO(f"[DataWorker:{self._node_id}] DataWorker stopped successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error stopping DataWorker: {e}")
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
        GLOG.INFO(f"[DataWorker:{self._node_id}] Worker thread started")

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

                                if message_value is None:
                                    # None 黑洞(2026-08-19 实证):value=None 曾被
                                    # 静默跳过+无条件 commit——消息凭空消失,queued
                                    # 记录永悬且零日志。至少留下案发现场
                                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Message value is None (offset={message.offset}, partition={message.partition}) — silently consumed")
                                    with self._lock:
                                        self._stats["errors"] += 1
                                elif isinstance(message_value, dict):
                                    # 已反序列化为dict，直接处理
                                    self._process_kafka_message_dict(message_value)
                                elif isinstance(message_value, str):
                                    # 仍是字符串，尝试手动解析JSON
                                    try:
                                        message_data = json.loads(message_value)
                                        self._process_kafka_message_dict(message_data)
                                    except json.JSONDecodeError as e:
                                        GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to parse message as JSON: {e}")
                                        GLOG.ERROR(f"[DataWorker:{self._node_id}] Raw message: {message_value[:200]}")
                                        with self._lock:
                                            self._stats["errors"] += 1
                                else:
                                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Unexpected message type: {type(message_value)}, value: {message_value}")
                                    with self._lock:
                                        self._stats["errors"] += 1

                                # 手动提交offset（处理完成后立即提交）
                                self._consumer.commit()

                                # 更新统计
                                with self._lock:
                                    self._stats["messages_processed"] += 1

                            except Exception as e:
                                GLOG.ERROR(f"[DataWorker:{self._node_id}] Error processing message: {e}")
                                import traceback
                                GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
                                with self._lock:
                                    self._stats["errors"] += 1

                except Exception as e:
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Error in worker loop: {e}")
                    import traceback
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
                    with self._lock:
                        self._stats["errors"] += 1
                    # #6183: consumer 失效则重建（带退避），避免瞬时断连永久卡死
                    if not self._rebuild_consumer():
                        # 重建失败，退避后重试（而非死循环重试同一个 None）
                        time.sleep(5)

        except KeyboardInterrupt:
            GLOG.WARN(f"[DataWorker:{self._node_id}] Worker received keyboard interrupt")
        except Exception as e:
            GLOG.CRITICAL(f"[DataWorker:{self._node_id}] Unexpected error in worker thread: {e}")
            # 发送系统事件：严重错误
            self._send_system_event("ERROR", {
                "error": str(e),
                "phase": "run",
                "stats": self.get_stats()
            })
        finally:
            GLOG.INFO(f"[DataWorker:{self._node_id}] Worker thread exiting")

    def wait_for_completion(self):
        """等待Worker完成（阻塞调用）"""
        try:
            while self.is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            GLOG.WARN(f"[DataWorker:{self._node_id}] Interrupted, stopping worker...")
            self.stop()

    def get_stats(self) -> Dict[str, Any]:
        """
        获取Worker统计信息

        Returns:
            Dict: 统计信息字典
        """
        with self._lock:
            return self._stats.copy()

    def _rebuild_consumer(self) -> bool:
        """检测 consumer 失效并重建（#6183）。

        GinkgoConsumer 异常即置 self.consumer=None，run() 循环若只重试
        同一个 None 会永久空转（错误计数无限增长）。此处检测失效后调
        _init_consumer 重建；成功返回 True，重建失败返回 False（调用方
        退避后再试），不 raise 以免拖垮 worker 线程。
        """
        if (
            self._consumer is not None
            and getattr(self._consumer, "consumer", None) is not None
            and getattr(self._consumer, "is_connected", False)
        ):
            return True

        GLOG.WARN(f"[DataWorker:{self._node_id}] Consumer lost or disconnected, rebuilding...")
        try:
            self._init_consumer()
        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Consumer rebuild failed: {e}")
            return False

        if self._consumer is not None and getattr(self._consumer, "consumer", None) is not None:
            GLOG.INFO(f"[DataWorker:{self._node_id}] Consumer rebuilt successfully")
            return True

        GLOG.ERROR(f"[DataWorker:{self._node_id}] Consumer rebuild yielded no usable consumer")
        return False

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

            GLOG.INFO(f"[DataWorker:{self._node_id}] Kafka consumer initialized: topic={self.CONTROL_COMMANDS_TOPIC}, group_id={self._group_id}")

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to initialize Kafka consumer: {e}")
            raise

    def _init_producer(self):
        """初始化Kafka生产者（用于发送系统事件）"""
        try:
            from ginkgo.data.drivers.ginkgo_kafka import GinkgoProducer

            self._producer = GinkgoProducer()

            if self._producer.is_connected:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Kafka producer initialized for system events")
            else:
                GLOG.WARN(f"[DataWorker:{self._node_id}] Warning: Kafka producer not connected, system events will not be sent")

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to initialize Kafka producer: {e}")
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
                GLOG.INFO(f"[DataWorker:{self._node_id}] System notification sent: {event_type}")
            else:
                GLOG.WARN(f"[DataWorker:{self._node_id}] Failed to send system notification: {event_type}")

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to send system event: {e}")

    def _notify_task_start(self, command: str, payload: Dict[str, Any]) -> None:
        """
        发送任务开始通知（立即发送，不批量）

        当DataWorker接收到控制命令并开始处理时，立即发送通知。

        Args:
            command: 命令类型
            payload: 命令参数
        """
        try:
            from ginkgo.notifier.core.notification_service import notify

            # 构建命令描述
            command_descriptions = {
                "bar_snapshot": "K线数据采集",
                "stockinfo": "股票基础信息同步",
                "adjustfactor": "复权因子同步",
                "tick": "Tick数据采集",
            }

            command_desc = command_descriptions.get(command, command)

            # 构建参数描述
            param_parts = []
            if command == "bar_snapshot":
                if payload.get("code"):
                    param_parts.append(f"code={payload.get('code')}")
                if payload.get("full"):
                    param_parts.append("full=True")
            elif command == "tick":
                if payload.get("code"):
                    param_parts.append(f"code={payload.get('code')}")
                if payload.get("full"):
                    param_parts.append(f"full={payload.get('full')}")
                if payload.get("overwrite"):
                    param_parts.append(f"overwrite={payload.get('overwrite')}")
            elif command == "adjustfactor":
                if payload.get("code"):
                    param_parts.append(f"code={payload.get('code')}")

            params_str = ", ".join(param_parts) if param_parts else "所有数据"

            # 构建通知内容
            content = f"DataWorker `{self._node_id}` 开始处理: {command_desc}"
            if params_str != "所有数据":
                content += f" ({params_str})"

            details = {
                "node_id": self._node_id,
                "command": command,
                "command_desc": command_desc,
                "params": payload
            }

            # 在新线程中发送通知，避免阻塞
            import threading
            def send_notification():
                try:
                    notify(
                        content=content,
                        level="INFO",
                        details=details,
                        module="DataWorker",
                        async_mode=False
                    )
                except Exception as e:
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to send notification: {e}")

            thread = threading.Thread(target=send_notification, daemon=True)
            thread.start()

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to queue task notification: {e}")

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
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to parse Kafka message as JSON: {e}")
            with self._lock:
                self._stats["errors"] += 1
        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error processing Kafka message: {e}")
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

            GLOG.INFO(f"[DataWorker:{self._node_id}] Received control command: {command_dto.command}, source: {command_dto.source}")

            # 处理命令;顶层 source 并入 params(下划线键避冲突)——handler 侧
            # _record_source 据此落触发来源(2026-08-18:实弹验证 source 在
            # DTO 顶层,仅传 params 会丢,探针曾落成 OTHER)
            merged_payload = dict(command_dto.params or {})
            if getattr(command_dto, "source", None):
                merged_payload["_source"] = command_dto.source
            success = self._process_command(
                command=command_dto.command,
                payload=merged_payload
            )

            if success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Command {command_dto.command} processed successfully")
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Command {command_dto.command} processing failed")

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error processing Kafka message dict: {e}")
            with self._lock:
                self._stats["errors"] += 1

    def _start_heartbeat_thread(self):
        """启动心跳线程"""
        def heartbeat_loop():
            while not self._stop_event.is_set():
                try:
                    from ginkgo.data.crud import RedisCRUD
                    from ginkgo.data.redis_schema import (
                        RedisKeyBuilder, DataWorkerHeartbeat, WorkerStatus, RedisTTL
                    )

                    redis_crud = RedisCRUD()
                    redis_client = redis_crud.redis

                    if not redis_client:
                        GLOG.ERROR(f"[DataWorker:{self._node_id}] Failed to get Redis client")
                        self._stop_event.wait(self.HEARTBEAT_INTERVAL)
                        continue

                    # 构建心跳键和数据
                    heartbeat_key = RedisKeyBuilder.data_worker_heartbeat(self._node_id)
                    heartbeat = DataWorkerHeartbeat.create(
                        node_id=self._node_id,
                        status=self._status.name.lower(),
                        stats=self._stats.copy()
                    )

                    # 写入Redis（带TTL）
                    redis_client.setex(
                        heartbeat_key,
                        RedisTTL.DATA_WORKER_HEARTBEAT,
                        heartbeat.to_json()
                    )

                    with self._lock:
                        self._stats["last_heartbeat"] = time.time()

                    GLOG.DEBUG(f"[DataWorker:{self._node_id}] Heartbeat sent: {heartbeat_key} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                except Exception as e:
                    GLOG.ERROR(f"[DataWorker:{self._node_id}] Error sending heartbeat: {e}")

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
        处理数据采集命令

        DataWorker 订阅 ginkgo.data.commands topic，
        只会收到 5 个核心数据采集命令：
        - bar_snapshot: K线数据采集
        - stockinfo: 股票基础信息同步
        - adjustfactor: 复权因子同步
        - tick: Tick数据采集
        - trade_day: 交易日历同步

        Args:
            command: 命令类型
            payload: 命令参数

        Returns:
            bool: 处理是否成功
        """
        try:
            GLOG.INFO(f"[DataWorker:{self._node_id}] Processing command: {command}")

            # 发送任务开始通知
            self._notify_task_start(command, payload)

            # 路由到对应的处理函数
            if command == "bar_snapshot":
                return self._handle_bar_snapshot(payload)
            elif command == "stockinfo":
                return self._handle_stockinfo(payload)
            elif command == "adjustfactor":
                return self._handle_adjustfactor(payload)
            elif command == "tick":
                return self._handle_tick(payload)
            elif command == "trade_day":
                return self._handle_trade_day(payload)
            else:
                # 理论上不会到达这里（topic 只有这 5 个命令）
                GLOG.WARN(f"[DataWorker:{self._node_id}] Unknown command: {command}")
                return False

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error processing command {command}: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            # 异常终结记录(2026-08-18):handler 任何异常(含 _recorded 行本身的
            # TypeError 等)必须落到 data_sync_record 为 failed——否则带 _record
            # 的 queued 记录悬死,只能等 reap 兜底且丢失错误信息。分发层统一
            # 兜底,一处覆盖全部命令。仅终结非终态(queued/running),不覆盖已成功
            # 记录(防 Kafka 重放场景)
            self._fail_record_from_payload(payload, command, str(e))
            with self._lock:
                self._stats["errors"] += 1
            return False

    def _fail_record_from_payload(self, payload: Dict[str, Any], command: str, err: str) -> None:
        """按消息 _record 终结滞留记录为 failed(handler 异常路径)。"""
        ru = payload.get("_record")
        if not ru:
            return  # 裸命令(tasktimer/旧格式)本就无记录,维持旧语义
        try:
            import datetime
            from ginkgo.data.containers import container
            container.data_sync_record_service()._crud_repo.modify(
                filters={"uuid": ru, "status__in": ["queued", "running"]},
                updates={
                    "status": "failed",
                    "completed_at": datetime.datetime.now(),
                    "error_message": f"handler error ({command}): {err[:400]}",
                },
            )
        except Exception as e:
            GLOG.WARN(f"[DataWorker:{self._node_id}] fail-record fallback error: {e}")

    @staticmethod
    def _record_source(payload: Dict[str, Any]) -> str:
        """命令触发来源归一(2026-08-18):读分发层并入的 _source(DTO 顶层)。
        输出必须是 TRIGGER_SOURCE_TYPES 的枚举名(web/cli/scheduled)——
        DTO 用 "task_timer",与枚举名 SCHEDULED 断层曾致全批落 OTHER(实测)"""
        src = str(payload.get("_source", "") or "")
        mapping = {"web": "web", "cli": "cli", "task_timer": "scheduled"}
        return mapping.get(src, "other")

    def _recorded(self, sync_type: str, code: str, source: str = "web", existing_uuid: str = None):
        """落记录统一包裹(2026-08-18 下沉 service 层,CLI 进程内模式共用)。
        existing_uuid: queued 方案——消息带 _record 时复活该记录而非新建
        (定义与调用点同轮收口,漏改致 TypeError,queued 卡排队根因)。"""
        from ginkgo.data.containers import container
        return container.data_sync_record_service().recorded(
            sync_type, code, trigger_source=source, existing_uuid=existing_uuid)

    def _record_result(self, uuid_, result, started: float) -> None:
        from ginkgo.data.containers import container
        container.data_sync_record_service().record_result(uuid_, result, started)

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
                GLOG.DEBUG(f"[DataWorker:{self._node_id}] Ignoring bar_snapshot without code (for DataManager)")
                return True

            GLOG.INFO(f"[DataWorker:{self._node_id}] Handling bar_snapshot: code={code}, force={force}, full={full}")

            # 使用container获取bar_service
            from ginkgo.data.containers import container

            bar_service = container.bar_service()

            # 日期范围(2026-08-18):Web 手动同步的定向补数;full 或带日期走 sync_range
            start_date = payload.get("start_date")
            end_date = payload.get("end_date")
            with self._recorded("bars", code, self._record_source(payload), existing_uuid=payload.get("_record")) as (rec_uuid, _t0):
                if full or start_date or end_date:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Starting range sync for {code} [{start_date}~{end_date}]")
                    result = bar_service.sync_range(code=code, start_date=start_date, end_date=end_date)
                else:
                    # 增量同步：使用sync_smart
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Starting incremental sync for {code}")
                    result = bar_service.sync_smart(code=code, fast_mode=not force)
                self._record_result(rec_uuid, result, _t0)

            if result.success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Bar sync completed for {code}")
                # 更新统计
                if result.data and hasattr(result.data, 'records_processed'):
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Processed {result.data.records_processed} records for {code}")
                    with self._lock:
                        self._stats["bars_written"] += result.data.records_processed
                return True
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Bar sync failed for {code}: {result.error}")
                return False

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error handling bar_snapshot: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_stockinfo(self, payload: Dict[str, Any]) -> bool:
        """
        处理stockinfo命令 - 股票信息更新

        StockinfoService.sync() 同步所有股票信息，不支持单个股票同步
        """
        try:
            code = payload.get("code")  # 参数会被忽略，sync()总是同步所有股票
            GLOG.INFO(f"[DataWorker:{self._node_id}] Handling stockinfo: code={code} (will sync all)")

            from ginkgo.data.containers import container
            stockinfo_service = container.stockinfo_service()

            # 同步所有股票信息（StockinfoService.sync() 不接受参数）
            with self._recorded("stockinfo", "ALL", self._record_source(payload), existing_uuid=payload.get("_record")) as (rec_uuid, _t0):
                result = stockinfo_service.sync()
                self._record_result(rec_uuid, result, _t0)

            if result.success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Stockinfo sync completed")
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Stockinfo sync failed: {result.error}")

            return result.success

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error handling stockinfo: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_trade_day(self, payload: Dict[str, Any]) -> bool:
        """
        处理 trade_day 命令 - 交易日历更新（#6488）

        TradeDayService.sync() 同步全量交易日历（开市/休市标记），不支持单日同步。
        paper worker 通过 trade_day_crud 查 is_open 判断是否开市，表空则整轮 skip 致 0 signal。
        """
        try:
            code = payload.get("code")  # 参数会被忽略，sync() 总是同步全量日历
            GLOG.INFO(f"[DataWorker:{self._node_id}] Handling trade_day: code={code} (will sync all)")

            from ginkgo.data.containers import container
            trade_day_service = container.trade_day_service()

            result = trade_day_service.sync()

            if result.success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Trade calendar sync completed")
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Trade calendar sync failed: {result.error}")

            return result.success

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error handling trade_day: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_adjustfactor(self, payload: Dict[str, Any]) -> bool:
        """
        处理adjustfactor命令 - 复权因子更新

        参考GTM的process_task实现
        """
        try:
            code = payload.get("code")  # 股票代码（必需）
            if not code:
                GLOG.WARN(f"[DataWorker:{self._node_id}] Adjustfactor requires code parameter")
                return False

            GLOG.INFO(f"[DataWorker:{self._node_id}] Handling adjustfactor: code={code}")

            from ginkgo.data.containers import container
            adjustfactor_service = container.adjustfactor_service()

            # 同步复权因子
            with self._recorded("adjustfactor", code, self._record_source(payload), existing_uuid=payload.get("_record")) as (rec_uuid, _t0):
                result = adjustfactor_service.sync(code)
                self._record_result(rec_uuid, result, _t0)

            if result.success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Adjustfactor sync completed for {code}")
                # 同步完成后计算复权因子
                calc_result = adjustfactor_service.calculate(code)
                if calc_result.success:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Adjustment factor calculation completed for {code}")
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Adjustfactor sync failed for {code}: {result.error}")

            return result.success

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error handling adjustfactor: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            return False

    def _handle_tick(self, payload: Dict[str, Any]) -> bool:
        """
        处理tick命令 - Tick数据更新

        参数说明:
            - code: 股票代码（必需）
            - full: 是否全量回填，默认 False
            - overwrite: 是否强制覆盖已有数据，默认 False

        组合说明:
            - full=False, overwrite=False: 日常增量更新（sync_smart，推荐）
            - full=True, overwrite=False: 全量补全缺失数据
            - full=True, overwrite=True: 数据修复（全量覆盖）
        """
        try:
            code = payload.get("code")  # 股票代码（必需）
            full = payload.get("full", False)  # 是否全量回填
            overwrite = payload.get("overwrite", False)  # 是否强制覆盖

            if not code:
                GLOG.WARN(f"[DataWorker:{self._node_id}] Tick requires code parameter")
                return False

            GLOG.INFO(f"[DataWorker:{self._node_id}] Handling tick: code={code}, full={full}, overwrite={overwrite}")

            from ginkgo.data.containers import container
            tick_service = container.tick_service()

            if full:
                # 全量回填
                if overwrite:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Starting tick data repair (full + overwrite) for {code}")
                else:
                    GLOG.INFO(f"[DataWorker:{self._node_id}] Starting tick backfill (full, skip existing) for {code}")
                with self._recorded("ticks", code, self._record_source(payload), existing_uuid=payload.get("_record")) as (rec_uuid, _t0):
                    result = tick_service.sync_backfill_by_date(code=code, force_overwrite=overwrite)
                    self._record_result(rec_uuid, result, _t0)
            else:
                # 增量更新 (使用 sync_smart);日期范围透传(Web 定向补数,2026-08-18)
                GLOG.INFO(f"[DataWorker:{self._node_id}] Starting tick incremental update for {code}")
                with self._recorded("ticks", code, self._record_source(payload), existing_uuid=payload.get("_record")) as (rec_uuid, _t0):
                    result = tick_service.sync_smart(
                        code=code, fast_mode=True,
                        start_date=payload.get("start_date"), end_date=payload.get("end_date"),
                    )
                    self._record_result(rec_uuid, result, _t0)

            if result.success:
                GLOG.INFO(f"[DataWorker:{self._node_id}] Tick sync completed for {code}")
            else:
                GLOG.ERROR(f"[DataWorker:{self._node_id}] Tick sync failed for {code}: {result.error}")

            return result.success

        except Exception as e:
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Error handling tick: {e}")
            import traceback
            GLOG.ERROR(f"[DataWorker:{self._node_id}] Traceback: {traceback.format_exc()}")
            # handler 吞异常路径也终结记录(2026-08-19):tick 源初始化崩时
            # except return False 不上抛,分发层兜底够不着,queued 悬死实测
            self._fail_record_from_payload(payload, "tick", str(e))
            return False
