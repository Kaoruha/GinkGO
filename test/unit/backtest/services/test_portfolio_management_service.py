"""
Unit tests for PortfolioManagementService

Tests the portfolio management service functionality including:
- Portfolio configuration management
- Component integration and binding
- Capital management operations
- Trading system configuration
- Performance analysis setup
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from ginkgo.backtest.services.portfolio_management_service import PortfolioManagementService
from ginkgo.enums import FILE_TYPES


class TestPortfolioManagementService(unittest.TestCase):
    """Test PortfolioManagementService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock component factory dependency
        self.mock_component_factory = Mock()
        
        # Create service instance
        self.service = PortfolioManagementService(
            component_factory=self.mock_component_factory
        )
        
        # Mock logger
        self.mock_logger = Mock()
        self.service._logger = self.mock_logger
        
        # Mock data services
        self.mock_portfolio_service = Mock()
        self.mock_capital_adjustment_service = Mock()
        self.service._portfolio_service = self.mock_portfolio_service
        self.service._capital_adjustment_service = self.mock_capital_adjustment_service

    def test_service_initialization(self):
        """Test service initialization."""
        service = PortfolioManagementService()
        
        self.assertIsNotNone(service)
        self.assertIsNone(service._component_factory)

    def test_initialize_success(self):
        """Test successful service initialization."""
        result = self.service.initialize()
        
        self.assertTrue(result)
        self.mock_logger.INFO.assert_called_with("PortfolioManagementService initialized")

    def test_initialize_failure(self):
        """Test service initialization failure."""
        # Mock logger to raise exception
        self.service._logger.INFO.side_effect = Exception("Test exception")
        
        result = self.service.initialize()
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called()


    def test_bind_components_to_portfolio_success(self):
        """Test successful component binding to portfolio."""
        mock_portfolio = Mock()
        portfolio_id = 'test-portfolio-id'
        
        # Mock strategies, analyzers, selectors, etc.
        mock_strategies = [Mock(), Mock()]
        mock_analyzers = [Mock()]
        mock_selectors = [Mock()]
        mock_sizers = [Mock()]
        mock_risk_managers = [Mock()]
        
        # Mock component factory methods
        self.mock_component_factory.create_strategies_by_portfolio.return_value = mock_strategies
        self.mock_component_factory.create_analyzers_by_portfolio.return_value = mock_analyzers
        self.mock_component_factory.create_selectors_by_portfolio.return_value = mock_selectors
        self.mock_component_factory.create_sizers_by_portfolio.return_value = mock_sizers
        self.mock_component_factory.create_risk_managers_by_portfolio.return_value = mock_risk_managers
        
        result = self.service.bind_components_to_portfolio(mock_portfolio, portfolio_id)
        
        self.assertTrue(result)
        
        # Verify component creation calls
        self.mock_component_factory.create_strategies_by_portfolio.assert_called_once_with(portfolio_id)
        self.mock_component_factory.create_analyzers_by_portfolio.assert_called_once_with(portfolio_id)
        self.mock_component_factory.create_selectors_by_portfolio.assert_called_once_with(portfolio_id)
        self.mock_component_factory.create_sizers_by_portfolio.assert_called_once_with(portfolio_id)
        self.mock_component_factory.create_risk_managers_by_portfolio.assert_called_once_with(portfolio_id)
        
        # Verify portfolio binding calls - using actual implementation methods
        # Verify strategies binding (2 strategies should be added individually)
        self.assertEqual(mock_portfolio.add_strategy.call_count, len(mock_strategies))
        for strategy in mock_strategies:
            mock_portfolio.add_strategy.assert_any_call(strategy)
        
        # Verify selectors binding (should use bind_selector for the first selector)
        mock_portfolio.bind_selector.assert_called_once_with(mock_selectors[0])
        
        # Verify sizers binding (should use bind_sizer for the first sizer) 
        mock_portfolio.bind_sizer.assert_called_once_with(mock_sizers[0])
        
        # Verify analyzers binding (should add each analyzer individually)
        self.assertEqual(mock_portfolio.add_analyzer.call_count, len(mock_analyzers))
        for analyzer in mock_analyzers:
            mock_portfolio.add_analyzer.assert_any_call(analyzer)
        
        # Verify risk managers binding (should add each risk manager individually)
        self.assertEqual(mock_portfolio.add_risk_manager.call_count, len(mock_risk_managers))
        for risk_manager in mock_risk_managers:
            mock_portfolio.add_risk_manager.assert_any_call(risk_manager)

    def test_bind_components_factory_not_initialized(self):
        """Test component binding when factory not initialized."""
        self.service._component_factory = None
        mock_portfolio = Mock()
        
        result = self.service.bind_components_to_portfolio(mock_portfolio, 'test-id')
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called_once()

    def test_bind_components_exception(self):
        """Test component binding with exception."""
        mock_portfolio = Mock()
        
        # Mock component factory to raise exception
        self.mock_component_factory.create_strategies_by_portfolio.side_effect = Exception("Component error")
        
        result = self.service.bind_components_to_portfolio(mock_portfolio, 'test-id')
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called()








if __name__ == '__main__':
    unittest.main()