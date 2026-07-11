"""系统通用域枚举：文件/记录/图形/参数/组件/实体/时间模式/日志级别/日志分类/环境/权限/部署验证状态。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


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
    ORDERCANCELLED = 5  # 双L别名 (#6061)
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


class LEVEL_TYPES(EnumBase):
    """日志级别枚举 - 用于标识日志严重程度"""

    VOID = -1
    DEBUG = 0       # 调试级别
    INFO = 1        # 信息级别
    WARNING = 2     # 警告级别
    ERROR = 3       # 错误级别
    CRITICAL = 4    # 严重错误级别


class LOG_CATEGORY_TYPES(EnumBase):
    """日志类别枚举 - 用于区分日志类型"""

    VOID = -1
    BACKTEST = 0     # 回测业务日志
    COMPONENT = 1    # 组件运行日志
    PERFORMANCE = 2  # 性能监控日志


# ==================== 实盘交易枚举 (从模型文件迁移, #3880) ====================

class EnvironmentType(str):
    """环境类型枚举"""

    PRODUCTION = "production"
    TESTNET = "testnet"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "production":
            return cls.PRODUCTION
        elif value == "testnet":
            return cls.TESTNET
        else:
            raise ValueError(f"Unknown environment type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证环境类型是否有效"""
        return value in [cls.PRODUCTION, cls.TESTNET]


class PermissionType(str):
    """API Key 权限类型枚举"""

    READ = "read"
    TRADE = "trade"
    ADMIN = "admin"

    @classmethod
    def from_str(cls, value: str) -> str:
        """从字符串转换为枚举值"""
        value = value.lower()
        if value == "read":
            return cls.READ
        elif value == "trade":
            return cls.TRADE
        elif value == "admin":
            return cls.ADMIN
        else:
            raise ValueError(f"Unknown permission type: {value}")

    @classmethod
    def validate(cls, value: str) -> bool:
        """验证权限类型是否有效"""
        return value in [cls.READ, cls.TRADE, cls.ADMIN]

    @classmethod
    def all_permissions(cls) -> list:
        """获取所有权限类型"""
        return [cls.READ, cls.TRADE, cls.ADMIN]


class DEPLOYMENT_STATUS:
    """部署状态"""

    PENDING = 0
    DEPLOYED = 1
    FAILED = 2
    STOPPED = 3


class VALIDATION_STATUS:
    """验证状态"""

    RUNNING = 0
    COMPLETED = 1
    FAILED = 2


__all__ = ['FILE_TYPES', 'RECORDSTAGE_TYPES', 'GRAPHY_TYPES', 'PARAMETER_TYPES', 'COMPONENT_TYPES', 'ENTITY_TYPES', 'TIME_MODE', 'LEVEL_TYPES', 'LOG_CATEGORY_TYPES', 'EnvironmentType', 'PermissionType', 'DEPLOYMENT_STATUS', 'VALIDATION_STATUS']
