# Upstream: 全系统（组件实现验证、类型检查、依赖注入）
# Downstream: interfaces.protocols.IStrategy, interfaces.protocols.IRiskManagement, interfaces.protocols.IPortfolio, interfaces.protocols.IEngine
# Role: 交易框架接口模块包入口，导出IStrategy/IRiskManagement/IPortfolio/IEngine四大Protocol接口协议






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
