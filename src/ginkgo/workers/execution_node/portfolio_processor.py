# Upstream: ExecutionNode (持有Portfolio实例，创建Input/Output Queue), Kafka (消费control.commands)
# Downstream: Portfolio (调用on_price_update/on_order_filled处理事件), Kafka (发布EventInterestUpdate)
# Role: Portfolio运行控制器，每个Portfolio一个独立线程，管理Portfolio生命周期和事件路由


"""
Portfolio运行控制器（Portfolio Run Controller）

PortfolioProcessor是Portfolio的完整运行控制器，类似于回测Engine的职责：
- 线程管理：每个Portfolio独立线程运行
- 生命周期：启动、停止、暂停、恢复
- 事件路由：从input_queue获取事件，路由到Portfolio对应方法
- 输出管理：将Portfolio生成的事件转发到output_queue
- 状态监控：队列使用率、处理延迟、异常统计

核心逻辑（类似于回测Engine）：
    while self.is_running:
        if self.is_paused:
            continue  # 暂停时不处理数据

        event = self.input_queue.get(timeout=1)
        self._route_event(event)  # 路由到Portfolio方法
        self.input_queue.task_done()

事件路由映射：
    EventPriceUpdate → portfolio.on_price_update()
    EventOrderPartiallyFilled → portfolio.on_order_filled()
    EventOrderCancelAck → portfolio.on_order_cancel_ack()
    EventSignalGeneration → portfolio.on_signal()
    其他 → portfolio.on_event() 或记录日志

双队列设计：
- input_queue: ExecutionNode → PortfolioProcessor（接收Kafka事件）
- output_queue: PortfolioProcessor → ExecutionNode（发送订单等）
- Portfolio通过put()发布事件，PortfolioProcessor转发到output_queue
"""

from threading import Thread
from queue import Queue, Empty
from typing import TYPE_CHECKING, Optional, List
from datetime import datetime
from enum import Enum

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.messaging import GinkgoConsumer
from ginkgo.interfaces.dtos import ControlCommandDTO
from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.libs import GLOG, GCONF


class PortfolioState(Enum):
    """Portfolio处理器状态机"""
    STARTING = "starting"      # 启动中
    RUNNING = "running"        # 运行中
    STOPPING = "stopping"      # 停止中（等待队列清空）
    STOPPED = "stopped"        # 已停止
    MIGRATING = "migrating"    # 迁移中


