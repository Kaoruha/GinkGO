# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 接口模块导出经纪商/组合/策略/风控等接口协议定义组件的标准契约支持交易系统功能和组件集成提供完整业务支持






"""
Trading Framework Interfaces

This module provides interface definitions for the Ginkgo trading framework.
It includes Protocol interfaces for type safety and Mixin classes for
functional enhancement.
"""

from .protocols import (
    IStrategy,
    IRiskManagement,
    IPortfolio,
    IEngine
)

__all__ = [
    "IStrategy",
    "IRiskManagement",
    "IPortfolio",
    "IEngine"
]