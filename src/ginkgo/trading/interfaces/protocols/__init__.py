# Upstream: interfaces.__init__, 全系统组件类型检查
# Downstream: protocols.strategy, protocols.risk_management, protocols.portfolio, protocols.engine
# Role: Protocol接口协议模块包入口，导出IStrategy/IRiskManagement/IPortfolio/IEngine四大运行时可检查协议






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
