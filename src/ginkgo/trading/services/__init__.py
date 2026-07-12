# Upstream: API Server, CLI commands, WebUI backtest actions
# Downstream: EngineAssemblyService, PortfolioManagementService
# Role: 交易服务模块包，导出引擎装配和组合管理等业务服务

# 注: ComponentFactoryService(组件工厂)已于 #6476 删除 —— 业务代码零实例化零调用,
# 组件创建的单一接缝是 ComponentLoader.perform_component_binding(ADR-022 原则 3)。

"""
Backtest Services Module

This module contains business services for the backtest functionality,
providing high-level APIs for engine assembly, component management,
and backtest execution.

Available Services:
- EngineAssemblyService: Assembles and configures backtest engines
- PortfolioManagementService: Manages portfolio lifecycle and configuration
"""

from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService

__all__ = [
    'EngineAssemblyService',
    'PortfolioManagementService'
]
