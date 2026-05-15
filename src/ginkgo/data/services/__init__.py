# Upstream: 依赖注入容器(services), 回测引擎, API层, Worker
# Downstream: BaseService, 各CRUD类(BarCRUD, OrderCRUD等)
# Role: 服务包入口，统一导出全部数据服务(BarService, EngineService, PortfolioService等)和ServiceResult

"""
Services Package - Flat Architecture

This package contains high-level services that orchestrate business logic.
Each service is responsible for a specific domain and directly inherits from BaseService.

Architecture:
    BaseService (Only base class)
    ├── All Services (Directly inherit from BaseService)
    └── Legacy Aliases (Backward compatibility)
"""

# Core classes — kept as direct imports (lightweight base classes used everywhere)
from ginkgo.data.services.base_service import BaseService, ServiceResult

# See #2715: PEP 562 懒加载
_LAZY_IMPORTS = {
    "AdjustfactorService": ("ginkgo.data.services.adjustfactor_service", "AdjustfactorService"),
    "BacktestTaskService": ("ginkgo.data.services.backtest_task_service", "BacktestTaskService"),
    "StockinfoService": ("ginkgo.data.services.stockinfo_service", "StockinfoService"),
    "BarService": ("ginkgo.data.services.bar_service", "BarService"),
    "TickService": ("ginkgo.data.services.tick_service", "TickService"),
    "FileService": ("ginkgo.data.services.file_service", "FileService"),
    "EngineService": ("ginkgo.data.services.engine_service", "EngineService"),
    "PortfolioMappingService": ("ginkgo.data.services.portfolio_mapping_service", "PortfolioMappingService"),
    "PortfolioService": ("ginkgo.data.services.portfolio_service", "PortfolioService"),
    "RedisService": ("ginkgo.data.services.redis_service", "RedisService"),
    "KafkaService": ("ginkgo.data.services.kafka_service", "KafkaService"),
    "FactorService": ("ginkgo.data.services.factor_service", "FactorService"),
    "ResultService": ("ginkgo.data.services.result_service", "ResultService"),
    "SignalTrackingService": ("ginkgo.data.services.signal_tracking_service", "SignalTrackingService"),
    "OrderService": ("ginkgo.data.services.order_service", "OrderService"),
    # See #22: CredentialService removed — dead code, zero callers
    "UserService": ("ginkgo.data.services.user_service", "UserService"),
    "UserGroupService": ("ginkgo.data.services.user_group_service", "UserGroupService"),
    "NotificationService": ("ginkgo.data.services.notification_service", "NotificationService"),
}


def __getattr__(name):
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        return getattr(module, attr_name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return sorted(_LAZY_IMPORTS.keys() | set(globals().keys()))


# Legacy aliases (Backward compatibility)
DataService = BaseService
ManagementService = BaseService
BusinessService = BaseService
