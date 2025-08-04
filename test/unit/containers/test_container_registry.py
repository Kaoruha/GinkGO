"""
Unit tests for ContainerRegistry

Tests the container registry functionality including container management,
service discovery, and cross-container dependency resolution.
"""

import unittest
import threading
import time
from unittest.mock import Mock, patch

from ginkgo.libs.containers import ContainerRegistry, BaseContainer
from ginkgo.libs.containers.exceptions import (
    ContainerNotRegisteredError,
    ServiceNotFoundError,
    DuplicateServiceError,
    ContainerLifecycleError
)
from ginkgo.libs.containers.base_container import ContainerState


class MockServiceA:
    """Mock service A for testing."""
    
    def __init__(self):
        self.name = "service_a"
    
    def get_name(self):
        return self.name


class MockServiceB:
    """Mock service B for testing."""
    
    def __init__(self):
        self.name = "service_b"
    
    def get_name(self):
        return self.name


class TestContainerA(BaseContainer):
    """Test container A."""
    
    module_name = "module_a"
    
    def configure(self):
        self.bind("service_a", MockServiceA)
        self.bind("shared_service", MockServiceA)


class TestContainerB(BaseContainer):
    """Test container B."""
    
    module_name = "module_b"
    
    def configure(self):
        self.bind("service_b", MockServiceB)
        # This service depends on service_a from module_a
        self.bind("cross_dependent_service", MockServiceB)


