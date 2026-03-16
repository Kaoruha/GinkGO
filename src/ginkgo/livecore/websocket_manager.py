# Upstream: LiveEngine (生命周期管理)、OKXFeeder/OKXBroker (WebSocket使用)
# Downstream: OKX WebSocket API (连接)、WebSocketEventAdapter (消息处理)
# Role: WebSocketManager WebSocket连接池管理器提供连接复用/自动重连/心跳检测


"""
WebSocket 连接管理器

提供统一的 WebSocket 连接管理：
- Public WebSocket: 市场行情数据（公开接口）
- Private WebSocket: 账户/订单/持仓数据（认证接口）
- 连接池复用：同一交易所共享连接
- 自动重连：指数退避重连策略
- 心跳检测：保持连接活跃
"""

import asyncio
import json
import threading
import time
from typing import Dict, Optional, Callable, Any, List
from datetime import datetime
from enum import Enum

try:
    import websockets
    from websockets.exceptions import ConnectionClosed, ConnectionClosedError
    WEBSOCKETS_AVAILABLE = True
except ImportError:
    WEBSOCKETS_AVAILABLE = False
    websockets = None

from ginkgo.libs import GLOG


class WebSocketType(Enum):
    """WebSocket类型"""
    PUBLIC = "public"      # 公开行情数据
    PRIVATE = "private"    # 私有账户数据


