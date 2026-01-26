# Upstream: Alpaca数据源（美股WebSocket）
# Downstream: DataManager (数据管理)
# Role: 美股实时Tick数据适配器

import asyncio
import json
import threading
import time
import websockets
from typing import List, Dict, Any, Optional
from datetime import datetime

from ginkgo.trading.feeders.live_feeder import LiveDataFeeder
from ginkgo.trading.feeders.interfaces import DataFeedStatus
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.libs import GCONF, GLOG


class AlpacaFeeder(LiveDataFeeder):
    """
    Alpaca WebSocket数据适配器（美股）

    配置写死在代码中：
    - WebSocket URI: wss://stream.data.alpaca.markets/v2/iex
    - API密钥: 从GCONF读取（data_sources.alpaca.api_key/api_secret）

    使用示例：
        feeder = AlpacaFeeder()
        feeder.initialize()
        feeder.start()
        feeder.subscribe_symbols(["AAPL", "TSLA"])
        feeder.start_subscription()
    """

    # 写死的配置
    WEBSOCKET_URI = "wss://stream.data.alpaca.markets/v2/iex"
    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    def __init__(self):
        """初始化AlpacaFeeder（配置写死）"""
        # 从secure.yml读取API密钥
        api_key = GCONF.ALPACA_API_KEY
        api_secret = GCONF.ALPACA_API_SECRET

        # 调用父类构造
        super().__init__(
            host="",
            port=0,
            api_key=api_key,  # 使用api_key字段存储api_key
            enable_rate_limit=True,
            rate_limit_per_second=5.0  # Alpaca限制
        )

        # 存储API secret
        self._api_secret = api_secret

        # 覆盖WebSocket URI
        self._websocket_uri = self.WEBSOCKET_URI

        GLOG.INFO(f"AlpacaFeeder initialized with URI: {self.WEBSOCKET_URI}")

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """初始化数据馈送器"""
        try:
            # 验证必需的凭证
            if not self.api_key or not self._api_secret:
                GLOG.WARN("AlpacaFeeder: API credentials not found in secure.yml")
                GLOG.INFO("Set data_sources.alpaca.api_key and api_secret in ~/.ginkgo/secure.yml")

            # 调用父类初始化
            success = super().initialize(config or {})
            if not success:
                return False

            GLOG.INFO("AlpacaFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"AlpacaFeeder initialization failed: {e}")
            return False

    async def _async_connect(self) -> bool:
        """异步连接（使用Alpaca认证）"""
        try:
            # Alpaca使用Basic Auth
            import base64
            credentials = base64.b64encode(
                f"{self.api_key}:{self._api_secret}".encode()
            ).decode()

            headers = {
                "Authorization": f"Basic {credentials}"
            }

            self.websocket = await asyncio.wait_for(
                websockets.connect(
                    self._websocket_uri,
                    extra_headers=headers,
                    ping_interval=self.HEARTBEAT_INTERVAL,
                    ping_timeout=60,
                ),
                timeout=10
            )

            self.is_connected = True
            self.reconnect_attempts = 0
            self.status = DataFeedStatus.CONNECTED
            GLOG.INFO(f"AlpacaFeeder connected to {self._websocket_uri}")

            return True

        except Exception as e:
            GLOG.ERROR(f"AlpacaFeeder connection failed: {e}")
            self.is_connected = False
            self.status = DataFeedStatus.DISCONNECTED
            return False

    async def _send_subscription_message(self, symbols: List[str]) -> bool:
        """
        发送订阅消息到Alpaca WebSocket

        Args:
            symbols: 股票代码列表

        Returns:
            bool: 发送是否成功
        """
        try:
            # Alpaca订阅格式
            subscription_data = {
                "action": "subscribe",
                "trades": symbols,
                "quotes": symbols,
                "bars": symbols
            }

            message = json.dumps(subscription_data)

            if self.websocket:
                await self.websocket.send(message)
                GLOG.INFO(f"AlpacaFeeder subscribed to {len(symbols)} symbols")
                return True

            return False

        except Exception as e:
            GLOG.ERROR(f"AlpacaFeeder subscription failed: {e}")
            return False

    def _handle_price_update(self, data: Dict[str, Any]) -> None:
        """
        处理Alpaca价格更新消息

        Args:
            data: 原始数据（trade或quote消息）
        """
        try:
            # 判断消息类型
            msg_type = data.get("T", "")  # T = message type

            if msg_type == "t":  # Trade message
                symbol = data.get("S", "")
                price = data.get("p", 0.0)
                volume = data.get("v", 0)
                timestamp = datetime.fromtimestamp(data.get("t", time.time()) / 1e9)

            elif msg_type == "q":  # Quote message
                symbol = data.get("S", "")
                price = data.get("bp", data.get("ap", 0.0))  # bid or ask price
                volume = 0
                timestamp = datetime.fromtimestamp(data.get("t", time.time()) / 1e9)

            else:
                return  # 忽略其他消息类型

            # 转换为标准格式
            event = EventPriceUpdate(
                code=symbol,
                timestamp=timestamp,
                price=price,
                volume=volume,
                bid_price=data.get("bp") if msg_type == "q" else None,
                ask_price=data.get("ap") if msg_type == "q" else None,
                bid_volume=data.get("bs") if msg_type == "q" else None,
                ask_volume=data.get("as") if msg_type == "q" else None,
            )

            # 发布事件
            if self.event_publisher:
                self.event_publisher(event)
                self.stats['events_published'] += 1

        except Exception as e:
            GLOG.ERROR(f"AlpacaFeeder price update handling failed: {e}")

    async def _async_receive_message(self) -> Optional[str]:
        """异步接收消息（处理Alpaca多消息格式）"""
        try:
            if not self.websocket or not self.is_connected:
                return None

            message = await self.websocket.receive()

            # Alpaca可能发送多个JSON在一个消息中
            messages = message.split('\n')
            for msg in messages:
                if msg.strip():
                    await self._process_message(msg)

            return message

        except Exception as e:
            GLOG.ERROR(f"AlpacaFeeder receive message failed: {e}")
            return None
