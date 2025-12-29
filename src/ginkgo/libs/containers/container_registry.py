# Upstream: All Modules
# Downstream: Standard Library
# Role: Container Registry容器提供ContainerRegistry依赖注入支持交易系统功能






"""
Container Registry

Central registry for managing all module containers in the Ginkgo framework.
Provides container discovery, cross-container dependency resolution, and
coordination between different module containers.
"""

from typing import Dict, Any, Optional, List, Type, Set
import threading
import time
from dataclasses import dataclass, field

from .base_container import BaseContainer, ContainerState
from .exceptions import (
    ContainerNotRegisteredError,
    ServiceNotFoundError,
    CircularDependencyError,
    DuplicateServiceError,
    ContainerLifecycleError
)


@dataclass
class ContainerInfo:
    """Information about a registered container."""
    container: BaseContainer
    registration_time: float = field(default_factory=time.time)
    dependencies: Set[str] = field(default_factory=set)
    dependents: Set[str] = field(default_factory=set)


class ContainerRegistry:
    """
    Central registry for all module containers.
    
    The registry provides:
    - Container registration and discovery
    - Cross-container service resolution
    - Dependency management between containers
    - Lifecycle coordination
    - Health monitoring
    
    Features:
    - Thread-safe operations
    - Automatic dependency tracking
    - Container health monitoring
    - Graceful startup and shutdown coordination
    """
    
    def __init__(self):
        self._containers: Dict[str, ContainerInfo] = {}
        self._service_index: Dict[str, str] = {}  # service_name -> container_name
        self._lock = threading.RLock()
        self._initialization_order: List[str] = []
        
        # Cross-container dependency resolution cache
        self._resolution_cache: Dict[str, Any] = {}
        self._cache_lock = threading.Lock()
    
    def register(self, container: BaseContainer) -> None:
        """
        Register a container with the registry.
        
        Args:
            container: The container instance to register
            
        Raises:
            DuplicateServiceError: If container with same name already registered
        """
        with self._lock:
            if container.module_name in self._containers:
                raise DuplicateServiceError(
                    container.module_name, 
                    "Container registry"
                )
            
            # Set registry reference on container
            container.set_registry(self)
            
            # Register container
            container_info = ContainerInfo(container=container)
            self._containers[container.module_name] = container_info
            
            # Initialize container if not already done
            if container.state == ContainerState.CREATED:
                container.initialize()
            
            # Update service index
            self._update_service_index(container)
            
            print(f"Registered container: {container.module_name}")
    
    def unregister(self, module_name: str) -> None:
        """
        Unregister a container from the registry.
        
        Args:
            module_name: Name of the module container to unregister
        """
        with self._lock:
            if module_name not in self._containers:
                return
            
            container_info = self._containers[module_name]
            container = container_info.container
            
            # Shutdown container
            if container.state != ContainerState.SHUTDOWN:
                container.shutdown()
            
            # Remove from service index
            services_to_remove = []
            for service_name, container_name in self._service_index.items():
                if container_name == module_name:
                    services_to_remove.append(service_name)
            
            for service_name in services_to_remove:
                del self._service_index[service_name]
            
            # Remove container
            del self._containers[module_name]
            
            # Clear cache entries related to this container
            self._clear_cache_for_container(module_name)
            
            print(f"Unregistered container: {module_name}")
    
    def get_container(self, module_name: str) -> BaseContainer:
        """
        Get a registered container by module name.
        
        Args:
            module_name: Name of the module container
            
        Returns:
            The container instance
            
        Raises:
            ContainerNotRegisteredError: If container is not registered
        """
        if module_name not in self._containers:
            raise ContainerNotRegisteredError(module_name)
        
        return self._containers[module_name].container
    
    def get_service(self, module_name: str, service_name: str) -> Any:
        """
        Get a service from a specific container.
        
        Args:
            module_name: Name of the module container
            service_name: Name of the service
            
        Returns:
            Service instance
            
        Raises:
            ContainerNotRegisteredError: If container is not registered
            ServiceNotFoundError: If service is not found
        """
        container = self.get_container(module_name)
        
        if not container.is_ready:
            raise ContainerLifecycleError(
                module_name,
                "get_service",
                f"Container is not ready (state: {container.state.value})"
            )
        
        return container.get(service_name)
    
    def find_service(self, service_name: str) -> Any:
        """
        Find a service by name across all containers.
        
        Args:
            service_name: Name of the service to find
            
        Returns:
            Service instance
            
        Raises:
            ServiceNotFoundError: If service is not found in any container
        """
        # Check service index first
        if service_name in self._service_index:
            container_name = self._service_index[service_name]
            return self.get_service(container_name, service_name)
        
        # If not in index, search all containers
        for container_name, container_info in self._containers.items():
            container = container_info.container
            if container.has(service_name):
                return self.get_service(container_name, service_name)
        
        raise ServiceNotFoundError(service_name)
    
    def resolve_cross_container_dependency(
        self, 
        service_name: str, 
        requesting_container: str
    ) -> Any:
        """
        Resolve a cross-container dependency.
        
        This method is called by containers when they need a service
        that's not available locally.
        
        Args:
            service_name: Name of the service to resolve
            requesting_container: Name of the container requesting the service
            
        Returns:
            Service instance
        """
        # Check cache first
        cache_key = f"{requesting_container}:{service_name}"
        with self._cache_lock:
            if cache_key in self._resolution_cache:
                return self._resolution_cache[cache_key]
        
        # Find and resolve service
        try:
            service_instance = self.find_service(service_name)
            
            # Cache the resolution
            with self._cache_lock:
                self._resolution_cache[cache_key] = service_instance
            
            # Update dependency tracking
            self._track_dependency(requesting_container, service_name)
            
            return service_instance
            
        except ServiceNotFoundError:
            raise ServiceNotFoundError(
                service_name,
                f"Cross-container resolution from {requesting_container}"
            )
    
    def list_containers(self) -> List[str]:
        """Get list of all registered container names."""
        return list(self._containers.keys())
    
    def list_services(self, module_name: str = None) -> Dict[str, List[str]]:
        """
        List all services, optionally filtered by container.
        
        Args:
            module_name: Optional container name to filter by
            
        Returns:
            Dictionary mapping container names to service lists
        """
        if module_name:
            if module_name not in self._containers:
                raise ContainerNotRegisteredError(module_name)
            container = self._containers[module_name].container
            return {module_name: container.list_services()}
        
        result = {}
        for container_name, container_info in self._containers.items():
            container = container_info.container
            result[container_name] = container.list_services()
        
        return result
    
    def get_container_dependencies(self, module_name: str) -> Dict[str, Any]:
        """
        Get dependency information for a container.
        
        Args:
            module_name: Name of the container
            
        Returns:
            Dictionary with dependency information
        """
        if module_name not in self._containers:
            raise ContainerNotRegisteredError(module_name)
        
        container_info = self._containers[module_name]
        
        return {
            "module_name": module_name,
            "state": container_info.container.state.value,
            "dependencies": list(container_info.dependencies),
            "dependents": list(container_info.dependents),
            "services": container_info.container.list_services(),
            "registration_time": container_info.registration_time
        }
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get overall health status of all containers.
        
        Returns:
            Dictionary with health information
        """
        status = {
            "total_containers": len(self._containers),
            "healthy_containers": 0,
            "error_containers": 0,
            "container_details": {}
        }
        
        for container_name, container_info in self._containers.items():
            container = container_info.container
            is_healthy = container.state == ContainerState.READY
            
            if is_healthy:
                status["healthy_containers"] += 1
            elif container.state == ContainerState.ERROR:
                status["error_containers"] += 1
            
            status["container_details"][container_name] = {
                "state": container.state.value,
                "healthy": is_healthy,
                "service_count": len(container.list_services()),
                "registration_time": container_info.registration_time
            }
        
        status["overall_healthy"] = (
            status["healthy_containers"] == status["total_containers"]
        )
        
        return status
    
    def initialize_all(self) -> None:
        """
        Initialize all registered containers in dependency order.
        
        This method ensures containers are initialized in the correct
        order based on their dependencies.
        """
        with self._lock:
            # Determine initialization order
            self._calculate_initialization_order()
            
            # Initialize containers in order
            for container_name in self._initialization_order:
                if container_name in self._containers:
                    container = self._containers[container_name].container
                    if container.state == ContainerState.CREATED:
                        try:
                            container.initialize()
                            print(f"Initialized container: {container_name}")
                        except Exception as e:
                            print(f"Failed to initialize container {container_name}: {e}")
                            raise
    
    def shutdown_all(self) -> None:
        """
        Shutdown all containers in reverse dependency order.
        
        This ensures that dependent containers are shutdown before
        their dependencies.
        """
        with self._lock:
            # Shutdown in reverse order
            shutdown_order = list(reversed(self._initialization_order))
            
            for container_name in shutdown_order:
                if container_name in self._containers:
                    container = self._containers[container_name].container
                    if container.state != ContainerState.SHUTDOWN:
                        try:
                            container.shutdown()
                            print(f"Shutdown container: {container_name}")
                        except Exception as e:
                            print(f"Error shutting down container {container_name}: {e}")
            
            # Clear all caches
            with self._cache_lock:
                self._resolution_cache.clear()
    
    def _update_service_index(self, container: BaseContainer) -> None:
        """Update the global service index with services from a container."""
        for service_name in container.list_services():
            self._service_index[service_name] = container.module_name
    
    def _track_dependency(self, requesting_container: str, service_name: str) -> None:
        """Track cross-container dependencies."""
        if service_name in self._service_index:
            providing_container = self._service_index[service_name]
            
            if requesting_container in self._containers:
                self._containers[requesting_container].dependencies.add(providing_container)
            
            if providing_container in self._containers:
                self._containers[providing_container].dependents.add(requesting_container)
    
    def _calculate_initialization_order(self) -> None:
        """Calculate the order in which containers should be initialized."""
        # Simple topological sort based on dependencies
        # For now, use registration order as a simple heuristic
        # TODO: Implement proper topological sort based on actual dependencies
        self._initialization_order = sorted(
            self._containers.keys(),
            key=lambda name: self._containers[name].registration_time
        )
    
    def _clear_cache_for_container(self, container_name: str) -> None:
        """Clear cache entries related to a specific container."""
        with self._cache_lock:
            keys_to_remove = []
            for cache_key in self._resolution_cache.keys():
                if cache_key.startswith(f"{container_name}:") or cache_key.endswith(f":{container_name}"):
                    keys_to_remove.append(cache_key)
            
            for key in keys_to_remove:
                del self._resolution_cache[key]


# Global registry instance
registry = ContainerRegistry()