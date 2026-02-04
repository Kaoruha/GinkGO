# Upstream: LiveDataFeeder/BarService (实时数据源/历史K线)
# Downstream: ExecutionNode (通过Kafka)
# Role: 实时数据管理器 - 管理LiveDataFeeder，推送当日K线数据

import asyncio
import json
import threading
import time
from typing import Set, Optional, Dict, Any, List
from datetime import datetime, timedelta
from queue import Queue

from ginkgo.interfaces.kafka_topics import KafkaTopics
from ginkgo.interfaces.dtos import (
    PriceUpdateDTO,
    BarDTO,
    InterestUpdateDTO,
    ControlCommandDTO,
)
from ginkgo.trading.feeders.eastmoney_feeder import EastMoneyFeeder
from ginkgo.trading.feeders.fushu_feeder import FuShuFeeder
from ginkgo.trading.feeders.alpaca_feeder import AlpacaFeeder
from ginkgo.libs import GLOG, GCONF
from ginkgo.libs.utils.common import retry
from ginkgo.messaging import GinkgoProducer, GinkgoConsumer


class DataManager(threading.Thread):
    """
    实时数据管理器

    职责：
    1. 管理实时数据源（LiveDataFeeder，多态创建）
    2. 订阅Kafka消息（interest.updates + control.commands）
    3. 接收实时Tick数据并转换为DTO
    4. 发布实时数据到Kafka
    5. 接收bar_snapshot命令，推送当日K线数据

    数据流：
    - LiveDataFeeder → DataManager → Kafka → ExecutionNode
    - TaskTimer → Kafka → DataManager → BarService → Kafka → ExecutionNode
    """

    def __init__(self, feeder_type: str = "eastmoney"):
        """
        初始化DataManager

        Args:
            feeder_type: LiveDataFeeder类型（eastmoney/fushu/alpaca）
        """
        super().__init__(daemon=True)

        # LiveDataFeeder管理（多态）
        self.live_feeder = self._create_feeder(feeder_type)
        self._feeder_type = feeder_type
        self._feeder_lock = threading.Lock()

        # 订阅管理
        self.all_symbols: Set[str] = set()
        self._symbol_lock = threading.Lock()

        # Kafka组件
        self._producer: Optional[GinkgoProducer] = None
        self._consumer_interest: Optional[GinkgoConsumer] = None
        self._consumer_control: Optional[GinkgoConsumer] = None

        # 运行状态
        self._running = threading.Event()
        self._stopped = threading.Event()

        # 数据队列（用于LiveDataFeeder推送）
        self._data_queue: Queue = Queue(maxsize=10000)

        GLOG.INFO(f"DataManager initialized with feeder_type: {feeder_type}")

    def _create_feeder(self, feeder_type: str) -> Any:
        """
        多态创建LiveDataFeeder实例

        Args:
            feeder_type: Feeder类型

        Returns:
            LiveDataFeeder实例
        """
        feeders = {
            "eastmoney": EastMoneyFeeder,
            "fushu": FuShuFeeder,
            "alpaca": AlpacaFeeder,
        }

        feeder_class = feeders.get(feeder_type)
        if not feeder_class:
            raise ValueError(f"Unknown feeder_type: {feeder_type}")

        return feeder_class()

    def start(self) -> bool:
        """
        启动DataManager

        Returns:
            bool: 启动是否成功
        """
        try:
            GLOG.INFO("DataManager starting...")

            # 初始化Kafka Producer
            self._producer = GinkgoProducer()

            # 初始化LiveDataFeeder
            with self._feeder_lock:
                if not self.live_feeder.initialize():
                    GLOG.ERROR("Failed to initialize LiveDataFeeder")
                    return False

                # 设置事件发布器
                self.live_feeder.set_event_publisher(self._on_live_data_received)

                # 启动LiveDataFeeder
                if not self.live_feeder.start():
                    GLOG.ERROR("Failed to start LiveDataFeeder")
                    return False

            # 启动主线程
            self._running.set()
            self.start()

            GLOG.INFO("DataManager started successfully")

            # 发送启动通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                from datetime import datetime
                notify(
                    "DataManager启动成功",
                    level="INFO",
                    module="DataManager",
                    details={
                        "组件": "DataManager",
                        "数据源": self.live_feeder.__class__.__name__,
                        "启动时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception as notify_error:
                GLOG.WARNING(f"Failed to send start notification: {notify_error}")

            return True

        except Exception as e:
            GLOG.ERROR(f"DataManager start failed: {e}")

            # 发送失败通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"DataManager启动失败: {e}",
                    level="ERROR",
                    module="DataManager",
                    details={
                        "组件": "DataManager",
                        "错误信息": str(e),
                    },
                )
            except Exception:
                pass

            return False

    def stop(self) -> bool:
        """
        停止DataManager

        Returns:
            bool: 停止是否成功
        """
        try:
            GLOG.INFO("DataManager stopping...")

            # 停止运行标志
            self._running.clear()
            self._stopped.set()

            # 停止LiveDataFeeder
            with self._feeder_lock:
                if self.live_feeder:
                    self.live_feeder.stop()

            # 关闭Kafka组件
            if self._consumer_interest:
                self._consumer_interest.close()
            if self._consumer_control:
                self._consumer_control.close()
            if self._producer:
                self._producer.close()

            # 等待线程结束
            self.join(timeout=10)

            GLOG.INFO("DataManager stopped")

            # 发送停止通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                from datetime import datetime
                notify(
                    "DataManager已停止",
                    level="INFO",
                    module="DataManager",
                    details={
                        "组件": "DataManager",
                        "停止时间": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    },
                )
            except Exception as notify_error:
                GLOG.WARNING(f"Failed to send stop notification: {notify_error}")

            return True

        except Exception as e:
            GLOG.ERROR(f"DataManager stop failed: {e}")

            # 发送失败通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    f"DataManager停止失败: {e}",
                    level="ERROR",
                    module="DataManager",
                    details={
                        "组件": "DataManager",
                        "错误信息": str(e),
                    },
                )
            except Exception:
                pass

            return False

    def run(self) -> None:
        """
        主循环 - 订阅Kafka消息

        订阅两个Topic：
        1. ginkgo.live.interest.updates - 订阅更新
        2. ginkgo.live.control.commands - 控制命令
        """
        GLOG.INFO("DataManager main loop started")

        # 创建Kafka Consumers
        bootstrap_servers = f"{GCONF.KAFKAHOST}:{GCONF.KAFKAPORT}"
        self._consumer_interest = GinkgoConsumer(
            topic=KafkaTopics.INTEREST_UPDATES,
            group_id="data_manager_interest_group",
            bootstrap_servers=bootstrap_servers,
        )

        self._consumer_control = GinkgoConsumer(
            topic=KafkaTopics.CONTROL_COMMANDS,
            group_id="data_manager_control_group",
            bootstrap_servers=bootstrap_servers,
        )

        while not self._stopped.is_set():
            try:
                # 处理interest updates
                self._process_interest_updates()

                # 处理control commands
                self._process_control_commands()

                # 短暂休眠避免CPU占用
                time.sleep(0.1)

            except Exception as e:
                GLOG.ERROR(f"DataManager main loop error: {e}")
                time.sleep(1)

        GLOG.INFO("DataManager main loop ended")

    def _process_interest_updates(self) -> None:
        """处理interest updates消息"""
        try:
            for message in self._consumer_interest.consume(timeout_ms=100):
                try:
                    dto = InterestUpdateDTO.model_validate_json(message.value)
                    self.update_subscriptions(dto)
                except Exception as e:
                    GLOG.ERROR(f"Failed to process interest update: {e}")
        except Exception as e:
            pass  # 超时是正常的

    def _process_control_commands(self) -> None:
        """处理control commands消息"""
        try:
            for message in self._consumer_control.consume(timeout_ms=100):
                try:
                    dto = ControlCommandDTO.model_validate_json(message.value)
                    self._handle_control_command(dto)
                except Exception as e:
                    GLOG.ERROR(f"Failed to process control command: {e}")
        except Exception as e:
            pass  # 超时是正常的

    def update_subscriptions(self, dto: InterestUpdateDTO) -> None:
        """
        更新订阅标的

        Args:
            dto: InterestUpdateDTO
        """
        try:
            with self._symbol_lock:
                if dto.is_replace():
                    self.all_symbols = dto.get_all_symbols()
                elif dto.is_add():
                    self.all_symbols.update(dto.get_all_symbols())
                elif dto.is_remove():
                    self.all_symbols.difference_update(dto.get_all_symbols())

            # 更新LiveDataFeeder订阅
            with self._feeder_lock:
                if self.live_feeder and self.all_symbols:
                    self.live_feeder.subscribe_symbols(list(self.all_symbols))
                    self.live_feeder.start_subscription()

            GLOG.INFO(f"Subscriptions updated: {len(self.all_symbols)} symbols")

        except Exception as e:
            GLOG.ERROR(f"Failed to update subscriptions: {e}")

    def _handle_control_command(self, dto: ControlCommandDTO) -> None:
        """
        处理控制命令

        Args:
            dto: ControlCommandDTO
        """
        try:
            if dto.is_stockinfo():
                GLOG.INFO("Received stockinfo command (handled by TaskTimer, ignoring)")
            elif dto.is_adjustfactor():
                GLOG.INFO("Received adjustfactor command (handled by TaskTimer, ignoring)")
            elif dto.is_bar_snapshot():
                GLOG.INFO("Received bar_snapshot command (handled by TaskTimer, ignoring)")
            elif dto.is_tick():
                GLOG.INFO("Received tick command (handled by TaskTimer, ignoring)")
            elif dto.is_update_selector():
                GLOG.INFO("Received update_selector command (ignored by DataManager)")
            elif dto.is_update_data():
                GLOG.INFO("Received update_data command (deprecated, use individual commands)")
            else:
                GLOG.WARN(f"Unknown control command: {dto.command}")

        except Exception as e:
            GLOG.ERROR(f"Failed to handle control command: {e}")

    @retry(max_try=3, backoff_factor=2)
    def _publish_to_kafka(self, topic: str, message: str) -> None:
        """
        发布消息到Kafka（带重试）

        Args:
            topic: Kafka主题
            message: JSON消息
        """
        if self._producer:
            self._producer.send(topic=topic, message=message)
            GLOG.DEBUG(f"Published to {topic}")

    def _on_live_data_received(self, event) -> None:
        """
        实时数据接收回调

        Args:
            event: EventPriceUpdate事件
        """
        try:
            # 转换为DTO
            if hasattr(event, 'event_type') and event.event_type.value == 1:  # PRICE_UPDATE
                dto = PriceUpdateDTO(
                    symbol=event.code,
                    timestamp=event.timestamp,
                    price=getattr(event, 'price', None),
                    bid_price=getattr(event, 'bid_price', None),
                    ask_price=getattr(event, 'ask_price', None),
                    bid_volume=getattr(event, 'bid_volume', None),
                    ask_volume=getattr(event, 'ask_volume', None),
                    volume=getattr(event, 'volume', None),
                    amount=getattr(event, 'amount', None),
                    source=self._feeder_type,
                )

                # 发布到Kafka（带重试）
                self._publish_to_kafka(
                    topic=KafkaTopics.MARKET_DATA,
                    message=dto.model_dump_json(),
                )
                GLOG.DEBUG(f"Published PriceUpdateDTO to Kafka: {event.code}")

        except Exception as e:
            GLOG.ERROR(f"Failed to process live data: {e}")

    def subscribe_live_data(self, symbols: List[str]) -> None:
        """
        订阅实时数据

        Args:
            symbols: 股票代码列表
        """
        try:
            with self._feeder_lock:
                if self.live_feeder:
                    self.live_feeder.subscribe_symbols(symbols, data_types=["price_update"])
                    self.live_feeder.start_subscription()

            GLOG.INFO(f"Subscribed to live data for {len(symbols)} symbols")

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe live data: {e}")
