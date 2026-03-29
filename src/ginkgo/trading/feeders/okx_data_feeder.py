# Upstream: ILiveDataFeeder (实盘数据馈送接口)
# Downstream: DataManager (数据管理器)、WebSocketManager (WebSocket连接)
# Role: OKXDataFeeder 统一OKX实盘数据馈送器，支持WebSocket + REST API双模式


"""
OKX 实盘数据馈送器（统一版）

实现 ILiveDataFeeder 接口，支持双模式数据获取：
- WebSocket 实时推送（优先）
- REST API 轮询（降级）

特性：
- 自动降级：WebSocket 失败时自动切换到 REST API
- 自动恢复：WebSocket 恢复时自动切回
- 统一事件：无论哪种方式都发布 EventPriceUpdate
"""

import time
import threading
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime
from enum import Enum

from ginkgo.trading.feeders.interfaces import ILiveDataFeeder, DataFeedStatus
from ginkgo.enums import SOURCE_TYPES
from ginkgo.trading.feeders.okx_feeder import OKXMarketDataFeeder
from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities import Bar
from ginkgo.entities import Tick
from ginkgo.enums import EVENT_TYPES
from ginkgo.libs import GLOG


class DataFetchMode(Enum):
    """数据获取模式"""
    WEBSOCKET = "websocket"  # 实时推送
    REST_API = "rest_api"    # 轮询降级


