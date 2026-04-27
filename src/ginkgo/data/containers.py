# Upstream: 全项目(from ginkgo.data import container), 回测引擎, Worker系统, CLI, API服务
# Downstream: 全部CRUD类, 全部Service类, 数据驱动(GinkgoMongo/GinkgoTushare等), dependency_injector
# Role: 数据层依赖注入容器，基于dependency_injector统一管理CRUD/Service/数据源的实例化和生命周期

from __future__ import annotations  # 启用延迟注解评估，避免循环导入






"""
Dependency Injection Container

This module initializes and holds instances of services, repositories (CRUDs),
and data sources, managing their dependencies in a central location.

Usage Examples:

    # Access CRUDs through the auto-discovered aggregate:
    from ginkgo.data.containers import container

    bar_crud = container.cruds.bar()
    signal_crud = container.cruds.signal()
    order_record_crud = container.cruds.order_record()

    # Most CRUDs are automatically available through container.cruds

    # Special cases that need parameters:
    # tick_crud will be defined inside Container

    # Access services:
    kafka_service = container.kafka_service()
    redis_service = container.redis_service()

    # For dependency injection:
    from dependency_injector.wiring import inject, Provide

    @inject
    def your_function(bar_crud = Provide[Container.cruds.bar]):
        # Use bar_crud here
        pass

    # Backward compatibility - explicit providers still work:
    engine_crud = container.engine_crud()
    portfolio_crud = container.portfolio_crud()
"""

from dependency_injector import containers, providers
from typing import TYPE_CHECKING

# Import your services, CRUDs, and data sources
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.utils import get_crud, get_available_crud_names  # get_crud is used to instantiate CRUD classes
from ginkgo.data.drivers.ginkgo_mongo import GinkgoMongo
from ginkgo.libs import GCONF
from ginkgo.data.services.adjustfactor_service import AdjustfactorService
from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.bar_service import BarService
from ginkgo.data.services.tick_service import TickService
from ginkgo.data.crud.tick_crud import TickCRUD
from ginkgo.data.services.file_service import FileService
from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.portfolio_mapping_service import PortfolioMappingService
from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.services.signal_tracking_service import SignalTrackingService
from ginkgo.data.services.factor_service import FactorService
from ginkgo.data.services.result_service import ResultService
from ginkgo.data.services.analyzer_service import AnalyzerService
from ginkgo.data.services.param_service import ParamService
from ginkgo.data.services.mapping_service import MappingService
from ginkgo.data.services.encryption_service import EncryptionService, get_encryption_service
from ginkgo.data.services.live_account_service import LiveAccountService
from ginkgo.data.services.api_key_service import ApiKeyService
from ginkgo.data.services.validation_service import ValidationService

# Live trading CRUDs
from ginkgo.data.crud.broker_instance_crud import BrokerInstanceCRUD
from ginkgo.data.crud.live_account_crud import LiveAccountCRUD
from ginkgo.data.crud.market_subscription_crud import MarketSubscriptionCRUD
from ginkgo.data.crud.deployment_crud import DeploymentCRUD
from ginkgo.data.crud.validation_result_crud import ValidationResultCRUD

# User management services
from ginkgo.user.services.user_service import UserService
from ginkgo.user.services.user_group_service import UserGroupService
from ginkgo.notifier.services.notification_recipient_service import NotificationRecipientService
from ginkgo.data.services.backtest_task_service import BacktestTaskService


