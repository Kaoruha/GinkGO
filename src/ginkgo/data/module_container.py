"""
Data Module Container

Modular DI container for the Ginkgo data module.
This container provides all data-related services including:
- Data sources (Tushare, TDX, AKShare, etc.)
- CRUD repositories for database operations
- Data services for business logic
- Caching and message queue services
"""

from typing import Dict, Any, List

from ginkgo.libs.containers import BaseContainer
from ginkgo.data.sources import GinkgoTushare, GinkgoTDX
from ginkgo.data.utils import get_crud, get_available_crud_names
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


class DataContainer(BaseContainer):
    """
    Container for all data module services.
    
    This container provides:
    - Data sources (Tushare, TDX, etc.)
    - CRUD repositories for all data models
    - Data services with business logic
    - Caching and messaging services
    
    Services provided:
    - Data Sources: ginkgo_tushare_source, ginkgo_tdx_source
    - CRUDs: All available CRUD repositories
    - Services: stockinfo_service, bar_service, tick_service, etc.
    - Infrastructure: redis_service, kafka_service
    """
    
    module_name = "data"
    
    def configure(self) -> None:
        """Configure the data module container with all services."""
        
        # === Data Sources ===
        self.bind("ginkgo_tushare_source", GinkgoTushare)
        self.bind("ginkgo_tdx_source", GinkgoTDX)
        
        # === CRUD Repositories ===
        # Auto-register all available CRUDs
        self._bind_crud_repositories()
        
        # === Data Services ===
        # Note: Order matters for dependencies
        
        # StockinfoService (foundation service)
        self.bind(
            "stockinfo_service", 
            StockinfoService,
            dependencies=["stockinfo_crud", "ginkgo_tushare_source"]
        )
        
        # AdjustfactorService (depends on stockinfo_service)
        self.bind(
            "adjustfactor_service",
            AdjustfactorService,
            dependencies=["adjustfactor_crud", "ginkgo_tushare_source", "stockinfo_service"]
        )
        
        # BarService
        self.bind(
            "bar_service",
            BarService,
            dependencies=["bar_crud", "ginkgo_tushare_source", "stockinfo_service"]
        )
        
        # TickService
        self.bind(
            "tick_service",
            TickService,
            dependencies=["tick_crud_factory", "ginkgo_tdx_source", "stockinfo_service"]
        )
        
        # FileService
        self.bind(
            "file_service",
            FileService,
            dependencies=["file_crud"]
        )
        
        # EngineService
        self.bind(
            "engine_service",
            EngineService,
            dependencies=["engine_crud", "engine_portfolio_mapping_crud"]
        )
        
        # PortfolioService
        self.bind(
            "portfolio_service",
            PortfolioService,
            dependencies=["portfolio_crud", "portfolio_file_mapping_crud", "param_crud"]
        )
        
        # ComponentService
        self.bind(
            "component_service",
            ComponentService,
            dependencies=["file_service", "portfolio_service"]
        )
        
        # RedisService
        self.bind(
            "redis_service",
            RedisService,
            dependencies=["redis_crud"]
        )
        
        # KafkaService
        self.bind(
            "kafka_service",
            KafkaService,
            dependencies=["kafka_crud"]  
        )
        
        # === Special Factory Methods ===
        self.bind(
            "tick_crud_factory",
            self._create_tick_crud_factory,
            factory_method=self._create_tick_crud_factory
        )
    
    def _bind_crud_repositories(self) -> None:
        """Bind all available CRUD repositories."""
        for crud_name in get_available_crud_names():
            # Skip 'tick' and 'base' as they need special handling
            if crud_name in ['tick', 'base']:
                continue
            
            # Bind CRUD with factory method
            self.bind(
                f"{crud_name}_crud",
                self._create_crud_factory(crud_name),
                factory_method=self._create_crud_factory(crud_name)
            )
        
        # Special handling for tick CRUD
        self.bind(
            "tick_crud",
            self._create_tick_crud,
            factory_method=self._create_tick_crud,
            singleton=False  # Tick CRUD is not singleton as it needs code parameter
        )
    
    def _create_crud_factory(self, crud_name: str):
        """Create a factory function for CRUD creation."""
        def factory():
            return get_crud(crud_name)
        return factory
    
    def _create_tick_crud(self, code: str = None):
        """Factory method for creating TickCRUD instances."""
        if not code:
            raise ValueError("TickCRUD requires a stock code parameter")
        
        from ginkgo.data.crud.tick_crud import TickCRUD
        return TickCRUD(code)
    
    def _create_tick_crud_factory(self):
        """Factory method for tick CRUD factory."""
        return self._create_tick_crud
    
    def create_tick_crud(self, code: str):
        """
        Public method to create TickCRUD instances.
        
        This maintains backward compatibility with the existing container interface.
        
        Args:
            code: Stock code (e.g., '000001.SZ')
            
        Returns:
            TickCRUD instance for the specified stock code
        """
        return self._create_tick_crud(code)
    
    def get_cruds_aggregate(self) -> Dict[str, Any]:
        """
        Get an aggregate of all CRUD repositories.
        
        This maintains backward compatibility with the existing container's
        'cruds' FactoryAggregate.
        
        Returns:
            Dictionary mapping CRUD names to their instances
        """
        cruds = {}
        for crud_name in get_available_crud_names():
            if crud_name in ['tick', 'base']:
                continue
            crud_service_name = f"{crud_name}_crud"
            if self.has(crud_service_name):
                cruds[crud_name] = self.get(crud_service_name)
        
        return cruds
    
    def list_data_sources(self) -> List[str]:
        """Get list of available data sources."""
        sources = []
        for service_name in self.list_services():
            if service_name.endswith('_source'):
                sources.append(service_name)
        return sources
    
    def list_crud_repositories(self) -> List[str]:
        """Get list of available CRUD repositories."""
        cruds = []
        for service_name in self.list_services():
            if service_name.endswith('_crud'):
                cruds.append(service_name)
        return cruds
    
    def list_data_services(self) -> List[str]:
        """Get list of available data services."""
        services = []
        for service_name in self.list_services():
            if service_name.endswith('_service'):
                services.append(service_name)
        return services
    
    def get_service_info(self) -> Dict[str, Any]:
        """
        Get detailed information about all services in this container.
        
        Returns:
            Dictionary with service categories and counts
        """
        return {
            "module_name": self.module_name,
            "total_services": len(self.list_services()),
            "data_sources": len(self.list_data_sources()),
            "crud_repositories": len(self.list_crud_repositories()),
            "data_services": len(self.list_data_services()),
            "container_state": self.state.value,
            "is_ready": self.is_ready
        }


# Create the module container instance
data_container = DataContainer()