class PortfolioProcessor(Thread):
    """Portfolio运行控制器，管理Portfolio生命周期和事件路由"""

    # 事件类型映射表（路由规则）
    EVENT_ROUTES = {}

    def __init__(
        self,
        portfolio: PortfolioLive,
        input_queue: Queue,
        output_queue: Queue,
        max_queue_size: int = 1000
    ):
        """
        初始化Portfolio运行控制器

        Args:
            portfolio: PortfolioLive实例（ExecutionNode创建并持有）
            input_queue: Input Queue（接收市场数据事件）
            output_queue: Output Queue（发送订单等领域事件）
            max_queue_size: 队列最大大小（用于反压检查）
        """
        super().__init__(daemon=True)

        # Portfolio引用
        self.portfolio = portfolio
        self.portfolio_id = portfolio.portfolio_id

        # 队列
        self.input_queue = input_queue
        self.output_queue = output_queue
        self.max_queue_size = max_queue_size

        # 状态机
        self.state = PortfolioState.STARTING

        # 控制状态
        self.is_running = False      # 主循环控制
        self.is_paused = False       # 暂停控制（暂停时不处理数据）
        self.is_active = False       # Portfolio是否激活

        # 统计信息
        self.processed_count = 0     # 已处理事件数
        self.error_count = 0         # 错误计数
        self.last_event_time = None  # 最后处理事件时间

        # 设置Portfolio的事件发布回调（双队列模式）
        # Portfolio通过put()发布事件到此回调，回调转发到output_queue
        self.portfolio.set_event_publisher(self._handle_portfolio_event)

        # Kafka控制命令消费者（订阅ginkgo.live.control.commands）
        self._control_consumer: Optional[GinkgoConsumer] = None

        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: initialized")

    def start(self):
        """启动Portfolio处理器"""
        if self.is_running:
            GLOG.warn(f"PortfolioProcessor {self.portfolio_id} is already running")
            return

        # 初始化Kafka控制命令消费者
        try:
            self._control_consumer = GinkgoConsumer(
                bootstrap_servers=GCONF.get("kafka.bootstrap_servers", "localhost:9092"),
                group_id=f"portfolio_processor_{self.portfolio_id}"
            )
            self._control_consumer.subscribe([KafkaTopics.CONTROL_COMMANDS])
            GLOG.info(f"PortfolioProcessor {self.portfolio_id}: subscribed to {KafkaTopics.CONTROL_COMMANDS}")
        except Exception as e:
            GLOG.error(f"PortfolioProcessor {self.portfolio_id}: failed to subscribe to control commands: {e}")
            # 即使Kafka订阅失败，也允许启动（控制命令功能将不可用）

        self.is_running = True
        self.is_active = True
        self.state = PortfolioState.RUNNING
        super().start()
        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: started")

    def graceful_stop(self, timeout: float = 30.0):
        """
        优雅停止：处理完队列中剩余消息

        Args:
            timeout: 等待队列清空的最大超时时间（秒）

        流程：
        1. 设置状态为STOPPING
        2. 等待input_queue清空
        3. 保存Portfolio状态到数据库
        4. 停止主循环
        """
        if not self.is_running:
            print(f"[WARNING] PortfolioProcessor {self.portfolio_id} is not running")
            return False

        print(f"[INFO] Gracefully stopping PortfolioProcessor {self.portfolio_id}...")

        # 1. 设置状态为STOPPING
        self.state = PortfolioState.STOPPING
        print(f"[INFO] PortfolioProcessor {self.portfolio_id}: state = STOPPING")

        # 2. 等待input_queue清空（带超时）
        import time
        start_time = time.time()
        while self.input_queue.qsize() > 0:
            if time.time() - start_time > timeout:
                print(f"[WARNING] PortfolioProcessor {self.portfolio_id}: timeout waiting for queue to empty, size={self.input_queue.qsize()}")
                break
            time.sleep(0.1)

        remaining = self.input_queue.qsize()
        if remaining > 0:
            print(f"[WARNING] PortfolioProcessor {self.portfolio_id}: {remaining} events remain in queue")
        else:
            print(f"[INFO] PortfolioProcessor {self.portfolio_id}: queue empty")

        # 3. 保存Portfolio状态到数据库
        try:
            self.save_state()
            print(f"[INFO] PortfolioProcessor {self.portfolio_id}: state saved to database")
        except Exception as e:
            print(f"[ERROR] PortfolioProcessor {self.portfolio_id}: failed to save state: {e}")
            return False

        # 4. 停止主循环
        self.is_running = False
        self.is_active = False
        self.state = PortfolioState.STOPPED

        # 注意：不在这里 join，由 ExecutionNode 负责等待线程结束

        print(f"[INFO] PortfolioProcessor {self.portfolio_id}: gracefully stopped")
        return True

    def save_state(self):
        """
        保存Portfolio状态到数据库

        将Portfolio的持仓、现金等状态持久化到ClickHouse/MySQL，
        用于Portfolio迁移和故障恢复。
        """
        # 调用Portfolio的sync_state_to_db方法
        if hasattr(self.portfolio, 'sync_state_to_db'):
            success = self.portfolio.sync_state_to_db()
            if not success:
                raise Exception("sync_state_to_db failed")
        else:
            GLOG.warn(f"Portfolio {self.portfolio_id} does not support state persistence")

    def load_state(self):
        """
        从数据库加载Portfolio状态

        从ClickHouse/MySQL恢复Portfolio的持仓、现金等状态，
        用于Portfolio迁移和故障恢复。
        """
        # TODO: Phase 5实现
        # 1. 从数据库读取最新持仓状态
        # 2. 恢复Portfolio的cash、positions等
        # 3. 恢复Portfolio的时间戳
        GLOG.warn(f"PortfolioProcessor {self.portfolio_id}: load_state not implemented yet")

    def stop(self):
        """
        停止处理器（立即停止，不等待队列清空）

        注意：如需优雅停止（处理完队列中消息），请使用graceful_stop()
        """
        if not self.is_running:
            GLOG.warn(f"PortfolioProcessor {self.portfolio_id} is not running")
            return

        GLOG.info(f"Stopping PortfolioProcessor {self.portfolio_id}...")

        # 关闭Kafka控制命令消费者
        if self._control_consumer:
            try:
                self._control_consumer.close()
                GLOG.info(f"PortfolioProcessor {self.portfolio_id}: control consumer closed")
            except Exception as e:
                GLOG.error(f"PortfolioProcessor {self.portfolio_id}: failed to close control consumer: {e}")

        self.is_running = False
        self.is_active = False
        self.state = PortfolioState.STOPPED

        # 注意：不在这里 join，由 ExecutionNode 负责等待线程结束

    def pause(self):
        """
        暂停处理数据

        暂停后，主循环继续运行但不处理input_queue中的事件
        Portfolio保持状态，可以随时恢复
        """
        if not self.is_running:
            GLOG.warn(f"PortfolioProcessor {self.portfolio_id} is not running")
            return

        self.is_paused = True
        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: paused")

    def resume(self):
        """
        恢复处理数据

        恢复后，继续从input_queue获取并处理事件
        """
        if not self.is_running:
            GLOG.warn(f"PortfolioProcessor {self.portfolio_id} is not running")
            return

        self.is_paused = False
        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: resumed")

    def run(self):
        """
        主循环：Portfolio运行控制器核心逻辑

        类似于回测Engine的主循环：
        1. 检查运行状态
        2. 检查暂停状态
        3. 从input_queue获取事件
        4. 从Kafka获取控制命令
        5. 路由到Portfolio对应方法
        6. 更新统计信息
        7. 捕获异常，确保连续性
        """
        from ginkgo.trading.events.price_update import EventPriceUpdate
        from ginkgo.trading.events.order_lifecycle_events import (
            EventOrderPartiallyFilled,
            EventOrderCancelAck
        )
        from ginkgo.trading.events.signal_generation import EventSignalGeneration

        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: main loop started")

        while self.is_running:
            try:
                # 1. 检查暂停状态
                if self.is_paused:
                    # 暂停时不处理数据，休眠3秒
                    import time
                    time.sleep(3)
                    continue

                # 2. 从input_queue获取事件（超时0.1秒，快速轮询Kafka控制命令）
                try:
                    event = self.input_queue.get(timeout=0.1)
                    # 路由事件到Portfolio对应方法
                    self._route_event(event)
                    # 更新统计信息
                    self.processed_count += 1
                    self.last_event_time = datetime.now()
                except Empty:
                    # 超时，继续轮询Kafka控制命令
                    pass

                # 3. 从Kafka获取控制命令（非阻塞）
                self._process_control_commands()

            except Exception as e:
                # 捕获异常，记录错误但不中断循环
                self.error_count += 1
                GLOG.error(f"PortfolioProcessor {self.portfolio_id} error: {e}")
                continue

        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: main loop stopped")
        GLOG.info(f"PortfolioProcessor {self.portfolio_id}: processed {self.processed_count} events, {self.error_count} errors")

    def _route_event(self, event):
        """
        事件路由：根据事件类型调用Portfolio对应方法，收集返回值并转发到output_queue

        Args:
            event: 输入事件（EventPriceUpdate, EventOrderPartiallyFilled等）

        注意：
            - EventSignalGeneration是内部事件，PortfolioLive在on_price_update内部自己生成和处理
            - 这里只处理外部输入事件（Kafka消息）
        """
        from ginkgo.trading.events.price_update import EventPriceUpdate
        from ginkgo.trading.events.order_lifecycle_events import (
            EventOrderPartiallyFilled,
            EventOrderCancelAck
        )

        result = None
        try:
            # 根据事件类型路由并收集返回值
            if isinstance(event, EventPriceUpdate):
                result = self.portfolio.on_price_update(event)
            elif isinstance(event, EventOrderPartiallyFilled):
                result = self.portfolio.on_order_filled(event)
            elif isinstance(event, EventOrderCancelAck):
                result = self.portfolio.on_order_cancel_ack(event)
            else:
                # 未知事件类型，尝试使用通用处理
                if hasattr(self.portfolio, 'on_event'):
                    result = self.portfolio.on_event(event)
                else:
                    print(f"[WARNING] PortfolioProcessor {self.portfolio_id}: unhandled event type {type(event).__name__}")

        except Exception as e:
            print(f"[ERROR] PortfolioProcessor {self.portfolio_id}: failed to route event {type(event).__name__}: {e}")

        # 将返回值转发到output_queue（如果不为None）
        if result is not None:
            try:
                # 如果是单个事件，直接放入
                if not isinstance(result, list):
                    result = [result]

                # 批量放入output_queue
                for evt in result:
                    if evt is not None:
                        self.output_queue.put(evt, block=False)
                        print(f"[DEBUG] PortfolioProcessor {self.portfolio_id}: event {type(evt).__name__} sent to output_queue")

            except Exception as e:
                print(f"[ERROR] PortfolioProcessor {self.portfolio_id}: failed to put event to output_queue: {e}")

    # ========== 状态查询方法 ==========

    def get_queue_size(self) -> int:
        """获取input_queue中待处理的事件数量"""
        return self.input_queue.qsize()

    def get_queue_usage(self) -> float:
        """
        获取队列使用率

        Returns:
            float: 队列使用率（0.0-1.0），用于反压检查
        """
        if self.max_queue_size <= 0:
            return 0.0
        return self.input_queue.qsize() / self.max_queue_size

    def get_status(self) -> dict:
        """
        获取处理器完整状态

        Returns:
            dict: 包含运行状态、队列状态、统计信息等
        """
        return {
            "portfolio_id": self.portfolio_id,
            "state": self.state.value,  # 状态机：starting/running/stopping/stopped/migrating
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "is_active": self.is_active,
            "is_alive": self.is_alive(),
            "queue_size": self.get_queue_size(),
            "queue_usage": self.get_queue_usage(),
            "queue_maxsize": self.max_queue_size,
            "processed_count": self.processed_count,
            "error_count": self.error_count,
            "last_event_time": self.last_event_time.isoformat() if self.last_event_time else None
        }

    def _handle_portfolio_event(self, event):
        """
        处理Portfolio通过put()发布的事件（双队列模式回调）

        这是Portfolio.set_event_publisher()的回调函数，当Portfolio调用
        self.put(event)时，事件会被转发到此方法，然后发送到output_queue。

        Args:
            event: Portfolio发布的事件（通常是Order、Signal等）

        注意：
            - 此方法运行在PortfolioProcessor线程中
            - 使用非阻塞put()避免死锁
            - 捕获异常确保不会中断Portfolio线程
        """
        try:
            # 非阻塞放入output_queue
            self.output_queue.put(event, block=False)
            GLOG.debug(f"PortfolioProcessor {self.portfolio_id}: Portfolio event {type(event).__name__} sent to output_queue")
        except Exception as e:
            # Queue满时记录警告，但不抛异常（避免中断Portfolio）
            GLOG.warn(f"PortfolioProcessor {self.portfolio_id}: failed to put Portfolio event to output_queue: {e}")

    # ========== Kafka控制命令处理 ==========

    def _process_control_commands(self) -> None:
        """
        处理Kafka控制命令（非阻塞）

        从Kafka的ginkgo.live.control.commands topic消费控制命令，
        解析后路由到对应的处理方法。
        """
        if not self._control_consumer:
            return

        try:
            # 非阻塞poll，超时10ms
            messages = self._control_consumer.poll(timeout_ms=10)

            for topic_partition, records in messages.items():
                for record in records:
                    try:
                        # 解析Kafka消息
                        self._handle_control_command(record.value)
                    except Exception as e:
                        GLOG.error(f"PortfolioProcessor {self.portfolio_id}: failed to handle control command: {e}")

        except Exception as e:
            # Kafka消费异常不中断主循环
            GLOG.error(f"PortfolioProcessor {self.portfolio_id}: Kafka poll error: {e}")

    def _handle_control_command(self, message: bytes) -> None:
        """
        处理控制命令

        解析Kafka消息中的ControlCommandDTO，根据命令类型路由到对应处理方法。

        Args:
            message: Kafka消息（JSON字节序列）

        支持的命令类型：
            - update_selector: 触发selector.pick()，发布EventInterestUpdate
            - bar_snapshot: 由DataManager处理，PortfolioProcessor忽略
            - update_data: 由DataManager处理，PortfolioProcessor忽略
        """
        try:
            # 解析JSON
            import json
            message_str = message.decode('utf-8') if isinstance(message, bytes) else message
            command_data = json.loads(message_str)

            # 使用ControlCommandDTO解析
            command_dto = ControlCommandDTO(**command_data)

            # 路由命令到对应处理方法
            if command_dto.command == ControlCommandDTO.Commands.UPDATE_SELECTOR:
                GLOG.info(f"PortfolioProcessor {self.portfolio_id}: received update_selector command")
                self._update_selectors()
            elif command_dto.command == ControlCommandDTO.Commands.BAR_SNAPSHOT:
                # bar_snapshot由DataManager处理，PortfolioProcessor忽略
                GLOG.debug(f"PortfolioProcessor {self.portfolio_id}: ignoring bar_snapshot command (handled by DataManager)")
            elif command_dto.command == ControlCommandDTO.Commands.UPDATE_DATA:
                # update_data由DataManager处理，PortfolioProcessor忽略
                GLOG.debug(f"PortfolioProcessor {self.portfolio_id}: ignoring update_data command (handled by DataManager)")
            else:
                GLOG.warn(f"PortfolioProcessor {self.portfolio_id}: unknown command type: {command_dto.command}")

        except json.JSONDecodeError as e:
            GLOG.error(f"PortfolioProcessor {self.portfolio_id}: invalid JSON in control command: {e}")
        except Exception as e:
            GLOG.error(f"PortfolioProcessor {self.portfolio_id}: failed to parse control command: {e}")

    def _update_selectors(self) -> None:
        """
        触发Selector选股，发布EventInterestUpdate到Kafka

        流程：
        1. 遍历portfolio._selectors
        2. 调用每个selector.pick(time)
        3. 收集所有选中的codes
        4. 创建EventInterestUpdate
        5. 发布到output_queue（由ExecutionNode转发到Kafka）

        注意：
            - selector.pick()可能抛异常，需要捕获并继续处理其他selector
            - 空selector列表是合法场景，返回空codes
            - EventInterestUpdate会被发布到Kafka的ginkgo.live.interest.updates topic
        """
        try:
            from ginkgo.trading.events.interest_update import EventInterestUpdate

            # 收集所有选中的codes
            all_codes: List[str] = []

            # 遍历所有selectors
            if hasattr(self.portfolio, '_selectors') and self.portfolio._selectors:
                for selector in self.portfolio._selectors:
                    try:
                        # 调用selector.pick()获取选中codes
                        current_time = datetime.now()
                        codes = selector.pick(current_time)

                        if codes:
                            all_codes.extend(codes)
                            GLOG.debug(f"PortfolioProcessor {self.portfolio_id}: selector {type(selector).__name__} picked {len(codes)} codes")

                    except Exception as e:
                        # selector异常不中断整体流程
                        GLOG.error(f"PortfolioProcessor {self.portfolio_id}: selector {type(selector).__name__}.pick() failed: {e}")
                        continue
            else:
                GLOG.debug(f"PortfolioProcessor {self.portfolio_id}: no selectors configured")

            # 去重
            all_codes = list(dict.fromkeys(all_codes))

            # 创建EventInterestUpdate
            event = EventInterestUpdate(
                portfolio_id=self.portfolio_id,
                codes=all_codes,
                timestamp=datetime.now()
            )

            # 发布到output_queue（由ExecutionNode转发到Kafka）
            self.output_queue.put(event, block=False)
            GLOG.info(f"PortfolioProcessor {self.portfolio_id}: EventInterestUpdate published with {len(all_codes)} codes")

        except Exception as e:
            GLOG.error(f"PortfolioProcessor {self.portfolio_id}: _update_selectors failed: {e}")
