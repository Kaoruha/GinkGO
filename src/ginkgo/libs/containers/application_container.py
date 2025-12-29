# Upstream: All Modules
# Downstream: Standard Library
# Role: Application Container容器提供ApplicationContainer应用依赖注入






"""
Application Container

Top-level container that coordinates all module containers in the Ginkgo framework.
This container serves as the main entry point for dependency injection and
provides a unified interface for managing the entire application's services.
"""

from typing import Dict, Any, Optional, List, Type
import threading
import time

from .base_container import BaseContainer
from .container_registry import ContainerRegistry, registry
from .cross_container_proxy import CrossContainerProxy, create_proxy
from .exceptions import (
    ContainerNotRegisteredError,
    ServiceNotFoundError,
    ContainerLifecycleError
)


class ApplicationContainer:
    """
    Application-level container that manages all module containers.
    
    This container provides:
    - Centralized service access across all modules
    - Application lifecycle management
    - Global service discovery and resolution
    - Unified configuration management
    - Health monitoring and diagnostics
    
    Features:
    - Thread-safe operations
    - Automatic container discovery
    - Service resolution with caching
    - Graceful startup and shutdown
    - Cross-module dependency coordination
    """
    
    def __init__(self, registry_instance: ContainerRegistry = None):
        """
        Initialize application container.
        
        Args:
            registry_instance: Container registry to use (defaults to global registry)
        """
        self._registry = registry_instance or registry
        self._lock = threading.RLock()
        self._initialized = False
        self._shutdown = False
        
        # Global services that need to be available to all modules
        self._global_services: Dict[str, Any] = {}
        
        # Application metadata
        self._startup_time = None
        self._initialization_order: List[str] = []
        
    @property
    def is_initialized(self) -> bool:
        """Check if application container is initialized."""
        return self._initialized
    
    @property
    def is_shutdown(self) -> bool:
        """Check if application container is shutdown."""
        return self._shutdown
    
    def register_module_container(self, container: BaseContainer) -> None:
        """
        Register a module container with the application.
        
        Args:
            container: Module container to register
        """
        if self._shutdown:
            raise ContainerLifecycleError(
                "application",
                "register_module_container",
                "Application is shutdown"
            )
        
        with self._lock:
            self._registry.register(container)
            print(f"Registered module container: {container.module_name}")
    
    def unregister_module_container(self, module_name: str) -> None:
        """
        Unregister a module container from the application.
        
        Args:
            module_name: Name of the module to unregister
        """
        with self._lock:
            self._registry.unregister(module_name)
            print(f"Unregistered module container: {module_name}")
    
    def get_service(
        self, 
        service_name: str, 
        module_name: str = None,
        create_proxy: bool = False
    ) -> Any:
        """
        Get a service from any registered container.
        
        Args:
            service_name: Name of the service to retrieve
            module_name: Optional specific module to search in
            create_proxy: Whether to return a proxy instead of direct instance
            
        Returns:
            Service instance or proxy
            
        Raises:
            ServiceNotFoundError: If service is not found
            ContainerNotRegisteredError: If specified module is not registered
        """
        if self._shutdown:
            raise ContainerLifecycleError(
                "application",
                "get_service",
                "Application is shutdown"
            )
        
        # Check global services first
        if service_name in self._global_services:
            return self._global_services[service_name]
        
        if module_name:
            # Get from specific module
            service = self._registry.get_service(module_name, service_name)
        else:
            # Search across all modules
            service = self._registry.find_service(service_name)
        
        if create_proxy:
            return CrossContainerProxy(
                service_name=service_name,
                registry=self._registry,
                preferred_container=module_name
            )
        
        return service
    
    def create_service_proxy(
        self, 
        service_name: str,
        preferred_container: str = None,
        service_type: Type = None
    ) -> CrossContainerProxy:
        """
        Create a cross-container proxy for a service.
        
        Args:
            service_name: Name of the service to proxy
            preferred_container: Preferred container to resolve from
            service_type: Expected service type for validation
            
        Returns:
            CrossContainerProxy instance
        """
        return create_proxy(
            service_name=service_name,
            registry=self._registry,
            preferred_container=preferred_container,
            service_type=service_type
        )
    
    def bind_global_service(self, name: str, instance: Any) -> None:
        """
        Bind a global service that's available to all modules.
        
        Args:
            name: Service name
            instance: Service instance
        """
        with self._lock:
            self._global_services[name] = instance
            print(f"Bound global service: {name}")
    
    def list_modules(self) -> List[str]:
        """Get list of all registered module names."""
        return self._registry.list_containers()
    
    def list_all_services(self) -> Dict[str, List[str]]:
        """Get all services from all modules."""
        result = self._registry.list_services()
        
        # Add global services
        if self._global_services:
            result["global"] = list(self._global_services.keys())
        
        return result
    
    def get_module_info(self, module_name: str) -> Dict[str, Any]:
        """
        Get detailed information about a module container.
        
        Args:
            module_name: Name of the module
            
        Returns:
            Dictionary with module information
        """
        return self._registry.get_container_dependencies(module_name)
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall application health status.
        
        Returns:
            Dictionary with health information
        """
        registry_status = self._registry.get_health_status()
        
        return {
            "application_initialized": self._initialized,
            "application_shutdown": self._shutdown,
            "startup_time": self._startup_time,
            "global_services": len(self._global_services),
            "registry_status": registry_status
        }
    
    def initialize(self) -> None:
        """
        Initialize the application container and all module containers.
        
        This method:
        1. Initializes all registered module containers
        2. Resolves cross-module dependencies
        3. Sets up global services
        4. Marks application as ready
        """
        if self._initialized:
            return
        
        if self._shutdown:
            raise ContainerLifecycleError(
                "application",
                "initialize",
                "Cannot initialize shutdown application"
            )
        
        try:
            with self._lock:
                print("Initializing application container...")
                start_time = time.time()
                
                # Initialize all module containers
                self._registry.initialize_all()
                
                # Verify all containers are healthy
                health = self._registry.get_health_status()
                if not health["overall_healthy"]:
                    raise ContainerLifecycleError(
                        "application",
                        "initialize",
                        "Some module containers failed to initialize"
                    )
                
                self._startup_time = time.time()
                self._initialized = True
                
                initialization_time = self._startup_time - start_time
                print(f"Application container initialized successfully in {initialization_time:.2f}s")
                
        except Exception as e:
            print(f"Failed to initialize application container: {e}")
            raise
    
    def shutdown(self) -> None:
        """
        Shutdown the application container and all module containers.
        
        This method:
        1. Marks application as shutting down
        2. Shuts down all module containers in reverse order
        3. Clears global services
        4. Marks application as shutdown
        """
        if self._shutdown:
            return
        
        try:
            with self._lock:
                print("Shutting down application container...")
                
                # Shutdown all module containers
                self._registry.shutdown_all()
                
                # Clear global services
                self._global_services.clear()
                
                self._shutdown = True
                self._initialized = False
                
                print("Application container shutdown completed")
                
        except Exception as e:
            print(f"Error during application shutdown: {e}")
            raise
    
    def restart(self) -> None:
        """
        Restart the application container.
        
        This performs a full shutdown followed by initialization.
        """
        print("Restarting application container...")
        self.shutdown()
        self.initialize()
        print("Application container restart completed")
    
    def get_service_dependencies(self, service_name: str) -> Dict[str, Any]:
        """
        Get dependency information for a specific service.
        
        Args:
            service_name: Name of the service
            
        Returns:
            Dictionary with dependency information
        """
        # Find which container provides this service
        for module_name in self.list_modules():
            try:
                container = self._registry.get_container(module_name)
                if container.has(service_name):
                    return {
                        "service_name": service_name,
                        "provider_module": module_name,
                        "container_info": self.get_module_info(module_name)
                    }
            except ContainerNotRegisteredError:
                continue
        
        raise ServiceNotFoundError(service_name)
    
    def __enter__(self):
        """Context manager entry."""
        self.initialize()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
    
    def __repr__(self) -> str:
        """String representation of the application container."""
        status = "initialized" if self._initialized else "not_initialized"
        if self._shutdown:
            status = "shutdown"
        
        module_count = len(self.list_modules())
        global_service_count = len(self._global_services)
        
        return (
            f"<ApplicationContainer(status={status}, "
            f"modules={module_count}, global_services={global_service_count})>"
        )


# Global application container instance
app_container = ApplicationContainer()