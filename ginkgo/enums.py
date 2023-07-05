from enum import Enum, IntEnum


class EnumBase(Enum):
    @classmethod
    def enum_convert(cls, string):
        r = None
        try:
            r = cls[string.upper()]
        except Exception as e:
            print(e)
        return r

    # def __repr__(self):
    #     return self.value


class TICKDIRECTION_TYPES(EnumBase):
    MINUSTICK = 1
    ZEROMINUSTICK = 2
    PLUSTICK = 3
    ZEROPLUSTICK = 4


class EVENT_TYPES(EnumBase):
    """
    Types of Events.For Backtest.
    """

    PRICEUPDATE = 1
    ORDERSUBMISSION = 2
    ORDERFILL = 3
    TRADEEXCUTION = 4
    TRADECANCELLATION = 5
    POSITIONUPDATE = 6
    CAPITALUPDATE = 7
    NEWSRECIEVE = 8
    NEXTPHASE = 9


class PRICEINFO_TYPES(EnumBase):
    BAR = 1
    TICK = 2


class SOURCE_TYPES(EnumBase):
    VOID = -1
    TEST = 0
    SIM = 1
    REALTIME = 2
    SINA = 3
    BAOSTOCK = 4
    AKSHARE = 5
    YAHOO = 6
    PORTFOLIO = 7
    TUSHARE = 7


class DIRECTION_TYPES(EnumBase):
    LONG = 1
    SHORT = -1


class ORDER_TYPES(EnumBase):
    MARKETORDER = 1
    LIMITORDER = 2


class ORDERSTATUS_TYPES(EnumBase):
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4


class FREQUENCY_TYPES(EnumBase):
    DAY = 1
    MIN5 = 2


class MARKET_TYPES(EnumBase):
    CHINA = 1
    NASDAQ = 2


class ATTITUDE_TYPES(EnumBase):
    PESSMISTIC = 1
    OPTIMISTIC = 2
