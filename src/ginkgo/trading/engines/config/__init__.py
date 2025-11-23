"""
回测引擎配置管理模块

提供统一的配置管理接口，支持不同引擎的配置参数管理。
"""

from ginkgo.trading.engines.config.backtest_config import BacktestConfig

__all__ = [
    'BacktestConfig'
]