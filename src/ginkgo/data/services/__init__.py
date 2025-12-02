"""
Services Package - 扁平化架构

This package contains high-level services that orchestrate business logic.
Each service is responsible for a specific domain and directly inherits from BaseService.

Architecture:
    BaseService (唯一的基础类)
    ├── All Services (直接继承BaseService)
    └── Legacy Aliases (向后兼容)
"""

# Core classes
from ginkgo.data.services.base_service import BaseService, ServiceResult

# Concrete service implementations
from ginkgo.data.services.adjustfactor_service import AdjustfactorService
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.bar_service import BarService
from ginkgo.data.services.tick_service import TickService
from ginkgo.data.services.file_service import FileService
from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.component_service import ComponentService
from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.services.factor_service import FactorService

# Legacy aliases (向后兼容)
DataService = BaseService
ManagementService = BaseService
BusinessService = BaseService