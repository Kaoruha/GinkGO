"""
Services Package

This package contains high-level services that orchestrate business logic.
Each service is responsible for a specific domain (e.g., adjustfactors, stockinfo, bars, ticks, files, engines, portfolios, components).

Architecture:
    BaseService (Abstract base class)
    ├── DataService (Data synchronization services)
    ├── ManagementService (Entity management services)  
    └── BusinessService (Business logic services)
"""
# Base classes
from .base_service import BaseService, DataService, ManagementService, BusinessService, ServiceResult

# Concrete service implementations
from .adjustfactor_service import AdjustfactorService
from .stockinfo_service import StockinfoService
from .bar_service import BarService
from .tick_service import TickService
from .file_service import FileService
from .engine_service import EngineService
from .portfolio_service import PortfolioService
from .component_service import ComponentService
from .redis_service import RedisService
from .kafka_service import KafkaService