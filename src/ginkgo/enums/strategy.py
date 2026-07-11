"""策略域枚举：态度/策略类型/模型类型/默认分析器集合。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class ATTITUDE_TYPES(EnumBase):
    VOID = -1
    OTHER = 0
    PESSIMISTIC = 1
    OPTIMISTIC = 2
    RANDOM = 3


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


class DEFAULT_ANALYZER_SET(EnumBase):
    """默认分析器集合枚举 - 用于Portfolio默认分析器配置"""

    MINIMAL = 1      # 最小集: NetValue, Profit
    STANDARD = 2     # 标准集: + MaxDrawdown, SharpeRatio, WinRate
    FULL = 3         # 完整集: 所有分析器


__all__ = ['ATTITUDE_TYPES', 'STRATEGY_TYPES', 'MODEL_TYPES', 'DEFAULT_ANALYZER_SET']
