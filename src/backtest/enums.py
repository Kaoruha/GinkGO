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

from matplotlib.pyplot import cla


class EventType(Enum):
    """
    事件类型

    :param Enum: [description]
    :type Enum: [type]
    """

    MARKET = "市场事件"
    SIGNAL = "信号事件"
    ORDER = "订单事件"
    FILL = "成交事件"


class OrderType(Enum):
    """
    订单类型

    :param Enum: [description]
    :type Enum: [type]
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


class InfoType(Enum):
    """
    信息类型

    :param Enum: [description]
    :type Enum: [type]
    """

    BAR = 100  # 日交易数据
    MinutePrice = 101  # 分钟交易数据
    Message = 102  # 消息数据 TODO后续还会完善扩充


class Direction(Enum):
    """
    交易类型

    :param Enum: [description]
    :type Enum: [type]
    """

    LONG = "多"
    SHORT = "空"
    NET = "净"


class MarketType(Enum):
    """
    市场类型

    :param Enum: [description]
    :type Enum: [type]
    """

    CN = "沪深A股"
    HK = "港股"
    JP = "日股"
    NASDAQ = "纳斯达克"


class Interval(Enum):
    """
    间隔
    Interval of bar
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
