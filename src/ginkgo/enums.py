# Upstream: 全项目所有模块(策略/风控/数据/引擎等依赖这些枚举值)
# Downstream: Python标准库Enum/IntEnum (基类提供枚举转换validate_input/from_int/to_int方法)
# Role: 枚举类型定义中心统一管理27个核心枚举类EnumBase提供转换方法支持交易系统功能和组件集成提供完整业务支持






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
    Types of Events. Extended for unified event-driven architecture.
    """

    VOID = -1
    OTHER = 0
    
    # Market Data Events (1-19)
    PRICEUPDATE = 1
    CLOCKTICK = 2
    MARKETSTATUS = 3
    BARCLOSE = 4
    ENDOFDAY = 5
    
    # Order Lifecycle Events (20-39) 
    ORDERSUBMITTED = 20
    ORDERACK = 21
    ORDERPARTIALLYFILLED = 22
    ORDERFILLED = 23           # 完全成交（兼容旧版，实际使用ORDERPARTIALLYFILLED）
    ORDERREJECTED = 24
    ORDERCANCELACK = 25
    ORDEREXPIRED = 26
    
    # Portfolio Events (40-59)
    POSITIONUPDATE = 40
    CAPITALUPDATE = 41
    PORTFOLIOUPDATE = 42
    INTERESTUPDATE = 43
    
    # Risk Management Events (60-79)
    RISKBREACH = 60
    POSITIONLIMITEXCEEDED = 61
    DAILYLOSSLIMITEXCEEDED = 62
    
    # System Events (80-99)
    NEXTPHASE = 80
    TIME_ADVANCE = 81  # 时间推进事件类型
    COMPONENT_TIME_ADVANCE = 82  # 组件时间推进事件类型
    ENGINESTART = 83
    ENGINESTOP = 84
    
    # Strategy Events (100-119)
    SIGNALGENERATION = 100
    
    # Execution Events (10-19)
    EXECUTIONCONFIRMATION = 11
    EXECUTIONREJECTION = 12
    EXECUTIONTIMEOUT = 13
    EXECUTIONCANCELLATION = 14
    
    # News and External Events (120-139)
    NEWSRECIEVE = 120


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
    TEST = 9
    DATABASE = 10
    BACKTESTFEEDER = 11
    STRATEGY = 12
    SELECTOR = 13
    SIMMATCH = 14
    BACKTEST = 15
    LIVE = 16
    BROKERMATCHMAKING = 17
    MANUAL = 18


class DIRECTION_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    LONG = 1
    SHORT = 2


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
    PARTIAL_FILLED = 3
    FILLED = 4
    CANCELED = 5
    REJECTED = 6


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
    MIN1 = 2
    MIN5 = 3
    MIN15 = 4
    MIN30 = 5
    HOUR1 = 6
    HOUR2 = 7
    HOUR4 = 8
    WEEK = 9
    MONTH = 10
    QUARTER = 11
    YEAR = 12


class MARKET_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    CHINA = 1
    NASDAQ = 2


class ATTITUDE_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    PESSIMISTIC = 1
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
    # T5/T6: 扩展订单生命周期阶段
    ORDERACK = 7
    ORDERPARTIALLYFILLED = 8
    ORDERREJECTED = 9
    ORDEREXPIRED = 10
    ORDERCANCELACK = 11


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
    PAUSED = 3
    STOPPED = 4


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
    COMPLETED = 5
    ERROR = 6
    CANCELED = 7


class ENGINE_ARCHITECTURE(EnumBase):
    """引擎架构类型枚举（执行方式）"""

    VOID = -1
    EVENT_DRIVEN = 1   # 事件驱动架构
    MATRIX = 2         # 矩阵/向量化架构
    HYBRID = 3         # 混合架构
    AUTO = 4           # 自动选择架构


class EXECUTION_MODE(EnumBase):
    """
    执行模式枚举

    支持回测、实盘、模拟等不同运行环境
    """
    VOID = -1
    BACKTEST = 0                # 历史回测
    LIVE = 1                    # 实盘模式（简化）
    SIMULATION = 2              # 模拟模式（简化）
    PAPER_MANUAL = 3            # 模拟盘-人工确认
    LIVE_MANUAL = 4             # 实盘-人工确认
    PAPER_AUTO = 5              # 模拟盘-自动执行
    LIVE_AUTO = 6               # 实盘-自动执行
    SEMI_AUTO = 7               # 半自动模式
    
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
    CANCELED = 4                # 已取消
    FILLED = 5                  # 已成交
    PARTIAL_FILLED = 6          # 部分成交
    ERROR = 7                   # 执行错误


class TRACKINGSTATUS_TYPES(EnumBase):
    """信号追踪状态枚举"""

    VOID = -1
    PENDING = 0                 # 待处理
    NOTIFIED = 1                # 已通知
    EXECUTED = 2                # 已执行
    TIMEOUT = 3                 # 超时
    CANCELED = 4                # 已取消


class ACCOUNT_TYPE(EnumBase):
    """账户类型枚举"""
    
    VOID = -1
    BACKTEST = 0                # 回测账户
    PAPER = 1                   # 模拟盘账户
    LIVE = 2                    # 实盘账户


class COMPONENT_TYPES(EnumBase):
    """组件类型枚举 - 用于标识不同的交易系统组件"""

    VOID = -1
    SIGNAL = 1       # 信号
    ORDER = 2        # 订单
    POSITION = 3     # 持仓
    BAR = 4          # K线数据
    TICK = 5         # Tick数据
    STRATEGY = 6     # 策略
    PORTFOLIO = 7    # 投资组合
    ENGINE = 8       # 引擎
    RISK = 9         # 风险管理
    STOCKINFO = 10   # 股票信息
    ADJUSTFACTOR = 11 # 复权因子
    TRADEDAY = 12    # 交易日历
    TRANSFER = 13    # 资金流转
    CAPITALADJUSTMENT = 14  # 资金调整


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


class TIME_MODE(EnumBase):
    """时间模式枚举 - 用于时间提供者"""

    LOGICAL = 1      # 逻辑时间（回测）
    SYSTEM = 2       # 系统时间（实盘）


# ==================== 用户管理系统枚举 (US2) ====================

class USER_TYPES(EnumBase):
    """用户类型枚举 - 支持用户管理系统"""

    VOID = -1
    OTHER = 0
    PERSON = 1           # 个人用户
    CHANNEL = 2          # 渠道用户（如第三方平台）
    ORGANIZATION = 3     # 组织用户


class CONTACT_TYPES(EnumBase):
    """联系方式类型枚举 - 支持多种通知渠道"""

    VOID = -1
    OTHER = 0
    EMAIL = 1            # 邮箱联系方式
    WEBHOOK = 2          # Webhook联系方式（如钉钉、企业微信等）
    DISCORD = 3          # Discord联系方式


class CONTACT_METHOD_STATUS_TYPES(EnumBase):
    """联系方式状态枚举 - 用于管理用户联系方式的激活状态"""

    VOID = -1
    INACTIVE = 0         # 未激活
    ACTIVE = 1           # 已激活
    DISABLED = 2         # 已禁用
    EXPIRED = 3          # 已过期


class NOTIFICATION_STATUS_TYPES(EnumBase):
    """通知状态枚举 - 用于跟踪通知发送状态"""

    PENDING = 0          # 待发送
    SENT = 1             # 已发送
    FAILED = 2           # 发送失败
    RETRYING = 3         # 重试中


class RECIPIENT_TYPES(EnumBase):
    """通知接收人类型枚举 - 用于区分接收人来源"""

    VOID = -1
    USER = 1             # 单个用户
    USER_GROUP = 2       # 用户组


class TEMPLATE_TYPES(EnumBase):
    """通知模板类型枚举 - 支持多种格式"""

    VOID = -1
    OTHER = 0
    TEXT = 1             # 纯文本模板
    MARKDOWN = 2         # Markdown格式模板
    EMBEDDED = 3         # 嵌入式模板（Discord Embed）


# ==================== Portfolio运行时状态枚举 (Phase 5: 优雅重启) ====================

class PORTFOLIO_RUNSTATE_TYPES(EnumBase):
    """Portfolio 运行时状态枚举（Phase 5: 优雅重启机制）"""

    RUNNING = "RUNNING"           # 正常运行
    STOPPING = "STOPPING"         # 正在停止（准备重载）
    STOPPED = "STOPPED"           # 已停止
    RELOADING = "RELOADING"       # 正在重载配置
    MIGRATING = "MIGRATING"       # 正在迁移到其他节点


# ==================== Data Worker 状态枚举 (009-data-worker) ====================

class WORKER_STATUS_TYPES(EnumBase):
    """Worker 状态枚举（Data Worker 容器化部署）"""

    VOID = -1
    STOPPED = 0      # 已停止
    STARTING = 1     # 启动中
    RUNNING = 2      # 运行中
    STOPPING = 3     # 停止中
    ERROR = 4        # 错误状态


# ==================== 导出所有枚举 ====================

__all__ = [
    # 原有枚举
    "CURRENCY_TYPES",
    "TICKDIRECTION_TYPES",
    "EVENT_TYPES",
    "PRICEINFO_TYPES",
    "SOURCE_TYPES",
    "DIRECTION_TYPES",
    "TRANSFERDIRECTION_TYPES",
    "ORDER_TYPES",
    "ORDERSTATUS_TYPES",
    "TRANSFERSTATUS_TYPES",
    "FREQUENCY_TYPES",
    "MARKET_TYPES",
    "ATTITUDE_TYPES",
    "FILE_TYPES",
    "RECORDSTAGE_TYPES",
    "GRAPHY_TYPES",
    "PARAMETER_TYPES",
    "CAPITALADJUSTMENT_TYPES",
    "ADJUSTMENT_TYPES",
    "ENGINESTATUS_TYPES",
    "STRATEGY_TYPES",
    "MODEL_TYPES",
    "ENGINE_TYPES",
    "EXECUTION_STATUS",
    "TRACKINGSTATUS_TYPES",
    "ACCOUNT_TYPE",
    "COMPONENT_TYPES",
    "ENTITY_TYPES",
    "TIME_MODE",
    # 用户管理系统枚举 (US2)
    "USER_TYPES",
    "CONTACT_TYPES",
    "CONTACT_METHOD_STATUS_TYPES",
    "NOTIFICATION_STATUS_TYPES",
    "TEMPLATE_TYPES",
    "RECIPIENT_TYPES",
    # Portfolio运行时状态枚举 (Phase 5)
    "PORTFOLIO_RUNSTATE_TYPES",
    # Data Worker 枚举 (009-data-worker)
    "WORKER_STATUS_TYPES",
]
