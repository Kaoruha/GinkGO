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

from .engine_assembly_service import EngineAssemblyService
from .component_factory_service import ComponentFactoryService  
from .portfolio_management_service import PortfolioManagementService

__all__ = [
    'EngineAssemblyService',
    'ComponentFactoryService', 
    'PortfolioManagementService'
]