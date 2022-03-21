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

    Market = 100  # 市场事件
    Signal = 101  # 信号事件
    Order = 102  # 订单事件
    Fill = 103  # 成交事件


class OrderType(Enum):
    """
    订单类型

    :param Enum: [description]
    :type Enum: [type]
    """

    Market = 100  # 市场订单
    Limit = 101  # 限价订单
    Close = 102
    Stop = 103
    StopLimit = 104
    Target = 105
    Oco = 106


class OrderStatud(Enum):
    """
    订单状态

    """

    Created = 100
    Submited = 102
    Accepted = 103
    Rejected = 201
    Margin = 202
    Canceled = 203
    Partial = 204
    Completed = 301
    Expired = 302


class TradeStatus(Enum):
    """
    交易状态
    """

    Created = 100
    Open = 101
    Closed = 102


class InfoType(Enum):
    """
    信息类型

    :param Enum: [description]
    :type Enum: [type]
    """

    DailyPrice = 100  # 日交易数据
    MinutePrice = 101  # 分钟交易数据
    Message = 102  # 消息数据 TODO后续还会完善扩充


class DealType(Enum):
    """
    交易类型

    :param Enum: [description]
    :type Enum: [type]
    """

    BUY = 100  # 买入
    SELL = 101  # 卖出


class MarketType(Enum):
    """
    市场类型

    :param Enum: [description]
    :type Enum: [type]
    """

    Stock_CN = 100  # 中国沪深A股
    Stock_HK = 101  # 港股
    Stock_JP = 102  # 日股
    Stock_US = 103  # 美股


class PriceType(Enum):
    """
    价格类型
    """

    Day = 100  # 日线
    Min5 = 101  # 5Min线
    Now = 102  # 当前价格
