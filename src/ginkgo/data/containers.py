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

# Import your services, CRUDs, and data sources
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.utils import get_crud, get_available_crud_names  # get_crud is used to instantiate CRUD classes
from ginkgo.data.services.adjustfactor_service import AdjustfactorService
from ginkgo.data.services.stockinfo_service import StockinfoService
from ginkgo.data.services.bar_service import BarService
from ginkgo.data.services.tick_service import TickService
from ginkgo.data.crud.tick_crud import TickCRUD
from ginkgo.data.services.file_service import FileService
from ginkgo.data.services.engine_service import EngineService
from ginkgo.data.services.portfolio_service import PortfolioService
from ginkgo.data.services.redis_service import RedisService
from ginkgo.data.services.kafka_service import KafkaService
from ginkgo.data.services.signal_tracking_service import SignalTrackingService
from ginkgo.data.services.factor_service import FactorService
from ginkgo.data.services.param_service import ParamService


class Container(containers.DeclarativeContainer):
    # Data Sources
    ginkgo_tushare_source = providers.Singleton(GinkgoTushare)
    ginkgo_tdx_source = providers.Singleton(GinkgoTDX)

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
    redis_crud = providers.Singleton(get_crud, "redis")
    kafka_crud = providers.Singleton(get_crud, "kafka")
    factor_crud = providers.Singleton(get_crud, "factor")

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
        adjustfactor_service=adjustfactor_service  # 添加缺失的adjustfactor_service依赖
    )

    # TickService requires special handling because TickCRUD needs a code parameter
    # Pass TickCRUD class directly, service will use it as factory: self._crud_repo(code).function()
    tick_service = providers.Singleton(
        TickService,
        data_source=ginkgo_tdx_source,
        stockinfo_service=stockinfo_service,
        crud_repo=TickCRUD
    )

    file_service = providers.Singleton(FileService, crud_repo=file_crud)

    engine_service = providers.Singleton(
        EngineService, crud_repo=engine_crud, engine_portfolio_mapping_crud=engine_portfolio_mapping_crud, param_crud=param_crud
    )

    portfolio_service = providers.Singleton(
        PortfolioService,
        crud_repo=portfolio_crud,
        portfolio_file_mapping_crud=portfolio_file_mapping_crud,
    )

    
    redis_service = providers.Singleton(RedisService, redis_crud=redis_crud)

    kafka_service = providers.Singleton(KafkaService, kafka_crud=kafka_crud)
    
    # Signal tracking service with SignalTrackerCRUD dependency
    signal_tracking_service = providers.Singleton(
        SignalTrackingService, 
        tracker_crud=providers.Singleton(get_crud, "signal_tracker")
    )
    
    # Factor service with FactorCRUD dependency
    factor_service = providers.Singleton(
        FactorService,
        factor_crud=factor_crud
    )

    # Param service with ParamCRUD dependency
    param_service = providers.Singleton(
        ParamService
    )


# A singleton instance of the container, accessible throughout the application
container = Container()


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
