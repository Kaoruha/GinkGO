"""
Ginkgo Core Module - Public API

This module provides core services like configuration, logging, and threading
using a Dependency Injection Container for managing services and their dependencies.

Following the successful data module pattern.
"""
import inspect

# Import the container to access services
from .containers import container

# Import decorators for API enhancement
try:
    from ginkgo.libs import time_logger, retry
except ImportError:
    # Fallback decorators if libs not available
    def time_logger(func):
        return func
    def retry(func):
        return func

# --- Core Service Functions ---

@time_logger
def get_config(*args, **kwargs):
    """Public API: Get configuration service."""
    return container.services.config()

@time_logger  
def get_logger(*args, **kwargs):
    """Public API: Get logger service."""
    return container.services.logger()

@time_logger
def get_thread_manager(*args, **kwargs):
    """Public API: Get thread management service."""
    return container.services.thread()

# --- Utility Functions ---

def validate_data(data, schema=None, *args, **kwargs):
    """Public API: Validate data against schema."""
    return container.utilities.validator().validate(data, schema)

def check_system_health(*args, **kwargs):
    """Public API: Perform system health check."""
    return container.utilities.health_check().run_check()

def check_stability(*args, **kwargs):
    """Public API: Check system stability."""
    return container.utilities.stability().check_stability()

# --- Convenience Functions ---

def get_available_services():
    """Get list of available service types."""
    return ["config", "logger", "thread"]

def get_available_utilities():
    """Get list of available utility types."""
    return ["validator", "health_check", "stability"]

# --- Backward Compatibility Functions ---
# Maintain existing API for smooth migration

def init_core_services():
    """Initialize core services (backward compatibility)."""
    config = container.services.config()
    logger = container.services.logger()
    thread = container.services.thread()
    return config, logger, thread

def get_core_service(service_type: str):
    """Get core service by type (backward compatibility)."""
    return container.get_service(service_type)

def get_core_utility(utility_type: str):
    """Get core utility by type (backward compatibility)."""
    return container.get_utility(utility_type)

# --- Import other components with error handling ---
# Try to import other components, but don't fail if they're not available

try:
    # Import interfaces if available
    from . import interfaces
except ImportError as e:
    interfaces = None

try:
    # Import adapters if available
    from . import adapters
except ImportError as e:
    adapters = None

try:
    # Import factories if available
    from . import factories
except ImportError as e:
    factories = None

# --- Module Information ---
__version__ = "1.0.0"

# --- Dynamic Export of all functions ---
__all__ = [name for name, obj in inspect.getmembers(inspect.getmodule(inspect.currentframe())) 
           if inspect.isfunction(obj) and not name.startswith('_')]

# Also export the container and important objects
__all__.extend(['container', 'interfaces', 'adapters', 'factories'])

# Legacy exports for backward compatibility
core_container = container