import datetime
from typing import Optional, Dict, Any, List

from ginkgo.enums import FILE_TYPES, EVENT_TYPES, ENGINESTATUS_TYPES
from ginkgo.backtest.trading.matchmakings import MatchMakingSim, MatchMakingLive
from ginkgo.backtest.execution.feeders import BacktestFeeder
from ginkgo.backtest.execution.engines import BaseEngine, HistoricEngine
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
from ginkgo.libs import GinkgoLogger
from ginkgo.libs import GLOG, datetime_normalize


def assembler_backtest_engine(
    engine_id: str, 
    engine_data: Dict[str, Any],
    portfolio_mappings: List[Dict[str, Any]],
    portfolio_configs: Dict[str, Dict[str, Any]],
    portfolio_components: Dict[str, Dict[str, Any]],
    logger: Optional[GinkgoLogger] = None
) -> Optional[BaseEngine]:
    """
    Assemble a backtest engine using pure dependency injection.
    
    This factory function focuses solely on engine assembly logic,
    receiving all necessary data through parameters rather than
    fetching data internally. Business logic should be handled by services.
    
    Args:
        engine_id: UUID of the engine
        engine_data: Engine configuration data
        portfolio_mappings: List of portfolio mappings for this engine
        portfolio_configs: Dict mapping portfolio_id to portfolio config
        portfolio_components: Dict mapping portfolio_id to its components
        logger: Optional logger instance
        
    Returns:
        Assembled engine instance or None if assembly failed
    """
    if logger is None:
        now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        logger = GinkgoLogger(
            logger_name="engine_logger", 
            file_names=[f"bt_{engine_id}_{now}"], 
            console_log=False
        )
    
    GLOG.WARN(f"Assembling backtest engine --> {engine_id}")
    
    try:
        # Create base engine
        engine = _create_base_engine(engine_data, engine_id, logger)
        if engine is None:
            return None
            
        # Setup engine infrastructure (matchmaking, feeder)
        _setup_engine_infrastructure(engine, logger)
        
        # Process all portfolios
        for portfolio_mapping in portfolio_mappings:
            portfolio_id = portfolio_mapping["portfolio_id"]
            
            if portfolio_id not in portfolio_configs:
                GLOG.WARN(f"No configuration found for portfolio {portfolio_id}")
                continue
                
            if portfolio_id not in portfolio_components:
                GLOG.WARN(f"No components found for portfolio {portfolio_id}")
                continue
            
            success = _bind_portfolio_to_engine(
                engine=engine,
                portfolio_config=portfolio_configs[portfolio_id],
                components=portfolio_components[portfolio_id],
                logger=logger
            )
            
            if not success:
                GLOG.ERROR(f"Failed to bind portfolio {portfolio_id} to engine")
                continue
        
        # Start the engine
        GLOG.INFO("Starting assembled engine")
        engine.start()
        return engine
        
    except Exception as e:
        GLOG.ERROR(f"Failed to assemble backtest engine {engine_id}: {e}")
        return None


def _create_base_engine(engine_data: Dict[str, Any], engine_id: str, logger: GinkgoLogger) -> Optional[HistoricEngine]:
    """Create and configure the base historic engine."""
    try:
        engine = HistoricEngine(engine_data["name"])
        engine.engine_id = engine_id
        engine.add_logger(logger)
        
        GLOG.DEBUG(f"Created base engine: {engine_data['name']}")
        return engine
        
    except Exception as e:
        GLOG.ERROR(f"Failed to create base engine: {e}")
        return None


def _setup_engine_infrastructure(engine: HistoricEngine, logger: GinkgoLogger) -> bool:
    """Set up matchmaking and data feeding for the engine."""
    try:
        # Set up simulation matchmaking
        match = MatchMakingSim()
        engine.bind_matchmaking(match)
        engine.register(EVENT_TYPES.ORDERSUBMITTED, match.on_order_received)
        engine.register(EVENT_TYPES.PRICEUPDATE, match.on_price_received)
        
        # Set up data feeder
        feeder = BacktestFeeder("ExampleFeeder")
        feeder.add_logger(logger)
        engine.bind_datafeeder(feeder)
        engine.register_time_hook(feeder.broadcast)
        
        GLOG.DEBUG("Engine infrastructure setup completed")
        return True
        
    except Exception as e:
        GLOG.ERROR(f"Failed to setup engine infrastructure: {e}")
        return False


