# Upstream: BacktestEngine, LiveEngine, EventProcessor, all time-aware components
# Downstream: ITimeProvider, ITimeAwareComponent, LogicalTimeProvider, SystemTimeProvider, TimeBoundaryValidator, TIME_MODE
# Role: 时间管理模块包，导出时间提供者接口和逻辑/系统时钟实现






"""
时间管理模块

提供统一的时间语义和时间控制接口，避免多时钟漂移问题。
"""

from .interfaces import ITimeProvider, ITimeAwareComponent
from .providers import LogicalTimeProvider, SystemTimeProvider, TimeBoundaryValidator
from ginkgo.enums import TIME_MODE

__all__ = [
    'ITimeProvider',
    'ITimeAwareComponent',
    'TIME_MODE',
    'LogicalTimeProvider',
    'SystemTimeProvider',
    'TimeBoundaryValidator'
]
