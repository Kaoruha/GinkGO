"""
Unit tests for BaseContainer

Tests the core functionality of the BaseContainer abstract class
without any external dependencies.
"""

import unittest
import threading
from unittest.mock import Mock, patch
from typing import Dict, Any

from ginkgo.libs.containers import BaseContainer
from ginkgo.libs.containers.exceptions import (
    ServiceNotFoundError,
    DuplicateServiceError,
    CircularDependencyError,
    ContainerLifecycleError
)
from ginkgo.libs.containers.base_container import ContainerState


class MockService:
    """Mock service for testing purposes."""
    
    def __init__(self, name: str = "mock_service"):
        self.name = name
        self.initialized = True
    
    def get_name(self):
        return self.name


class MockDependentService:
    """Mock service that depends on another service."""
    
    def __init__(self, mock_service: MockService):
        self.dependency = mock_service
        self.initialized = True
    
    def get_dependency_name(self):
        return self.dependency.get_name()


class TestContainer(BaseContainer):
    """Concrete implementation of BaseContainer for testing."""
    
    module_name = "test_module"
    
    def configure(self):
        """Configure test services."""
        self.bind("mock_service", MockService)
        self.bind(
            "dependent_service", 
            MockDependentService,
            dependencies=["mock_service"]
        )
        self.bind_instance("config_value", {"test": "value"})


