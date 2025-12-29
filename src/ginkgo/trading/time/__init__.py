# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 时间管理模块公共接口，导出Clock时钟、TimeProvider时间提供者、Timestamp时间戳等时间管理组件，提供统一的时间抽象






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
