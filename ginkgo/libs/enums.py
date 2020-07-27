# 在这里定义枚举类型
from enum import Enum


class ClientType(Enum):
    USER_EMAIL = 100
    USER_MOBILE = 101

    # 微信小程序
    USER_MINA = 200
    # 微信公众号
    USER_WX = 201

class EventType(Enum):
    Market = 100
    Signal = 101
    Order = 102
    Fill = 103


class InfoType(Enum):
    DailyPrice = 100
    MinutePrice = 101
    Message = 102

class MarketType(Enum):
    Stock_CN = 100
