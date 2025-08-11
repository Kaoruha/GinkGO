from enum import Enum, IntEnum


class EnumBase(Enum):
    @classmethod
    def enum_convert(cls, string):
        r = None
        try:
            r = cls[string.upper()]
        except Exception as e:
            return
        return r

    @classmethod
    def from_int(cls, value):
        """Convert integer value to enum"""
        if isinstance(value, cls):
            return value
        if value is None:
            return None
        try:
            return cls(int(value))
        except (ValueError, TypeError):
            return None

    def to_int(self):
        """Convert enum to integer value"""
        return self.value

    @classmethod
    def validate_input(cls, value):
        """Validate and convert input (enum or int) to integer for database storage"""
        if value is None:
            return None
        if isinstance(value, cls):
            return value.value
        if isinstance(value, int):
            # Validate that the int value exists in enum
            try:
                cls(value)
                return value
            except ValueError:
                return None
        return None

    # def __repr__(self):
    #     return self.value


class CURRENCY_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    CNY = 1
    USD = 2


class TICKDIRECTION_TYPES(EnumBase):
    VOID = -1
    NEUTRAL = 0  # 中性盘 / Unknown direction
    ACTIVEBUY = 1  # 主动买盘 / Aggressor buy
    ACTIVESELL = 2  # 主动卖盘 / Aggressor sell
    CANCEL = 3  # 撤单 / Order cancelled
    REMAIN2LIMIT = 4  # 市价剩余转限价 / Market-to-limit remainder
    MARKET2LIMIT = 5  # 市价剩余转限价 (another flag) / Market-to-limit
    FOKIOC = 6  # 全额成交或撤销 / Fill-or-Kill / Immediate-or-Cancel
    SELFOPTIMAL = 7  # 本方最优 / Best on same side
    COUNTEROPTIMAL = 8  # 对手方最优 / Best on opposite side


class EVENT_TYPES(EnumBase):
    """
    Types of Events.For Backtest.
    """

    VOID = -1
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
    VOID = -1
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
    DATABASE = 9
    BACKTESTFEEDER = 10
    STRATEGY = 11
    SIMMATCH = 12
    BACKTEST = 13
    LIVE = 14


class DIRECTION_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    LONG = 1
    SHORT = -1


class TRANSFERDIRECTION_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    IN = 1
    OUT = 2


class ORDER_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    MARKETORDER = 1
    LIMITORDER = 2


class ORDERSTATUS_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4


class TRANSFERSTATUS_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    NEW = 1
    SUBMITTED = 2
    FILLED = 3
    CANCELED = 4
    PENDING = 5


class FREQUENCY_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    DAY = 1
    MIN5 = 2


class MARKET_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    CHINA = 1
    NASDAQ = 2


class ATTITUDE_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    PESSMISTIC = 1
    OPTIMISTIC = 2
    RANDOM = 3


class FILE_TYPES(EnumBase):
    VOID = -1
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
    VOID = -1
    OTHER = 0
    NEWDAY = 1
    SIGNALGENERATION = 2
    ORDERSEND = 3
    ORDERFILLED = 4
    ORDERCANCELED = 5
    ENDDAY = 6


class GRAPHY_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    BAR = 1
    LINE = 2


class PARAMETER_TYPES(EnumBase):
    VOID = -1
    INT = 0
    STRING = 1
    FLOAT = 2


class CAPITALADJUSTMENT_TYPES(EnumBase):
    VOID = -1
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


class LIVE_MODE(str, Enum):
    VOID = -1
    ON = "on"
    OFF = "off"


class ADJUSTMENT_TYPES(EnumBase):
    """Price adjustment types for stock data"""

    VOID = -1
    NONE = 0  # No adjustment (original data)
    FORE = 1  # Forward adjustment (前复权) - latest price as base
    BACK = 2  # Backward adjustment (后复权) - earliest price as base


class ENGINESTATUS_TYPES(EnumBase):
    VOID = -1
    IDLE = 0
    INITIALIZING = 1
    RUNNING = 2
    STOPPED = 3


class STRATEGY_TYPES(EnumBase):
    """策略类型枚举"""

    VOID = -1
    UNKNOWN = 0
    TRADITIONAL = 1
    ML = 2
    QUANTITATIVE = 3
    TECHNICAL = 4
    FUNDAMENTAL = 5


class MODEL_TYPES(EnumBase):
    """ML模型类型枚举"""

    VOID = -1
    UNKNOWN = 0
    TIME_SERIES = 1
    TABULAR = 2
    ENSEMBLE = 3
    DEEP_LEARNING = 4
    REINFORCEMENT = 5


class ENGINE_TYPES(EnumBase):
    """引擎类型枚举"""

    VOID = -1
    UNKNOWN = 0
    EVENT_DRIVEN = 1
    MATRIX = 2
    HYBRID = 3
    LIVE = 4
    COMPLETED = 4
    ERROR = 5
    CANCELED = 6