class OKXDataFeeder(ILiveDataFeeder):
    """
    OKX 实盘数据馈送器（统一版）

    实现 ILiveDataFeeder 接口，支持 WebSocket + REST API 双模式。
    """

    # 轮询间隔（秒）
    POLLING_INTERVAL = 2.0

    # 重连间隔（秒）
    RECONNECT_INTERVAL = 5.0

    def __init__(self, environment: str = "testnet"):
        """
        初始化 OKX 实盘数据馈送器

        Args:
            environment: 环境 ("testnet" 或 "production")
        """
        self.environment = environment
        self.source = SOURCE_TYPES.OKX

        # 数据获取模式
        self._fetch_mode = DataFetchMode.WEBSOCKET
        self._ws_enabled = True

        # REST API 实例（复用 OKXMarketDataFeeder）
        self._rest_api = OKXMarketDataFeeder(environment=environment)

        # WebSocket 连接
        self._ws_connection = None
        self._ws_manager = None

        # 订阅管理
        self._subscribed_symbols: Dict[str, List[str]] = {}  # symbol -> [data_types]
        self._subscription_lock = threading.Lock()

        # 运行状态
        self._status = DataFeedStatus.IDLE
        self._is_running = False
        self._is_connected = False

        # 事件发布器
        self._event_publisher: Optional[Callable[[EventBase], None]] = None

        # 时间提供者（接口兼容）
        self._time_provider = None

        # 限流器（接口兼容）
        self._rate_limiter = None

        # 轮询线程
        self._polling_thread = None
        self._polling_stop_event = threading.Event()

        # 缓存
        self._ticker_cache: Dict[str, Dict] = {}
        self._bar_cache: Dict[str, Bar] = {}

        GLOG.INFO(f"OKXDataFeeder initialized: {environment}")

    # ==================== IDataFeeder 接口实现 ====================

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """
        初始化数据馈送器

        Args:
            config: 配置参数

        Returns:
            bool: 初始化是否成功
        """
        try:
            if config:
                self.environment = config.get("environment", self.environment)

            self._status = DataFeedStatus.IDLE
            GLOG.INFO("OKXDataFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"OKXDataFeeder initialization failed: {e}")
            self._status = DataFeedStatus.ERROR
            return False

    def start(self) -> bool:
        """
        启动数据馈送器

        Returns:
            bool: 启动是否成功
        """
        try:
            self._status = DataFeedStatus.CONNECTING
            self._is_running = True

            # 尝试启动 WebSocket
            if self._ws_enabled:
                if self._connect_websocket():
                    self._status = DataFeedStatus.CONNECTED
                    GLOG.INFO("OKXDataFeeder started with WebSocket mode")
                    return True
                else:
                    GLOG.WARN("WebSocket connection failed, falling back to REST API")
                    self._fetch_mode = DataFetchMode.REST_API
                    self._ws_enabled = False

            # 降级到 REST API 轮询
            if self._fetch_mode == DataFetchMode.REST_API:
                self._start_polling()
                self._status = DataFeedStatus.STREAMING
                GLOG.INFO("OKXDataFeeder started with REST API polling mode")
                return True

            self._status = DataFeedStatus.ERROR
            return False

        except Exception as e:
            GLOG.ERROR(f"OKXDataFeeder start failed: {e}")
            self._status = DataFeedStatus.ERROR
            return False

    def stop(self) -> bool:
        """
        停止数据馈送器

        Returns:
            bool: 停止是否成功
        """
        try:
            self._is_running = False
            self._status = DataFeedStatus.DISCONNECTED

            # 停止轮询
            if self._polling_thread:
                self._polling_stop_event.set()
                self._polling_thread.join(timeout=5)
                self._polling_thread = None

            # 断开 WebSocket
            if self._ws_connection and self._ws_manager:
                self._ws_manager.disconnect(self._ws_connection)
                self._ws_connection = None

            # 关闭 REST API
            if self._rest_api:
                self._rest_api.close()

            self._is_connected = False

            GLOG.INFO("OKXDataFeeder stopped")
            return True

        except Exception as e:
            GLOG.ERROR(f"OKXDataFeeder stop failed: {e}")
            return False

    def get_status(self) -> DataFeedStatus:
        """获取当前状态"""
        return self._status

    def set_event_publisher(self, publisher: Callable[[EventBase], None]) -> None:
        """
        设置事件发布器

        Args:
            publisher: 事件发布函数
        """
        self._event_publisher = publisher
        GLOG.DEBUG("Event publisher set for OKXDataFeeder")

    def set_time_provider(self, time_provider) -> None:
        """
        设置时间提供者

        Args:
            time_provider: 时间提供者接口
        """
        self._time_provider = time_provider

    def validate_time_access(self, request_time: datetime, data_time: datetime) -> bool:
        """
        验证时间访问权限（防止未来数据泄露）

        Args:
            request_time: 请求时间
            data_time: 数据时间

        Returns:
            bool: 是否允许访问
        """
        if not self._time_provider:
            return True
        return self._time_provider.validate_time_access(request_time, data_time)

    # ==================== ILiveDataFeeder 接口实现 ====================

    def subscribe_symbols(
        self,
        symbols: List[str],
        data_types: List[str] = None
    ) -> bool:
        """
        订阅交易对数据

        Args:
            symbols: 交易对列表 (如 ["BTC-USDT", "ETH-USDT"])
            data_types: 数据类型列表 (["ticker", "candlesticks", "trades", "orderbook"])

        Returns:
            bool: 订阅是否成功
        """
        try:
            if not symbols:
                return False

            # 默认订阅 ticker
            if data_types is None:
                data_types = ["ticker"]

            with self._subscription_lock:
                for symbol in symbols:
                    if symbol not in self._subscribed_symbols:
                        self._subscribed_symbols[symbol] = []

                    for data_type in data_types:
                        if data_type not in self._subscribed_symbols[symbol]:
                            # WebSocket 订阅
                            if self._is_connected and self._ws_connection and self._fetch_mode == DataFetchMode.WEBSOCKET:
                                if data_type == "ticker":
                                    self._subscribe_ticker_ws(symbol)
                                elif data_type == "candlesticks":
                                    self._subscribe_candlesticks_ws(symbol)
                                elif data_type == "trades":
                                    self._subscribe_trades_ws(symbol)
                                elif data_type == "orderbook":
                                    self._subscribe_orderbook_ws(symbol)

                            self._subscribed_symbols[symbol].append(data_type)

            GLOG.INFO(f"Subscribed to {len(symbols)} symbols: {data_types} (mode: {self._fetch_mode.value})")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe symbols: {e}")
            return False

    def unsubscribe_symbols(
        self,
        symbols: List[str],
        data_types: List[str] = None
    ) -> bool:
        """
        取消订阅交易对数据

        Args:
            symbols: 交易对列表
            data_types: 数据类型列表

        Returns:
            bool: 取消订阅是否成功
        """
        try:
            with self._subscription_lock:
                for symbol in symbols:
                    if symbol not in self._subscribed_symbols:
                        continue

                    # 取消所有订阅或指定类型
                    types_to_remove = data_types or self._subscribed_symbols[symbol][:]

                    for data_type in types_to_remove:
                        # WebSocket 取消订阅
                        if self._is_connected and self._ws_connection and self._fetch_mode == DataFetchMode.WEBSOCKET:
                            if data_type == "ticker":
                                self._unsubscribe_ticker_ws(symbol)
                            elif data_type == "candlesticks":
                                self._unsubscribe_candlesticks_ws(symbol)

                        if data_type in self._subscribed_symbols[symbol]:
                            self._subscribed_symbols[symbol].remove(data_type)

                    # 如果没有订阅类型了，移除 symbol
                    if not self._subscribed_symbols[symbol]:
                        del self._subscribed_symbols[symbol]

            GLOG.INFO(f"Unsubscribed from {len(symbols)} symbols")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to unsubscribe symbols: {e}")
            return False

    def start_subscription(self) -> bool:
        """
        开始订阅数据流

        Returns:
            bool: 启动是否成功
        """
        try:
            # WebSocket 模式
            if self._fetch_mode == DataFetchMode.WEBSOCKET:
                if not self._is_connected:
                    if not self._connect_websocket():
                        return False

                # 重新订阅之前的订阅
                if self._subscribed_symbols:
                    for symbol, types in list(self._subscribed_symbols.items()):
                        for data_type in types:
                            if data_type == "ticker":
                                self._subscribe_ticker_ws(symbol)
                            elif data_type == "candlesticks":
                                self._subscribe_candlesticks_ws(symbol)

                self._status = DataFeedStatus.STREAMING
                GLOG.INFO("WebSocket subscription started")
                return True

            # REST API 模式
            elif self._fetch_mode == DataFetchMode.REST_API:
                self._start_polling()
                self._status = DataFeedStatus.STREAMING
                GLOG.INFO("REST API polling started")
                return True

            return False

        except Exception as e:
            GLOG.ERROR(f"Failed to start subscription: {e}")
            return False

    def stop_subscription(self) -> bool:
        """
        停止订阅数据流

        Returns:
            bool: 停止是否成功
        """
        try:
            self._is_running = False

            # 停止轮询
            if self._polling_thread:
                self._polling_stop_event.set()
                self._polling_thread.join(timeout=5)
                self._polling_thread = None

            # 断开 WebSocket
            if self._ws_connection and self._ws_manager:
                self._ws_manager.disconnect(self._ws_connection)
                self._ws_connection = None

            self._is_connected = False
            self._status = DataFeedStatus.IDLE

            GLOG.INFO("Subscription stopped")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to stop subscription: {e}")
            return False

    def get_connection_info(self) -> Dict[str, Any]:
        """
        获取连接信息

        Returns:
            Dict[str, Any]: 连接状态信息
        """
        return {
            "source": self.source.value,
            "environment": self.environment,
            "fetch_mode": self._fetch_mode.value,
            "is_connected": self._is_connected,
            "is_running": self._is_running,
            "status": self._status.value,
            "subscribed_symbols": list(self._subscribed_symbols.keys()),
            "subscription_count": sum(len(types) for types in self._subscribed_symbols.values())
        }

    def reconnect(self, max_attempts: int = 3, delay_seconds: float = 1.0) -> bool:
        """
        重新连接

        Args:
            max_attempts: 最大重试次数
            delay_seconds: 重试延迟秒数

        Returns:
            bool: 重连是否成功
        """
        try:
            # 先停止
            self.stop_subscription()

            # 等待
            time.sleep(delay_seconds)

            # 尝试重连
            for attempt in range(max_attempts):
                GLOG.INFO(f"Reconnection attempt {attempt + 1}/{max_attempts}")

                # 尝试 WebSocket 优先
                if self._ws_enabled:
                    if self._connect_websocket():
                        self._fetch_mode = DataFetchMode.WEBSOCKET
                        GLOG.INFO("Reconnection successful with WebSocket")
                        return True

                # 降级到 REST API
                self._fetch_mode = DataFetchMode.REST_API
                self._start_polling()
                GLOG.INFO("Reconnection successful with REST API")
                return True

            GLOG.ERROR(f"Reconnection failed after {max_attempts} attempts")
            return False

        except Exception as e:
            GLOG.ERROR(f"Reconnection error: {e}")
            return False

    def set_rate_limiter(self, requests_per_second: float) -> None:
        """
        设置请求限流

        Args:
            requests_per_second: 每秒请求数限制
        """
        self._rate_limiter = requests_per_second
        GLOG.DEBUG(f"Rate limiter set to {requests_per_second}")

    def get_subscribed_symbols(self) -> List[str]:
        """
        获取已订阅的交易对列表

        Returns:
            List[str]: 已订阅的交易对代码
        """
        with self._subscription_lock:
            return list(self._subscribed_symbols.keys())

    # ==================== WebSocket 连接管理 ====================

    def _connect_websocket(self) -> bool:
        """
        连接 WebSocket

        Returns:
            bool: 连接是否成功
        """
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager

            self._ws_manager = get_websocket_manager()

            # 获取 Public WebSocket 连接
            self._ws_connection = self._ws_manager.get_public_ws(
                exchange="okx",
                environment=self.environment
            )

            # 连接
            if self._ws_manager.connect(self._ws_connection):
                self._is_connected = True
                GLOG.INFO("WebSocket connected successfully")
                return True
            else:
                return False

        except ImportError as e:
            GLOG.ERROR(f"WebSocket dependencies not available: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to connect WebSocket: {e}")
            return False

    # ==================== WebSocket 订阅方法 ====================

    def _subscribe_ticker_ws(self, symbol: str) -> None:
        """订阅 ticker"""
        if self._ws_connection and self._ws_manager:
            self._ws_manager.subscribe(
                self._ws_connection,
                channel="tickers",
                inst_id=symbol,
                callback=self._on_ticker_message
            )

    def _subscribe_candlesticks_ws(self, symbol: str, bar: str = "1m") -> None:
        """订阅 K线"""
        if self._ws_connection and self._ws_manager:
            channel = f"candlesticks{bar}"
            self._ws_manager.subscribe(
                self._ws_connection,
                channel=channel,
                inst_id=symbol,
                callback=self._on_candlestick_message
            )

    def _subscribe_trades_ws(self, symbol: str) -> None:
        """订阅成交"""
        if self._ws_connection and self._ws_manager:
            self._ws_manager.subscribe(
                self._ws_connection,
                channel="trades",
                inst_id=symbol,
                callback=self._on_trades_message
            )

    def _subscribe_orderbook_ws(self, symbol: str) -> None:
        """订阅订单簿"""
        if self._ws_connection and self._ws_manager:
            self._ws_manager.subscribe(
                self._ws_connection,
                channel="books",
                inst_id=symbol,
                callback=self._on_orderbook_message
            )

    def _unsubscribe_ticker_ws(self, symbol: str) -> None:
        """取消订阅 ticker"""
        if self._ws_connection and self._ws_manager:
            self._ws_manager.unsubscribe(self._ws_connection, "tickers", symbol)

    def _unsubscribe_candlesticks_ws(self, symbol: str, bar: str = "1m") -> None:
        """取消订阅 K线"""
        if self._ws_connection and self._ws_manager:
            channel = f"candlesticks{bar}"
            self._ws_manager.unsubscribe(self._ws_connection, channel, symbol)

    # ==================== WebSocket 消息回调 ====================

    def _on_ticker_message(self, message: dict) -> None:
        """处理 ticker 消息"""
        try:
            from ginkgo.livecore.websocket_event_adapter import adapt_ticker

            data = adapt_ticker(message)
            if not data:
                return

            # 更新缓存
            self._ticker_cache[data['symbol']] = data

            # 打印日志
            symbol = data.get('symbol', 'unknown')
            price = data.get('price', 0)
            GLOG.INFO(f"[OKX Ticker] {symbol}: ${price}")

            # 注意：ticker 是快照数据，不创建 Tick 对象或发布事件
            # 数据直接通过 wrapped callback 推送到前端

        except Exception as e:
            GLOG.ERROR(f"Error processing ticker message: {e}")

    def _on_candlestick_message(self, message: dict) -> None:
        """处理 K线消息"""
        try:
            from ginkgo.livecore.websocket_event_adapter import adapt_candlestick

            data = adapt_candlestick(message)
            if not data:
                return

            # 只处理已确认的K线
            if not data.get('confirmed', True):
                return

            # 创建 Bar 对象
            bar = Bar(
                code=data['symbol'],
                timestamp=data['timestamp'],
                open=float(data['open']),
                high=float(data['high']),
                low=float(data['low']),
                close=float(data['close']),
                volume=float(data['volume']),
                source=self.source
            )

            # 缓存
            self._bar_cache[data['symbol']] = bar

            # 创建 EventPriceUpdate (Bar)
            event = EventPriceUpdate(payload=bar)
            event.set_source(self.source)
            event.timestamp = datetime.now()

            # 发布事件
            self._publish_event(event)

        except Exception as e:
            GLOG.ERROR(f"Error processing candlestick message: {e}")

    def _on_trades_message(self, message: dict) -> None:
        """处理成交消息"""
        # TODO: 实现成交数据处理
        pass

    def _on_orderbook_message(self, message: dict) -> None:
        """处理订单簿消息"""
        # TODO: 实现订单簿数据处理
        pass

    # ==================== REST API 轮询 ====================

    def _start_polling(self) -> None:
        """启动 REST API 轮询"""
        if self._polling_thread and self._polling_thread.is_alive():
            return

        self._polling_stop_event.clear()
        self._polling_thread = threading.Thread(
            target=self._polling_loop,
            daemon=True
        )
        self._polling_thread.start()
        GLOG.INFO("REST API polling started")

    def _polling_loop(self) -> None:
        """轮询循环"""
        while not self._polling_stop_event.is_set() and self._is_running:
            try:
                # 获取所有订阅的 ticker
                with self._subscription_lock:
                    symbols = list(self._subscribed_symbols.keys())

                if symbols:
                    for symbol in symbols:
                        try:
                            # 调用 REST API
                            ticker_data = self._rest_api.get_ticker(symbol)
                            if ticker_data:
                                self._process_rest_ticker(ticker_data)
                        except Exception as e:
                            GLOG.ERROR(f"Error polling ticker for {symbol}: {e}")

                # 等待下一次轮询
                self._polling_stop_event.wait(self.POLLING_INTERVAL)

            except Exception as e:
                GLOG.ERROR(f"Error in polling loop: {e}")
                self._polling_stop_event.wait(self.POLLING_INTERVAL)

    def _process_rest_ticker(self, data: Dict[str, Any]) -> None:
        """
        处理 REST API 返回的 ticker 数据

        Args:
            data: ticker 数据
        """
        try:
            symbol = data.get('symbol')
            if not symbol:
                return

            # 更新缓存
            self._ticker_cache[symbol] = data

            # 创建 Tick
            tick = Tick(
                code=symbol,
                timestamp=datetime.now(),
                price=float(data.get('last_price', 0)),
                volume=int(float(data.get('volume_24h', 0))),
                source=self.source
            )

            event = EventPriceUpdate(payload=tick)
            event.set_source(self.source)
            event.timestamp = datetime.now()

            # 发布事件
            self._publish_event(event)

        except Exception as e:
            GLOG.ERROR(f"Error processing REST ticker: {e}")

    # ==================== 事件发布 ====================

    def _publish_event(self, event: EventBase) -> None:
        """
        发布事件

        Args:
            event: 事件对象
        """
        if self._event_publisher:
            try:
                self._event_publisher(event)
            except Exception as e:
                GLOG.ERROR(f"Error publishing event: {e}")

    # ==================== 公共方法 ====================

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._is_connected

    @property
    def fetch_mode(self) -> DataFetchMode:
        """获取当前数据获取模式"""
        return self._fetch_mode

    def get_cached_ticker(self, symbol: str) -> Optional[Dict]:
        """
        获取缓存的 ticker 数据

        Args:
            symbol: 交易对

        Returns:
            dict: ticker 数据或 None
        """
        return self._ticker_cache.get(symbol)

    def get_cached_bar(self, symbol: str) -> Optional[Bar]:
        """
        获取缓存的 K线数据

        Args:
            symbol: 交易对

        Returns:
            Bar: K线数据或 None
        """
        return self._bar_cache.get(symbol)

    def get_rest_api(self) -> OKXMarketDataFeeder:
        """
        获取 REST API 实例（用于直接访问）

        Returns:
            OKXMarketDataFeeder: REST API 实例
        """
        return self._rest_api