def _bind_portfolio_to_engine(
    engine: HistoricEngine, 
    portfolio_config: Dict[str, Any],
    components: Dict[str, Any],
    logger: GinkgoLogger
) -> bool:
    """Bind a single portfolio to the engine with all its components."""
    try:
        portfolio_id = portfolio_config["uuid"]
        
        # Update engine date range based on portfolio
        _update_engine_date_range(engine, portfolio_config)
        
        # Create portfolio instance
        portfolio = _create_portfolio_instance(portfolio_config, logger)
        if portfolio is None:
            return False
        
        # Bind components to portfolio
        success = _bind_components_to_portfolio(portfolio, components, logger)
        if not success:
            return False
        
        # Bind portfolio to engine and register events
        _register_portfolio_with_engine(engine, portfolio)
        
        GLOG.DEBUG(f"Portfolio {portfolio_id} bound to engine successfully")
        return True
        
    except Exception as e:
        GLOG.ERROR(f"Failed to bind portfolio to engine: {e}")
        return False


def _update_engine_date_range(engine: HistoricEngine, portfolio_config: Dict[str, Any]):
    """Update engine date range to encompass all portfolios."""
    date_start = datetime_normalize(portfolio_config["backtest_start_date"])
    date_end = datetime_normalize(portfolio_config["backtest_end_date"])
    
    if engine.start_date is None or engine.start_date > date_start:
        engine.start_date = date_start
    if engine.end_date is None or engine.end_date < date_end:
        engine.end_date = date_end


def _create_portfolio_instance(portfolio_config: Dict[str, Any], logger: GinkgoLogger) -> Optional[PortfolioT1Backtest]:
    """Create a portfolio instance with proper configuration."""
    try:
        portfolio = PortfolioT1Backtest()
        portfolio.add_logger(logger)
        portfolio.set_portfolio_name(portfolio_config["name"])
        portfolio.set_portfolio_id(portfolio_config["uuid"])
        
        return portfolio
        
    except Exception as e:
        GLOG.ERROR(f"Failed to create portfolio instance: {e}")
        return None


def _bind_components_to_portfolio(
    portfolio: PortfolioT1Backtest, 
    components: Dict[str, Any], 
    logger: GinkgoLogger
) -> bool:
    """Bind all trading components to the portfolio."""
    try:
        # Add strategies (required)
        strategies = components.get("strategies", [])
        if len(strategies) == 0:
            GLOG.CRITICAL(f"No strategy found for portfolio {portfolio._portfolio_id}")
            return False
            
        for strategy in strategies:
            strategy.add_logger(logger)
            portfolio.add_strategy(strategy)
        
        # Add selector (required)
        selectors = components.get("selectors", [])
        if len(selectors) == 0:
            GLOG.ERROR(f"No selector found for portfolio {portfolio._portfolio_id}")
            return False
        selector = selectors[0]
        portfolio.bind_selector(selector)
        
        # Add sizer (required)
        sizers = components.get("sizers", [])
        if len(sizers) == 0:
            GLOG.ERROR(f"No sizer found for portfolio {portfolio._portfolio_id}")
            return False
        sizer = sizers[0]
        sizer.add_logger(logger)
        portfolio.bind_sizer(sizer)
        
        # Add risk managers (optional)
        risk_managers = components.get("risk_managers", [])
        if len(risk_managers) == 0:
            GLOG.WARN(f"No risk manager found for portfolio {portfolio._portfolio_id}. Backtest will go on without risk control.")
        else:
            for risk_manager in risk_managers:
                risk_manager.add_logger(logger)
                portfolio.add_risk_manager(risk_manager)
        
        # Add analyzers (required)
        analyzers = components.get("analyzers", [])
        if len(analyzers) == 0:
            GLOG.ERROR(f"No analyzer found for portfolio {portfolio._portfolio_id}")
            return False
        for analyzer in analyzers:
            analyzer.add_logger(logger)
            portfolio.add_analyzer(analyzer)
        
        return True
        
    except Exception as e:
        GLOG.ERROR(f"Failed to bind components to portfolio: {e}")
        return False


def _register_portfolio_with_engine(engine: HistoricEngine, portfolio: PortfolioT1Backtest):
    """Register the configured portfolio with the engine and bind event handlers."""
    # Bind portfolio to engine
    engine.bind_portfolio(portfolio)
    
    # Register portfolio event handlers
    engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_received)
    engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
    engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)
    engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)
    
    # Register portfolio with feeder
    engine._datafeeder.add_subscriber(portfolio)
