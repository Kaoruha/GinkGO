"""
回测引擎需要的枚举在这里定义
"""
from enum import Enum

class EventType(Enum):
    Market = 100
    Signal = 101
    Order = 102
    Fill = 103

class OrderType(Enum):
    BuyMarket = 100
    SellMarket = 101
    BuyPrice = 200
    SellPrice = 201

class InfoType(Enum):
    DailyPrice = 100
    MinutePrice = 101
    Message = 102

class DealType(Enum):
    BUY = 100
    SELL = 101


class MarketType(Enum):
    Stock_CN = 100