class BaseContainerTest(unittest.TestCase):
    """Test cases for BaseContainer functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.container = TestContainer()
    
    def test_container_initialization(self):
        """Test container basic initialization."""
        self.assertEqual(self.container.module_name, "test_module")
        self.assertEqual(self.container.state, ContainerState.CREATED)
        self.assertFalse(self.container.is_ready)
        self.assertEqual(len(self.container._services), 0)
    
    def test_container_without_module_name_raises_error(self):
        """Test that container without module_name raises ValueError."""
        
        class InvalidContainer(BaseContainer):
            # Missing module_name
            def configure(self):
                pass
        
        with self.assertRaises(ValueError) as context:
            InvalidContainer()
        
        self.assertIn("must define module_name", str(context.exception))
    
    def test_service_binding(self):
        """Test basic service binding."""
        self.container.bind("test_service", MockService)
        
        self.assertTrue(self.container.has("test_service"))
        self.assertIn("test_service", self.container.list_services())
    
    def test_instance_binding(self):
        """Test binding existing instances."""
        test_instance = MockService("bound_instance")
        self.container.bind_instance("test_instance", test_instance)
        
        self.assertTrue(self.container.has("test_instance"))
        # Should return the exact same instance
        retrieved = self.container.get("test_instance")
        self.assertIs(retrieved, test_instance)
    
    def test_duplicate_service_binding_raises_error(self):
        """Test that binding duplicate services raises DuplicateServiceError."""
        self.container.bind("duplicate_service", MockService)
        
        with self.assertRaises(DuplicateServiceError) as context:
            self.container.bind("duplicate_service", MockService)
        
        self.assertEqual(context.exception.container_name, "test_module")
    
    def test_service_not_found_raises_error(self):
        """Test that accessing non-existent service raises ServiceNotFoundError."""
        with self.assertRaises(ServiceNotFoundError) as context:
            self.container.get("non_existent_service")
        
        self.assertEqual(context.exception.service_name, "non_existent_service")
        self.assertEqual(context.exception.container_name, "test_module")
    
    def test_container_initialization_lifecycle(self):
        """Test container initialization lifecycle."""
        # Initially created
        self.assertEqual(self.container.state, ContainerState.CREATED)
        
        # Initialize
        self.container.initialize()
        
        # Should be ready
        self.assertEqual(self.container.state, ContainerState.READY)
        self.assertTrue(self.container.is_ready)
        
        # Services should be configured
        self.assertTrue(self.container.has("mock_service"))
        self.assertTrue(self.container.has("dependent_service"))
        self.assertTrue(self.container.has("config_value"))
    
    def test_service_resolution_with_dependencies(self):
        """Test service resolution with dependency injection."""
        self.container.initialize()
        
        # Get dependent service
        dependent_service = self.container.get("dependent_service")
        
        self.assertIsInstance(dependent_service, MockDependentService)
        self.assertEqual(dependent_service.get_dependency_name(), "mock_service")
    
    def test_singleton_behavior(self):
        """Test that singleton services return the same instance."""
        self.container.initialize()
        
        service1 = self.container.get("mock_service")
        service2 = self.container.get("mock_service")
        
        self.assertIs(service1, service2)
    
    def test_non_singleton_behavior(self):
        """Test non-singleton services return different instances."""
        self.container.bind("non_singleton", MockService, singleton=False)
        self.container.initialize()
        
        service1 = self.container.get("non_singleton")
        service2 = self.container.get("non_singleton")
        
        self.assertIsNot(service1, service2)
        self.assertIsInstance(service1, MockService)
        self.assertIsInstance(service2, MockService)
    
    def test_circular_dependency_detection(self):
        """Test circular dependency detection."""
        
        class CircularContainer(BaseContainer):
            module_name = "circular_test"
            
            def configure(self):
                self.bind("service_a", MockService, dependencies=["service_b"])
                self.bind("service_b", MockService, dependencies=["service_a"])
        
        container = CircularContainer()
        
        with self.assertRaises(CircularDependencyError) as context:
            container.initialize()
        
        self.assertIn("service_a", context.exception.dependency_chain)
        self.assertIn("service_b", context.exception.dependency_chain)
    
    def test_container_shutdown(self):
        """Test container shutdown lifecycle."""
        self.container.initialize()
        self.assertEqual(self.container.state, ContainerState.READY)
        
        # Shutdown
        self.container.shutdown()
        
        self.assertEqual(self.container.state, ContainerState.SHUTDOWN)
        # Instance cache should be cleared
        self.assertEqual(len(self.container._instances), 0)
    
    def test_service_cleanup_during_shutdown(self):
        """Test that services with cleanup methods are called during shutdown."""
        
        class ServiceWithCleanup:
            def __init__(self):
                self.cleaned_up = False
            
            def cleanup(self):
                self.cleaned_up = True
        
        self.container.bind("cleanup_service", ServiceWithCleanup)
        self.container.initialize()
        
        # Get service to ensure it's instantiated
        service = self.container.get("cleanup_service")
        self.assertFalse(service.cleaned_up)
        
        # Shutdown should call cleanup
        self.container.shutdown()
        self.assertTrue(service.cleaned_up)
    
    def test_thread_safety(self):
        """Test that container operations are thread-safe."""
        self.container.initialize()
        
        results = {}
        threads = []
        
        def get_service(thread_id):
            service = self.container.get("mock_service")
            results[thread_id] = service
        
        # Create multiple threads accessing the same service
        for i in range(10):
            thread = threading.Thread(target=get_service, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # All threads should get the same singleton instance
        first_service = results[0]
        for thread_id, service in results.items():
            self.assertIs(service, first_service)
    
    def test_container_state_transitions(self):
        """Test all container state transitions."""
        # CREATED -> CONFIGURING -> INITIALIZING -> READY
        self.assertEqual(self.container.state, ContainerState.CREATED)
        
        self.container.initialize()
        self.assertEqual(self.container.state, ContainerState.READY)
        
        # READY -> SHUTTING_DOWN -> SHUTDOWN
        self.container.shutdown()
        self.assertEqual(self.container.state, ContainerState.SHUTDOWN)
    
    def test_container_error_state(self):
        """Test container error state handling."""
        
        class FailingContainer(BaseContainer):
            module_name = "failing_test"
            
            def configure(self):
                # This will cause an error during initialization
                raise RuntimeError("Configuration failed")
        
        container = FailingContainer()
        
        with self.assertRaises(ContainerLifecycleError):
            container.initialize()
        
        self.assertEqual(container.state, ContainerState.ERROR)
    
    def test_factory_method_service_creation(self):
        """Test service creation using factory methods."""
        
        def create_custom_service():
            return MockService("factory_created")
        
        self.container.bind(
            "factory_service", 
            MockService,
            factory_method=create_custom_service
        )
        self.container.initialize()
        
        service = self.container.get("factory_service")
        self.assertEqual(service.name, "factory_created")
    
    def test_container_registry_integration(self):
        """Test container registry integration."""
        mock_registry = Mock()
        
        self.container.set_registry(mock_registry)
        self.assertEqual(self.container._registry, mock_registry)
    
    def test_container_string_representation(self):
        """Test container string representation."""
        repr_str = repr(self.container)
        
        self.assertIn("TestContainer", repr_str)
        self.assertIn("test_module", repr_str)
        self.assertIn("created", repr_str.lower())


class ContainerValidationTest(unittest.TestCase):
    """Test cases for container validation logic."""
    
    def test_service_dependency_validation(self):
        """Test validation of service dependencies."""
        
        class ValidatingContainer(BaseContainer):
            module_name = "validation_test"
            
            def configure(self):
                self.bind("valid_service", MockService)
                self.bind(
                    "dependent_service",
                    MockDependentService,
                    dependencies=["valid_service"]
                )
        
        container = ValidatingContainer()
        container.initialize()  # Should not raise any errors
        
        self.assertEqual(container.state, ContainerState.READY)
    
    def test_missing_dependency_handling(self):
        """Test handling of missing dependencies."""
        
        class MissingDepContainer(BaseContainer):
            module_name = "missing_dep_test"
            
            def configure(self):
                self.bind(
                    "dependent_service",
                    MockDependentService,
                    dependencies=["missing_service"]  # This service doesn't exist
                )
        
        container = MissingDepContainer()
        container.initialize()
        
        with self.assertRaises(ServiceNotFoundError):
            container.get("dependent_service")


if __name__ == '__main__':
    unittest.main()