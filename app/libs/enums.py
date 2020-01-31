# 在这里定义枚举类型
from enum import Enum


class ClientTypeEnum(Enum):
    USER_EMAIL = 100
    USER_MOBILE = 101

    # 微信小程序
    USER_MINA = 200
    # 微信公众号
    USER_WX = 201


class BuyOrSell(Enum):
    BUY = 1
    SELL = 0
