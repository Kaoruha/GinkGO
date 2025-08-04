"""
Ginkgo Modular DI Container Framework - Usage Examples

This file demonstrates how to use the new modular dependency injection
container architecture in the Ginkgo framework.
"""

from ginkgo.libs.containers import (
    BaseContainer, 
    ContainerRegistry, 
    ApplicationContainer,
    CrossContainerProxy,
    registry,
    app_container
)
from ginkgo.data.module_container import data_container


def example_1_basic_container_usage():
    """
    Example 1: Basic container usage
    
    Shows how to register a module container and access its services.
    """
    print("=== Example 1: Basic Container Usage ===")
    
    # Register the data container
    registry.register(data_container)
    
    # Initialize all containers
    registry.initialize_all()
    
    # Access services directly from registry
    stockinfo_service = registry.get_service("data", "stockinfo_service")
    print(f"Retrieved stockinfo_service: {stockinfo_service}")
    
    # List all available services
    services = registry.list_services()
    print(f"All services: {services}")
    
    # Get container health status
    health = registry.get_health_status()
    print(f"Health status: {health}")


def example_2_application_container():
    """
    Example 2: Using ApplicationContainer
    
    Shows the recommended way to manage containers through ApplicationContainer.
    """
    print("\n=== Example 2: Application Container ===")
    
    # Register module container through app container
    app_container.register_module_container(data_container)
    
    # Initialize the application
    app_container.initialize()
    
    # Access services through app container
    bar_service = app_container.get_service("bar_service")
    print(f"Retrieved bar_service: {bar_service}")
    
    # Get service from specific module
    tick_service = app_container.get_service("tick_service", module_name="data")
    print(f"Retrieved tick_service from data module: {tick_service}")
    
    # List all modules and their services
    modules = app_container.list_modules()
    all_services = app_container.list_all_services()
    print(f"Modules: {modules}")
    print(f"All services by module: {all_services}")


def example_3_cross_container_proxy():
    """
    Example 3: Cross-container service proxies
    
    Shows how to create proxies for services that might be in different containers.
    """
    print("\n=== Example 3: Cross-Container Proxies ===")
    
    # Create a proxy for a data service
    stockinfo_proxy = app_container.create_service_proxy(
        "stockinfo_service",
        preferred_container="data"
    )
    
    print(f"Created proxy: {stockinfo_proxy}")
    
    # Use the proxy - it will resolve to the actual service when accessed
    try:
        # This would call methods on the actual service
        print(f"Proxy metadata: {stockinfo_proxy.get_metadata()}")
    except Exception as e:
        print(f"Proxy usage note: {e}")
    
    # Create a typed proxy
    from ginkgo.data.services.stockinfo_service import StockinfoService
    typed_proxy = app_container.create_service_proxy(
        "stockinfo_service",
        service_type=StockinfoService
    )
    print(f"Created typed proxy: {typed_proxy}")


def example_4_custom_module_container():
    """
    Example 4: Creating a custom module container
    
    Shows how to create your own module container.
    """
    print("\n=== Example 4: Custom Module Container ===")
    
    class ExampleService:
        def __init__(self, message: str = "Hello from ExampleService"):
            self.message = message
        
        def get_message(self):
            return self.message
    
    class AnotherService:
        def __init__(self, example_service: ExampleService):
            self.example_service = example_service
        
        def get_combined_message(self):
            return f"AnotherService says: {self.example_service.get_message()}"
    
    class CustomContainer(BaseContainer):
        module_name = "custom"
        
        def configure(self):
            # Bind services with dependencies
            self.bind("example_service", ExampleService)
            self.bind(
                "another_service", 
                AnotherService,
                dependencies=["example_service"]
            )
            
            # Bind an instance directly
            self.bind_instance("config_value", {"setting": "production"})
    
    # Create and register the custom container
    custom_container = CustomContainer()
    app_container.register_module_container(custom_container)
    
    # Access services
    example_service = app_container.get_service("example_service", "custom")
    another_service = app_container.get_service("another_service", "custom")
    config_value = app_container.get_service("config_value", "custom")
    
    print(f"Example service message: {example_service.get_message()}")
    print(f"Another service message: {another_service.get_combined_message()}")
    print(f"Config value: {config_value}")


