# Upstream: All Modules
# Downstream: Standard Library
# Role: Base Container容器提供BaseContainer基础依赖注入支持交易系统功能支持相关功能






"""
Base Container Abstract Class

Provides the foundation for all module containers in the Ginkgo framework.
Each module should inherit from this class to create their own container
with module-specific services and dependencies.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Type, Callable, Set, List
from enum import Enum
import inspect
import threading
from dependency_injector import containers, providers

from .exceptions import (
    ServiceNotFoundError, 
    DuplicateServiceError, 
    CircularDependencyError,
    ContainerLifecycleError
)


class ContainerState(Enum):
    """Container lifecycle states."""
    CREATED = "created"
    CONFIGURING = "configuring"
    CONFIGURED = "configured"
    INITIALIZING = "initializing"
    READY = "ready"
    SHUTTING_DOWN = "shutting_down"
    SHUTDOWN = "shutdown"
    ERROR = "error"


class ServiceDefinition:
    """Defines a service with its dependencies and configuration."""
    
    def __init__(
        self, 
        service_class: Type,
        dependencies: List[str] = None,
        singleton: bool = True,
        factory_method: Callable = None,
        lazy: bool = True
    ):
        self.service_class = service_class
        self.dependencies = dependencies or []
        self.singleton = singleton
        self.factory_method = factory_method
        self.lazy = lazy
        self.instance = None
        self._lock = threading.Lock()


class BaseContainer(ABC):
    """
    Abstract base class for all module containers.
    
    Each module should inherit from this class and implement:
    - module_name: Unique identifier for the module
    - configure(): Method to define services and their dependencies
    
    Features:
    - Service registration and resolution
    - Dependency injection
    - Lifecycle management
    - Cross-container service access
    - Thread-safe operations
    """
    
    # Must be overridden by subclasses
    module_name: str = None
    
    def __init__(self):
        if not self.module_name:
            raise ValueError(f"Container {self.__class__.__name__} must define module_name")
        
        self._services: Dict[str, ServiceDefinition] = {}
        self._instances: Dict[str, Any] = {}
        self._state = ContainerState.CREATED
        self._registry = None  # Will be set by ContainerRegistry
        self._lock = threading.RLock()
        self._resolution_stack: Set[str] = set()
        
        # Internal dependency_injector container for backward compatibility
        self._di_container = containers.DeclarativeContainer()
        
    @property
    def state(self) -> ContainerState:
        """Get current container state."""
        return self._state
    
    @property
    def is_ready(self) -> bool:
        """Check if container is ready for service resolution."""
        return self._state == ContainerState.READY
    
    def set_registry(self, registry):
        """Set the container registry reference."""
        self._registry = registry
    
    @abstractmethod
    def configure(self) -> None:
        """
        Configure the container by defining services and their dependencies.
        
        This method must be implemented by each module container to define
        what services it provides and their dependencies.
        
        Example:
            def configure(self):
                self.bind("stockinfo_service", StockinfoService, ["stockinfo_crud"])
                self.bind("bar_service", BarService, ["bar_crud", "stockinfo_service"])
        """
        pass
    
    def bind(
        self, 
        name: str, 
        service_class: Type,
        dependencies: List[str] = None,
        singleton: bool = True,
        factory_method: Callable = None,
        lazy: bool = True
    ) -> None:
        """
        Bind a service to the container.
        
        Args:
            name: Service name (unique within this container)
            service_class: The service class to instantiate
            dependencies: List of dependency service names
            singleton: Whether to create singleton instances
            factory_method: Optional factory method for service creation
            lazy: Whether to create instance lazily (on first access)
        """
        with self._lock:
            if name in self._services:
                raise DuplicateServiceError(name, self.module_name)
            
            self._services[name] = ServiceDefinition(
                service_class=service_class,
                dependencies=dependencies or [],
                singleton=singleton,
                factory_method=factory_method,
                lazy=lazy
            )
    
    def bind_instance(self, name: str, instance: Any) -> None:
        """
        Bind an existing instance to the container.
        
        Args:
            name: Service name
            instance: The service instance
        """
        with self._lock:
            if name in self._services:
                raise DuplicateServiceError(name, self.module_name)
            
            # Create a dummy service definition for the instance
            self._services[name] = ServiceDefinition(
                service_class=type(instance),
                singleton=True,
                lazy=False
            )
            self._instances[name] = instance
    
    def get(self, name: str) -> Any:
        """
        Get a service instance from this container.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            ServiceNotFoundError: If service is not found
            CircularDependencyError: If circular dependency detected
        """
        if name not in self._services:
            raise ServiceNotFoundError(name, self.module_name)
        
        return self._resolve_service(name)
    
    def has(self, name: str) -> bool:
        """Check if container has a service."""
        return name in self._services
    
    def list_services(self) -> List[str]:
        """Get list of all service names in this container."""
        return list(self._services.keys())
    
    def _resolve_service(self, name: str) -> Any:
        """
        Resolve a service instance with dependency injection.
        
        This method handles:
        - Circular dependency detection
        - Dependency resolution
        - Instance caching for singletons
        - Thread safety
        """
        service_def = self._services[name]
        
        # Check for existing instance (singleton)
        if service_def.singleton and name in self._instances:
            return self._instances[name]
        
        # Circular dependency detection
        if name in self._resolution_stack:
            cycle = list(self._resolution_stack) + [name]
            raise CircularDependencyError(cycle)
        
        with self._lock:
            # Double-check pattern for singleton
            if service_def.singleton and name in self._instances:
                return self._instances[name]
            
            self._resolution_stack.add(name)
            try:
                # Resolve dependencies
                resolved_deps = {}
                for dep_name in service_def.dependencies:
                    resolved_deps[dep_name] = self._resolve_dependency(dep_name)
                
                # Create instance
                if service_def.factory_method:
                    instance = service_def.factory_method(**resolved_deps)
                else:
                    instance = self._create_instance(service_def.service_class, resolved_deps)
                
                # Cache for singletons
                if service_def.singleton:
                    self._instances[name] = instance
                
                return instance
                
            finally:
                self._resolution_stack.discard(name)
    
    def _resolve_dependency(self, dep_name: str) -> Any:
        """
        Resolve a dependency, which may be from this container or another container.
        
        Dependency resolution order:
        1. Local services (this container)
        2. Cross-container services (via registry)
        """
        # First try local services
        if dep_name in self._services:
            return self._resolve_service(dep_name)
        
        # Then try cross-container resolution via registry
        if self._registry:
            return self._registry.resolve_cross_container_dependency(dep_name, self.module_name)
        
        raise ServiceNotFoundError(dep_name, self.module_name)
    
    def _create_instance(self, service_class: Type, dependencies: Dict[str, Any]) -> Any:
        """
        Create a service instance with dependency injection.
        
        This method uses introspection to match constructor parameters
        with resolved dependencies.
        """
        sig = inspect.signature(service_class.__init__)
        params = sig.parameters
        
        # Build constructor arguments
        kwargs = {}
        for param_name, param in params.items():
            if param_name == 'self':
                continue
            
            # Try to match parameter name with dependency
            if param_name in dependencies:
                kwargs[param_name] = dependencies[param_name]
            elif param.default is not param.empty:
                # Use default value if available
                continue
            else:
                # Try to find dependency by type annotation or name matching
                for dep_name, dep_instance in dependencies.items():
                    if (param.annotation != param.empty and 
                        isinstance(dep_instance, param.annotation)):
                        kwargs[param_name] = dep_instance
                        break
                else:
                    # Parameter not satisfied
                    raise ValueError(
                        f"Cannot resolve parameter '{param_name}' for service "
                        f"{service_class.__name__} in container {self.module_name}"
                    )
        
        return service_class(**kwargs)
    
    def initialize(self) -> None:
        """
        Initialize the container.
        
        This method:
        1. Calls configure() to define services
        2. Validates service definitions
        3. Pre-creates non-lazy services
        4. Sets container state to READY
        """
        try:
            self._state = ContainerState.CONFIGURING
            self.configure()
            
            self._state = ContainerState.INITIALIZING
            self._validate_services()
            self._create_eager_services()
            
            self._state = ContainerState.READY
            
        except Exception as e:
            self._state = ContainerState.ERROR
            raise ContainerLifecycleError(
                self.module_name, 
                "initialize", 
                str(e)
            )
    
    def _validate_services(self) -> None:
        """Validate service definitions for consistency."""
        # Check for circular dependencies
        for service_name in self._services:
            self._check_circular_dependencies(service_name, set())
    
    def _check_circular_dependencies(self, service_name: str, visited: Set[str]) -> None:
        """Recursively check for circular dependencies."""
        if service_name in visited:
            cycle = list(visited) + [service_name]
            raise CircularDependencyError(cycle)
        
        if service_name not in self._services:
            return  # External dependency, skip validation
        
        visited.add(service_name)
        service_def = self._services[service_name]
        
        for dep_name in service_def.dependencies:
            if dep_name in visited:
                raise ValueError(f"Circular dependency detected: {' -> '.join(visited)} -> {dep_name}")
            self._check_circular_dependencies(dep_name, visited)
    
    def _create_eager_services(self) -> None:
        """Create instances for non-lazy services."""
        for name, service_def in self._services.items():
            if not service_def.lazy:
                self._resolve_service(name)
    
    def shutdown(self) -> None:
        """
        Shutdown the container and cleanup resources.
        
        This method:
        1. Changes state to SHUTTING_DOWN
        2. Calls cleanup methods on services that have them
        3. Clears instance cache
        4. Sets state to SHUTDOWN
        """
        try:
            self._state = ContainerState.SHUTTING_DOWN
            
            # Call cleanup methods on services
            for name, instance in self._instances.items():
                if hasattr(instance, 'cleanup'):
                    try:
                        instance.cleanup()
                    except Exception as e:
                        # Log but don't stop shutdown process
                        print(f"Warning: Error during cleanup of {name}: {e}")
            
            self._instances.clear()
            self._state = ContainerState.SHUTDOWN
            
        except Exception as e:
            self._state = ContainerState.ERROR
            raise ContainerLifecycleError(
                self.module_name,
                "shutdown",
                str(e)
            )
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(module='{self.module_name}', state='{self.state.value}', services={len(self._services)})>"