# Upstream: FuShu数据源（港股HTTP轮询）
# Downstream: DataManager (数据管理)
# Role: 港股实时Tick数据适配器（HTTP轮询模式）

import asyncio
import json
import threading
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from queue import Queue

import requests

from ginkgo.trading.feeders.live_feeder import LiveDataFeeder
from ginkgo.trading.feeders.interfaces import DataFeedStatus
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.libs import GCONF, GLOG


class FuShuFeeder(LiveDataFeeder):
    """
    FuShu HTTP轮询数据适配器（港股）

    配置写死在代码中：
    - API Base URL: https://api.fushu.com/v1
    - 轮询间隔: 5秒
    - API密钥: 从GCONF读取（data_sources.fushu.api_key）

    使用示例：
        feeder = FuShuFeeder()
        feeder.initialize()
        feeder.start()
        feeder.subscribe_symbols(["00700.HK"])
        feeder.start_subscription()
    """

    # 写死的配置
    API_BASE_URL = "https://api.fushu.com/v1"
    POLL_INTERVAL = 5  # 轮询间隔（秒）
    TICK_ENDPOINT = "/tick"  # Tick数据端点

    def __init__(self):
        """初始化FuShuFeeder（配置写死）"""
        # 从secure.yml读取API密钥
        api_key = GCONF.FUSHU_API_KEY

        # HTTP轮询模式，不需要host/port
        super().__init__(
            host="",
            port=0,
            api_key=api_key,
            enable_rate_limit=True,
            rate_limit_per_second=0.2  # 每5秒一次请求
        )

        # HTTP会话
        self._session: Optional[requests.Session] = None
        self._polling_thread: Optional[threading.Thread] = None
        self._stop_polling = threading.Event()
        self._data_queue: Queue = Queue(maxsize=1000)

        GLOG.INFO(f"FuShuFeeder initialized with API URL: {self.API_BASE_URL}")

    def initialize(self, config: Dict[str, Any] = None) -> bool:
        """初始化数据馈送器"""
        try:
            # 创建HTTP会话
            self._session = requests.Session()
            if self.api_key:
                self._session.headers.update({
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                })

            # 调用父类初始化
            success = super().initialize(config or {})
            if not success:
                return False

            GLOG.INFO("FuShuFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder initialization failed: {e}")
            return False

    def start(self) -> bool:
        """启动数据馈送"""
        try:
            if self.status != DataFeedStatus.IDLE:
                return False

            # 启动轮询线程
            self._stop_polling.clear()
            self._polling_thread = threading.Thread(
                target=self._polling_loop,
                daemon=True
            )
            self._polling_thread.start()

            self.status = DataFeedStatus.CONNECTED
            GLOG.INFO("FuShuFeeder started successfully (HTTP polling mode)")
            return True

        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder start failed: {e}")
            return False

    def stop(self) -> bool:
        """停止数据馈送"""
        try:
            self._stop_polling.set()

            # 等待轮询线程结束
            if self._polling_thread and self._polling_thread.is_alive():
                self._polling_thread.join(timeout=10)

            # 关闭HTTP会话
            if self._session:
                self._session.close()

            self.status = DataFeedStatus.DISCONNECTED
            GLOG.INFO("FuShuFeeder stopped")
            return True

        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder stop failed: {e}")
            return False

    def subscribe_symbols(self, symbols: List[str], data_types: List[str] = None) -> bool:
        """订阅股票数据（HTTP轮询模式）"""
        try:
            self.subscribed_symbols = symbols
            self.subscribed_data_types = data_types or ["tick"]
            GLOG.INFO(f"FuShuFeeder subscribed to {len(symbols)} symbols")
            return True

        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder subscription failed: {e}")
            return False

    def start_subscription(self) -> bool:
        """开始订阅（HTTP轮询模式已自动开始）"""
        self.status = DataFeedStatus.STREAMING
        return True

    def _polling_loop(self) -> None:
        """HTTP轮询循环"""
        while not self._stop_polling.is_set():
            try:
                # 轮询所有订阅的股票
                if self.subscribed_symbols:
                    self._fetch_tick_data(self.subscribed_symbols)

                # 等待下一次轮询
                self._stop_polling.wait(self.POLL_INTERVAL)

            except Exception as e:
                GLOG.ERROR(f"FuShuFeeder polling error: {e}")
                time.sleep(self.POLL_INTERVAL)

    def _fetch_tick_data(self, symbols: List[str]) -> None:
        """
        获取Tick数据

        Args:
            symbols: 股票代码列表
        """
        try:
            if not self._session:
                return

            # 批量请求数据
            url = f"{self.API_BASE_URL}{self.TICK_ENDPOINT}"
            params = {"symbols": ",".join(symbols)}

            response = self._session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()

            # 处理返回的数据
            self._process_tick_data(data)

        except requests.RequestException as e:
            GLOG.ERROR(f"FuShuFeeder HTTP request failed: {e}")
        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder data processing failed: {e}")

    def _process_tick_data(self, data: Dict[str, Any]) -> None:
        """
        处理Tick数据

        Args:
            data: API返回的数据
        """
        try:
            tick_list = data.get("data", [])

            for tick_data in tick_list:
                symbol = tick_data.get("symbol", "")
                price = tick_data.get("price", 0.0)
                volume = tick_data.get("volume", 0)
                timestamp = datetime.fromisoformat(tick_data.get("timestamp", datetime.now().isoformat()))

                # 创建事件
                event = EventPriceUpdate(
                    code=symbol,
                    timestamp=timestamp,
                    price=price,
                    volume=volume,
                    bid_price=tick_data.get("bid_price"),
                    ask_price=tick_data.get("ask_price"),
                    bid_volume=tick_data.get("bid_volume"),
                    ask_volume=tick_data.get("ask_volume"),
                )

                # 发布事件
                if self.event_publisher:
                    self.event_publisher(event)
                    self.stats['events_published'] += 1

            self.stats['messages_received'] += len(tick_list)

        except Exception as e:
            GLOG.ERROR(f"FuShuFeeder tick data processing failed: {e}")

    def get_connection_info(self) -> Dict[str, Any]:
        """获取连接信息"""
        return {
            "type": "HTTP_POLLING",
            "api_url": self.API_BASE_URL,
            "poll_interval": self.POLL_INTERVAL,
            "subscribed_count": len(self.subscribed_symbols),
            "is_polling": self._polling_thread and self._polling_thread.is_alive() if self._polling_thread else False,
        }
