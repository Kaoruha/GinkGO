"""
Unit tests for ComponentFactoryService

Tests the component factory service functionality including:
- Service initialization and base class mapping
- Component creation from file configuration
- Component validation
- Different component types support
- Error handling for component creation
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from typing import Any, Dict, List

from ginkgo.backtest.services.component_factory_service import ComponentFactoryService
from ginkgo.enums import FILE_TYPES


class TestComponentFactoryService(unittest.TestCase):
    """Test ComponentFactoryService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.service = ComponentFactoryService()
        
        # Mock logger
        self.mock_logger = Mock()
        self.service._logger = self.mock_logger
        
        # Mock component service
        self.mock_component_service = Mock()
        self.service._component_service = self.mock_component_service

    def test_service_initialization(self):
        """Test service initialization."""
        service = ComponentFactoryService()
        
        self.assertIsNotNone(service)
        self.assertIsNone(service._component_service)
        self.assertEqual(service._base_class_mapping, {})

    @patch('ginkgo.backtest.services.component_factory_service.container')
    def test_initialize_success(self, mock_container):
        """Test successful service initialization."""
        # Mock container and component service
        mock_component_service = Mock()
        mock_container.component_service.return_value = mock_component_service
        
        # Mock base class imports
        with patch.object(self.service, '_initialize_base_class_mapping'):
            result = self.service.initialize()
            
            self.assertTrue(result)
            self.assertEqual(self.service._component_service, mock_component_service)
            self.mock_logger.INFO.assert_called_with("ComponentFactoryService initialized")

    @patch('ginkgo.backtest.services.component_factory_service.container')
    def test_initialize_failure(self, mock_container):
        """Test service initialization failure."""
        # Mock container to raise exception
        mock_container.component_service.side_effect = Exception("Container error")
        
        result = self.service.initialize()
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called()

    def test_initialize_base_class_mapping(self):
        """Test base class mapping initialization."""
        # Mock the imports with correct module paths
        mock_base_strategy = Mock()
        mock_base_analyzer = Mock()
        mock_base_selector = Mock()
        mock_base_sizer = Mock()
        mock_base_risk = Mock()
        
        with patch.dict('sys.modules', {
            'ginkgo.backtest.strategy.strategies': Mock(StrategyBase=mock_base_strategy),
            'ginkgo.backtest.analysis.analyzers': Mock(BaseAnalyzer=mock_base_analyzer),
            'ginkgo.backtest.strategy.selectors': Mock(BaseSelector=mock_base_selector),
            'ginkgo.backtest.strategy.sizers': Mock(BaseSizer=mock_base_sizer),
            'ginkgo.backtest.strategy.risk_managements': Mock(BaseRiskManagement=mock_base_risk)
        }):
            self.service._initialize_base_class_mapping()
            
            expected_mapping = {
                FILE_TYPES.STRATEGY: mock_base_strategy,
                FILE_TYPES.ANALYZER: mock_base_analyzer,
                FILE_TYPES.SELECTOR: mock_base_selector,
                FILE_TYPES.SIZER: mock_base_sizer,
                FILE_TYPES.RISKMANAGER: mock_base_risk
            }
            
            self.assertEqual(self.service._base_class_mapping, expected_mapping)


    def test_create_component_success(self):
        """Test successful component creation."""
        # Mock component service
        mock_component = Mock()
        self.mock_component_service.get_instance_by_file.return_value = mock_component
        
        result = self.service.create_component(
            file_id="test-file-id",
            mapping_id="test-mapping-id",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertEqual(result, mock_component)
        self.mock_component_service.get_instance_by_file.assert_called_once_with(
            file_id="test-file-id",
            mapping_id="test-mapping-id",
            file_type=FILE_TYPES.STRATEGY
        )

    def test_create_component_service_not_initialized(self):
        """Test component creation when service not initialized."""
        self.service._component_service = None
        
        result = self.service.create_component(
            file_id="test-file-id",
            mapping_id="test-mapping-id",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertIsNone(result)
        self.mock_logger.ERROR.assert_called_with("ComponentFactoryService not initialized")

    def test_create_component_creation_failed(self):
        """Test component creation when creation fails."""
        # Mock component service to return None
        self.mock_component_service.get_instance_by_file.return_value = None
        
        result = self.service.create_component(
            file_id="test-file-id",
            mapping_id="test-mapping-id",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertIsNone(result)
        self.mock_logger.ERROR.assert_called()

    def test_create_component_exception(self):
        """Test component creation with exception."""
        # Mock component service to raise exception
        self.mock_component_service.get_instance_by_file.side_effect = Exception("Creation error")
        
        result = self.service.create_component(
            file_id="test-file-id",
            mapping_id="test-mapping-id",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertIsNone(result)
        self.mock_logger.ERROR.assert_called()

    def test_create_components_by_portfolio_success(self):
        """Test successful components creation by portfolio."""
        # Mock component list
        mock_components = [Mock(), Mock(), Mock()]
        self.mock_component_service.get_trading_system_components_by_portfolio.return_value = mock_components
        
        result = self.service.create_components_by_portfolio(
            portfolio_id="test-portfolio-id",
            file_type=FILE_TYPES.ANALYZER
        )
        
        self.assertEqual(result, mock_components)
        self.assertEqual(len(result), 3)

    def test_create_components_by_portfolio_service_not_initialized(self):
        """Test components creation when service not initialized."""
        self.service._component_service = None
        
        result = self.service.create_components_by_portfolio(
            portfolio_id="test-portfolio-id",
            file_type=FILE_TYPES.ANALYZER
        )
        
        self.assertEqual(result, [])
        self.mock_logger.ERROR.assert_called()

    def test_create_components_by_portfolio_exception(self):
        """Test components creation with exception."""
        # Mock service to raise exception
        self.mock_component_service.get_trading_system_components_by_portfolio.side_effect = Exception("Portfolio error")
        
        result = self.service.create_components_by_portfolio(
            portfolio_id="test-portfolio-id",
            file_type=FILE_TYPES.ANALYZER
        )
        
        self.assertEqual(result, [])
        self.mock_logger.ERROR.assert_called()

    def test_validate_component_code_success(self):
        """Test successful component code validation."""
        # Mock validation result
        validation_result = {"success": True, "errors": []}
        self.mock_component_service.validate_component_code.return_value = validation_result
        
        result = self.service.validate_component_code(
            code="class TestStrategy(BaseStrategy): pass",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertEqual(result, validation_result)

    def test_validate_component_code_service_not_initialized(self):
        """Test code validation when service not initialized."""
        self.service._component_service = None
        
        result = self.service.validate_component_code(
            code="test code",
            file_type=FILE_TYPES.STRATEGY
        )
        
        expected = {"success": False, "error": "Service not initialized"}
        self.assertEqual(result, expected)

    def test_validate_component_code_exception(self):
        """Test code validation with exception."""
        # Mock service to raise exception
        self.mock_component_service.validate_component_code.side_effect = Exception("Validation error")
        
        result = self.service.validate_component_code(
            code="test code",
            file_type=FILE_TYPES.STRATEGY
        )
        
        self.assertIn("success", result)
        self.assertFalse(result["success"])
        self.assertIn("error", result)

    def test_get_component_requirements_success(self):
        """Test getting component requirements."""
        # Set up base class mapping
        mock_base_class = Mock()
        mock_base_class.__name__ = "BaseStrategy"
        mock_base_class.__module__ = "ginkgo.backtest.strategies.base_strategy"
        mock_base_class.__abstractmethods__ = {"cal", "on_market_data"}
        
        self.service._base_class_mapping = {FILE_TYPES.STRATEGY: mock_base_class}
        
        with patch('ginkgo.backtest.services.component_factory_service.inspect') as mock_inspect:
            # Mock inspect.signature
            mock_signature = Mock()
            mock_signature.__str__ = Mock(return_value="(self, name: str = 'default')")
            mock_inspect.signature.return_value = mock_signature
            
            result = self.service.get_component_requirements(FILE_TYPES.STRATEGY)
            
            self.assertIn("base_class", result)
            self.assertIn("required_methods", result)
            self.assertIn("available_methods", result)
            self.assertEqual(result["base_class"], "BaseStrategy")

    def test_get_component_requirements_unsupported_type(self):
        """Test getting requirements for unsupported component type."""
        result = self.service.get_component_requirements(FILE_TYPES.STRATEGY)
        
        self.assertIn("error", result)

    def test_get_component_requirements_exception(self):
        """Test getting requirements with exception."""
        # Set up base class mapping with problematic mock
        mock_base_class = Mock()
        mock_base_class.__name__ = "BaseStrategy"
        mock_base_class.__module__ = "test.module"
        mock_base_class.__abstractmethods__ = set()
        
        self.service._base_class_mapping = {FILE_TYPES.STRATEGY: mock_base_class}
        
        with patch('ginkgo.backtest.services.component_factory_service.inspect.signature',
                   side_effect=Exception("Signature error")):
            
            result = self.service.get_component_requirements(FILE_TYPES.STRATEGY)
            
            self.assertIn("error", result)

    def test_create_strategies_by_portfolio(self):
        """Test creating strategies by portfolio."""
        mock_strategies = [Mock(), Mock()]
        
        with patch.object(self.service, 'create_components_by_portfolio', 
                         return_value=mock_strategies) as mock_create:
            
            result = self.service.create_strategies_by_portfolio("test-portfolio-id")
            
            self.assertEqual(result, mock_strategies)
            mock_create.assert_called_once_with("test-portfolio-id", FILE_TYPES.STRATEGY)

    def test_create_analyzers_by_portfolio(self):
        """Test creating analyzers by portfolio."""
        mock_analyzers = [Mock(), Mock(), Mock()]
        
        with patch.object(self.service, 'create_components_by_portfolio', 
                         return_value=mock_analyzers) as mock_create:
            
            result = self.service.create_analyzers_by_portfolio("test-portfolio-id")
            
            self.assertEqual(result, mock_analyzers)
            mock_create.assert_called_once_with("test-portfolio-id", FILE_TYPES.ANALYZER)

    def test_create_selectors_by_portfolio(self):
        """Test creating selectors by portfolio."""
        mock_selectors = [Mock()]
        
        with patch.object(self.service, 'create_components_by_portfolio', 
                         return_value=mock_selectors) as mock_create:
            
            result = self.service.create_selectors_by_portfolio("test-portfolio-id")
            
            self.assertEqual(result, mock_selectors)
            mock_create.assert_called_once_with("test-portfolio-id", FILE_TYPES.SELECTOR)

    def test_create_sizers_by_portfolio(self):
        """Test creating sizers by portfolio."""
        mock_sizers = [Mock()]
        
        with patch.object(self.service, 'create_components_by_portfolio', 
                         return_value=mock_sizers) as mock_create:
            
            result = self.service.create_sizers_by_portfolio("test-portfolio-id")
            
            self.assertEqual(result, mock_sizers)
            mock_create.assert_called_once_with("test-portfolio-id", FILE_TYPES.SIZER)

    def test_create_risk_managers_by_portfolio(self):
        """Test creating risk managers by portfolio."""
        mock_risk_managers = [Mock(), Mock()]
        
        with patch.object(self.service, 'create_components_by_portfolio', 
                         return_value=mock_risk_managers) as mock_create:
            
            result = self.service.create_risk_managers_by_portfolio("test-portfolio-id")
            
            self.assertEqual(result, mock_risk_managers)
            mock_create.assert_called_once_with("test-portfolio-id", FILE_TYPES.RISKMANAGER)

    def test_get_supported_component_types(self):
        """Test getting supported component types."""
        # Set up base class mapping
        self.service._base_class_mapping = {
            FILE_TYPES.STRATEGY: Mock(),
            FILE_TYPES.ANALYZER: Mock(),
            FILE_TYPES.SELECTOR: Mock()
        }
        
        result = self.service.get_supported_component_types()
        
        expected_types = [
            FILE_TYPES.STRATEGY.value,
            FILE_TYPES.ANALYZER.value,
            FILE_TYPES.SELECTOR.value
        ]
        
        self.assertEqual(sorted(result), sorted(expected_types))


if __name__ == '__main__':
    unittest.main()