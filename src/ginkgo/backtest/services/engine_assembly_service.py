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
from ginkgo.backtest.trading.matchmakings import MatchMakingSim
from ginkgo.backtest.execution.feeders import BacktestFeeder
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest

# Import data services through container
from ginkgo.data.containers import container


class EngineAssemblyService:
    """
    Service for assembling and configuring backtest engines.
    
    This service encapsulates the complex logic of creating, configuring,
    and binding various components to create a complete backtest engine.
    """
    
    def __init__(self, component_factory=None, portfolio_service=None):
        """
        Initialize the engine assembly service.
        
        Args:
            component_factory: Service for creating trading components
            portfolio_service: Service for portfolio management
        """
        self._component_factory = component_factory
        self._portfolio_service = portfolio_service
        self._logger = GLOG
        
        # Access data services through container
        self._engine_service = container.engine_service()
        self._portfolio_data_service = container.portfolio_service()
        self._component_service = container.component_service()
    
    def initialize(self) -> bool:
        """Initialize the engine assembly service."""
        try:
            self._logger.INFO("EngineAssemblyService initialized")
            return True
        except Exception as e:
            self._logger.ERROR(f"Failed to initialize EngineAssemblyService: {e}")
            return False
    
    def assemble_backtest_engine(self, engine_id: str, *args, **kwargs) -> Optional[BaseEngine]:
        """
        Assemble a complete backtest engine with all components.
        
        This method replaces the original assembler_backtest_engine function
        with proper dependency injection and service-oriented architecture.
        
        Args:
            engine_id: UUID of the engine configuration
            
        Returns:
            Configured backtest engine or None if assembly failed
        """
        self._logger.WARN(f"Assembling backtest engine --> {engine_id}")
        
        try:
            # Get engine configuration
            engine_data = self._get_engine_configuration(engine_id)
            if engine_data is None:
                return None
            
            # Create and configure the base engine
            engine = self._create_base_engine(engine_data, engine_id)
            if engine is None:
                return None
            
            # Set up matchmaking and data feeding
            self._setup_engine_infrastructure(engine)
            
            # Get and bind portfolios
            success = self._bind_portfolios_to_engine(engine, engine_id)
            if not success:
                return None
            
            self._logger.INFO("Engine assembly completed successfully")
            return engine
            
        except Exception as e:
            self._logger.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
            return None
    
    def _get_engine_configuration(self, engine_id: str) -> Optional[dict]:
        """Get engine configuration from data service."""
        try:
            engine_df = self._engine_service.get_engine(engine_id, as_dataframe=True)
            if engine_df.shape[0] == 0:
                self._logger.WARN(f"No engine found for id: {engine_id}")
                return None
            
            return engine_df.iloc[0].to_dict()
            
        except Exception as e:
            self._logger.ERROR(f"Failed to get engine configuration: {e}")
            return None
    
    def _create_base_engine(self, engine_data: dict, engine_id: str) -> Optional[HistoricEngine]:
        """Create and configure the base historic engine."""
        try:
            # Create logger for this specific engine
            now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
            logger = GinkgoLogger(
                logger_name="engine_logger",
                file_names=[f"bt_{engine_id}_{now}"],
                console_log=False
            )
            
            # Create engine instance
            engine = HistoricEngine(engine_data["name"])
            engine.engine_id = engine_id
            engine.add_logger(logger)
            
            self._logger.DEBUG(f"Created base engine: {engine_data['name']}")
            return engine
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create base engine: {e}")
            return None
    
    def _setup_engine_infrastructure(self, engine: HistoricEngine) -> bool:
        """Set up matchmaking and data feeding for the engine."""
        try:
            # Set up simulation matchmaking
            match = MatchMakingSim()
            engine.bind_matchmaking(match)
            engine.register(EVENT_TYPES.ORDERSUBMITTED, match.on_order_received)
            engine.register(EVENT_TYPES.PRICEUPDATE, match.on_price_received)
            
            # Set up data feeder
            feeder = BacktestFeeder("ExampleFeeder")
            # Use the logger service or create a new one
            logger = GinkgoLogger(
                logger_name="feeder_logger",
                file_names=[f"bt_feeder_{int(datetime.datetime.now().timestamp())}"],
                console_log=False
            )
            feeder.add_logger(logger)
            engine.bind_datafeeder(feeder)
            engine.register_time_hook(feeder.broadcast)
            
            self._logger.DEBUG("Engine infrastructure setup completed")
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to setup engine infrastructure: {e}")
            return False
    
    def _bind_portfolios_to_engine(self, engine: HistoricEngine, engine_id: str) -> bool:
        """Bind all portfolios associated with this engine."""
        try:
            # Get portfolio mappings for this engine
            portfolio_mappings = self._engine_service.get_engine_portfolio_mappings(engine_id=engine_id, as_dataframe=True)
            if portfolio_mappings.shape[0] == 0:
                self._logger.WARN(f"No portfolios found for engine {engine_id}")
                return False
            
            self._logger.DEBUG("Binding portfolios to engine")
            
            for _, mapping in portfolio_mappings.iterrows():
                portfolio_id = mapping["portfolio_id"]
                success = self._bind_single_portfolio(engine, engine_id, portfolio_id)
                if not success:
                    self._logger.WARN(f"Failed to bind portfolio {portfolio_id}")
                    continue
            
            # Start the engine after all portfolios are bound
            self._logger.INFO("Starting assembled engine")
            engine.start()
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolios to engine: {e}")
            return False
    
    def _bind_single_portfolio(self, engine: HistoricEngine, engine_id: str, portfolio_id: str) -> bool:
        """Bind a single portfolio to the engine with all its components."""
        try:
            # Get portfolio configuration
            portfolio_data = self._portfolio_data_service.get_portfolio(portfolio_id, as_dataframe=True)
            if portfolio_data.shape[0] == 0:
                self._logger.WARN(f"No portfolio found for id: {portfolio_id}")
                return False
            
            portfolio_config = portfolio_data.iloc[0]
            
            # Update engine date range based on portfolio
            self._update_engine_date_range(engine, portfolio_config)
            
            # Create portfolio instance - use the engine's logger service
            logger = GinkgoLogger(
                logger_name="portfolio_logger",
                file_names=[f"bt_portfolio_{portfolio_id}_{int(datetime.datetime.now().timestamp())}"],
                console_log=False
            )
            portfolio = self._create_portfolio_instance(portfolio_config, logger)
            if portfolio is None:
                return False
            
            # Bind components to portfolio - use the same logger
            success = self._bind_components_to_portfolio(portfolio, portfolio_id, logger)
            if not success:
                return False
            
            # Bind portfolio to engine and register events
            self._bind_portfolio_to_engine(engine, portfolio, portfolio_id, engine_id)
            
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolio {portfolio_id}: {e}")
            return False
    
    def _update_engine_date_range(self, engine: HistoricEngine, portfolio_config: dict):
        """Update engine date range to encompass all portfolios."""
        date_start = datetime_normalize(portfolio_config["backtest_start_date"])
        date_end = datetime_normalize(portfolio_config["backtest_end_date"])
        
        if engine.start_date is None or engine.start_date > date_start:
            engine.start_date = date_start
        if engine.end_date is None or engine.end_date < date_end:
            engine.end_date = date_end
    
    def _create_portfolio_instance(self, portfolio_config: dict, logger) -> Optional[PortfolioT1Backtest]:
        """Create a portfolio instance with proper configuration."""
        try:
            portfolio = PortfolioT1Backtest()
            portfolio.add_logger(logger)
            portfolio.set_portfolio_name(portfolio_config["name"])
            portfolio.set_portfolio_id(portfolio_config["uuid"])
            
            return portfolio
            
        except Exception as e:
            self._logger.ERROR(f"Failed to create portfolio instance: {e}")
            return None
    
    def _bind_components_to_portfolio(self, portfolio: PortfolioT1Backtest, portfolio_id: str, logger) -> bool:
        """Bind all trading components to the portfolio."""
        try:
            # Use component service from data container to get components
            
            # Add strategies
            strategies = self._component_service.get_strategies_by_portfolio(portfolio_id)
            if len(strategies) == 0:
                self._logger.CRITICAL(f"No strategy found for portfolio {portfolio_id}")
                return False
                
            for strategy in strategies:
                strategy.add_logger(logger)
                portfolio.add_strategy(strategy)
            
            # Add selector (required)
            selectors = self._component_service.get_selectors_by_portfolio(portfolio_id)
            if len(selectors) == 0:
                self._logger.ERROR(f"No selector found for portfolio {portfolio_id}")
                return False
            selector = selectors[0]
            portfolio.bind_selector(selector)
            
            # Add sizer (required)
            sizers = self._component_service.get_sizers_by_portfolio(portfolio_id)
            if len(sizers) == 0:
                self._logger.ERROR(f"No sizer found for portfolio {portfolio_id}")
                return False
            sizer = sizers[0]
            sizer.add_logger(logger)
            portfolio.bind_sizer(sizer)
            
            # Add risk managers (optional)
            risk_managers = self._component_service.get_risk_managers_by_portfolio(portfolio_id)
            if len(risk_managers) == 0:
                self._logger.WARN(f"No risk manager found for portfolio {portfolio_id}. Backtest will go on without risk control.")
            else:
                for risk_manager in risk_managers:
                    risk_manager.add_logger(logger)
                    portfolio.add_risk_manager(risk_manager)
            
            # Add analyzers (required)
            analyzers = self._component_service.get_analyzers_by_portfolio(portfolio_id)
            if len(analyzers) == 0:
                self._logger.ERROR(f"No analyzer found for portfolio {portfolio_id}")
                return False
            for analyzer in analyzers:
                analyzer.add_logger(logger)
                portfolio.add_analyzer(analyzer)
            
            return True
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind components to portfolio: {e}")
            return False
    
    def _bind_portfolio_to_engine(self, engine: HistoricEngine, portfolio: PortfolioT1Backtest, 
                                portfolio_id: str, engine_id: str):
        """Bind the configured portfolio to the engine and register events."""
        try:
            # Bind portfolio to engine
            engine.bind_portfolio(portfolio)
            
            # Register portfolio event handlers
            engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_received)
            engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
            engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)
            engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
            
            # Register portfolio with feeder
            engine._datafeeder.add_subscriber(portfolio)
            
            # Clean up historic records for this portfolio
            self._cleanup_historic_records(portfolio_id, engine_id)
            
            self._logger.DEBUG(f"Portfolio {portfolio_id} bound to engine successfully")
            
        except Exception as e:
            self._logger.ERROR(f"Failed to bind portfolio to engine: {e}")
            raise
    
    def _cleanup_historic_records(self, portfolio_id: str, engine_id: str):
        """Clean up historic records for fresh backtest run."""
        try:
            # Use CRUD operations through container
            analyzer_crud = container.cruds.analyzer_record()
            analyzer_crud.delete_filtered(portfolio_id=portfolio_id, engine_id=engine_id)
            
            self._logger.DEBUG(f"Cleaned historic records for portfolio {portfolio_id}")
            
        except Exception as e:
            self._logger.WARN(f"Failed to clean historic records: {e}")
            # Non-critical error, continue execution