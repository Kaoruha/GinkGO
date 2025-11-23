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
