# Upstream: BaseEngine, TimeControlledEventEngine, CLI回测命令
# Downstream: engines.config.backtest_config
# Role: 引擎配置模块包入口，导出BacktestConfig回测配置数据类，统一管理回测参数






"""
回测引擎配置管理模块

提供统一的配置管理接口，支持不同引擎的配置参数管理。
"""

from ginkgo.trading.engines.config.backtest_config import BacktestConfig

__all__ = [
    'BacktestConfig'
]
