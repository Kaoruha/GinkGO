"""引擎与执行域枚举：引擎架构/执行模式/账户类型/引擎状态/执行状态/实盘开关。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase
from enum import Enum


class LIVE_MODE(str, Enum):
    VOID = -1
    ON = "on"
    OFF = "off"


class ENGINESTATUS_TYPES(EnumBase):
    VOID = -1
    IDLE = 0
    INITIALIZING = 1
    RUNNING = 2
    PAUSED = 3
    STOPPED = 4


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
    CANCELLED = 7  # 双L别名 (#6061)


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
    PAPER = 2                   # 模拟盘模式
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
    CANCELLED = 4                # 双L别名 (#6061)
    FILLED = 5                  # 已成交
    PARTIAL_FILLED = 6          # 部分成交
    ERROR = 7                   # 执行错误


class ACCOUNT_TYPE(EnumBase):
    """账户类型枚举"""
    
    VOID = -1
    BACKTEST = 0                # 回测账户
    PAPER = 1                   # 模拟盘账户
    LIVE = 2                    # 实盘账户


__all__ = ['LIVE_MODE', 'ENGINESTATUS_TYPES', 'ENGINE_TYPES', 'ENGINE_ARCHITECTURE', 'EXECUTION_MODE', 'EXECUTION_STATUS', 'ACCOUNT_TYPE']
