"""
Author: Kaoru
Date: 2021-12-23 00:06:29
LastEditTime: 2022-03-22 01:03:49
LastEditors: Kaoru
Description: Be stronger,be patient,be confident and never say die.
FilePath: /Ginkgo/src/backtest/enums.py
What goes around comes around.
"""
"""
回测引擎需要的枚举在这里定义
"""
from enum import Enum


class EventType(Enum):
    """
    事件类型
    """

    MARKET = "市场事件"
    SIGNAL = "信号事件"
    ORDER = "订单事件"
    FILL = "成交事件"


class OrderType(Enum):
    """
    订单类型
    """

    MARKET = "市价订单"
    LIMIT = "限价订单"
    Close = 102
    Stop = 103
    StopLimit = 104
    Target = 105
    Oco = 106


class OrderStatus(Enum):
    """
    订单状态

    """

    CREATED = "完成创建"
    SUBMITED = "已提交"
    ACCEPTED = "被接受"
    REJECTED = "被拒绝"
    MARGIN = "margin 超出保证金？"
    CANCELLED = "被取消"
    PARTIAL = "部分成交"
    COMPLETED = "全部成交"
    EXPIRED = "失效"


class TradeStatus(Enum):
    """
    交易状态
    """

    CREATED = "完成创建"
    OPEN = "进行中"
    CLOSED = "结束"


class MarketEventType(Enum):
    """
    市场事件类型
    """

    BAR = "Bar"
    TICK = "Tick"
    NEWS = "News"


class Direction(Enum):
    """
    交易类型
    """

    LONG = "多"
    SHORT = "空"
    NET = "净"


class MarketType(Enum):
    """
    市场类型
    """

    CN = "沪深A股"
    HK = "港股"
    JP = "日股"
    NASDAQ = "纳斯达克"


class Interval(Enum):
    """
    间隔
    """

    DAILY = "d"
    MIN5 = "5m"
    TICK = "tick"


class Source(Enum):
    """
    Where the data comes
    """

    BACKTEST = "回测"
    SHLIVE = "上交所实时"
    SNOW = "雪球社区"