class ConnectionState(Enum):
    """连接状态"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


class WebSocketConnection:
    """
    WebSocket连接实例

    封装单个WebSocket连接的生命周期管理
    """

    # OKX WebSocket端点
    PUBLIC_ENDPOINTS = {
        "production": "wss://ws.okx.com:8443/ws/v5/public",
        "testnet": "wss://ws.okx.com:8443/ws/v5/public"
    }

    PRIVATE_ENDPOINTS = {
        "production": "wss://ws.okx.com:8443/ws/v5/private",
        "testnet": "wss://ws.okx.com:8443/ws/v5/private"
    }

    # 重连配置
    MAX_RECONNECT_ATTEMPTS = 5
    INITIAL_RECONNECT_DELAY = 1.0  # 秒
    MAX_RECONNECT_DELAY = 30.0     # 秒

    def __init__(
        self,
        ws_type: WebSocketType,
        exchange: str = "okx",
        environment: str = "production",
        credentials: Optional[Dict[str, str]] = None,
        connection_id: Optional[str] = None
    ):
        """
        初始化WebSocket连接

        Args:
            ws_type: WebSocket类型 (PUBLIC/PRIVATE)
            exchange: 交易所名称
            environment: 环境 (production/testnet)
            credentials: API凭证 (仅PRIVATE需要)
            connection_id: 连接ID (可选)
        """
        if not WEBSOCKETS_AVAILABLE:
            raise ImportError("websockets package not installed. Run: pip install websockets")

        self.ws_type = ws_type
        self.exchange = exchange.lower()
        self.environment = environment
        self.credentials = credentials or {}

        # 生成唯一连接ID
        self.connection_id = connection_id or f"{exchange}_{ws_type.value}_{environment}"

        # 连接状态
        self._state = ConnectionState.DISCONNECTED
        self._websocket = None
        self._loop = None
        self._thread = None

        # 订阅管理
        self._subscriptions: Dict[str, Callable] = {}  # channel -> callback

        # 重连控制
        self._reconnect_attempts = 0
        self._should_reconnect = True

        # 心跳配置
        self._last_ping = None
        self._last_pong = None
        self._ping_interval = 30  # 秒

        GLOG.INFO(f"WebSocketConnection created: {self.connection_id}")

    @property
    def state(self) -> ConnectionState:
        """获取连接状态"""
        return self._state

    @property
    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._state == ConnectionState.CONNECTED

    def get_endpoint(self) -> str:
        """获取WebSocket端点URL"""
        if self.ws_type == WebSocketType.PUBLIC:
            return self.PUBLIC_ENDPOINTS.get(self.environment, self.PUBLIC_ENDPOINTS["production"])
        else:
            return self.PRIVATE_ENDPOINTS.get(self.environment, self.PRIVATE_ENDPOINTS["production"])

    async def connect(self) -> bool:
        """
        建立WebSocket连接

        Returns:
            bool: 连接是否成功
        """
        try:
            if self._state in [ConnectionState.CONNECTING, ConnectionState.CONNECTED]:
                GLOG.WARNING(f"WebSocket already connected or connecting: {self.connection_id}")
                return True

            self._state = ConnectionState.CONNECTING
            endpoint = self.get_endpoint()

            GLOG.INFO(f"Connecting to WebSocket: {self.connection_id} -> {endpoint}")

            # 建立连接
            self._websocket = await websockets.connect(
                endpoint,
                ping_interval=self._ping_interval,
                ping_timeout=10,
                close_timeout=10
            )

            # 私有WebSocket需要认证
            if self.ws_type == WebSocketType.PRIVATE:
                if not await self._authenticate():
                    GLOG.ERROR("WebSocket authentication failed")
                    await self._websocket.close()
                    self._state = ConnectionState.ERROR
                    return False

            self._state = ConnectionState.CONNECTED
            self._reconnect_attempts = 0
            self._last_pong = datetime.now()

            GLOG.INFO(f"WebSocket connected successfully: {self.connection_id}")

            # 启动消息接收循环
            asyncio.create_task(self._receive_loop())

            # 重新订阅之前的频道
            await self._resubscribe_all()

            return True

        except Exception as e:
            GLOG.ERROR(f"WebSocket connection failed: {self.connection_id} - {e}")
            self._state = ConnectionState.ERROR
            return False

    async def _authenticate(self) -> bool:
        """
        WebSocket认证 (私有频道)

        OKX私有WebSocket需要登录签名

        Returns:
            bool: 认证是否成功
        """
        try:
            if not self.credentials:
                GLOG.ERROR("No credentials provided for private WebSocket")
                return False

            import hmac
            import base64
            from datetime import datetime

            api_key = self.credentials.get("api_key")
            api_secret = self.credentials.get("api_secret")
            passphrase = self.credentials.get("passphrase")

            if not all([api_key, api_secret, passphrase]):
                GLOG.ERROR("Incomplete credentials for OKX WebSocket authentication")
                return False

            # 生成签名
            timestamp = datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'
            message = timestamp + "GET" + "/users/self/verify"
            signature = hmac.new(
                api_secret.encode('utf-8'),
                message.encode('utf-8'),
                digestmod='sha256'
            ).digest()
            signature_b64 = base64.b64encode(signature).decode('utf-8')

            # 登录消息
            login_msg = {
                "op": "login",
                "args": [{
                    "apiKey": api_key,
                    "passphrase": passphrase,
                    "timestamp": timestamp,
                    "sign": signature_b64
                }]
            }

            await self._websocket.send(json.dumps(login_msg))

            # 等待登录响应
            response = await asyncio.wait_for(self._websocket.recv(), timeout=10)
            response_data = json.loads(response)

            if response_data.get("code") == "0":
                event = response_data.get("data", {}).get("event", "")
                if event == "login":
                    GLOG.INFO(f"WebSocket authentication successful: {self.connection_id}")
                    return True

            GLOG.ERROR(f"WebSocket authentication failed: {response_data}")
            return False

        except asyncio.TimeoutError:
            GLOG.ERROR("WebSocket authentication timeout")
            return False
        except Exception as e:
            GLOG.ERROR(f"WebSocket authentication error: {e}")
            return False

    async def subscribe(
        self,
        channel: str,
        inst_id: str,
        callback: Callable[[dict], None]
    ) -> bool:
        """
        订阅频道

        Args:
            channel: 频道名称 (如 "tickers", "candlesticks")
            inst_id: 交易对ID (如 "BTC-USDT")
            callback: 消息回调函数

        Returns:
            bool: 订阅是否成功
        """
        try:
            if not self.is_connected:
                GLOG.ERROR(f"Cannot subscribe: WebSocket not connected: {self.connection_id}")
                return False

            # 构建订阅消息
            subscribe_key = f"{channel}:{inst_id}"
            subscribe_msg = {
                "op": "subscribe",
                "args": [{
                    "channel": channel,
                    "instId": inst_id
                }]
            }

            await self._websocket.send(json.dumps(subscribe_msg))

            # 注册回调
            self._subscriptions[subscribe_key] = callback

            GLOG.INFO(f"Subscribed to {subscribe_key} on {self.connection_id}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Subscribe failed: {e}")
            return False

    async def unsubscribe(self, channel: str, inst_id: str) -> bool:
        """
        取消订阅频道

        Args:
            channel: 频道名称
            inst_id: 交易对ID

        Returns:
            bool: 取消订阅是否成功
        """
        try:
            unsubscribe_key = f"{channel}:{inst_id}"

            if unsubscribe_key not in self._subscriptions:
                GLOG.WARNING(f"No subscription found for {unsubscribe_key}")
                return False

            unsubscribe_msg = {
                "op": "unsubscribe",
                "args": [{
                    "channel": channel,
                    "instId": inst_id
                }]
            }

            await self._websocket.send(json.dumps(unsubscribe_msg))

            # 移除回调
            del self._subscriptions[unsubscribe_key]

            GLOG.INFO(f"Unsubscribed from {unsubscribe_key} on {self.connection_id}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Unsubscribe failed: {e}")
            return False

    async def _resubscribe_all(self) -> None:
        """重新订阅所有频道"""
        if not self._subscriptions:
            return

        GLOG.INFO(f"Resubscribing to {len(self._subscriptions)} channels")

        for subscribe_key, callback in self._subscriptions.items():
            try:
                channel, inst_id = subscribe_key.split(":", 1)
                subscribe_msg = {
                    "op": "subscribe",
                    "args": [{
                        "channel": channel,
                        "instId": inst_id
                    }]
                }
                await self._websocket.send(json.dumps(subscribe_msg))
            except Exception as e:
                GLOG.ERROR(f"Failed to resubscribe to {subscribe_key}: {e}")

    async def _receive_loop(self) -> None:
        """消息接收循环"""
        try:
            async for message in self._websocket:
                try:
                    data = json.loads(message)
                    await self._handle_message(data)
                except json.JSONDecodeError as e:
                    GLOG.ERROR(f"Invalid JSON message: {e}")
                except Exception as e:
                    GLOG.ERROR(f"Error handling message: {e}")

        except ConnectionClosed:
            GLOG.WARNING(f"WebSocket connection closed: {self.connection_id}")
            await self._handle_disconnect()
        except Exception as e:
            GLOG.ERROR(f"Receive loop error: {e}")
            await self._handle_disconnect()

    async def _handle_message(self, data: dict) -> None:
        """
        处理接收到的消息

        Args:
            data: 消息数据
        """
        try:
            # 处理pong响应
            if data.get("event") == "pong":
                self._last_pong = datetime.now()
                return

            # 处理订阅确认
            if data.get("event") == "subscribe":
                GLOG.DEBUG(f"Subscription confirmed: {data}")
                return

            # 处理业务消息
            arg = data.get("data", {}).get("arg", {})
            channel = arg.get("channel", "")

            if channel:
                # 查找并调用回调
                for subscribe_key, callback in self._subscriptions.items():
                    sub_channel = subscribe_key.split(":", 1)[0]
                    if sub_channel == channel:
                        # 在线程池中执行回调，避免阻塞异步循环
                        asyncio.get_event_loop().run_in_executor(
                            None, callback, data
                        )
                        break

        except Exception as e:
            GLOG.ERROR(f"Error in _handle_message: {e}")

    async def _handle_disconnect(self) -> None:
        """处理断开连接"""
        self._state = ConnectionState.DISCONNECTED

        if self._should_reconnect:
            await self._reconnect()

    async def _reconnect(self) -> bool:
        """
        重连

        使用指数退避策略

        Returns:
            bool: 重连是否成功
        """
        self._state = ConnectionState.RECONNECTING

        while self._reconnect_attempts < self.MAX_RECONNECT_ATTEMPTS:
            self._reconnect_attempts += 1

            # 计算延迟（指数退避）
            delay = min(
                self.INITIAL_RECONNECT_DELAY * (2 ** (self._reconnect_attempts - 1)),
                self.MAX_RECONNECT_DELAY
            )

            GLOG.INFO(f"Reconnecting in {delay}s (attempt {self._reconnect_attempts}/{self.MAX_RECONNECT_ATTEMPTS})")
            await asyncio.sleep(delay)

            if await self.connect():
                GLOG.INFO(f"WebSocket reconnected successfully: {self.connection_id}")
                return True

        GLOG.ERROR(f"Failed to reconnect after {self.MAX_RECONNECT_ATTEMPTS} attempts")
        self._state = ConnectionState.ERROR
        return False

    async def disconnect(self) -> None:
        """断开连接"""
        self._should_reconnect = False

        if self._websocket:
            try:
                await self._websocket.close()
            except Exception as e:
                GLOG.ERROR(f"Error closing WebSocket: {e}")

        self._state = ConnectionState.DISCONNECTED
        GLOG.INFO(f"WebSocket disconnected: {self.connection_id}")

    async def send_ping(self) -> None:
        """发送ping"""
        if self.is_connected and self._websocket:
            try:
                ping_msg = {"op": "ping"}
                await self._websocket.send(json.dumps(ping_msg))
                self._last_ping = datetime.now()
            except Exception as e:
                GLOG.ERROR(f"Failed to send ping: {e}")


class WebSocketManager:
    """
    WebSocket连接管理器

    管理多个WebSocket连接，提供连接复用和统一管理
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """初始化WebSocketManager单例"""
        if self._initialized:
            return

        self._connections: Dict[str, WebSocketConnection] = {}
        self._loop = None
        self._thread = None
        self._running = False

        self._initialized = True
        GLOG.INFO("WebSocketManager initialized")

    def _start_event_loop(self) -> None:
        """启动事件循环线程"""
        if self._loop is None or self._loop.is_closed():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        if not self._running:
            self._running = True
            self._loop.run_forever()

    def _run_coroutine(self, coro):
        """在事件循环中运行协程"""
        if self._loop is None:
            self._thread = threading.Thread(target=self._start_event_loop, daemon=True)
            self._thread.start()
            time.sleep(0.1)  # 等待事件循环启动

        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        return future.result(timeout=30)

    def get_public_ws(self, exchange: str = "okx", environment: str = "production") -> WebSocketConnection:
        """
        获取或创建公开WebSocket连接

        Args:
            exchange: 交易所名称
            environment: 环境

        Returns:
            WebSocketConnection: WebSocket连接实例
        """
        connection_id = f"{exchange}_{WebSocketType.PUBLIC.value}_{environment}"

        if connection_id not in self._connections:
            connection = WebSocketConnection(
                ws_type=WebSocketType.PUBLIC,
                exchange=exchange,
                environment=environment
            )
            self._connections[connection_id] = connection

        return self._connections[connection_id]

    def get_private_ws(
        self,
        exchange: str = "okx",
        environment: str = "production",
        credentials: Optional[Dict[str, str]] = None,
        connection_id: Optional[str] = None
    ) -> WebSocketConnection:
        """
        获取或创建私有WebSocket连接

        Args:
            exchange: 交易所名称
            environment: 环境
            credentials: API凭证
            connection_id: 连接ID (每个Broker需要独立连接)

        Returns:
            WebSocketConnection: WebSocket连接实例
        """
        if not connection_id:
            connection_id = f"{exchange}_{WebSocketType.PRIVATE.value}_{environment}_{id(credentials)}"

        if connection_id not in self._connections:
            connection = WebSocketConnection(
                ws_type=WebSocketType.PRIVATE,
                exchange=exchange,
                environment=environment,
                credentials=credentials,
                connection_id=connection_id
            )
            self._connections[connection_id] = connection

        return self._connections[connection_id]

    def connect(self, connection: WebSocketConnection) -> bool:
        """
        连接WebSocket

        Args:
            connection: WebSocket连接实例

        Returns:
            bool: 连接是否成功
        """
        return self._run_coroutine(connection.connect())

    def disconnect(self, connection: WebSocketConnection) -> None:
        """
        断开WebSocket连接

        Args:
            connection: WebSocket连接实例
        """
        self._run_coroutine(connection.disconnect())

        # 从管理器中移除
        if connection.connection_id in self._connections:
            del self._connections[connection.connection_id]

    def subscribe(
        self,
        connection: WebSocketConnection,
        channel: str,
        inst_id: str,
        callback: Callable[[dict], None]
    ) -> bool:
        """
        订阅频道

        Args:
            connection: WebSocket连接实例
            channel: 频道名称
            inst_id: 交易对ID
            callback: 回调函数

        Returns:
            bool: 订阅是否成功
        """
        return self._run_coroutine(connection.subscribe(channel, inst_id, callback))

    def unsubscribe(self, connection: WebSocketConnection, channel: str, inst_id: str) -> bool:
        """
        取消订阅

        Args:
            connection: WebSocket连接实例
            channel: 频道名称
            inst_id: 交易对ID

        Returns:
            bool: 取消订阅是否成功
        """
        return self._run_coroutine(connection.unsubscribe(channel, inst_id))

    def shutdown(self) -> None:
        """关闭所有连接"""
        for connection_id, connection in list(self._connections.items()):
            try:
                self.disconnect(connection)
            except Exception as e:
                GLOG.ERROR(f"Error disconnecting {connection_id}: {e}")

        if self._loop:
            self._loop.call_soon_threadsafe(self._loop.stop)

        if self._thread:
            self._thread.join(timeout=5)

        self._running = False
        GLOG.INFO("WebSocketManager shutdown complete")


# 全局单例
_websocket_manager = None

def get_websocket_manager() -> WebSocketManager:
    """获取WebSocketManager单例"""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager
