"""
回测引擎需要的枚举在这里定义
"""
from enum import Enum


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

    BuyMarket = 100  # 以市场价买入
    SellMarket = 101  # 以市场价格卖出
    BuyPrice = 200  # 以特定价格买入
    SellPrice = 201  # 以特定价格卖出


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
