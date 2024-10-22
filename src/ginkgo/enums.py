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
    OTHER = -1
    CANCEL = 0
    BUY = 1
    SELL = 2


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
    OTHER = 0
    SIM = 1
    REALTIME = 2
    SINA = 3
    BAOSTOCK = 4
    AKSHARE = 5
    YAHOO = 6
    TUSHARE = 7
    TDX = 8


class DIRECTION_TYPES(EnumBase):
    OTHER = 0
    LONG = 1
    SHORT = -1


class TRANSFERDIRECTION_TYPES(EnumBase):
    OTHER = 0
    IN = 1
    OUT = 2


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
    ENGINE = 7
    HANDLER = 8


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


class CAPITALADJUSTMENT_TYPES(EnumBase):
    OTHER = 0
    EXR_EXD = 1  # 除权除息
    BONUS_RIGHTS_LIST = 2  # 送配股上市
    NON_TRADABLE_LIST = 3  # 非流通股上市
    UNKNOWN_CHANGE = 4  # 为知股本变动
    CAPITALCHANGE = 5  # 股本变化
    ADDITIONAL_ISSUANCE = 6  # 新股发行
    SHARE_BUYBACK = 7  # 股份回购
    NEW_SHARE_LIST = 8  # 增发新股上市
    TRANSFER_RIGHTS_LIST = 9  # 转配股上市
    CB_LIST = 10  # 可转债上市
    SPLIT_REVERSE_SPLIT = 11  # 扩缩股
    NON_TRADABLE_REVERSE_SPLIT = 12  # 非流通股缩股
    CALL_WARRANT = 13  # 送认购权证
    PUT_WARRANT = 14  # 送认沽权证
