"""
Engine Assembly Service

This service handles the assembly and configuration of backtest engines,
replacing the direct function calls in engine_assembler_factory.py with
a proper service-oriented approach using dependency injection.
"""

from typing import Optional
import datetime

from ginkgo.libs import GLOG, GinkgoLogger, datetime_normalize
from ginkgo.enums import FILE_TYPES, EVENT_TYPES
from ginkgo.backtest.execution.engines import BaseEngine, HistoricEngine
from ginkgo.backtest.execution.engines.engine_assembler_factory import assembler_backtest_engine

# Import data services through dependency injection instead of direct container access
from ginkgo.data.services.base_service import BaseService, ServiceResult


class EngineAssemblyService(BaseService):
    """
    Service for assembling and configuring backtest engines.
    
    This service uses pure dependency injection and delegates the actual
    engine assembly to the factory while handling all data preparation.
    """
    
    def __init__(self, engine_service, portfolio_service, component_service, analyzer_record_crud=None):
        """
        Initialize the engine assembly service with required dependencies.
        
        Args:
            engine_service: Service for engine data operations
            portfolio_service: Service for portfolio data operations
            component_service: Service for component management operations
            analyzer_record_crud: CRUD service for analyzer record cleanup
        """
        super().__init__()
        self._engine_service = engine_service
        self._portfolio_service = portfolio_service
        self._component_service = component_service
        self._analyzer_record_crud = analyzer_record_crud
        self._logger = GLOG
    
    def initialize(self) -> bool:
        """Initialize the engine assembly service."""
        try:
            self._logger.INFO("EngineAssemblyService initialized")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to initialize EngineAssemblyService: {e}")
            return False
    
    def assemble_backtest_engine(self, engine_id: str, *args, **kwargs) -> ServiceResult:
        """
        Assemble a complete backtest engine with all components.
        
        This method prepares all necessary data and delegates the actual
        assembly to the factory function, following proper service architecture.
        
        Args:
            engine_id: UUID of the engine configuration
            
        Returns:
            ServiceResult containing the assembled engine or error information
        """
        self._logger.WARN(f"Preparing data for backtest engine assembly --> {engine_id}")
        
        try:
            # Prepare all data needed by the factory
            preparation_result = self._prepare_engine_data(engine_id)
            if not preparation_result.success:
                return preparation_result
                
            # Delegate to the factory for actual assembly
            engine = assembler_backtest_engine(
                engine_id=engine_id,
                engine_data=preparation_result.data["engine_data"],
                portfolio_mappings=preparation_result.data["portfolio_mappings"],
                portfolio_configs=preparation_result.data["portfolio_configs"],
                portfolio_components=preparation_result.data["portfolio_components"]
            )
            
            if engine is None:
                return ServiceResult(
                    success=False,
                    error=f"Factory failed to assemble engine {engine_id}"
                )
            
            # Clean up historic records after successful assembly
            self._cleanup_historic_records(engine_id, preparation_result.data["portfolio_configs"])
            
            self._logger.INFO(f"Engine {engine_id} assembly completed successfully")
            result = ServiceResult(success=True)
            result.data = engine
            return result
            
        except Exception as e:
            self._logger.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
            return ServiceResult(
                success=False,
                error=f"Engine assembly failed: {str(e)}"
            )
    
    def _prepare_engine_data(self, engine_id: str) -> ServiceResult:
        """Prepare all data needed for engine assembly."""
        try:
            # Get engine configuration
            engine_df = self._engine_service.get_engine(engine_id, as_dataframe=True)
            if engine_df.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No engine found for id: {engine_id}"
                )
            
            engine_data = engine_df.iloc[0].to_dict()
            
            # Get portfolio mappings
            portfolio_mappings = self._engine_service.get_engine_portfolio_mappings(engine_id=engine_id)
            if portfolio_mappings.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No portfolios found for engine {engine_id}"
                )
            
            # Convert DataFrame to list of dicts for easier processing
            portfolio_mapping_list = portfolio_mappings.to_dict('records')
            
            # Get portfolio configurations and components
            portfolio_configs = {}
            portfolio_components = {}
            
            for mapping in portfolio_mapping_list:
                portfolio_id = mapping["portfolio_id"]
                
                # Get portfolio configuration
                portfolio_df = self._portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
                if portfolio_df.shape[0] == 0:
                    self._logger.WARN(f"No portfolio found for id: {portfolio_id}")
                    continue
                    
                portfolio_configs[portfolio_id] = portfolio_df.iloc[0].to_dict()
                
                # Get portfolio components
                components = self._get_portfolio_components(portfolio_id)
                if components is None:
                    self._logger.WARN(f"Failed to get components for portfolio {portfolio_id}")
                    continue
                    
                portfolio_components[portfolio_id] = components
            
            result = ServiceResult(success=True)
            result.data = {
                "engine_data": engine_data,
                "portfolio_mappings": portfolio_mapping_list,
                "portfolio_configs": portfolio_configs,
                "portfolio_components": portfolio_components
            }
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=f"Failed to prepare engine data: {str(e)}"
            )
    
    def _get_portfolio_components(self, portfolio_id: str) -> Optional[dict]:
        """Get all components for a portfolio."""
        try:
            components = {}
            
            # Get strategies (required)
            strategies = self._component_service.get_strategies_by_portfolio(portfolio_id)
            components["strategies"] = strategies
            
            # Get selectors (required)
            selectors = self._component_service.get_selectors_by_portfolio(portfolio_id)
            components["selectors"] = selectors
            
            # Get sizers (required)
            sizers = self._component_service.get_sizers_by_portfolio(portfolio_id)
            components["sizers"] = sizers
            
            # Get risk managers (optional)
            risk_managers = self._component_service.get_risk_managers_by_portfolio(portfolio_id)
            components["risk_managers"] = risk_managers
            
            # Get analyzers (required)
            analyzers = self._component_service.get_analyzers_by_portfolio(portfolio_id)
            components["analyzers"] = analyzers
            
            return components
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get components for portfolio {portfolio_id}: {e}")
            return None
    
    def _cleanup_historic_records(self, engine_id: str, portfolio_configs: dict):
        """Clean up historic records for all portfolios in the engine."""
        if self._analyzer_record_crud is None:
            self._logger.WARN("No analyzer record CRUD provided, skipping record cleanup")
            return
            
        try:
            for portfolio_id in portfolio_configs.keys():
                self._logger.DEBUG(f"Cleaning historic records for portfolio {portfolio_id}")
                self._analyzer_record_crud.delete_filtered(portfolio_id=portfolio_id, engine_id=engine_id)
                
        except Exception as e:
            self._logger.WARN(f"Failed to clean historic records: {e}")
            # Non-critical error, continue execution
    
    def get_engine_by_id(self, engine_id: str) -> ServiceResult:
        """Get engine configuration by ID."""
        try:
            engine_df = self._engine_service.get_engine(engine_id, as_dataframe=True)
            if engine_df.shape[0] == 0:
                return ServiceResult(
                    success=False,
                    error=f"No engine found for id: {engine_id}"
                )
            
            result = ServiceResult(success=True)
            result.data = engine_df.iloc[0].to_dict()
            return result
            
        except Exception as e:
            return ServiceResult(
                success=False,
                error=f"Failed to get engine: {str(e)}"
            )
    
