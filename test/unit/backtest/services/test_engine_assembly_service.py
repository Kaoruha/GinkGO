"""
Unit tests for EngineAssemblyService

Tests the engine assembly service functionality including:
- Engine configuration retrieval
- Base engine creation and configuration  
- Infrastructure setup (matchmaking, data feeding)
- Portfolio binding and component integration
- Error handling and cleanup
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import pandas as pd

from ginkgo.backtest.services.engine_assembly_service import EngineAssemblyService
from ginkgo.backtest.execution.engines import HistoricEngine


class TestEngineAssemblyService(unittest.TestCase):
    """Test EngineAssemblyService functionality."""

    def setUp(self):
        """Set up test fixtures."""
        # Mock dependencies
        self.mock_component_factory = Mock()
        self.mock_portfolio_service = Mock()
        
        # Create service instance
        self.service = EngineAssemblyService(
            component_factory=self.mock_component_factory,
            portfolio_service=self.mock_portfolio_service
        )
        
        # Mock logger
        self.mock_logger = Mock()
        self.service._logger = self.mock_logger
        
        # Mock data services
        self.mock_engine_service = Mock()
        self.mock_portfolio_data_service = Mock()
        self.service._engine_service = self.mock_engine_service
        self.service._portfolio_data_service = self.mock_portfolio_data_service

    def test_service_initialization(self):
        """Test service initialization."""
        service = EngineAssemblyService()
        
        self.assertIsNotNone(service)
        self.assertIsNone(service._component_factory)
        self.assertIsNone(service._portfolio_service)

    def test_initialize_success(self):
        """Test successful service initialization."""
        result = self.service.initialize()
        
        self.assertTrue(result)
        self.mock_logger.INFO.assert_called_with("EngineAssemblyService initialized")

    def test_initialize_failure(self):
        """Test service initialization failure."""
        # Mock logger to raise exception
        self.service._logger.INFO.side_effect = Exception("Test exception")
        
        result = self.service.initialize()
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called()

    @patch('ginkgo.backtest.services.engine_assembly_service.datetime')
    @patch('ginkgo.backtest.services.engine_assembly_service.GinkgoLogger')
    def test_get_engine_configuration_success(self, mock_logger_class, mock_datetime):
        """Test successful engine configuration retrieval."""
        # Mock engine data
        engine_data = pd.DataFrame([{
            'uuid': 'test-engine-id',
            'name': 'Test Engine',
            'desc': 'Test Description'
        }])
        
        self.mock_engine_service.get_engine.return_value = engine_data
        
        result = self.service._get_engine_configuration('test-engine-id')
        
        self.assertIsNotNone(result)
        self.assertEqual(result['uuid'], 'test-engine-id')
        self.assertEqual(result['name'], 'Test Engine')

    def test_get_engine_configuration_not_found(self):
        """Test engine configuration not found."""
        # Mock empty result
        empty_df = pd.DataFrame()
        self.mock_engine_service.get_engine.return_value = empty_df
        
        result = self.service._get_engine_configuration('nonexistent-id')
        
        self.assertIsNone(result)
        self.mock_logger.WARN.assert_called()

    def test_get_engine_configuration_exception(self):
        """Test engine configuration retrieval with exception."""
        # Mock exception
        self.mock_engine_service.get_engine.side_effect = Exception("Database error")
        
        result = self.service._get_engine_configuration('test-id')
        
        self.assertIsNone(result)
        self.mock_logger.ERROR.assert_called()

    @patch('ginkgo.backtest.services.engine_assembly_service.datetime')
    @patch('ginkgo.backtest.services.engine_assembly_service.GinkgoLogger')
    @patch('ginkgo.backtest.services.engine_assembly_service.HistoricEngine')
    def test_create_base_engine_success(self, mock_engine_class, mock_logger_class, mock_datetime):
        """Test successful base engine creation."""
        # Mock datetime
        mock_datetime.datetime.now.return_value.strftime.return_value = "20240101120000"
        
        # Mock engine data
        engine_data = {
            'name': 'Test Engine',
            'uuid': 'test-engine-id'
        }
        
        # Mock logger instance
        mock_logger_instance = Mock()
        mock_logger_class.return_value = mock_logger_instance
        
        # Mock engine instance
        mock_engine_instance = Mock()
        mock_engine_class.return_value = mock_engine_instance
        
        result = self.service._create_base_engine(engine_data, 'test-engine-id')
        
        self.assertIsNotNone(result)
        mock_engine_class.assert_called_once_with('Test Engine')
        mock_engine_instance.add_logger.assert_called_once_with(mock_logger_instance)

    @patch('ginkgo.backtest.services.engine_assembly_service.datetime')
    @patch('ginkgo.backtest.services.engine_assembly_service.GinkgoLogger')
    def test_create_base_engine_exception(self, mock_logger_class, mock_datetime):
        """Test base engine creation with exception."""
        # Mock logger class to raise exception
        mock_logger_class.side_effect = Exception("Logger creation failed")
        
        engine_data = {'name': 'Test Engine'}
        
        result = self.service._create_base_engine(engine_data, 'test-id')
        
        self.assertIsNone(result)
        self.mock_logger.ERROR.assert_called()

    @patch('ginkgo.backtest.services.engine_assembly_service.MatchMakingSim')
    @patch('ginkgo.backtest.services.engine_assembly_service.BacktestFeeder')
    def test_setup_engine_infrastructure_success(self, mock_feeder_class, mock_match_class):
        """Test successful engine infrastructure setup."""
        # Mock engine
        mock_engine = Mock()
        mock_engine._loggers = [Mock()]
        
        # Mock instances
        mock_match_instance = Mock()
        mock_feeder_instance = Mock()
        mock_match_class.return_value = mock_match_instance
        mock_feeder_class.return_value = mock_feeder_instance
        
        result = self.service._setup_engine_infrastructure(mock_engine)
        
        self.assertTrue(result)
        mock_engine.bind_matchmaking.assert_called_once_with(mock_match_instance)
        mock_engine.bind_datafeeder.assert_called_once_with(mock_feeder_instance)

    def test_setup_engine_infrastructure_exception(self):
        """Test engine infrastructure setup with exception."""
        # Mock engine to raise exception
        mock_engine = Mock()
        mock_engine.bind_matchmaking.side_effect = Exception("Infrastructure setup failed")
        
        result = self.service._setup_engine_infrastructure(mock_engine)
        
        self.assertFalse(result)
        self.mock_logger.ERROR.assert_called()

    def test_bind_portfolios_no_mappings(self):
        """Test portfolio binding with no mappings found."""
        mock_engine = Mock()
        empty_df = pd.DataFrame()
        
        self.mock_engine_service.get_engine_portfolio_mappings.return_value = empty_df
        
        result = self.service._bind_portfolios_to_engine(mock_engine, 'test-engine-id')
        
        self.assertFalse(result)
        self.mock_logger.WARN.assert_called()

    def test_bind_portfolios_success(self):
        """Test successful portfolio binding."""
        mock_engine = Mock()
        mock_engine.start_date = None
        mock_engine.end_date = None
        
        # Mock portfolio mappings
        portfolio_mappings = pd.DataFrame([{
            'portfolio_id': 'test-portfolio-id',
            'engine_id': 'test-engine-id'
        }])
        
        self.mock_engine_service.get_engine_portfolio_mappings.return_value = portfolio_mappings
        
        # Mock bind_single_portfolio to return True
        with patch.object(self.service, '_bind_single_portfolio', return_value=True):
            result = self.service._bind_portfolios_to_engine(mock_engine, 'test-engine-id')
            
            self.assertTrue(result)
            mock_engine.start.assert_called_once()

    def test_bind_single_portfolio_not_found(self):
        """Test binding single portfolio when portfolio not found."""
        mock_engine = Mock()
        empty_df = pd.DataFrame()
        
        self.mock_portfolio_data_service.get_portfolio.return_value = empty_df
        
        result = self.service._bind_single_portfolio(mock_engine, 'engine-id', 'portfolio-id')
        
        self.assertFalse(result)
        self.mock_logger.WARN.assert_called()

    def test_update_engine_date_range(self):
        """Test engine date range update."""
        mock_engine = Mock()
        mock_engine.start_date = None
        mock_engine.end_date = None
        
        portfolio_config = {
            'backtest_start_date': '20240101',
            'backtest_end_date': '20241231'
        }
        
        with patch('ginkgo.backtest.services.engine_assembly_service.datetime_normalize') as mock_normalize:
            start_date = datetime(2024, 1, 1)
            end_date = datetime(2024, 12, 31)
            mock_normalize.side_effect = [start_date, end_date]
            
            self.service._update_engine_date_range(mock_engine, portfolio_config)
            
            self.assertEqual(mock_engine.start_date, start_date)
            self.assertEqual(mock_engine.end_date, end_date)

    @patch('ginkgo.backtest.services.engine_assembly_service.PortfolioT1Backtest')
    def test_create_portfolio_instance_success(self, mock_portfolio_class):
        """Test successful portfolio instance creation."""
        mock_logger = Mock()
        portfolio_config = {
            'name': 'Test Portfolio',
            'uuid': 'test-portfolio-id'
        }
        
        mock_portfolio_instance = Mock()
        mock_portfolio_class.return_value = mock_portfolio_instance
        
        result = self.service._create_portfolio_instance(portfolio_config, mock_logger)
        
        self.assertIsNotNone(result)
        mock_portfolio_instance.add_logger.assert_called_once_with(mock_logger)
        mock_portfolio_instance.set_portfolio_name.assert_called_once_with('Test Portfolio')
        mock_portfolio_instance.set_portfolio_id.assert_called_once_with('test-portfolio-id')

    def test_create_portfolio_instance_exception(self):
        """Test portfolio instance creation with exception."""
        with patch('ginkgo.backtest.services.engine_assembly_service.PortfolioT1Backtest', 
                   side_effect=Exception("Portfolio creation failed")):
            
            portfolio_config = {'name': 'Test Portfolio', 'uuid': 'test-id'}
            
            result = self.service._create_portfolio_instance(portfolio_config, Mock())
            
            self.assertIsNone(result)
            self.mock_logger.ERROR.assert_called()

    @patch('ginkgo.backtest.services.engine_assembly_service.container')
    def test_cleanup_historic_records_success(self, mock_container):
        """Test successful historic records cleanup."""
        mock_analyzer_crud = Mock()
        mock_container.cruds.analyzer_record.return_value = mock_analyzer_crud
        
        self.service._cleanup_historic_records('portfolio-id', 'engine-id')
        
        mock_analyzer_crud.delete_filtered.assert_called_once_with(
            portfolio_id='portfolio-id', 
            engine_id='engine-id'
        )

    @patch('ginkgo.backtest.services.engine_assembly_service.container')
    def test_cleanup_historic_records_exception(self, mock_container):
        """Test historic records cleanup with exception."""
        mock_container.cruds.analyzer_record.side_effect = Exception("Cleanup failed")
        
        # Should not raise exception, just log warning
        self.service._cleanup_historic_records('portfolio-id', 'engine-id')
        
        self.mock_logger.WARN.assert_called()


    def test_assemble_backtest_engine_exception(self):
        """Test engine assembly with exception handling."""
        # Mock get_engine_configuration to raise exception
        with patch.object(self.service, '_get_engine_configuration', 
                         side_effect=Exception("Configuration error")):
            
            result = self.service.assemble_backtest_engine('test-engine-id')
            
            self.assertIsNone(result)
            self.mock_logger.ERROR.assert_called()


if __name__ == '__main__':
    unittest.main()