class Container(containers.DeclarativeContainer):
    # Data Sources
    ginkgo_tushare_source = providers.Singleton(GinkgoTushare)
    ginkgo_tdx_source = providers.Singleton(GinkgoTDX)

    # MongoDB Driver - Lazy singleton initialized on first access
    mongo_driver = providers.Singleton(
        GinkgoMongo,
        user=GCONF.MONGOUSER,
        pwd=GCONF.MONGOPWD,
        host=GCONF.MONGOHOST,
        port=GCONF.MONGOPORT,
        db=GCONF.MONGODB,
    )

    # CRUD Repositories - Auto-discovered from crud module
    # Generate provider configurations for all available CRUDs
    _crud_configs = {}
    for crud_name in get_available_crud_names():
        # Skip 'tick' and 'base' as they need special handling
        if crud_name in ["tick", "base"]:
            continue
        _crud_configs[crud_name] = providers.Singleton(get_crud, crud_name)

    # Create FactoryAggregate for unified CRUD access
    cruds = providers.FactoryAggregate(**_crud_configs)

    # Special handling for TickCRUD - it requires a code parameter
    # Users should create tick CRUD instances through a factory method

    # Backward compatibility - keep existing explicit providers
    adjustfactor_crud = providers.Singleton(get_crud, "adjustfactor")
    stockinfo_crud = providers.Singleton(get_crud, "stock_info")
    bar_crud = providers.Singleton(get_crud, "bar")
    engine_crud = providers.Singleton(get_crud, "engine")
    file_crud = providers.Singleton(get_crud, "file")
    portfolio_crud = providers.Singleton(get_crud, "portfolio")
    engine_portfolio_mapping_crud = providers.Singleton(get_crud, "engine_portfolio_mapping")
    portfolio_file_mapping_crud = providers.Singleton(get_crud, "portfolio_file_mapping")
    param_crud = providers.Singleton(get_crud, "param")
    engine_handler_mapping_crud = providers.Singleton(get_crud, "engine_handler_mapping")
    redis_crud = providers.Singleton(get_crud, "redis")
    kafka_crud = providers.Singleton(get_crud, "kafka")
    factor_crud = providers.Singleton(get_crud, "factor")
    analyzer_record_crud = providers.Singleton(get_crud, "analyzer_record")
    backtest_task_crud = providers.Singleton(get_crud, "backtest_task")

    # User management CRUDs
    user_crud = providers.Singleton(get_crud, "user")
    user_contact_crud = providers.Singleton(get_crud, "user_contact")
    user_credential_crud = providers.Singleton(get_crud, "user_credential")
    user_group_crud = providers.Singleton(get_crud, "user_group")
    user_group_mapping_crud = providers.Singleton(get_crud, "user_group_mapping")

    # Notification system CRUDs
    notification_template_crud = providers.Singleton(get_crud, "notification_template")
    notification_record_crud = providers.Singleton(get_crud, "notification_record")
    notification_recipient_crud = providers.Singleton(get_crud, "notification_recipient")

    # Live trading CRUDs
    live_account_crud = providers.Singleton(get_crud, "live_account")
    broker_instance_crud = providers.Singleton(get_crud, "broker_instance")
    trade_record_crud = providers.Singleton(get_crud, "trade_record")
    market_subscription_crud = providers.Singleton(get_crud, "market_subscription")
    api_key_crud = providers.Singleton(get_crud, "api_key")
    deployment_crud = providers.Singleton(get_crud, "deployment")

    # Backtest task CRUD
    backtest_task_crud = providers.Singleton(get_crud, "backtest_task")

    # Services (Dependencies are injected here)
    # StockinfoService must be defined before AdjustfactorService as it's a dependency
    stockinfo_service = providers.Singleton(
        StockinfoService, crud_repo=stockinfo_crud, data_source=ginkgo_tushare_source
    )

    adjustfactor_service = providers.Singleton(
        AdjustfactorService,
        crud_repo=adjustfactor_crud,
        data_source=ginkgo_tushare_source,
        stockinfo_service=stockinfo_service,  # Inject stockinfo_service here
    )

    bar_service = providers.Singleton(
        BarService,
        crud_repo=bar_crud,
        data_source=ginkgo_tushare_source,
        stockinfo_service=stockinfo_service,
        adjustfactor_service=adjustfactor_service,  # 添加缺失的adjustfactor_service依赖
    )

    # TickService with TickCRUD instance
    tick_service = providers.Singleton(
        TickService, data_source=ginkgo_tdx_source, stockinfo_service=stockinfo_service, crud_repo=TickCRUD()
    )

    file_service = providers.Singleton(FileService, crud_repo=file_crud)

    engine_service = providers.Singleton(
        EngineService,
        crud_repo=engine_crud,
        engine_portfolio_mapping_crud=engine_portfolio_mapping_crud,
        param_crud=param_crud,
    )

    portfolio_service = providers.Singleton(
        PortfolioService,
        crud_repo=portfolio_crud,
        portfolio_file_mapping_crud=portfolio_file_mapping_crud,
        deployment_crud=deployment_crud,
    )

    # Portfolio Mapping Service - MongoDB 图结构与 MySQL Mapping+Param 双向同步
    portfolio_mapping_service = providers.Singleton(
        PortfolioMappingService,
        mapping_crud=portfolio_file_mapping_crud,
        param_crud=param_crud,
        mongo_driver=mongo_driver,
        file_crud=file_crud,
    )

    # Mapping Service for managing all mapping relationships
    mapping_service = providers.Singleton(
        MappingService,
        engine_portfolio_mapping_crud=engine_portfolio_mapping_crud,
        portfolio_file_mapping_crud=portfolio_file_mapping_crud,
        engine_handler_mapping_crud=engine_handler_mapping_crud,
        param_crud=param_crud,
    )

    redis_service = providers.Singleton(RedisService, redis_crud=redis_crud)

    kafka_service = providers.Singleton(KafkaService, kafka_crud=kafka_crud)

    # Signal tracking service with SignalTrackerCRUD dependency
    signal_tracking_service = providers.Singleton(
        SignalTrackingService, tracker_crud=providers.Singleton(get_crud, "signal_tracker")
    )

    # Factor service with FactorCRUD dependency
    factor_service = providers.Singleton(FactorService, factor_crud=factor_crud)

    # Param service with ParamCRUD dependency
    param_service = providers.Singleton(ParamService)

    # Result service with AnalyzerRecordCRUD dependency
    result_service = providers.Singleton(ResultService, analyzer_crud=analyzer_record_crud)

    # Analyzer service with AnalyzerRecordCRUD dependency
    analyzer_service = providers.Singleton(AnalyzerService, analyzer_crud=analyzer_record_crud)

    # Backtest task service
    backtest_task_service = providers.Singleton(
        BacktestTaskService,
        crud_repo=backtest_task_crud,
        analyzer_service=analyzer_service,
        engine_service=providers.Singleton(get_crud, "engine"),
        portfolio_service=portfolio_service,
    )

    # User management services
    user_service = providers.Singleton(
        UserService,
        user_crud=user_crud,
        user_contact_crud=user_contact_crud
    )

    user_group_service = providers.Singleton(
        UserGroupService,
        user_group_crud=user_group_crud,
        user_group_mapping_crud=user_group_mapping_crud
    )

    # Notification management services
    # NotificationRecipientService manages global notification recipients (MySQL)
    notification_recipient_service = providers.Singleton(
        lambda: NotificationRecipientService(
            recipient_crud=get_crud("notification_recipient"),
            user_contact_crud=get_crud("user_contact"),
            user_group_mapping_crud=get_crud("user_group_mapping")
        )
    )

    # Encryption service for API credentials
    encryption_service = providers.Singleton(get_encryption_service)

    # Live account service for live trading
    live_account_service = providers.Singleton(
        LiveAccountService,
        live_account_crud=providers.Singleton(get_crud, "live_account")
    )

    # API Key service for API key management
    api_key_service = providers.Singleton(
        ApiKeyService
    )

    # Validation result CRUD
    validation_result_crud = providers.Singleton(ValidationResultCRUD)

    # Validation service for backtest validation (segment stability, monte carlo)
    validation_service = providers.Singleton(
        ValidationService,
        analyzer_record_crud=providers.Singleton(get_crud, "analyzer_record"),
        validation_result_crud=validation_result_crud,
    )

    # Backtest task service
    backtest_task_service = providers.Singleton(
        BacktestTaskService,
        crud_repo=backtest_task_crud
    )

    # Mapping service with all mapping CRUD dependencies
    mapping_service = providers.Singleton(
        MappingService,
        engine_portfolio_mapping_crud=engine_portfolio_mapping_crud,
        portfolio_file_mapping_crud=portfolio_file_mapping_crud,
        engine_handler_mapping_crud=engine_handler_mapping_crud,
        param_crud=param_crud,
    )

    # Deployment service for one-click deploy (placeholder, set after Container instantiation)
    deployment_service = providers.Singleton(object)


