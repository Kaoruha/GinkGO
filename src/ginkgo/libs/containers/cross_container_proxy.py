# Upstream: All Modules
# Downstream: Standard Library
# Role: Cross Container Proxy容器提供CrossContainerProxy跨依赖注入支持相关功能






"""
Cross Container Proxy

Provides transparent access to services across different containers
while maintaining lazy loading and dependency injection principles.
"""

from typing import Any, Optional, Dict, Type
from functools import wraps
import weakref

from .exceptions import ServiceNotFoundError, ContainerNotRegisteredError


class CrossContainerProxy:
    """
    Proxy object for accessing services from other containers.
    
    This proxy allows containers to declare dependencies on services
    from other containers without needing to know the exact container
    or manage the lifecycle.
    
    Features:
    - Lazy service resolution
    - Automatic retry on service updates
    - Transparent method forwarding
    - Weak reference management to avoid circular references
    """
    
    def __init__(
        self, 
        service_name: str, 
        registry=None,
        preferred_container: str = None,
        service_type: Type = None
    ):
        """
        Initialize cross-container service proxy.
        
        Args:
            service_name: Name of the service to proxy
            registry: Container registry instance
            preferred_container: Preferred container to resolve from
            service_type: Expected service type for validation
        """
        self._service_name = service_name
        self._registry = registry
        self._preferred_container = preferred_container
        self._service_type = service_type
        
        # Cached service reference (weak to avoid circular refs)
        self._cached_service = None
        self._cached_service_ref = None
        
        # Metadata
        self._resolution_count = 0
        self._last_resolution_error = None
    
    def _resolve_service(self) -> Any:
        """
        Resolve the actual service instance.
        
        Returns:
            The resolved service instance
            
        Raises:
            ServiceNotFoundError: If service cannot be resolved
        """
        if not self._registry:
            raise ServiceNotFoundError(
                self._service_name, 
                "No registry available for proxy"
            )
        
        try:
            # Try preferred container first
            if self._preferred_container:
                try:
                    service = self._registry.get_service(
                        self._preferred_container, 
                        self._service_name
                    )
                    self._update_cache(service)
                    return service
                except (ContainerNotRegisteredError, ServiceNotFoundError):
                    pass  # Fall back to global search
            
            # Search across all containers
            service = self._registry.find_service(self._service_name)
            self._update_cache(service)
            return service
            
        except Exception as e:
            self._last_resolution_error = e
            self._resolution_count += 1
            raise
    
    def _update_cache(self, service: Any) -> None:
        """Update the cached service reference."""
        self._cached_service = service
        # Use weak reference to avoid circular dependencies
        try:
            self._cached_service_ref = weakref.ref(service)
        except TypeError:
            # Some objects can't be weakly referenced
            self._cached_service_ref = None
        
        # Validate service type if specified
        if self._service_type and not isinstance(service, self._service_type):
            raise TypeError(
                f"Service {self._service_name} is not of expected type "
                f"{self._service_type.__name__}, got {type(service).__name__}"
            )
        
        self._resolution_count += 1
        self._last_resolution_error = None
    
    def _get_cached_service(self) -> Optional[Any]:
        """Get cached service if still valid."""
        if self._cached_service_ref:
            service = self._cached_service_ref()
            if service is not None:
                return service
        
        return self._cached_service
    
    def __getattr__(self, name: str) -> Any:
        """
        Proxy attribute access to the underlying service.
        
        This method is called when an attribute is accessed on the proxy
        that doesn't exist on the proxy itself. It forwards the access
        to the underlying service.
        """
        # Try cached service first
        cached_service = self._get_cached_service()
        if cached_service and hasattr(cached_service, name):
            attr = getattr(cached_service, name)
            
            # If it's a method, wrap it to handle service updates
            if callable(attr):
                return self._wrap_method(attr)
            else:
                return attr
        
        # Resolve service and try again
        service = self._resolve_service()
        if hasattr(service, name):
            attr = getattr(service, name)
            
            if callable(attr):
                return self._wrap_method(attr)
            else:
                return attr
        
        raise AttributeError(
            f"Service '{self._service_name}' has no attribute '{name}'"
        )
    
    def _wrap_method(self, method):
        """
        Wrap a service method to handle service updates.
        
        This wrapper ensures that if a service is replaced or updated,
        subsequent method calls will use the new service instance.
        """
        @wraps(method)
        def wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except Exception as e:
                # If method call fails, try to resolve service again
                # in case it was replaced or updated
                try:
                    fresh_service = self._resolve_service()
                    fresh_method = getattr(fresh_service, method.__name__)
                    return fresh_method(*args, **kwargs)
                except:
                    # If re-resolution also fails, raise original error
                    raise e
        
        return wrapper
    
    def __call__(self, *args, **kwargs):
        """
        Make the proxy callable if the underlying service is callable.
        """
        service = self._get_cached_service()
        if not service:
            service = self._resolve_service()
        
        if not callable(service):
            raise TypeError(
                f"Service '{self._service_name}' is not callable"
            )
        
        return service(*args, **kwargs)
    
    def __bool__(self) -> bool:
        """
        Check if the service can be resolved.
        
        This allows using the proxy in boolean contexts to check
        service availability.
        """
        try:
            service = self._get_cached_service()
            if not service:
                service = self._resolve_service()
            return service is not None
        except:
            return False
    
    def __repr__(self) -> str:
        """String representation of the proxy."""
        status = "resolved" if self._cached_service else "unresolved"
        container_info = f" from {self._preferred_container}" if self._preferred_container else ""
        
        return (
            f"<CrossContainerProxy(service='{self._service_name}'{container_info}, "
            f"status={status}, resolutions={self._resolution_count})>"
        )
    
    def force_refresh(self) -> Any:
        """
        Force refresh of the cached service.
        
        This method clears the cache and re-resolves the service,
        useful when you know the service has been updated.
        
        Returns:
            The freshly resolved service instance
        """
        self._cached_service = None
        self._cached_service_ref = None
        return self._resolve_service()
    
    def get_metadata(self) -> Dict[str, Any]:
        """
        Get metadata about this proxy.
        
        Returns:
            Dictionary with proxy metadata
        """
        return {
            "service_name": self._service_name,
            "preferred_container": self._preferred_container,
            "service_type": self._service_type.__name__ if self._service_type else None,
            "is_cached": self._cached_service is not None,
            "resolution_count": self._resolution_count,
            "last_error": str(self._last_resolution_error) if self._last_resolution_error else None
        }


def create_proxy(
    service_name: str,
    registry=None,
    preferred_container: str = None,
    service_type: Type = None
) -> CrossContainerProxy:
    """
    Factory function to create a cross-container service proxy.
    
    Args:
        service_name: Name of the service to proxy
        registry: Container registry instance
        preferred_container: Preferred container to resolve from
        service_type: Expected service type for validation
        
    Returns:
        CrossContainerProxy instance
    """
    return CrossContainerProxy(
        service_name=service_name,
        registry=registry,
        preferred_container=preferred_container,
        service_type=service_type
    )