def example_5_container_lifecycle():
    """
    Example 5: Container lifecycle management
    
    Shows how to manage container initialization and shutdown.
    """
    print("\n=== Example 5: Container Lifecycle ===")
    
    # Use application container as context manager
    with ApplicationContainer() as app:
        # Register containers
        app.register_module_container(data_container)
        
        print(f"App initialized: {app.is_initialized}")
        print(f"App health: {app.get_health_status()}")
        
        # Access services
        stockinfo_service = app.get_service("stockinfo_service")
        print(f"Service accessed: {stockinfo_service is not None}")
    
    # Container is automatically shutdown when exiting context
    print("Application shutdown completed")


def example_6_service_discovery():
    """
    Example 6: Service discovery and introspection
    
    Shows how to discover and inspect services across containers.
    """
    print("\n=== Example 6: Service Discovery ===")
    
    # Get detailed information about a module
    try:
        data_info = app_container.get_module_info("data")
        print(f"Data module info: {data_info}")
    except Exception as e:
        print(f"Module info error: {e}")
    
    # Find service dependencies
    try:
        service_deps = app_container.get_service_dependencies("stockinfo_service")
        print(f"Service dependencies: {service_deps}")
    except Exception as e:
        print(f"Service dependencies error: {e}")
    
    # Get container registry status
    if hasattr(registry, 'get_health_status'):
        registry_health = registry.get_health_status()
        print(f"Registry health: {registry_health}")


def example_7_error_handling():
    """
    Example 7: Error handling
    
    Shows how the container framework handles various error conditions.
    """
    print("\n=== Example 7: Error Handling ===")
    
    from ginkgo.libs.containers.exceptions import (
        ServiceNotFoundError,
        ContainerNotRegisteredError,
        CircularDependencyError
    )
    
    # Service not found
    try:
        app_container.get_service("nonexistent_service")
    except ServiceNotFoundError as e:
        print(f"Expected error - Service not found: {e}")
    
    # Container not registered
    try:
        app_container.get_service("some_service", "nonexistent_module")
    except ContainerNotRegisteredError as e:
        print(f"Expected error - Container not registered: {e}")
    
    # Circular dependency example (would be caught during container initialization)
    class CircularContainer(BaseContainer):
        module_name = "circular_test"
        
        def configure(self):
            # This would create a circular dependency
            self.bind("service_a", object, dependencies=["service_b"])
            self.bind("service_b", object, dependencies=["service_a"])
    
    circular_container = CircularContainer()
    try:
        circular_container.initialize()
    except CircularDependencyError as e:
        print(f"Expected error - Circular dependency: {e}")


def run_all_examples():
    """Run all usage examples."""
    print("Ginkgo Modular DI Container Framework - Usage Examples")
    print("=" * 60)
    
    try:
        example_1_basic_container_usage()
        example_2_application_container()
        example_3_cross_container_proxy()
        example_4_custom_module_container()
        example_5_container_lifecycle()
        example_6_service_discovery()
        example_7_error_handling()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        
    except Exception as e:
        print(f"\nExample execution error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Cleanup
        try:
            app_container.shutdown()
        except:
            pass
        
        try:
            registry.shutdown_all()
        except:
            pass


if __name__ == "__main__":
    run_all_examples()


# Quick reference for common usage patterns:

"""
Quick Reference - Common Usage Patterns:

1. Register and use a module container:
   ```python
   from ginkgo.libs.containers import app_container
   from ginkgo.data.module_container import data_container
   
   app_container.register_module_container(data_container)
   app_container.initialize()
   
   service = app_container.get_service("stockinfo_service")
   ```

2. Create a custom module container:
   ```python
   class MyContainer(BaseContainer):
       module_name = "my_module"
       
       def configure(self):
           self.bind("my_service", MyService, dependencies=["dependency"])
   ```

3. Use cross-container proxies:
   ```python
   proxy = app_container.create_service_proxy("service_name")
   result = proxy.some_method()  # Calls actual service method
   ```

4. Context manager usage:
   ```python
   with ApplicationContainer() as app:
       app.register_module_container(my_container)
       service = app.get_service("service_name")
   # Automatic cleanup on exit
   ```

5. Service discovery:
   ```python
   modules = app_container.list_modules()
   services = app_container.list_all_services()
   health = app_container.get_health_status()
   ```
"""