# A singleton instance of the container, accessible throughout the application
container = Container()

# Lazy-init deployment service to avoid circular import (trading.services → containers)
_deployment_service_instance = None


def _get_deployment_service():
    """Lazy factory for DeploymentService to break circular import."""
    global _deployment_service_instance
    if _deployment_service_instance is None:
        from ginkgo.trading.services.deployment_service import DeploymentService
        _deployment_service_instance = DeploymentService(
            portfolio_service=container.portfolio_service(),
            mapping_service=container.portfolio_mapping_service(),
            file_service=container.file_service(),
            deployment_crud=container.deployment_crud(),
            broker_instance_crud=container.broker_instance_crud(),
            live_account_service=container.live_account_service(),
            mongo_driver=container.mongo_driver(),
        )
    return _deployment_service_instance


# Override the placeholder with the lazy factory
container.deployment_service.override(providers.Singleton(_get_deployment_service))


# Add special methods to the container instance for special cases
def create_tick_crud(code: str):
    """
    Factory method to create TickCRUD instances with specific stock codes.

    Args:
        code: Stock code (e.g., '000001.SZ')

    Returns:
        TickCRUD: A TickCRUD instance for the specified stock code

    Example:
        tick_crud = container.create_tick_crud('000001.SZ')
    """
    from ginkgo.data.crud.tick_crud import TickCRUD

    return TickCRUD(code)


# Add service discovery interface for consistency with other modules
def get_service_info():
    """Get service information (backward compatibility and standardization)"""
    available_cruds = get_available_crud_names()

    # Get available services by inspecting the container
    services_list = []
    for attr_name in dir(container):
        if attr_name.endswith("_service") and not attr_name.startswith("_"):
            service_name = attr_name[:-8]  # Remove '_service' suffix
            services_list.append(service_name)

    # Get data sources
    data_sources = ["tushare", "tdx"]

    return {
        "cruds": available_cruds,
        "services": services_list,
        "data_sources": data_sources,
        "special_methods": ["create_tick_crud"],
    }


# Bind the factory method and service info to the container instance
container.create_tick_crud = create_tick_crud
container.get_service_info = get_service_info

