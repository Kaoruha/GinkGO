# Upstream: All Modules (全局访问core.containers.container获取配置和日志服务)
# Downstream: dependency_injector (依赖注入框架)、GCONF/GLOG/GTM (全局单例)
# Role: 核心模块依赖注入容器管理配置/日志/线程管理等核心服务支持懒加载和兼容支持交易系统功能和组件集成提供完整业务支持






"""
Core Module Container

Provides unified access to core services using dependency-injector,
following the same pattern as data and backtest modules.

Usage Examples:

    from ginkgo.core.containers import container
    
    # Access core services (similar to data.cruds.bar())
    config_service = container.services.config()
    logger_service = container.services.logger()
    thread_service = container.services.thread()
    
    # Access utilities
    validator = container.utilities.validator()
    health_checker = container.utilities.health_check()
    
    # For dependency injection:
    from dependency_injector.wiring import inject, Provide
    
    @inject
    def your_function(config = Provide[Container.services.config]):
        # Use config here
        pass
"""

from dependency_injector import containers, providers


# ============= LAZY IMPORT FUNCTIONS =============
# Core service classes
def _get_config_service_class():
    """Lazy import for config service."""
    try:
        from ginkgo.libs.core.config import GCONF
        return type(GCONF)
    except ImportError:
        # Fallback to a simple config class if not available
        class MockConfigService:
            def __init__(self):
                self._config = {}
            def get(self, key, default=None):
                return self._config.get(key, default)
            def set(self, key, value):
                self._config[key] = value
        return MockConfigService

def _get_logger_service_class():
    """Lazy import for logger service."""
    try:
        from ginkgo.libs.core.logger import GLOG
        return type(GLOG)
    except ImportError:
        # Fallback to a simple logger class if not available
        class MockLoggerService:
            def __init__(self):
                pass
            def info(self, msg):
                print(f"INFO: {msg}")
            def debug(self, msg):
                print(f"DEBUG: {msg}")
            def error(self, msg):
                print(f"ERROR: {msg}")
        return MockLoggerService

def _get_thread_service_class():
    """Lazy import for thread service."""
    try:
        from ginkgo.libs.core.threading import GTM
        return type(GTM)
    except ImportError:
        # Fallback to a simple thread manager if not available
        class MockThreadService:
            def __init__(self):
                pass
            def submit_task(self, func, *args, **kwargs):
                return func(*args, **kwargs)
        return MockThreadService

# Utility classes
def _get_validator_class():
    """Lazy import for validator."""
    try:
        from ginkgo.libs.validators.base_validator import BaseValidator
        return BaseValidator
    except ImportError:
        # Fallback to a simple validator if not available
        class MockValidator:
            def __init__(self):
                pass
            def validate(self, data, schema=None):
                return True
        return MockValidator

def _get_health_check_class():
    """Lazy import for health check."""
    try:
        from ginkgo.libs.utils.health_check import HealthCheck
        return HealthCheck
    except ImportError:
        # Fallback to a simple health checker if not available
        class MockHealthCheck:
            def __init__(self):
                pass
            def run_check(self):
                return {"status": "ok", "components": []}
        return MockHealthCheck

def _get_stability_util_class():
    """Lazy import for stability utilities."""
    try:
        from ginkgo.libs.utils.stability_utils import StabilityUtils
        return StabilityUtils
    except ImportError:
        # Fallback to a simple stability util if not available
        class MockStabilityUtils:
            def __init__(self):
                pass
            def check_stability(self):
                return True
        return MockStabilityUtils


class Container(containers.DeclarativeContainer):
    """
    Core module dependency injection container.
    
    Provides unified access to core services and utilities using FactoryAggregate,
    following the data module's successful pattern.
    """
    
    # ============= CORE SERVICES =============
    # Service factories - using Singleton for shared state services
    config_service = providers.Singleton(_get_config_service_class)
    logger_service = providers.Singleton(_get_logger_service_class)
    thread_service = providers.Singleton(_get_thread_service_class)
    
    # Services aggregate - similar to data module's cruds
    services = providers.FactoryAggregate(
        config=config_service,
        logger=logger_service,
        thread=thread_service
    )
    
    # ============= UTILITIES =============
    # Utility factories - using Factory for per-use instances
    validator = providers.Factory(_get_validator_class)
    health_check = providers.Factory(_get_health_check_class)
    stability_util = providers.Factory(_get_stability_util_class)
    
    # Utilities aggregate
    utilities = providers.FactoryAggregate(
        validator=validator,
        health_check=health_check,
        stability=stability_util
    )


# Create a singleton instance of the container, accessible throughout the application
container = Container()

# Backward compatibility - provide old access methods (following backtest pattern)
def get_service(service_type: str):
    """Get service by type (backward compatibility)"""
    service_mapping = {
        'config': container.services.config,
        'logger': container.services.logger,
        'thread': container.services.thread
    }
    
    if service_type in service_mapping:
        return service_mapping[service_type]()
    else:
        raise ValueError(f"Unknown service type: {service_type}")

def get_utility(utility_type: str):
    """Get utility by type (backward compatibility)"""
    utility_mapping = {
        'validator': container.utilities.validator,
        'health_check': container.utilities.health_check,
        'stability': container.utilities.stability
    }
    
    if utility_type in utility_mapping:
        return utility_mapping[utility_type]()
    else:
        raise ValueError(f"Unknown utility type: {utility_type}")

def get_service_info():
    """Get service information (backward compatibility)"""
    return {
        "services": ["config", "logger", "thread"],
        "utilities": ["validator", "health_check", "stability"]
    }

# Bind backward compatibility methods to container (following backtest pattern)
container.get_service = get_service
container.get_utility = get_utility
container.get_service_info = get_service_info

# Create alias for backward compatibility
core_container = container