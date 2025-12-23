"""
Services Package - Flat Architecture

This package contains high-level services that orchestrate business logic.
Each service is responsible for a specific domain and directly inherits from BaseService.

Architecture:
    BaseService (Only base class)
    ├── All Services (Directly inherit from BaseService)
    └── Legacy Aliases (Backward compatibility)
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
from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.services.factor_service import FactorService
from ginkgo.data.services.result_service import ResultService
from ginkgo.data.services.signal_tracking_service import SignalTrackingService

# Legacy aliases (Backward compatibility)
DataService = BaseService
ManagementService = BaseService
BusinessService = BaseService