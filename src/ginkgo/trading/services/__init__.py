# Upstream: API Server, CLI commands, WebUI backtest actions
# Downstream: EngineAssemblyService, ComponentFactoryService, PortfolioManagementService
# Role: 交易服务模块包，导出引擎装配、组件工厂和组合管理等业务服务






"""
Backtest Services Module

This module contains business services for the backtest functionality,
providing high-level APIs for engine assembly, component management,
and backtest execution.

Available Services:
- EngineAssemblyService: Assembles and configures backtest engines
- ComponentFactoryService: Creates trading system components dynamically
- PortfolioManagementService: Manages portfolio lifecycle and configuration
"""

from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
from ginkgo.trading.services.component_factory_service import ComponentFactoryService  
from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService

__all__ = [
    'EngineAssemblyService',
    'ComponentFactoryService', 
    'PortfolioManagementService'
]
