# Upstream: 全系统（组件实现验证、类型检查、依赖注入）
# Downstream: interfaces.protocols.PortfolioInfo
# Role: 交易框架接口模块包入口，导出PortfolioInfo Protocol与Mixin组件契约




"""
Trading Framework Interfaces

This module provides interface definitions for the Ginkgo trading framework.
It includes Protocol interfaces for type safety and Mixin classes for
functional enhancement.
"""

from .protocols import PortfolioInfo

__all__ = [
    "PortfolioInfo"
]
