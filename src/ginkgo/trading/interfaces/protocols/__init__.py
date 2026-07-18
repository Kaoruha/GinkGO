# Upstream: interfaces.__init__, 全系统组件类型检查
# Downstream: protocols.portfolio_info
# Role: Protocol接口协议模块包入口，导出PortfolioInfo运行时可检查协议




"""
Trading Framework Protocol Interfaces

This module provides Protocol interfaces for the Ginkgo trading framework components.
These interfaces define contracts that ensure type safety and consistent behavior
across different implementations.
"""

from .portfolio_info import PortfolioInfo

__all__ = [
    "PortfolioInfo"
]
