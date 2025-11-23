"""
实盘数据馈送实现

实现实盘数据馈送的核心功能：
- WebSocket连接管理
- 数据订阅和推送
- 断线重连机制
- 限流控制
- 时间边界验证
"""

import asyncio
import json
import threading
import time
import websockets
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime, date
from urllib.parse import urljoin
import logging

from ginkgo.trading.feeders.interfaces import (
    ILiveDataFeeder, DataFeedStatus
)
from ginkgo.trading.events import EventBase, EventPriceUpdate
from ginkgo.trading.time.interfaces import ITimeProvider
from ginkgo.trading.time.providers import TimeBoundaryValidator
from ginkgo.libs import GLOG
from ginkgo.trading.time.clock import now as clock_now


class RateLimiter:
    """简单的令牌桶限流器"""
    
    def __init__(self, requests_per_second: float):
        self.rate = requests_per_second
        self.bucket_size = requests_per_second * 2  # 桶容量为2倍速率
        self.tokens = self.bucket_size
        self.last_update = time.time()
        self._lock = threading.Lock()
    
    def acquire(self, tokens: int = 1) -> bool:
        """获取令牌"""
        with self._lock:
            now = time.time()
            # 添加令牌
            elapsed = now - self.last_update
            self.tokens = min(self.bucket_size, self.tokens + elapsed * self.rate)
            self.last_update = now
            
            # 检查是否有足够令牌
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_for_tokens(self, tokens: int = 1, timeout: float = 5.0) -> bool:
        """等待获取令牌"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.acquire(tokens):
                return True
            time.sleep(0.1)
        return False


class ConnectionManager:
    """WebSocket连接管理器"""

    def __init__(
        self,
        host: str,
        port: int,
        api_key: str = "",
        max_reconnect_attempts: int = 5,
        reconnect_delay_seconds: float = 2.0,
        heartbeat_interval_seconds: float = 30.0
    ):
        self.host = host
        self.port = port
        self.api_key = api_key
        self.max_reconnect_attempts = max_reconnect_attempts
        self.reconnect_delay_seconds = reconnect_delay_seconds
        self.heartbeat_interval_seconds = heartbeat_interval_seconds

        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.connection_url = f"ws://{host}:{port}/ws"
        self.is_connected = False
        self.reconnect_attempts = 0
        self._reconnect_event = asyncio.Event()
        
    async def connect(self) -> bool:
        """建立WebSocket连接"""
        try:
            # 构建连接URL（包含认证信息）
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self.websocket = await websockets.connect(
                self.connection_url,
                extra_headers=headers,
                ping_interval=self.heartbeat_interval_seconds,
                ping_timeout=self.heartbeat_interval_seconds * 2
            )
            
            self.is_connected = True
            self.reconnect_attempts = 0
            GLOG.INFO(f"WebSocket connected to {self.connection_url}")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"WebSocket connection failed: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self) -> None:
        """断开WebSocket连接"""
        if self.websocket:
            await self.websocket.close()
            self.websocket = None
        self.is_connected = False
        GLOG.INFO("WebSocket disconnected")
    
    async def send_message(self, message: Dict[str, Any]) -> bool:
        """发送消息"""
        if not self.is_connected or not self.websocket:
            return False
        
        try:
            await self.websocket.send(json.dumps(message))
            return True
        except Exception as e:
            GLOG.ERROR(f"Failed to send message: {e}")
            return False
    
    async def receive_message(self) -> Optional[Dict[str, Any]]:
        """接收消息"""
        if not self.is_connected or not self.websocket:
            return None
        
        try:
            message = await self.websocket.recv()
            return json.loads(message)
        except websockets.exceptions.ConnectionClosed:
            self.is_connected = False
            return None
        except Exception as e:
            GLOG.ERROR(f"Failed to receive message: {e}")
            return None
    
    async def auto_reconnect(self) -> None:
        """自动重连逻辑"""
        while self.reconnect_attempts < self.max_reconnect_attempts:
            if self.is_connected:
                break

            self.reconnect_attempts += 1
            GLOG.INFO(f"Attempting to reconnect ({self.reconnect_attempts}/{self.max_reconnect_attempts})")

            if await self.connect():
                break

            await asyncio.sleep(self.reconnect_delay_seconds * self.reconnect_attempts)


class LiveDataFeeder(ILiveDataFeeder):
    """
    实盘数据馈送器实现

    支持WebSocket实时数据推送、断线重连、限流控制等功能。
    """

    def __init__(
        self,
        host: str = "",
        port: int = 0,
        api_key: str = "",
        enable_rate_limit: bool = True,
        rate_limit_per_second: float = 10.0
    ):
        # 连接参数
        self.host = host
        self.port = port
        self.api_key = api_key

        # 核心组件（懒加载）
        self.connection_manager: Optional[ConnectionManager] = None
        self.rate_limiter: Optional[RateLimiter] = None
        self.time_controller: Optional[ITimeProvider] = None
        self.time_boundary_validator: Optional[TimeBoundaryValidator] = None
        self.event_publisher: Optional[Callable[[EventBase], None]] = None

        # 限流配置
        self.enable_rate_limit = enable_rate_limit
        self.rate_limit_per_second = rate_limit_per_second

        # 状态管理
        self.status = DataFeedStatus.IDLE
        self.subscribed_symbols: List[str] = []
        self.subscribed_data_types: List[str] = []

        # 异步运行时
        self.loop: Optional[asyncio.AbstractEventLoop] = None
        self.event_loop_thread: Optional[threading.Thread] = None
        self._shutdown_event = threading.Event()

        # 数据处理
        self.message_handlers: Dict[str, Callable] = {}
        self._initialize_handlers()

        # 统计信息
        self.stats = {
            'messages_received': 0,
            'events_published': 0,
            'connection_errors': 0,
            'last_message_time': None
        }
    
    def _initialize_handlers(self):
        """初始化消息处理器"""
        self.message_handlers = {
            'price_update': self._handle_price_update,
            'trade': self._handle_trade_data,
            'orderbook': self._handle_orderbook_data,
            'status': self._handle_status_message,
            'error': self._handle_error_message
        }
    
    # === IDataFeeder 基础接口实现 ===
    
    def initialize(self) -> bool:
        """初始化数据馈送器"""
        try:
            # 初始化连接管理器
            if self.host and self.port:
                self.connection_manager = ConnectionManager(
                    host=self.host,
                    port=self.port,
                    api_key=self.api_key
                )

            # 初始化限流器
            if self.enable_rate_limit:
                self.rate_limiter = RateLimiter(self.rate_limit_per_second)

            # 初始化时间边界验证器（如果time_controller已注入）
            if self.time_controller:
                self.time_boundary_validator = TimeBoundaryValidator(self.time_controller)

            self.status = DataFeedStatus.IDLE
            GLOG.INFO("LiveDataFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"LiveDataFeeder initialization failed: {e}")
            return False
    
    def start(self) -> bool:
        """启动数据馈送"""
        try:
            if self.status != DataFeedStatus.IDLE:
                return False
            
            # 启动事件循环线程
            self._start_event_loop()
            
            # 等待连接建立
            self._wait_for_connection(timeout_seconds=10)
            
            if self.status == DataFeedStatus.CONNECTED:
                GLOG.INFO("LiveDataFeeder started successfully")
                return True
            else:
                GLOG.ERROR("LiveDataFeeder failed to establish connection")
                return False
                
        except Exception as e:
            GLOG.ERROR(f"LiveDataFeeder start failed: {e}")
            return False
    
    def stop(self) -> bool:
        """停止数据馈送"""
        try:
            self._shutdown_event.set()
            
            # 停止事件循环
            if self.loop and self.loop.is_running():
                asyncio.run_coroutine_threadsafe(self._async_shutdown(), self.loop)
            
            # 等待线程结束
            if self.event_loop_thread and self.event_loop_thread.is_alive():
                self.event_loop_thread.join(timeout=5)
            
            self.status = DataFeedStatus.DISCONNECTED
            GLOG.INFO("LiveDataFeeder stopped")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"LiveDataFeeder stop failed: {e}")
            return False
    
    def get_status(self) -> DataFeedStatus:
        """获取当前状态"""
        return self.status
    
    def set_event_publisher(self, publisher: Callable[[EventBase], None]) -> None:
        """设置事件发布器"""
        self.event_publisher = publisher
    
    def set_time_provider(self, time_controller: ITimeProvider) -> None:
        """设置时间控制器"""
        self.time_controller = time_controller
        # 自动启用时间边界检查
        self.time_boundary_validator = TimeBoundaryValidator(time_controller)
    
    def get_trading_calendar(self, start_date: date, end_date: date) -> List[date]:
        """获取交易日历（实盘模式从系统获取）"""
        # 实盘模式下的简化实现，实际应该从交易所API获取
        trading_days = []
        current = start_date
        from datetime import timedelta as _td
        while current <= end_date:
            # 简单过滤：排除周末
            if current.weekday() < 5:  # Monday = 0, Sunday = 6
                trading_days.append(current)
            current = current + _td(days=1)
        return trading_days
    
    def validate_time_access(self, request_time: datetime, data_time: datetime) -> bool:
        """验证时间访问权限"""
        if self.time_boundary_validator:
            return self.time_boundary_validator.can_access_time(data_time, request_time)
        # 实盘模式下，只能访问当前时间之前的数据
        return data_time <= request_time
    
    # === ILiveDataFeeder 扩展接口实现 ===
    
    def subscribe_symbols(self, symbols: List[str], data_types: List[str] = None) -> bool:
        """订阅股票数据"""
        if not symbols:
            return False
        
        data_types = data_types or ["price_update"]
        
        # 限流检查
        if self.rate_limiter and not self.rate_limiter.wait_for_tokens():
            GLOG.ERROR("Rate limit exceeded for subscription request")
            return False
        
        # 构建订阅消息
        subscribe_message = {
            "action": "subscribe",
            "symbols": symbols,
            "data_types": data_types,
            "timestamp": (self.time_controller.now() if self.time_controller else clock_now()).isoformat()
        }
        
        # 发送订阅请求
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self.connection_manager.send_message(subscribe_message), self.loop
            )
            try:
                success = future.result(timeout=5)
                if success:
                    self.subscribed_symbols.extend([s for s in symbols if s not in self.subscribed_symbols])
                    self.subscribed_data_types.extend([dt for dt in data_types if dt not in self.subscribed_data_types])
                    GLOG.INFO(f"Subscribed to symbols: {symbols}, data_types: {data_types}")
                return success
            except Exception as e:
                GLOG.ERROR(f"Subscription failed: {e}")
                return False
        
        return False
    
    def unsubscribe_symbols(self, symbols: List[str], data_types: List[str] = None) -> bool:
        """取消订阅股票数据"""
        if not symbols:
            return False
        
        data_types = data_types or self.subscribed_data_types
        
        unsubscribe_message = {
            "action": "unsubscribe",
            "symbols": symbols,
            "data_types": data_types,
            "timestamp": (self.time_controller.now() if self.time_controller else clock_now()).isoformat()
        }
        
        if self.loop:
            future = asyncio.run_coroutine_threadsafe(
                self.connection_manager.send_message(unsubscribe_message), self.loop
            )
            try:
                success = future.result(timeout=5)
                if success:
                    for symbol in symbols:
                        if symbol in self.subscribed_symbols:
                            self.subscribed_symbols.remove(symbol)
                    GLOG.INFO(f"Unsubscribed from symbols: {symbols}")
                return success
            except Exception as e:
                GLOG.ERROR(f"Unsubscription failed: {e}")
                return False
        
        return False
    
    def start_subscription(self) -> bool:
        """开始订阅数据流"""
        if self.status != DataFeedStatus.CONNECTED:
            return False
        
        self.status = DataFeedStatus.STREAMING
        GLOG.INFO("Started data streaming")
        return True
    
    def stop_subscription(self) -> bool:
        """停止订阅数据流"""
        if self.status == DataFeedStatus.STREAMING:
            self.status = DataFeedStatus.CONNECTED
            GLOG.INFO("Stopped data streaming")
        return True
    
    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            'status': self.status.value,
            'url': self.connection_manager.connection_url,
            'is_connected': self.connection_manager.is_connected,
            'reconnect_attempts': self.connection_manager.reconnect_attempts,
            'subscribed_symbols': self.subscribed_symbols.copy(),
            'subscribed_data_types': self.subscribed_data_types.copy(),
            'stats': self.stats.copy()
        }
    
    def reconnect(self, max_attempts: int = 3, delay_seconds: float = 1.0) -> bool:
        """重新连接"""
        if self.loop and self.connection_manager:
            # 触发重连
            future = asyncio.run_coroutine_threadsafe(
                self.connection_manager.auto_reconnect(), self.loop
            )
            try:
                future.result(timeout=max_attempts * delay_seconds + 10)
                return self.connection_manager.is_connected
            except Exception as e:
                GLOG.ERROR(f"Reconnection failed: {e}")

        return False

    def set_rate_limiter(self, requests_per_second: float) -> None:
        """设置请求限流"""
        self.rate_limiter = RateLimiter(requests_per_second)
        self.rate_limit_per_second = requests_per_second
    
    def get_subscribed_symbols(self) -> List[str]:
        """获取已订阅的股票列表"""
        return self.subscribed_symbols.copy()
    
    # === 内部实现方法 ===
    
    def _start_event_loop(self):
        """启动事件循环线程"""
        self.event_loop_thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self.event_loop_thread.start()
    
    def _run_event_loop(self):
        """运行事件循环"""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            self.loop.run_until_complete(self._async_main())
        except Exception as e:
            GLOG.ERROR(f"Event loop error: {e}")
        finally:
            self.loop.close()
    
    async def _async_main(self):
        """异步主循环"""
        # 建立连接
        self.status = DataFeedStatus.CONNECTING
        if await self.connection_manager.connect():
            self.status = DataFeedStatus.CONNECTED
            
            # 启动消息接收循环
            await self._message_loop()
        else:
            self.status = DataFeedStatus.ERROR
    
    async def _message_loop(self):
        """消息接收循环"""
        while not self._shutdown_event.is_set() and self.connection_manager.is_connected:
            try:
                message = await self.connection_manager.receive_message()
                if message:
                    await self._process_message(message)
                    self.stats['messages_received'] += 1
                    self.stats['last_message_time'] = (self.time_controller.now() if self.time_controller else clock_now())
                else:
                    # 连接断开，尝试自动重连
                    await self.connection_manager.auto_reconnect()
                    if not self.connection_manager.is_connected:
                        self.status = DataFeedStatus.DISCONNECTED
                        break
                    
            except Exception as e:
                GLOG.ERROR(f"Message loop error: {e}")
                self.stats['connection_errors'] += 1

                # 短暂延迟后重试
                await asyncio.sleep(1)
    
    async def _process_message(self, message: Dict[str, Any]):
        """处理接收到的消息"""
        try:
            message_type = message.get('type', 'unknown')
            handler = self.message_handlers.get(message_type)
            
            if handler:
                await handler(message)
            else:
                GLOG.WARN(f"Unknown message type: {message_type}")
                
        except Exception as e:
            GLOG.ERROR(f"Message processing error: {e}")
    
    async def _handle_price_update(self, message: Dict[str, Any]):
        """处理价格更新消息"""
        try:
            # 解析消息数据
            symbol = message.get('symbol')
            price = float(message.get('price', 0))
            volume = int(message.get('volume', 0))
            timestamp_str = message.get('timestamp')
            
            if timestamp_str:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            else:
                timestamp = self.time_controller.now() if self.time_controller else clock_now()
            
            # 时间边界检查
            if not self.validate_time_access((self.time_controller.now() if self.time_controller else clock_now()), timestamp):
                GLOG.WARN(f"Time boundary violation for {symbol} at {timestamp}")
                return
            
            # 创建价格更新事件
            event = EventPriceUpdate(
                code=symbol,
                price=price,
                volume=volume,
                timestamp=timestamp
            )
            
            # 发布事件
            if self.event_publisher:
                self.event_publisher(event)
                self.stats['events_published'] += 1
                
        except Exception as e:
            GLOG.ERROR(f"Price update handling error: {e}")
    
    async def _handle_trade_data(self, message: Dict[str, Any]):
        """处理交易数据消息"""
        # 实现交易数据处理逻辑
        pass
    
    async def _handle_orderbook_data(self, message: Dict[str, Any]):
        """处理订单簿数据消息"""
        # 实现订单簿数据处理逻辑
        pass
    
    async def _handle_status_message(self, message: Dict[str, Any]):
        """处理状态消息"""
        status = message.get('status')
        GLOG.INFO(f"Received status message: {status}")
    
    async def _handle_error_message(self, message: Dict[str, Any]):
        """处理错误消息"""
        error = message.get('error')
        GLOG.ERROR(f"Received error message: {error}")
        self.stats['connection_errors'] += 1
    
    async def _async_shutdown(self):
        """异步关闭"""
        await self.connection_manager.disconnect()
    
    def _wait_for_connection(self, timeout_seconds: float = 10):
        """等待连接建立"""
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            if self.status == DataFeedStatus.CONNECTED:
                return
            time.sleep(0.1)
