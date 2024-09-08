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


class CURRENCY_TYPES(EnumBase):
    OTHER = 0
    CNY = 1
    USD = 2


class TICKDIRECTION_TYPES(EnumBase):
    OTHER = 0
    MINUSTICK = 1
    ZEROMINUSTICK = 2
    PLUSTICK = 3
    ZEROPLUSTICK = 4
    NOIDEA = 5


class EVENT_TYPES(EnumBase):
    """
    Types of Events.For Backtest.
    """

    OTHER = 0
    PRICEUPDATE = 1
    ORDERSUBMITTED = 2
    ORDERFILLED = 3
    ORDERCANCELED = 4
    ORDEREXECUTE = 5
    POSITIONUPDATE = 6
    CAPITALUPDATE = 7
    NEWSRECIEVE = 8
    NEXTPHASE = 9
    SIGNALGENERATION = 10


class PRICEINFO_TYPES(EnumBase):
    OTHER = 0
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
    TUSHARE = 7
    PORTFOLIO = 8
    STRATEGY = 9
    SIZER = 10


class DIRECTION_TYPES(EnumBase):
    OTHER = 0
    LONG = 1
    SHORT = -1


class ORDER_TYPES(EnumBase):
    OTHER = 0
    MARKETORDER = 1
    LIMITORDER = 2


class ORDERSTATUS_TYPES(EnumBase):
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4


class TRANSFERSTATUS_TYPES(EnumBase):
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4


class FREQUENCY_TYPES(EnumBase):
    OTHER = 0
    DAY = 1
    MIN5 = 2


class MARKET_TYPES(EnumBase):
    OTHER = 0
    CHINA = 1
    NASDAQ = 2


class ATTITUDE_TYPES(EnumBase):
    OTHER = 0
    PESSMISTIC = 1
    OPTIMISTIC = 2
    RANDOM = 3


class FILE_TYPES(EnumBase):
    OTHER = 0
    ANALYZER = 1
    INDEX = 2
    RISKMANAGER = 3
    SELECTOR = 4
    SIZER = 5
    STRATEGY = 6
    BACKTEST = 7


class RECORDSTAGE_TYPES(EnumBase):
    OTHER = 0
    NEWDAY = 1
    SIGNALGENERATION = 2
    ORDERSEND = 3
    ORDERFILLED = 4
    ORDERCANCELED = 5


class GRAPHY_TYPES(EnumBase):
    OTHER = 0
    BAR = 1
    LINE = 2


class PARAMETER_TYPES(EnumBase):
    INT = 0
    STRING = 1
    FLOAT = 2
