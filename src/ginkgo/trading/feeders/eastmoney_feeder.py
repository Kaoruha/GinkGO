# Upstream: EastMoney数据源（东方财富WebSocket）
# Downstream: DataManager (数据管理)
# Role: A股实时Tick数据适配器

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


class EastMoneyFeeder(LiveDataFeeder):
    """
    东方财富WebSocket数据适配器（A股）

    配置写死在代码中：
    - WebSocket URI: wss://push2.eastmoney.com/ws/qt/stock/klt.min
    - API密钥: 从GCONF读取（data_sources.eastmoney.api_key）

    使用示例：
        feeder = EastMoneyFeeder()
        feeder.initialize()
        feeder.start()
        feeder.subscribe_symbols(["000001.SZ", "600000.SH"])
        feeder.start_subscription()
    """

    # 写死的配置
    WEBSOCKET_URI = "wss://push2.eastmoney.com/ws/qt/stock/klt.min"
    HEARTBEAT_INTERVAL = 30  # 心跳间隔（秒）

    def __init__(self):
        """初始化EastMoneyFeeder（配置写死）"""
        # 从secure.yml读取API密钥
        api_key = GCONF.get("data_sources.eastmoney.api_key", default="")

        # 调用父类构造（使用写死的配置）
        super().__init__(
            host="",  # 使用完整URI，不需要单独host
            port=0,   # 使用完整URI，不需要单独port
            api_key=api_key,
            enable_rate_limit=True,
            rate_limit_per_second=10.0  # 东方财富限制
        )

        # 覆盖WebSocket URI
        self._websocket_uri = self.WEBSOCKET_URI

        GLOG.INFO(f"EastMoneyFeeder initialized with URI: {self.WEBSOCKET_URI}")

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """
        初始化数据馈送器

        Args:
            config: 忽略（配置写死在代码中）

        Returns:
            bool: 初始化是否成功
        """
        try:
            # 调用父类初始化
            success = super().initialize(config or {})
            if not success:
                return False

            GLOG.INFO("EastMoneyFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"EastMoneyFeeder initialization failed: {e}")
            return False

    async def _async_connect(self) -> bool:
        """异步连接（覆盖父类方法使用完整URI）"""
        try:
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

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
            GLOG.INFO(f"EastMoneyFeeder connected to {self._websocket_uri}")

            return True

        except Exception as e:
            GLOG.ERROR(f"EastMoneyFeeder connection failed: {e}")
            self.is_connected = False
            self.status = DataFeedStatus.DISCONNECTED
            return False

    def _parse_stock_code(self, symbol: str) -> str:
        """
        解析股票代码为东方财富格式

        Args:
            symbol: 标准格式（如000001.SZ）

        Returns:
            东方财富格式（如0.000001）
        """
        if "." in symbol:
            code, market = symbol.split(".")
            if market == "SZ":
                return f"0.{code}"
            elif market == "SH":
                return f"1.{code}"
        return symbol

    async def _send_subscription_message(self, symbols: List[str]) -> bool:
        """
        发送订阅消息到东方财富WebSocket

        Args:
            symbols: 股票代码列表

        Returns:
            bool: 发送是否成功
        """
        try:
            # 构建订阅消息
            subscription_data = {
                "cmd": "sub",
                "param": {
                    "codes": [self._parse_stock_code(s) for s in symbols]
                }
            }

            message = json.dumps(subscription_data)

            if self.websocket:
                await self.websocket.send(message)
                GLOG.INFO(f"EastMoneyFeeder subscribed to {len(symbols)} symbols")
                return True

            return False

        except Exception as e:
            GLOG.ERROR(f"EastMoneyFeeder subscription failed: {e}")
            return False

    def _handle_price_update(self, data: Dict[str, Any]) -> None:
        """
        处理东方财富价格更新消息

        Args:
            data: 原始数据
        """
        try:
            # 解析东方财富数据格式
            symbol = data.get("code", "")
            price = data.get("price", 0.0)
            volume = data.get("volume", 0)
            timestamp = datetime.now()

            # 转换为标准格式
            event = EventPriceUpdate(
                code=symbol,
                timestamp=timestamp,
                price=price,
                volume=volume,
            )

            # 发布事件
            if self.event_publisher:
                self.event_publisher(event)
                self.stats['events_published'] += 1

        except Exception as e:
            GLOG.ERROR(f"EastMoneyFeeder price update handling failed: {e}")
