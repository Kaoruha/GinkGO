"""
Container Framework Exceptions

Custom exceptions for the Ginkgo modular DI container framework.
These exceptions provide specific error handling for container operations
and dependency resolution issues.
"""


class ContainerError(Exception):
    """Base exception for all container-related errors."""
    
    def __init__(self, message: str, container_name: str = None):
        self.container_name = container_name
        super().__init__(message)


class ServiceNotFoundError(ContainerError):
    """Raised when a requested service is not found in any container."""
    
    def __init__(self, service_name: str, container_name: str = None):
        self.service_name = service_name
        message = f"Service '{service_name}' not found"
        if container_name:
            message += f" in container '{container_name}'"
        super().__init__(message, container_name)


class CircularDependencyError(ContainerError):
    """Raised when a circular dependency is detected during service resolution."""
    
    def __init__(self, dependency_chain: list):
        self.dependency_chain = dependency_chain
        chain_str = " -> ".join(dependency_chain)
        message = f"Circular dependency detected: {chain_str}"
        super().__init__(message)


class ContainerNotRegisteredError(ContainerError):
    """Raised when trying to access a container that hasn't been registered."""
    
    def __init__(self, container_name: str):
        message = f"Container '{container_name}' is not registered in the registry"
        super().__init__(message, container_name)


class DuplicateServiceError(ContainerError):
    """Raised when trying to register a service that already exists."""
    
    def __init__(self, service_name: str, container_name: str):
        message = f"Service '{service_name}' already exists in container '{container_name}'"
        super().__init__(message, container_name)


class InvalidContainerConfigError(ContainerError):
    """Raised when container configuration is invalid."""
    
    def __init__(self, container_name: str, config_issue: str):
        message = f"Invalid configuration for container '{container_name}': {config_issue}"
        super().__init__(message, container_name)


class ContainerLifecycleError(ContainerError):
    """Raised when container lifecycle operations fail."""
    
    def __init__(self, container_name: str, operation: str, reason: str):
        message = f"Container '{container_name}' failed to {operation}: {reason}"
        super().__init__(message, container_name)