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
    tick_crud = container.create_tick_crud('000001.SZ')  # TickCRUD needs stock code
    
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
from .sources import GinkgoTushare, GinkgoTDX
from .utils import get_crud, get_available_crud_names  # get_crud is used to instantiate CRUD classes
from .services.adjustfactor_service import AdjustfactorService
from .services.stockinfo_service import StockinfoService
from .services.bar_service import BarService
from .services.tick_service import TickService
from .services.file_service import FileService
from .services.engine_service import EngineService
from .services.portfolio_service import PortfolioService
from .services.component_service import ComponentService
from .services.redis_service import RedisService
from .services.kafka_service import KafkaService


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
        BarService, crud_repo=bar_crud, data_source=ginkgo_tushare_source, stockinfo_service=stockinfo_service
    )

    # TickService requires special handling because TickCRUD needs a code parameter
    # TickService implements get_crud method to dynamically create TickCRUD instances
    tick_service = providers.Singleton(TickService, data_source=ginkgo_tdx_source, stockinfo_service=stockinfo_service)

    file_service = providers.Singleton(FileService, crud_repo=file_crud)

    engine_service = providers.Singleton(
        EngineService, crud_repo=engine_crud, engine_portfolio_mapping_crud=engine_portfolio_mapping_crud
    )

    portfolio_service = providers.Singleton(
        PortfolioService,
        crud_repo=portfolio_crud,
        portfolio_file_mapping_crud=portfolio_file_mapping_crud,
        param_crud=param_crud,
    )

    component_service = providers.Singleton(
        ComponentService, file_service=file_service, portfolio_service=portfolio_service
    )

    redis_service = providers.Singleton(RedisService, redis_crud=redis_crud)

    kafka_service = providers.Singleton(KafkaService, kafka_crud=kafka_crud)


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
    from .crud.tick_crud import TickCRUD

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
