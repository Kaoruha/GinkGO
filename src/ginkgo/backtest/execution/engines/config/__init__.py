"""
回测引擎配置管理模块

提供统一的配置管理接口，支持不同引擎的配置参数管理。
"""

from .backtest_config import BacktestConfig
from .performance_config import PerformanceConfig

__all__ = [
    'BacktestConfig',
    'PerformanceConfig'
]