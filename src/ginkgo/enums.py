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
    EXECUTION_CONFIRMATION = 11
    EXECUTION_REJECTION = 12
    EXECUTION_TIMEOUT = 13
    EXECUTION_CANCELLATION = 14


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


class EXECUTION_MODE(EnumBase):
    """
    执行模式枚举
    
    支持当前的人工确认模式和未来的自动化交易模式
    """
    VOID = -1
    BACKTEST = 0                # 历史回测
    PAPER_MANUAL = 1            # 模拟盘-人工确认
    LIVE_MANUAL = 2             # 实盘-人工确认
    PAPER_AUTO = 3              # 模拟盘-自动执行（未来）
    LIVE_AUTO = 4               # 实盘-自动执行（未来）
    SEMI_AUTO = 5               # 半自动模式（未来）
    
    @classmethod
    def is_manual_mode(cls, mode) -> bool:
        """判断是否为人工确认模式"""
        return mode in [cls.PAPER_MANUAL, cls.LIVE_MANUAL]
    
    @classmethod
    def is_auto_mode(cls, mode) -> bool:
        """判断是否为自动执行模式"""
        return mode in [cls.PAPER_AUTO, cls.LIVE_AUTO, cls.SEMI_AUTO]
    
    @classmethod
    def is_paper_mode(cls, mode) -> bool:
        """判断是否为模拟盘模式"""
        return mode in [cls.PAPER_MANUAL, cls.PAPER_AUTO]
    
    @classmethod
    def is_live_mode(cls, mode) -> bool:
        """判断是否为实盘模式"""
        return mode in [cls.LIVE_MANUAL, cls.LIVE_AUTO]
    
    @classmethod
    def get_account_type(cls, mode) -> str:
        """获取账户类型"""
        if cls.is_paper_mode(mode):
            return "paper"
        elif cls.is_live_mode(mode):
            return "live"
        else:
            return "backtest"


class EXECUTION_STATUS(EnumBase):
    """执行状态枚举"""
    
    VOID = -1
    PENDING_CONFIRMATION = 0    # 等待人工确认
    CONFIRMED = 1               # 已确认
    REJECTED = 2                # 被拒绝
    TIMEOUT = 3                 # 超时
    CANCELLED = 4               # 已取消
    FILLED = 5                  # 已成交
    PARTIAL_FILLED = 6          # 部分成交
    ERROR = 7                   # 执行错误


class TRACKING_STATUS(EnumBase):
    """信号追踪状态枚举"""
    
    VOID = -1
    NOTIFIED = 0                # 已通知
    EXECUTED = 1                # 已执行
    TIMEOUT = 2                 # 超时
    CANCELLED = 3               # 已取消


class ACCOUNT_TYPE(EnumBase):
    """账户类型枚举"""
    
    VOID = -1
    BACKTEST = 0                # 回测账户
    PAPER = 1                   # 模拟盘账户
    LIVE = 2                    # 实盘账户


class ENTITY_TYPES(EnumBase):
    """实体类型枚举 - 用于因子管理系统"""
    
    VOID = -1
    STOCK = 1        # 个股
    MARKET = 2       # 市场/指数  
    COUNTRY = 3      # 国家/宏观
    INDUSTRY = 4     # 行业
    COMMODITY = 5    # 商品
    CURRENCY = 6     # 汇率/货币
    BOND = 7         # 债券
    FUND = 8         # 基金
    CRYPTO = 9       # 加密货币
