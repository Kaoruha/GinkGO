# Upstream: WebSocketManager (接收WebSocket消息)
# Downstream: Event Bus (发布事件到系统)
# Role: WebSocketEventAdapter 将OKX WebSocket消息转换为Ginkgo事件


"""
WebSocket事件适配器

将OKX WebSocket消息转换为Ginkgo事件系统中的事件对象：
- ticker消息 -> EventPriceUpdate
- account消息 -> EventAccountUpdate
- positions消息 -> EventPositionUpdate
- orders消息 -> EventOrderAck/EventOrderPartiallyFilled/EventOrderRejected
"""

import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from ginkgo.libs import GLOG


def adapt_ticker(message: dict) -> Optional[Dict[str, Any]]:
    """
    将ticker消息转换为价格更新事件数据

    OKX ticker消息格式：
    {
        "arg": {"channel": "tickers", "instId": "BTC-USDT"},
        "data": [{
            "instType": "SPOT",
            "instId": "BTC-USDT",
            "last": "50000.5",
            "lastSz": "0.01",
            "askPx": "50001",
            "bidPx": "50000",
            "open24h": "49500",
            "high24h": "51000",
            "low24h": "49000",
            "volCcy24h": "1000000",
            "vol24h": "20",
            "ts": "1699000000000"
        }]
    }

    Args:
        message: OKX WebSocket ticker消息

    Returns:
        dict: 价格更新事件数据 {
            "symbol": str,
            "price": float,
            "bid_price": float,
            "ask_price": float,
            "volume_24h": float,
            "timestamp": datetime
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        data = data_list[0]
        arg = message.get("arg", {})

        symbol = arg.get("instId", "")
        last_price = float(data.get("last", 0))
        bid_price = float(data.get("bidPx", 0))
        ask_price = float(data.get("askPx", 0))
        volume_24h = float(data.get("vol24h", 0))
        timestamp_ms = int(data.get("ts", 0))

        return {
            "symbol": symbol,
            "price": last_price,
            "bid_price": bid_price,
            "ask_price": ask_price,
            "volume_24h": volume_24h,
            "timestamp": datetime.fromtimestamp(timestamp_ms / 1000)
        }

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt ticker message: {e}")
        return None


def adapt_candlestick(message: dict) -> Optional[Dict[str, Any]]:
    """
    将K线消息转换为K线数据

    OKX candlestick消息格式：
    {
        "arg": {"channel": "candlesticks", "instId": "BTC-USDT"},
        "data": [
            ["1699000000000", "50000", "51000", "49000", "50500", "100", "10", "1"]
        ]
    }
    格式: [时间戳, 开盘, 最高, 最低, 收盘, 成交量, 成交额, 确认状态]

    Args:
        message: OKX WebSocket candlestick消息

    Returns:
        dict: K线数据 {
            "symbol": str,
            "timestamp": datetime,
            "open": float,
            "high": float,
            "low": float,
            "close": float,
            "volume": float,
            "confirmed": bool
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        candle = data_list[0]
        arg = message.get("arg", {})

        symbol = arg.get("instId", "")
        timestamp = datetime.fromtimestamp(int(candle[0]) / 1000)
        open_price = float(candle[1])
        high = float(candle[2])
        low = float(candle[3])
        close = float(candle[4])
        volume = float(candle[5])
        confirmed = candle[7] == "1" or candle[7] == "1"

        return {
            "symbol": symbol,
            "timestamp": timestamp,
            "open": open_price,
            "high": high,
            "low": low,
            "close": close,
            "volume": volume,
            "confirmed": confirmed
        }

    except (ValueError, KeyError, TypeError, IndexError) as e:
        GLOG.ERROR(f"Failed to adapt candlestick message: {e}")
        return None


def adapt_account(message: dict) -> Optional[Dict[str, Any]]:
    """
    将账户余额消息转换为账户更新数据

    OKX account消息格式：
    {
        "arg": {"channel": "account"},
        "data": [{
            "uTime": "1699000000000",
            "totalEq": "10000.5",
            "availEq": "9000",
            "frozenBal": "1000",
            "details": [...]
        }]
    }

    Args:
        message: OKX WebSocket account消息

    Returns:
        dict: 账户更新数据 {
            "total_equity": float,
            "available_balance": float,
            "frozen_balance": float,
            "currency_balances": list,
            "timestamp": datetime
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        data = data_list[0]

        total_equity = float(data.get("totalEq", 0))
        available_balance = float(data.get("availEq", 0))
        frozen_balance = float(data.get("frozenBal", 0))
        timestamp_ms = int(data.get("uTime", 0))

        # 解析币种余额
        currency_balances = []
        details = data.get("details", [])
        for detail in details:
            currency_balances.append({
                "currency": detail.get("ccy", ""),
                "available": detail.get("availBal", "0"),
                "frozen": detail.get("frozenBal", "0"),
                "balance": detail.get("bal", "0")
            })

        return {
            "total_equity": total_equity,
            "available_balance": available_balance,
            "frozen_balance": frozen_balance,
            "currency_balances": currency_balances,
            "timestamp": datetime.fromtimestamp(timestamp_ms / 1000)
        }

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt account message: {e}")
        return None


def adapt_position(message: dict) -> Optional[Dict[str, Any]]:
    """
    将持仓消息转换为持仓更新数据

    OKX positions消息格式：
    {
        "arg": {"channel": "positions", "instType": "SPOT"},
        "data": [{
            "instId": "BTC-USDT",
            "pos": "0.1",
            "avgPx": "50000",
            "upl": "50",
            "uplRatio": "0.01",
            "lever": "1"
        }]
    }

    Args:
        message: OKX WebSocket positions消息

    Returns:
        dict: 持仓更新数据 {
            "symbol": str,
            "side": str,
            "size": float,
            "avg_price": float,
            "unrealized_pnl": float,
            "unrealized_pnl_ratio": float,
            "timestamp": datetime
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        data = data_list[0]
        arg = message.get("arg", {})

        symbol = data.get("instId", "")
        size = float(data.get("pos", 0))

        # OKX现货没有持仓概念，跳过
        if size == 0:
            return None

        avg_price = float(data.get("avgPx", 0))
        unrealized_pnl = float(data.get("upl", 0))
        unrealized_pnl_ratio = float(data.get("uplRatio", 0))

        return {
            "symbol": symbol,
            "side": "long",  # OKX默认为long
            "size": size,
            "avg_price": avg_price,
            "unrealized_pnl": unrealized_pnl,
            "unrealized_pnl_ratio": unrealized_pnl_ratio,
            "timestamp": datetime.now()
        }

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt position message: {e}")
        return None


def adapt_order(message: dict) -> Optional[Dict[str, Any]]:
    """
    将订单消息转换为订单更新数据

    OKX orders消息格式：
    {
        "arg": {"channel": "orders", "instType": "SPOT"},
        "data": [{
            "instId": "BTC-USDT",
            "ordId": "12345",
            "clOrdId": "client-123",
            "side": "buy",
            "ordType": "limit",
            "px": "50000",
            "sz": "0.1",
            "fillSz": "0.05",
            "avgPx": "50001",
            "state": "live",  # live, partially_filled, filled, canceled
            "cTime": "1699000000000"
        }]
    }

    订单状态映射：
    - live -> SUBMITTED (已提交)
    - partially_filled -> PARTIAL_FILLED (部分成交)
    - filled -> FILLED (完全成交)
    - canceled -> CANCELED (已撤销)

    Args:
        message: OKX WebSocket orders消息

    Returns:
        dict: 订单更新数据 {
            "exchange_order_id": str,
            "client_order_id": str,
            "symbol": str,
            "side": str,
            "order_type": str,
            "price": float,
            "size": float,
            "filled_size": float,
            "avg_fill_price": float,
            "status": str,
            "timestamp": datetime
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        data = data_list[0]

        exchange_order_id = data.get("ordId", "")
        client_order_id = data.get("clOrdId", "")
        symbol = data.get("instId", "")
        side = data.get("side", "")
        order_type = data.get("ordType", "")
        price = float(data.get("px", 0))
        size = float(data.get("sz", 0))
        filled_size = float(data.get("fillSz", 0))
        avg_fill_price = float(data.get("avgPx", 0))

        # 映射OKX状态到Ginkgo状态
        okx_state = data.get("state", "")
        status = _map_order_status(okx_state)

        timestamp_ms = int(data.get("cTime", 0))

        return {
            "exchange_order_id": exchange_order_id,
            "client_order_id": client_order_id,
            "symbol": symbol,
            "side": side,
            "order_type": order_type,
            "price": price,
            "size": size,
            "filled_size": filled_size,
            "avg_fill_price": avg_fill_price,
            "status": status,
            "timestamp": datetime.fromtimestamp(timestamp_ms / 1000)
        }

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt order message: {e}")
        return None


def adapt_order_algo(message: dict) -> Optional[Dict[str, Any]]:
    """
    将策略订单消息转换为订单更新数据

    OKX orders-algo消息格式类似orders，但包含策略订单特有的字段

    Args:
        message: OKX WebSocket orders-algo消息

    Returns:
        dict: 订单更新数据（格式与adapt_order相同）
    """
    # 策略订单的适配逻辑与普通订单类似
    return adapt_order(message)


def _map_order_status(okx_state: str) -> str:
    """
    映射OKX订单状态到Ginkgo状态

    Args:
        okx_state: OKX订单状态

    Returns:
        str: Ginkgo订单状态
    """
    status_map = {
        "live": "submitted",           # 已提交
        "partially_filled": "partially_filled",  # 部分成交
        "filled": "filled",            # 完全成交
        "canceled": "canceled",        # 已撤销
        "mmp": "rejected",             # MMP保护拒绝
    }

    return status_map.get(okx_state, "unknown")


def adapt_trades(message: dict) -> Optional[List[Dict[str, Any]]]:
    """
    将成交消息转换为成交数据列表

    OKX trades消息格式：
    {
        "arg": {"channel": "trades", "instId": "BTC-USDT"},
        "data": [{
            "tradeId": "12345",
            "px": "50000",
            "sz": "0.1",
            "side": "buy",
            "ts": "1699000000000"
        }]
    }

    Args:
        message: OKX WebSocket trades消息

    Returns:
        list: 成交数据列表 [{
            "trade_id": str,
            "price": float,
            "size": float,
            "side": str,
            "timestamp": datetime
        }]
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        trades = []
        for data in data_list:
            trades.append({
                "trade_id": data.get("tradeId", ""),
                "price": float(data.get("px", 0)),
                "size": float(data.get("sz", 0)),
                "side": data.get("side", ""),
                "timestamp": datetime.fromtimestamp(int(data.get("ts", 0)) / 1000)
            })

        return trades

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt trades message: {e}")
        return None


def adapt_orderbook(message: dict) -> Optional[Dict[str, Any]]:
    """
    将订单簿消息转换为订单簿数据

    OKX books消息格式：
    {
        "arg": {"channel": "books", "instId": "BTC-USDT"},
        "data": [{
            "bids": [["50000", "1", "1", "1"]],
            "asks": [["50001", "1", "1", "1"]],
            "ts": "1699000000000"
        }]
    }
    格式: [价格, 数量, 订单数, ...]

    Args:
        message: OKX WebSocket books消息

    Returns:
        dict: 订单簿数据 {
            "symbol": str,
            "bids": list,  # [[price, size, orders], ...]
            "asks": list,
            "timestamp": datetime
        }
    """
    try:
        data_list = message.get("data", [])
        if not data_list:
            return None

        data = data_list[0]
        arg = message.get("arg", {})

        symbol = arg.get("instId", "")
        bids = [[float(x[0]), float(x[1])] for x in data.get("bids", [])[:20]]
        asks = [[float(x[0]), float(x[1])] for x in data.get("asks", [])[:20]]
        timestamp_ms = int(data.get("ts", 0))

        return {
            "symbol": symbol,
            "bids": bids,
            "asks": asks,
            "timestamp": datetime.fromtimestamp(timestamp_ms / 1000)
        }

    except (ValueError, KeyError, TypeError) as e:
        GLOG.ERROR(f"Failed to adapt orderbook message: {e}")
        return None


class WebSocketEventAdapter:
    """
    WebSocket事件适配器类

    提供统一的接口将OKX WebSocket消息转换为Ginkgo事件
    """

    # 支持的频道映射
    CHANNEL_ADAPTERS = {
        "tickers": adapt_ticker,
        "candlesticks": adapt_candlestick,
        "candlesticks1m": adapt_candlestick,
        "candlesticks3m": adapt_candlestick,
        "candlesticks5m": adapt_candlestick,
        "candlesticks15m": adapt_candlestick,
        "candlesticks30m": adapt_candlestick,
        "candlesticks1H": adapt_candlestick,
        "candlesticks2H": adapt_candlestick,
        "candlesticks4H": adapt_candlestick,
        "candlesticks6H": adapt_candlestick,
        "candlesticks12H": adapt_candlestick,
        "candlesticks1D": adapt_candlestick,
        "candlesticks1W": adapt_candlestick,
        "candlesticks1M": adapt_candlestick,
        "account": adapt_account,
        "positions": adapt_position,
        "orders": adapt_order,
        "orders-algo": adapt_order_algo,
        "trades": adapt_trades,
        "books": adapt_orderbook,
        "books-l2-tbt": adapt_orderbook,
        "books5-l2-tbt": adapt_orderbook,
    }

    @classmethod
    def adapt(cls, message: dict) -> Optional[Any]:
        """
        根据消息类型自动适配

        Args:
            message: OKX WebSocket消息

        Returns:
            适配后的数据
        """
        try:
            arg = message.get("data", {}).get("arg", {})
            channel = arg.get("channel", "")

            adapter = cls.CHANNEL_ADAPTERS.get(channel)
            if adapter:
                return adapter(message)
            else:
                GLOG.WARNING(f"No adapter found for channel: {channel}")
                return None

        except Exception as e:
            GLOG.ERROR(f"Error adapting message: {e}")
            return None

    @classmethod
    def adapt_to_event(cls, message: dict, event_factory):
        """
        将消息转换为事件对象

        Args:
            message: OKX WebSocket消息
            event_factory: 事件工厂函数

        Returns:
            Event: 事件对象或None
        """
        adapted_data = cls.adapt(message)
        if adapted_data is None:
            return None

        # 根据数据类型创建对应的事件
        arg = message.get("data", {}).get("arg", {})
        channel = arg.get("channel", "")

        if channel == "tickers":
            return event_factory.create_price_update(adapted_data)
        elif channel == "account":
            return event_factory.create_account_update(adapted_data)
        elif channel == "positions":
            return event_factory.create_position_update(adapted_data)
        elif channel in ["orders", "orders-algo"]:
            return event_factory.create_order_update(adapted_data)
        elif channel.startswith("candlesticks"):
            return event_factory.create_candlestick_update(adapted_data)
        else:
            GLOG.DEBUG(f"No event mapping for channel: {channel}")
            return None