class ContainerRegistryTest(unittest.TestCase):
    """Test cases for ContainerRegistry functionality."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = ContainerRegistry()
        self.container_a = TestContainerA()
        self.container_b = TestContainerB()
    
    def test_registry_initialization(self):
        """Test registry basic initialization."""
        self.assertEqual(len(self.registry._containers), 0)
        self.assertEqual(len(self.registry._service_index), 0)
        self.assertEqual(len(self.registry.list_containers()), 0)
    
    def test_container_registration(self):
        """Test container registration."""
        self.registry.register(self.container_a)
        
        self.assertIn("module_a", self.registry._containers)
        self.assertEqual(len(self.registry.list_containers()), 1)
        self.assertIn("module_a", self.registry.list_containers())
        
        # Container should be initialized
        self.assertEqual(self.container_a.state, ContainerState.READY)
    
    def test_duplicate_container_registration_raises_error(self):
        """Test that registering duplicate containers raises error."""
        self.registry.register(self.container_a)
        
        duplicate_container = TestContainerA()
        
        with self.assertRaises(DuplicateServiceError) as context:
            self.registry.register(duplicate_container)
        
        self.assertEqual(context.exception.container_name, "Container registry")
    
    def test_container_unregistration(self):
        """Test container unregistration."""
        self.registry.register(self.container_a)
        self.assertEqual(len(self.registry.list_containers()), 1)
        
        self.registry.unregister("module_a")
        
        self.assertEqual(len(self.registry.list_containers()), 0)
        self.assertNotIn("module_a", self.registry._containers)
        
        # Container should be shutdown
        self.assertEqual(self.container_a.state, ContainerState.SHUTDOWN)
    
    def test_get_container(self):
        """Test getting registered containers."""
        self.registry.register(self.container_a)
        
        retrieved = self.registry.get_container("module_a")
        self.assertIs(retrieved, self.container_a)
    
    def test_get_nonexistent_container_raises_error(self):
        """Test getting non-existent container raises error."""
        with self.assertRaises(ContainerNotRegisteredError) as context:
            self.registry.get_container("nonexistent")
        
        self.assertEqual(context.exception.container_name, "nonexistent")
    
    def test_get_service_from_specific_container(self):
        """Test getting service from specific container."""
        self.registry.register(self.container_a)
        
        service = self.registry.get_service("module_a", "service_a")
        
        self.assertIsInstance(service, MockServiceA)
        self.assertEqual(service.get_name(), "service_a")
    
    def test_get_service_from_unready_container_raises_error(self):
        """Test getting service from unready container raises error."""
        # Register but don't initialize container
        unready_container = TestContainerA()
        unready_container._state = ContainerState.CREATED  # Keep in created state
        
        self.registry._containers["unready"] = Mock()
        self.registry._containers["unready"].container = unready_container
        
        with self.assertRaises(ContainerLifecycleError):
            self.registry.get_service("unready", "service_a")
    
    def test_find_service_across_containers(self):
        """Test finding service across all containers."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # Find service from container A
        service_a = self.registry.find_service("service_a")
        self.assertIsInstance(service_a, MockServiceA)
        
        # Find service from container B
        service_b = self.registry.find_service("service_b")
        self.assertIsInstance(service_b, MockServiceB)
    
    def test_find_nonexistent_service_raises_error(self):
        """Test finding non-existent service raises error."""
        self.registry.register(self.container_a)
        
        with self.assertRaises(ServiceNotFoundError) as context:
            self.registry.find_service("nonexistent_service")
        
        self.assertEqual(context.exception.service_name, "nonexistent_service")
    
    def test_cross_container_dependency_resolution(self):
        """Test cross-container dependency resolution."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # Request service_a from module_b context
        resolved_service = self.registry.resolve_cross_container_dependency(
            "service_a", "module_b"
        )
        
        self.assertIsInstance(resolved_service, MockServiceA)
    
    def test_cross_container_dependency_caching(self):
        """Test that cross-container dependencies are cached."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # First resolution
        service1 = self.registry.resolve_cross_container_dependency(
            "service_a", "module_b"
        )
        
        # Second resolution should return cached result
        service2 = self.registry.resolve_cross_container_dependency(
            "service_a", "module_b"
        )
        
        self.assertIs(service1, service2)
        
        # Check cache was used
        cache_key = "module_b:service_a"
        self.assertIn(cache_key, self.registry._resolution_cache)
    
    def test_service_index_management(self):
        """Test service index is properly maintained."""
        self.registry.register(self.container_a)
        
        # Service index should be populated
        self.assertIn("service_a", self.registry._service_index)
        self.assertEqual(self.registry._service_index["service_a"], "module_a")
        
        # After unregistration, index should be cleaned
        self.registry.unregister("module_a")
        self.assertNotIn("service_a", self.registry._service_index)
    
    def test_list_services(self):
        """Test listing services."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # List all services
        all_services = self.registry.list_services()
        
        self.assertIn("module_a", all_services)
        self.assertIn("module_b", all_services)
        self.assertIn("service_a", all_services["module_a"])
        self.assertIn("service_b", all_services["module_b"])
        
        # List services from specific module
        module_a_services = self.registry.list_services("module_a")
        
        self.assertEqual(len(module_a_services), 1)
        self.assertIn("module_a", module_a_services)
        self.assertNotIn("module_b", module_a_services)
    
    def test_get_container_dependencies(self):
        """Test getting container dependency information."""
        self.registry.register(self.container_a)
        
        dep_info = self.registry.get_container_dependencies("module_a")
        
        self.assertEqual(dep_info["module_name"], "module_a")
        self.assertEqual(dep_info["state"], ContainerState.READY.value)
        self.assertIn("services", dep_info)
        self.assertIn("dependencies", dep_info)
        self.assertIn("dependents", dep_info)
    
    def test_get_health_status(self):
        """Test getting overall health status."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        health = self.registry.get_health_status()
        
        self.assertEqual(health["total_containers"], 2)
        self.assertEqual(health["healthy_containers"], 2)
        self.assertEqual(health["error_containers"], 0)
        self.assertTrue(health["overall_healthy"])
        
        self.assertIn("container_details", health)
        self.assertIn("module_a", health["container_details"])
        self.assertIn("module_b", health["container_details"])
    
    def test_initialize_all_containers(self):
        """Test initializing all containers."""
        # Create containers in CREATED state
        container_a = TestContainerA()
        container_b = TestContainerB()
        
        # Manually set them to created state
        container_a._state = ContainerState.CREATED
        container_b._state = ContainerState.CREATED
        
        # Register without auto-initialization
        with patch.object(self.registry, '_update_service_index'):
            self.registry._containers["module_a"] = Mock()
            self.registry._containers["module_a"].container = container_a
            self.registry._containers["module_b"] = Mock()
            self.registry._containers["module_b"].container = container_b
        
        # Initialize all
        self.registry.initialize_all()
        
        # Both should be ready
        self.assertEqual(container_a.state, ContainerState.READY)
        self.assertEqual(container_b.state, ContainerState.READY)
    
    def test_shutdown_all_containers(self):
        """Test shutting down all containers."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # Both should be ready
        self.assertEqual(self.container_a.state, ContainerState.READY)
        self.assertEqual(self.container_b.state, ContainerState.READY)
        
        # Shutdown all
        self.registry.shutdown_all()
        
        # Both should be shutdown
        self.assertEqual(self.container_a.state, ContainerState.SHUTDOWN)
        self.assertEqual(self.container_b.state, ContainerState.SHUTDOWN)
        
        # Cache should be cleared
        self.assertEqual(len(self.registry._resolution_cache), 0)
    
    def test_thread_safety(self):
        """Test that registry operations are thread-safe."""
        self.registry.register(self.container_a)
        
        results = {}
        threads = []
        
        def get_service(thread_id):
            try:
                service = self.registry.get_service("module_a", "service_a")
                results[thread_id] = service
            except Exception as e:
                results[thread_id] = e
        
        # Create multiple threads accessing services
        for i in range(10):
            thread = threading.Thread(target=get_service, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All should succeed and get the same singleton instance
        first_service = results[0]
        for thread_id, service in results.items():
            self.assertIsInstance(service, MockServiceA)
            self.assertIs(service, first_service)
    
    def test_dependency_tracking(self):
        """Test dependency tracking between containers."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # Create a cross-container dependency
        self.registry.resolve_cross_container_dependency("service_a", "module_b")
        
        # Check dependency tracking
        container_b_info = self.registry.get_container_dependencies("module_b")
        container_a_info = self.registry.get_container_dependencies("module_a")
        
        # module_b should depend on module_a
        self.assertIn("module_a", container_b_info["dependencies"])
        # module_a should have module_b as dependent
        self.assertIn("module_b", container_a_info["dependents"])
    
    def test_cache_cleanup_on_unregister(self):
        """Test that cache is cleaned up when containers are unregistered."""
        self.registry.register(self.container_a)
        self.registry.register(self.container_b)
        
        # Create cached dependency
        self.registry.resolve_cross_container_dependency("service_a", "module_b")
        
        # Verify cache exists
        cache_key = "module_b:service_a"
        self.assertIn(cache_key, self.registry._resolution_cache)
        
        # Unregister container
        self.registry.unregister("module_a")
        
        # Cache should be cleaned
        self.assertNotIn(cache_key, self.registry._resolution_cache)


class RegistryLifecycleTest(unittest.TestCase):
    """Test cases for registry lifecycle management."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.registry = ContainerRegistry()
    
    def test_empty_registry_operations(self):
        """Test operations on empty registry."""
        # These should not raise errors
        self.registry.initialize_all()
        self.registry.shutdown_all()
        
        self.assertEqual(len(self.registry.list_containers()), 0)
        
        health = self.registry.get_health_status()
        self.assertEqual(health["total_containers"], 0)
        self.assertTrue(health["overall_healthy"])
    
    def test_registry_with_failing_container(self):
        """Test registry behavior with failing containers."""
        
        class FailingContainer(BaseContainer):
            module_name = "failing"
            
            def configure(self):
                raise RuntimeError("Configuration failed")
        
        failing_container = FailingContainer()
        
        # Registration should handle the error
        with self.assertRaises(ContainerLifecycleError):
            self.registry.register(failing_container)
        
        # Registry should remain functional
        self.assertEqual(len(self.registry.list_containers()), 0)


if __name__ == '__main__':
    unittest.main()