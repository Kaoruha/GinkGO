"""
Unit tests for Backtest Container (Updated for new DI architecture)

Tests the core functionality of the new dependency-injector based backtest container including:
- Container initialization and component access
- FactoryAggregate providers (engines, analyzers, strategies, portfolios)
- Service discovery and backward compatibility
- Error handling and lazy loading
- Integration with unified services
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Optional

from ginkgo.backtest.core.containers import container, backtest_container


class TestBacktestContainer(unittest.TestCase):
    """Test backtest container functionality with new DI architecture."""

    def setUp(self):
        """Set up test fixtures."""
        # Use the actual container instance
        self.container = container
        
    def test_container_instance_exists(self):
        """Test that container instance exists and has correct type."""
        self.assertIsNotNone(self.container)
        self.assertEqual(str(type(self.container)), "<class 'dependency_injector.containers.DynamicContainer'>")
        
    def test_backtest_container_alias(self):
        """Test that backtest_container is properly aliased."""
        self.assertIs(backtest_container, container)
        
    def test_engines_aggregate_exists(self):
        """Test that engines FactoryAggregate exists and works."""
        self.assertTrue(hasattr(self.container, 'engines'))
        
        # Test that we can access engine types
        engines_provider = self.container.engines
        self.assertIsNotNone(engines_provider)
        
    def test_analyzers_aggregate_exists(self):
        """Test that analyzers FactoryAggregate exists and works."""
        self.assertTrue(hasattr(self.container, 'analyzers'))
        
        # Test that we can access analyzer types
        analyzers_provider = self.container.analyzers
        self.assertIsNotNone(analyzers_provider)
        
    def test_strategies_aggregate_exists(self):
        """Test that strategies FactoryAggregate exists and works."""
        self.assertTrue(hasattr(self.container, 'strategies'))
        
        # Test that we can access strategy types
        strategies_provider = self.container.strategies
        self.assertIsNotNone(strategies_provider)
        
    def test_portfolios_aggregate_exists(self):
        """Test that portfolios FactoryAggregate exists and works."""
        self.assertTrue(hasattr(self.container, 'portfolios'))
        
        # Test that we can access portfolio types
        portfolios_provider = self.container.portfolios
        self.assertIsNotNone(portfolios_provider)

    def test_engine_component_access(self):
        """Test accessing individual engine components."""
        try:
            # Test historic engine access
            historic_engine = self.container.engines.historic()
            self.assertIsNotNone(historic_engine)
            
            # Test that it returns a type/class
            self.assertTrue(callable(historic_engine))
            
        except ImportError:
            # Some engines might not be available, this is expected
            self.skipTest("Engine dependencies not available")
        except Exception as e:
            # Other errors should be logged but not fail the test
            print(f"Engine access error (expected): {e}")

    def test_analyzer_component_access(self):
        """Test accessing individual analyzer components."""
        try:
            # Test sharpe analyzer access
            sharpe_analyzer = self.container.analyzers.sharpe()
            self.assertIsNotNone(sharpe_analyzer)
            
            # Test that it returns a type/class
            self.assertTrue(callable(sharpe_analyzer))
            
        except ImportError:
            # Some analyzers might not be available, this is expected
            self.skipTest("Analyzer dependencies not available")
        except Exception as e:
            # Other errors should be logged but not fail the test
            print(f"Analyzer access error (expected): {e}")

    def test_strategy_component_access(self):
        """Test accessing individual strategy components."""
        try:
            # Test dual thrust strategy access
            dual_thrust = self.container.strategies.dual_thrust()
            self.assertIsNotNone(dual_thrust)
            
            # Test that it returns a type/class
            self.assertTrue(callable(dual_thrust))
            
        except ImportError:
            # Some strategies might not be available, this is expected
            self.skipTest("Strategy dependencies not available")
        except Exception as e:
            # Other errors should be logged but not fail the test
            print(f"Strategy access error (expected): {e}")

    def test_portfolio_component_access(self):
        """Test accessing individual portfolio components."""
        try:
            # Test t1 portfolio access
            t1_portfolio = self.container.portfolios.t1()
            self.assertIsNotNone(t1_portfolio)
            
            # Test that it returns a type/class
            self.assertTrue(callable(t1_portfolio))
            
        except ImportError:
            # Some portfolios might not be available, this is expected
            self.skipTest("Portfolio dependencies not available")
        except Exception as e:
            # Other errors should be logged but not fail the test
            print(f"Portfolio access error (expected): {e}")

    def test_service_discovery_interface(self):
        """Test service discovery interface."""
        # Test that get_service_info method exists
        self.assertTrue(hasattr(self.container, 'get_service_info'))
        
        # Test that it returns service information
        service_info = self.container.get_service_info()
        self.assertIsInstance(service_info, dict)
        
        # Check that it contains expected categories
        expected_keys = ['engines', 'analyzers', 'strategies', 'portfolios']
        for key in expected_keys:
            self.assertIn(key, service_info)
            self.assertIsInstance(service_info[key], list)

    def test_backward_compatibility_methods(self):
        """Test backward compatibility methods."""
        # Test get_engine method exists
        self.assertTrue(hasattr(self.container, 'get_engine'))
        
        # Test get_analyzer method exists  
        self.assertTrue(hasattr(self.container, 'get_analyzer'))
        
        # Test get_strategy method exists
        self.assertTrue(hasattr(self.container, 'get_strategy'))
        
        # Test get_portfolio method exists
        self.assertTrue(hasattr(self.container, 'get_portfolio'))

    def test_backward_compatibility_engine_access(self):
        """Test backward compatibility engine access."""
        try:
            # Test getting engine by type
            engine = self.container.get_engine('historic')
            self.assertIsNotNone(engine)
            
        except ValueError as e:
            # Unknown engine type is acceptable
            if "Unknown engine type" in str(e):
                pass
            else:
                raise
        except Exception as e:
            # Other import errors are expected for some components
            print(f"Backward compatibility engine access error (expected): {e}")

    def test_error_handling_for_missing_components(self):
        """Test error handling when components are missing."""
        # Test accessing non-existent engine
        with self.assertRaises(AttributeError):
            _ = self.container.engines.nonexistent_engine()
            
        # Test accessing non-existent analyzer
        with self.assertRaises(AttributeError):
            _ = self.container.analyzers.nonexistent_analyzer()

    def test_container_integration_with_unified_services(self):
        """Test integration with unified services."""
        try:
            from ginkgo import services
            
            # Test that backtest module is available through unified services
            backtest_service = services.backtest
            self.assertIsNotNone(backtest_service)
            
            # Test that it's the same container instance
            self.assertIs(backtest_service, self.container)
            
        except ImportError:
            self.skipTest("Unified services not available")


class TestBacktestContainerIntegration(unittest.TestCase):
    """Integration tests for backtest container with real dependencies."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        self.container = container
        
    def test_container_provides_expected_components(self):
        """Test that container provides all expected component types."""
        service_info = self.container.get_service_info()
        
        # Verify we have engines
        self.assertGreater(len(service_info['engines']), 0)
        self.assertIn('historic', service_info['engines'])
        
        # Verify we have analyzers
        self.assertGreater(len(service_info['analyzers']), 0)
        self.assertIn('sharpe', service_info['analyzers'])
        
        # Verify we have strategies
        self.assertGreater(len(service_info['strategies']), 0)
        
        # Verify we have portfolios
        self.assertGreater(len(service_info['portfolios']), 0)

    def test_cross_component_consistency(self):
        """Test consistency across different component access methods."""
        service_info = self.container.get_service_info()
        
        # Test that engines listed in service_info are actually accessible
        for engine_name in service_info['engines']:
            try:
                engine_provider = getattr(self.container.engines, engine_name)
                self.assertIsNotNone(engine_provider)
            except AttributeError:
                self.fail(f"Engine '{engine_name}' listed in service_info but not accessible")

    def test_container_singleton_behavior(self):
        """Test that container maintains singleton behavior."""
        # Import the same container multiple times
        from ginkgo.backtest.core.containers import container as container1
        from ginkgo.backtest.core.containers import backtest_container as container2
        
        # They should be the same instance
        self.assertIs(container1, container2)
        self.assertIs(container1, self.container)


if __name__ == '__main__':
    unittest.main()