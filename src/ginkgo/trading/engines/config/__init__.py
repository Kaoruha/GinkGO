# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Config配置模块提供回测引擎配置定义和管理支持配置加载/验证和保存功能确保配置正确性支持交易系统功能和组件集成提供完整业务支持






"""
回测引擎配置管理模块

提供统一的配置管理接口，支持不同引擎的配置参数管理。
"""

from ginkgo.trading.engines.config.backtest_config import BacktestConfig

__all__ = [
    'BacktestConfig'
]