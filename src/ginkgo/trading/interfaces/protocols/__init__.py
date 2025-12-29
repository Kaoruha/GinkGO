# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 接口协议模块导出引擎协议/组合协议/策略协议/风控协议等标准接口支持交易系统功能和组件集成提供完整业务支持






"""
Trading Framework Protocol Interfaces

This module provides Protocol interfaces for the Ginkgo trading framework components.
These interfaces define contracts that ensure type safety and consistent behavior
across different implementations of strategies, risk management systems,
portfolios, and backtest engines.
"""

from .strategy import IStrategy
from .risk_management import IRiskManagement
from .portfolio import IPortfolio
from .engine import IEngine

__all__ = [
    "IStrategy",
    "IRiskManagement",
    "IPortfolio",
    "IEngine"
]