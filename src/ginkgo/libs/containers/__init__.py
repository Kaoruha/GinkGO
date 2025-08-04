"""
Ginkgo Modular DI Container Framework

This module provides a distributed dependency injection container architecture
that allows each module to have its own container while maintaining 
cross-module dependency resolution and coordination.

Key Components:
- BaseContainer: Abstract base class for all module containers
- ContainerRegistry: Global registry for container discovery and coordination
- CrossContainerProxy: Proxy for cross-container service access
- ApplicationContainer: Top-level container managing all module containers

Usage Example:

    # Define a module container
    class DataContainer(BaseContainer):
        module_name = "data"
        
        def configure(self):
            self.bind("stockinfo_service", StockinfoService)
            self.bind("bar_service", BarService)
    
    # Register and use
    registry = ContainerRegistry()
    data_container = DataContainer()
    registry.register(data_container)
    
    # Access services
    stockinfo_service = registry.get_service("data", "stockinfo_service")
    
    # Cross-module access
    backtest_service = registry.get_service("backtest", "strategy_runner")
"""

from .base_container import BaseContainer
from .container_registry import ContainerRegistry
from .cross_container_proxy import CrossContainerProxy
from .application_container import ApplicationContainer
from .exceptions import (
    ContainerError,
    ServiceNotFoundError,
    CircularDependencyError,
    ContainerNotRegisteredError
)

__all__ = [
    'BaseContainer',
    'ContainerRegistry', 
    'CrossContainerProxy',
    'ApplicationContainer',
    'ContainerError',
    'ServiceNotFoundError',
    'CircularDependencyError',
    'ContainerNotRegisteredError'
]