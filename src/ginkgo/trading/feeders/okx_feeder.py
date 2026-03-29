# Upstream: BaseFeeder (数据馈送器基类)
# Downstream: OKX Public Market Data API
# Role: OKX 市场数据馈送器，提供K线、实时行情、交易对查询功能


"""
OKX 市场数据馈送器

通过 OKX Public Market Data API 获取市场数据：
- K线数据（多时间周期）
- 实时行情（ticker）
- 交易对信息
- 订单簿深度

无需 API 认证，使用公开接口。
"""

import requests

from ginkgo.libs import GCONF
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from functools import lru_cache

from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.enums import SOURCE_TYPES
from ginkgo.libs import GLOG


class OKXMarketDataFeeder(BaseFeeder):
    """
    OKX 市场数据馈送器

    继承 BaseFeeder，实现 OKX 交易所的数据获取功能。
    使用 OKX Public Market Data API，无需认证。
    """

    # K线周期映射
    BAR_MAPPING = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1H": "1H",
        "2H": "2H",
        "4H": "4H",
        "6H": "6H",
        "12H": "12H",
        "1D": "1D",
        "1W": "1W",
        "1M": "1M"
    }

    def __init__(self, environment: str = "testnet", name: str = "okx_feeder", *args, **kwargs):
        """
        初始化 OKX 行情数据源

        Args:
            environment: 环境 ("testnet" 或 "production")
            name: Feeder 名称
        """
        super().__init__(name=name, *args, **kwargs)

        # OKX API 配置
        self.OKX_DOMAIN = GCONF.OKX_DOMAIN

        if environment == "testnet":
            self.domain = self.OKX_DOMAIN
            self.flag = "1"
        else:
            self.domain = self.OKX_DOMAIN
            self.flag = "0"

        self.environment = environment
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Ginkgo-OKXFeeder/1.0"
        })

        # WebSocket相关
        self._ws_enabled = False
        self._ws_connection = None
        self._ticker_cache = {}
        self._candle_cache = {}
        self._orderbook_cache = {}
        self._trades_cache = {}

        GLOG.INFO(f"OKXMarketDataFeeder initialized: {environment}")

    # ==================== BaseFeeder 接口实现 ====================

    def is_code_on_market(self, code: str, *args, **kwargs) -> bool:
        """
        检查交易对是否在市场上

        Args:
            code: 交易对代码 (如 "SAHARA-USDT")

        Returns:
            bool: 是否存在该交易对
        """
        try:
            instruments = self.get_instruments(inst_type="SPOT")
            return any(inst["instId"] == code for inst in instruments)
        except Exception as e:
            GLOG.ERROR(f"Failed to check if {code} is on market: {e}")
            return False

    def _load_daybar(self, code: str, dt, *args, **kwargs) -> pd.DataFrame:
        """
        加载日线K线数据

        Args:
            code: 交易对代码
            dt: 日期

        Returns:
            pd.DataFrame: K线数据
        """
        try:
            # 调用 OKX candles API
            url = f"{self.domain}/api/v5/market/candles"
            params = {
                "instId": code,
                "bar": "1D",
                "after": str(int(dt.timestamp() * 1000))  # 时间戳（毫秒）
            }

            response = self.session.get(url, params=params, timeout=10)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX candles API error: {result.get('msg')}")
                return pd.DataFrame()

            # 解析K线数据
            # 格式: [timestamp, open, high, low, close, volume, ccyVol, confirm]
            candles = result.get("data", [])

            if not candles:
                return pd.DataFrame()

            # 转换为 DataFrame (OKX 返回 9 列)
            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "ccy_volume", "vol_ccy_quote", "confirm"
            ])

            # 数据类型转换
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # 只返回指定日期的数据
            df = df[df["timestamp"].dt.date == dt.date()]

            return df

        except Exception as e:
            GLOG.ERROR(f"Failed to load daybar for {code} at {dt}: {e}")
            return pd.DataFrame()

    # ==================== OKX 特定功能 ====================

    def get_all_tickers(self, inst_type: str = "SPOT") -> Dict[str, Dict[str, Any]]:
        """
        批量获取所有交易对实时行情

        Args:
            inst_type: 产品类型 (SPOT 现货, SWAP 永续合约等)

        Returns:
            dict: 所有交易对行情数据 {symbol: ticker_data}
        """
        try:
            url = f"{self.domain}/api/v5/market/tickers"
            params = {"instType": inst_type}

            response = self.session.get(url, params=params, timeout=10)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX all tickers API error: {result.get('msg')}")
                return {}

            tickers = {}
            for item in result.get("data", []):
                symbol = item.get("instId", "")
                tickers[symbol] = {
                    "symbol": symbol,
                    "last_price": item.get("last", "0"),
                    "bid_price": item.get("bidPx", "0"),
                    "ask_price": item.get("askPx", "0"),
                    "open_24h": item.get("open24h", "0"),
                    "high_24h": item.get("high24h", "0"),
                    "low_24h": item.get("low24h", "0"),
                    "volume_24h": item.get("vol24h", "0"),
                    "volume_ccy_24h": item.get("volCcy24h", "0"),
                    "timestamp": item.get("ts", "0")
                }

            GLOG.INFO(f"获取到 {len(tickers)} 个交易对行情")
            return tickers

        except Exception as e:
            GLOG.ERROR(f"获取所有 ticker 失败: {e}")
            return {}

    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """
        获取交易标的实时行情

        Args:
            symbol: 交易对 (如 "SAHARA-USDT", "BTC-USDT")

        Returns:
            dict: 行情数据
            {
                "symbol": str,
                "last_price": str,
                "bid_price": str,
                "ask_price": str,
                "open_24h": str,
                "high_24h": str,
                "low_24h": str,
                "volume_24h": str,
                "volume_ccy_24h": str,
                "timestamp": str
            }
        """
        try:
            url = f"{self.domain}/api/v5/market/ticker"
            params = {"instId": symbol}

            response = self.session.get(url, params=params, timeout=5)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX ticker API error for {symbol}: {result.get('msg')}")
                return {}

            data = result.get("data", [])
            if not data:
                return {}

            ticker = data[0]
            return {
                "symbol": symbol,
                "last_price": ticker.get("last", "0"),
                "bid_price": ticker.get("bidPx", "0"),
                "ask_price": ticker.get("askPx", "0"),
                "open_24h": ticker.get("open24h", "0"),
                "high_24h": ticker.get("high24h", "0"),
                "low_24h": ticker.get("low24h", "0"),
                "volume_24h": ticker.get("vol24h", "0"),
                "volume_ccy_24h": ticker.get("volCcy24h", "0"),
                "timestamp": ticker.get("ts", "")
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to get ticker for {symbol}: {e}")
            return {}

    def get_klines(
        self,
        symbol: str,
        bar: str = "1H",
        limit: int = 100,
        after: Optional[datetime] = None,
        before: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        获取K线数据

        Args:
            symbol: 交易对 (如 "SAHARA-USDT")
            bar: K线周期 (1m/3m/5m/15m/30m/1H/2H/4H/6H/12H/1D/1W/1M)
            limit: 返回数量 (最大300)
            after: 查询此时间戳之前的数据
            before: 查询此时间戳之后的数据

        Returns:
            pd.DataFrame: K线数据
        """
        try:
            if bar not in self.BAR_MAPPING:
                raise ValueError(f"Invalid bar period: {bar}. Supported: {list(self.BAR_MAPPING.keys())}")

            url = f"{self.domain}/api/v5/market/candles"
            params = {
                "instId": symbol,
                "bar": self.BAR_MAPPING[bar],
                "limit": str(min(limit, 300))
            }

            if after:
                params["after"] = str(int(after.timestamp() * 1000))
            if before:
                params["before"] = str(int(before.timestamp() * 1000))

            response = self.session.get(url, params=params, timeout=10)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX candles API error: {result.get('msg')}")
                return pd.DataFrame()

            candles = result.get("data", [])
            if not candles:
                return pd.DataFrame()

            # 转换为 DataFrame (OKX 返回 9 列)
            df = pd.DataFrame(candles, columns=[
                "timestamp", "open", "high", "low", "close", "volume",
                "ccy_volume", "vol_ccy_quote", "confirm"
            ])

            # 数据类型转换
            df["timestamp"] = pd.to_datetime(df["timestamp"].astype(int), unit="ms")
            df["open"] = df["open"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            df["close"] = df["close"].astype(float)
            df["volume"] = df["volume"].astype(float)

            # 按时间排序
            df = df.sort_values("timestamp").reset_index(drop=True)

            return df

        except Exception as e:
            GLOG.ERROR(f"Failed to get klines for {symbol}: {e}")
            return pd.DataFrame()

    @lru_cache(maxsize=1000)
    def get_instruments(self, inst_type: str = "SPOT", inst_id: str = "") -> List[Dict[str, Any]]:
        """
        获取交易对列表

        Args:
            inst_type: 产品类型 (SPOT/SWAP/FUTURES/OPTION)
            inst_id: 产品ID (如 "SAHARA-USDT")

        Returns:
            list: 交易对信息列表
        """
        try:
            url = f"{self.domain}/api/v5/public/instruments"
            params = {"instType": inst_type}

            if inst_id:
                params["instId"] = inst_id

            response = self.session.get(url, params=params, timeout=10)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX instruments API error: {result.get('msg')}")
                return []

            return result.get("data", [])

        except Exception as e:
            GLOG.ERROR(f"Failed to get instruments: {e}")
            return []

    def get_orderbook(self, symbol: str, depth: int = 20) -> Dict[str, Any]:
        """
        获取订单簿深度

        Args:
            symbol: 交易对
            depth: 深度 (最大400)

        Returns:
            dict: 订单簿数据
            {
                "bids": [[price, size, orders, ...], ...],
                "asks": [[price, size, orders, ...], ...],
                "timestamp": str
            }
        """
        try:
            url = f"{self.domain}/api/v5/market/books"
            params = {
                "instId": symbol,
                "sz": str(min(depth, 400))
            }

            response = self.session.get(url, params=params, timeout=5)
            result = response.json()

            if result.get("code") != "0":
                GLOG.ERROR(f"OKX orderbook API error: {result.get('msg')}")
                return {}

            data = result.get("data", [])
            if not data:
                return {}

            book = data[0]
            return {
                "bids": book.get("bids", []),
                "asks": book.get("asks", []),
                "timestamp": book.get("ts", "")
            }

        except Exception as e:
            GLOG.ERROR(f"Failed to get orderbook for {symbol}: {e}")
            return {}

    def get_supported_symbols(self, quote_ccy: str = "USDT") -> List[str]:
        """
        获取支持的交易对列表

        Args:
            quote_ccy: 计价货币 (如 "USDT", "USD", "BTC")

        Returns:
            list: 交易对列表
        """
        try:
            instruments = self.get_instruments(inst_type="SPOT")

            symbols = []
            for inst in instruments:
                # 只返回状态为 live 的交易对
                if inst.get("state") == "live":
                    inst_id = inst.get("instId", "")
                    # 过滤指定计价货币
                    if inst_id.endswith(f"-{quote_ccy}"):
                        symbols.append(inst_id)

            return sorted(symbols)

        except Exception as e:
            GLOG.ERROR(f"Failed to get supported symbols: {e}")
            return []

    def close(self):
        """关闭会话"""
        if self.session:
            self.session.close()
        if hasattr(self, '_ws_connection') and self._ws_connection:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            ws_manager.disconnect(self._ws_connection)
        GLOG.INFO("OKXMarketDataFeeder closed")

    # ==================== WebSocket 支持 ====================

    def enable_websocket(self) -> bool:
        """
        启用WebSocket连接

        使用WebSocket接收实时行情推送，替代轮询方式

        Returns:
            bool: 启用是否成功
        """
        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager, WebSocketType

            ws_manager = get_websocket_manager()

            # 获取公开WebSocket连接
            self._ws_connection = ws_manager.get_public_ws(
                exchange="okx",
                environment=self.environment
            )

            # 连接WebSocket
            if ws_manager.connect(self._ws_connection):
                self._ws_enabled = True
                GLOG.INFO("WebSocket enabled for OKXMarketDataFeeder")
                return True
            else:
                GLOG.ERROR("Failed to connect WebSocket")
                return False

        except ImportError as e:
            GLOG.ERROR(f"WebSocket dependencies not available: {e}")
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to enable WebSocket: {e}")
            return False

    def subscribe_ticker_ws(self, symbol: str, callback=None) -> bool:
        """
        订阅ticker推送 (WebSocket)

        Args:
            symbol: 交易对 (如 "BTC-USDT")
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            # 默认回调：更新本地缓存
            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_ticker
                data = adapt_ticker(message)
                if data:
                    # 更新缓存
                    self._ticker_cache[symbol] = data
                    GLOG.DEBUG(f"Ticker updated via WebSocket: {symbol} = {data['price']}")

            # 使用提供的回调或默认回调
            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel="tickers",
                inst_id=symbol,
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe ticker via WebSocket: {e}")
            return False

    def subscribe_candlesticks_ws(
        self,
        symbol: str,
        bar: str = "1H",
        callback=None
    ) -> bool:
        """
        订阅K线推送 (WebSocket)

        Args:
            symbol: 交易对 (如 "BTC-USDT")
            bar: K线周期 (1m/3m/5m/15m/30m/1H/2H/4H/6H/12H/1D/1W/1M)
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            # OKX WebSocket频道名
            channel = f"candlesticks{bar}"

            # 默认回调：更新本地缓存
            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_candlestick
                data = adapt_candlestick(message)
                if data:
                    key = f"{symbol}_{bar}"
                    if not hasattr(self, '_candle_cache'):
                        self._candle_cache = {}
                    self._candle_cache[key] = data
                    GLOG.DEBUG(f"Candlestick updated via WebSocket: {key}")

            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel=channel,
                inst_id=symbol,
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe candlesticks via WebSocket: {e}")
            return False

    def subscribe_orderbook_ws(self, symbol: str, channel: str = "books", callback=None) -> bool:
        """
        订阅订单簿推送 (WebSocket)

        Args:
            symbol: 交易对 (如 "BTC-USDT")
            channel: 频道类型 (books/books-l2-tbt/books5-l2-tbt)
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_orderbook
                data = adapt_orderbook(message)
                if data:
                    if not hasattr(self, '_orderbook_cache'):
                        self._orderbook_cache = {}
                    self._orderbook_cache[symbol] = data
                    GLOG.DEBUG(f"Orderbook updated via WebSocket: {symbol}")

            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel=channel,
                inst_id=symbol,
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe orderbook via WebSocket: {e}")
            return False

    def subscribe_trades_ws(self, symbol: str, callback=None) -> bool:
        """
        订阅成交推送 (WebSocket)

        Args:
            symbol: 交易对 (如 "BTC-USDT")
            callback: 回调函数 (可选)

        Returns:
            bool: 订阅是否成功
        """
        if not hasattr(self, '_ws_connection') or not self._ws_connection:
            if not self.enable_websocket():
                return False

        try:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()

            def default_callback(message):
                from ginkgo.livecore.websocket_event_adapter import adapt_trades
                trades = adapt_trades(message)
                if trades:
                    if not hasattr(self, '_trades_cache'):
                        self._trades_cache = {}
                    if symbol not in self._trades_cache:
                        self._trades_cache[symbol] = []
                    self._trades_cache[symbol].extend(trades)
                    # 限制缓存大小
                    if len(self._trades_cache[symbol]) > 100:
                        self._trades_cache[symbol] = self._trades_cache[symbol][-100:]
                    GLOG.DEBUG(f"Trades updated via WebSocket: {symbol}, {len(trades)} new trades")

            cb = callback or default_callback

            return ws_manager.subscribe(
                self._ws_connection,
                channel="trades",
                inst_id=symbol,
                callback=cb
            )

        except Exception as e:
            GLOG.ERROR(f"Failed to subscribe trades via WebSocket: {e}")
            return False

    def unsubscribe_ticker_ws(self, symbol: str) -> bool:
        """取消订阅ticker"""
        if hasattr(self, '_ws_connection') and self._ws_connection:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            return ws_manager.unsubscribe(self._ws_connection, "tickers", symbol)
        return False

    def unsubscribe_candlesticks_ws(self, symbol: str, bar: str = "1H") -> bool:
        """取消订阅K线"""
        if hasattr(self, '_ws_connection') and self._ws_connection:
            from ginkgo.livecore.websocket_manager import get_websocket_manager
            ws_manager = get_websocket_manager()
            channel = f"candlesticks{bar}"
            return ws_manager.unsubscribe(self._ws_connection, channel, symbol)
        return False

    def get_cached_ticker(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        获取缓存的ticker数据（来自WebSocket推送）

        Args:
            symbol: 交易对

        Returns:
            dict: ticker数据或None
        """
        return getattr(self, '_ticker_cache', {}).get(symbol)

    def get_cached_candlestick(self, symbol: str, bar: str = "1H") -> Optional[Dict[str, Any]]:
        """
        获取缓存的K线数据（来自WebSocket推送）

        Args:
            symbol: 交易对
            bar: K线周期

        Returns:
            dict: K线数据或None
        """
        key = f"{symbol}_{bar}"
        return getattr(self, '_candle_cache', {}).get(key)
