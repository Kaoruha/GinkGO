# Upstream: LiveDataFeeder/BarService (实时数据源/历史K线)
# Downstream: ExecutionNode (通过Kafka)
# Role: 实时数据管理器 - 管理多个LiveDataFeeder，支持多数据源接入


"""
实时数据管理器（多数据源支持）

职责：
1. 管理多个实时数据源（多 LiveDataFeeder 实例）
2. 根据数据源类型自动路由订阅请求
3. 统一事件发布到 Kafka
4. 支持动态添加/移除数据源

数据流：
- LiveDataFeeder (多个) → DataManager → Kafka → ExecutionNode

支持的数据源：
- eastmoney: A股实时行情
- fushu: 辅助数据源
- alpaca: 美股数据
- okx: 加密货币数据（WebSocket + REST API）
"""

import re
import threading
import time
from typing import Set, Optional, Dict, Any, List, Callable
from datetime import datetime
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
from ginkgo.trading.feeders.okx_data_feeder import OKXDataFeeder
from ginkgo.trading.events.base_event import EventBase
from ginkgo.libs import GLOG, GCONF
from ginkgo.libs.utils.common import retry
from ginkgo.messaging import GinkgoProducer, GinkgoConsumer


class DataManager(threading.Thread):
    """
    实时数据管理器（多数据源版本）

    特性：
    - 支持同时接入多个数据源
    - 根据代码格式自动路由到正确的 feeder
    - 统一事件发布接口
    - 动态数据源管理
    """

    # 数据源模式（用于自动路由）
    SOURCE_PATTERNS = {
        "okx": re.compile(r'^[A-Z]+-[A-Z]+$'),  # BTC-USDT, ETH-USDT
        "eastmoney": re.compile(r'^\d{6}\.(SZ|SH)$'),  # 000001.SZ
        "alpaca": re.compile(r'^[A-Z]+$'),  # AAPL (美股，需要更复杂的判断)
        "fushu": re.compile(r'^\d{6}$'),  # 000001 (纯数字)
    }

    def __init__(self, feeder_types: Optional[List[str]] = None):
        """
        初始化 DataManager

        Args:
            feeder_types: 要启动的数据源列表，如 ["eastmoney", "okx"]
                         如果为 None，则默认启动 ["eastmoney"]
        """
        super().__init__(daemon=True)

        # 多个 LiveDataFeeder 管理
        self._feeders: Dict[str, Any] = {}  # feeder_type -> feeder_instance
        self._feeder_configs: Dict[str, Dict[str, Any]] = {}  # feeder_type -> config
        self._feeder_lock = threading.Lock()

        # 订阅管理（按数据源分组）
        self._symbols_by_source: Dict[str, Set[str]] = {}  # source -> symbols
        self._symbol_to_source: Dict[str, str] = {}  # symbol -> source
        self._symbol_lock = threading.Lock()

        # Kafka 组件
        self._producer: Optional[GinkgoProducer] = None
        self._consumer_interest: Optional[GinkgoConsumer] = None
        self._consumer_control: Optional[GinkgoConsumer] = None

        # 运行状态
        self._running = threading.Event()
        self._stopped = threading.Event()

        # Feeder 类映射
        self._feeder_classes = {
            "eastmoney": EastMoneyFeeder,
            "fushu": FuShuFeeder,
            "alpaca": AlpacaFeeder,
            "okx": OKXDataFeeder,
        }

        # 初始化指定的数据源
        feeder_types = feeder_types or ["eastmoney"]
        for feeder_type in feeder_types:
            self._initialize_feeder(feeder_type)

        GLOG.INFO(f"DataManager initialized with sources: {list(self._feeders.keys())}")

    def _initialize_feeder(self, feeder_type: str, config: Dict[str, Any] = None) -> bool:
        """
        初始化单个数据源

        Args:
            feeder_type: 数据源类型
            config: 配置参数

        Returns:
            bool: 是否成功
        """
        try:
            if feeder_type in self._feeders:
                GLOG.WARNING(f"Feeder {feeder_type} already initialized")
                return True

            feeder_class = self._feeder_classes.get(feeder_type)
            if not feeder_class:
                GLOG.ERROR(f"Unknown feeder type: {feeder_type}")
                return False

            # 创建 feeder 实例
            if config:
                feeder = feeder_class(**config)
            else:
                feeder = feeder_class()

            # 保存配置
            self._feeder_configs[feeder_type] = config or {}
            self._feeders[feeder_type] = feeder
            self._symbols_by_source[feeder_type] = set()

            GLOG.INFO(f"Feeder {feeder_type} initialized: {feeder.__class__.__name__}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to initialize feeder {feeder_type}: {e}")
            return False

    def add_feeder(self, feeder_type: str, config: Dict[str, Any] = None) -> bool:
        """
        动态添加数据源

        Args:
            feeder_type: 数据源类型
            config: 配置参数

        Returns:
            bool: 是否成功
        """
        with self._feeder_lock:
            if not self._initialize_feeder(feeder_type, config):
                return False

            feeder = self._feeders[feeder_type]

            # 设置事件发布器
            feeder.set_event_publisher(lambda event: self._on_live_data_received(event, feeder_type))

            # 如果 DataManager 正在运行，启动新的 feeder
            if self._running.is_set():
                if feeder.initialize():
                    if feeder.start():
                        GLOG.INFO(f"Feeder {feeder_type} started")
                        return True

            return True

    def remove_feeder(self, feeder_type: str) -> bool:
        """
        移除数据源

        Args:
            feeder_type: 数据源类型

        Returns:
            bool: 是否成功
        """
        with self._feeder_lock:
            if feeder_type not in self._feeders:
                GLOG.WARNING(f"Feeder {feeder_type} not found")
                return False

            feeder = self._feeders[feeder_type]

            # 停止 feeder
            try:
                feeder.stop()
            except Exception as e:
                GLOG.ERROR(f"Error stopping feeder {feeder_type}: {e}")

            # 清理订阅
            if feeder_type in self._symbols_by_source:
                for symbol in self._symbols_by_source[feeder_type]:
                    self._symbol_to_source.pop(symbol, None)
                del self._symbols_by_source[feeder_type]

            # 移除 feeder
            del self._feeders[feeder_type]
            del self._feeder_configs[feeder_type]

            GLOG.INFO(f"Feeder {feeder_type} removed")
            return True

    def _detect_source(self, symbol: str) -> Optional[str]:
        """
        根据代码格式检测数据源

        Args:
            symbol: 代码

        Returns:
            str: 数据源类型或 None
        """
        for source, pattern in self.SOURCE_PATTERNS.items():
            if pattern.match(symbol):
                return source

        # 默认返回第一个可用的 feeder
        if self._feeders:
            return list(self._feeders.keys())[0]

        return None

    def start(self) -> bool:
        """
        启动 DataManager

        Returns:
            bool: 启动是否成功
        """
        try:
            GLOG.INFO("DataManager starting...")

            # 初始化 Kafka Producer
            self._producer = GinkgoProducer()

            # 启动所有 feeders
            with self._feeder_lock:
                for feeder_type, feeder in self._feeders.items():
                    if not feeder.initialize():
                        GLOG.ERROR(f"Failed to initialize feeder {feeder_type}")
                        continue

                    # 设置事件发布器
                    feeder.set_event_publisher(lambda event, ft=feeder_type: self._on_live_data_received(event, ft))

                    # 启动 feeder
                    if not feeder.start():
                        GLOG.ERROR(f"Failed to start feeder {feeder_type}")
                        continue

                    GLOG.INFO(f"Feeder {feeder_type} started")

            # 启动主线程
            self._running.set()
            self.start()

            GLOG.INFO("DataManager started successfully")

            # 发送启动通知
            try:
                from ginkgo.notifier.core.notification_service import notify
                notify(
                    "DataManager启动成功",
                    level="INFO",
                    module="DataManager",
                    details={
                        "组件": "DataManager",
                        "数据源": list(self._feeders.keys()),
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
                    details={"组件": "DataManager", "错误信息": str(e)},
                )
            except Exception:
                pass

            return False

    def stop(self) -> bool:
        """
        停止 DataManager

        Returns:
            bool: 停止是否成功
        """
        try:
            GLOG.INFO("DataManager stopping...")

            # 停止运行标志
            self._running.clear()
            self._stopped.set()

            # 停止所有 feeders
            with self._feeder_lock:
                for feeder_type, feeder in self._feeders.items():
                    try:
                        feeder.stop()
                        GLOG.INFO(f"Feeder {feeder_type} stopped")
                    except Exception as e:
                        GLOG.ERROR(f"Error stopping feeder {feeder_type}: {e}")

            # 关闭 Kafka 组件
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
            return False

    def run(self) -> None:
        """
        主循环 - 订阅 Kafka 消息

        订阅两个 Topic：
        1. ginkgo.live.interest.updates - 订阅更新
        2. ginkgo.live.control.commands - 控制命令
        """
        GLOG.INFO("DataManager main loop started")

        # 创建 Kafka Consumers
        self._consumer_interest = GinkgoConsumer(
            topic=KafkaTopics.INTEREST_UPDATES,
            group_id="data_manager_interest_group",
        )

        self._consumer_control = GinkgoConsumer(
            topic=KafkaTopics.CONTROL_COMMANDS,
            group_id="data_manager_control_group",
        )

        while not self._stopped.is_set():
            try:
                # 处理 interest updates
                self._process_interest_updates()

                # 处理 control commands
                self._process_control_commands()

                # 短暂休眠避免 CPU 占用
                time.sleep(0.1)

            except Exception as e:
                GLOG.ERROR(f"DataManager main loop error: {e}")
                time.sleep(1)

        GLOG.INFO("DataManager main loop ended")

    def _process_interest_updates(self) -> None:
        """处理 interest updates 消息"""
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
        """处理 control commands 消息"""
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

        根据代码格式自动路由到正确的数据源

        Args:
            dto: InterestUpdateDTO
        """
        try:
            with self._symbol_lock:
                if dto.is_replace():
                    # 替换所有订阅
                    self._symbol_to_source.clear()
                    for source in self._symbols_by_source:
                        self._symbols_by_source[source].clear()

                    # 重新分配
                    for symbol in dto.get_all_symbols():
                        source = self._detect_source(symbol)
                        if source and source in self._feeders:
                            self._symbol_to_source[symbol] = source
                            self._symbols_by_source[source].add(symbol)

                elif dto.is_add():
                    # 添加订阅
                    for symbol in dto.get_all_symbols():
                        source = self._detect_source(symbol)
                        if source and source in self._feeders:
                            self._symbol_to_source[symbol] = source
                            self._symbols_by_source[source].add(symbol)

                elif dto.is_remove():
                    # 移除订阅
                    for symbol in dto.get_all_symbols():
                        source = self._symbol_to_source.pop(symbol, None)
                        if source and source in self._symbols_by_source:
                            self._symbols_by_source[source].discard(symbol)

            # 更新每个 feeder 的订阅
            with self._feeder_lock:
                for source, feeder in self._feeders.items():
                    symbols = list(self._symbols_by_source.get(source, set()))
                    if symbols:
                        feeder.subscribe_symbols(symbols)
                        feeder.start_subscription()

            total_symbols = sum(len(s) for s in self._symbols_by_source.values())
            GLOG.INFO(f"Subscriptions updated: {total_symbols} symbols across {len(self._feeders)} sources")

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
                GLOG.WARNING(f"Unknown control command: {dto.command}")

        except Exception as e:
            GLOG.ERROR(f"Failed to handle control command: {e}")

    @retry(max_try=3, backoff_factor=2)
    def _publish_to_kafka(self, topic: str, message: str) -> None:
        """
        发布消息到 Kafka（带重试）

        Args:
            topic: Kafka 主题
            message: JSON 消息
        """
        if self._producer:
            self._producer.send(topic=topic, message=message)
            GLOG.DEBUG(f"Published to {topic}")

    def _on_live_data_received(self, event: EventBase, source: str) -> None:
        """
        实时数据接收回调

        Args:
            event: EventPriceUpdate 事件
            source: 数据源类型
        """
        try:
            # 转换为 DTO
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
                    source=source,
                )

                # 发布到 Kafka（带重试）
                self._publish_to_kafka(
                    topic=KafkaTopics.MARKET_DATA,
                    message=dto.model_dump_json(),
                )
                GLOG.DEBUG(f"Published PriceUpdateDTO to Kafka: {event.code} (source: {source})")

        except Exception as e:
            GLOG.ERROR(f"Failed to process live data: {e}")

    def subscribe_live_data(self, symbols: List[str], source: Optional[str] = None) -> None:
        """
        订阅实时数据

        Args:
            symbols: 股票代码列表
            source: 指定数据源（可选），如果为 None 则自动检测
        """
        try:
            with self._symbol_lock:
                for symbol in symbols:
                    # 确定数据源
                    if source:
                        target_source = source
                    else:
                        target_source = self._detect_source(symbol)

                    if not target_source or target_source not in self._feeders:
                        GLOG.WARNING(f"No suitable feeder for symbol: {symbol}")
                        continue

                    # 记录订阅
                    self._symbol_to_source[symbol] = target_source
                    self._symbols_by_source[target_source].add(symbol)

            # 更新 feeder 订阅
            with self._feeder_lock:
                for feeder_type, feeder in self._feeders.items():
                    symbols_for_feeder = list(self._symbols_by_source.get(feeder_type, set()))
                    if symbols_for_feeder:
                        feeder.subscribe_symbols(symbols_for_feeder)
                        feeder.start_subscription()

            total_symbols = sum(len(s) for s in self._symbols_by_source.values())
            GLOG.INFO(f"Subscribed to live data for {total_symbols} symbols")

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe live data: {e}")

    def get_status(self) -> Dict[str, Any]:
        """
        获取 DataManager 状态

        Returns:
            Dict[str, Any]: 状态信息
        """
        with self._feeder_lock:
            feeder_status = {}
            for feeder_type, feeder in self._feeders.items():
                if hasattr(feeder, 'get_connection_info'):
                    feeder_status[feeder_type] = feeder.get_connection_info()
                else:
                    feeder_status[feeder_type] = {"status": "unknown"}

            return {
                "is_running": self._running.is_set(),
                "feeders": feeder_status,
                "symbols_by_source": {
                    source: list(symbols)
                    for source, symbols in self._symbols_by_source.items()
                },
                "total_symbols": sum(len(s) for s in self._symbols_by_source.values()),
            }
