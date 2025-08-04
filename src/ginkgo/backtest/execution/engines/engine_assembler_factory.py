from rich import inspect
import datetime

from ginkgo.enums import FILE_TYPES, EVENT_TYPES, ENGINESTATUS_TYPES
from ginkgo.backtest.trading.matchmakings import MatchMakingSim, MatchMakingLive
from ginkgo.backtest.execution.feeders import BacktestFeeder
from ginkgo.backtest.execution.engines import BaseEngine, HistoricEngine
from ginkgo.backtest.execution.portfolios import PortfolioT1Backtest
from ginkgo.libs import GinkgoLogger
from ginkgo.data.containers import container
from ginkgo.libs import GLOG, datetime_normalize

# Import the unified services
from ginkgo import services


def assembler_backtest_engine(id: str, *args, **kwargs) -> BaseEngine:
    """
    Assemble a backtest engine using the unified service architecture.
    
    This function now delegates to the EngineAssemblyService for proper
    dependency injection and service-oriented architecture.
    
    Args:
        id: Engine ID to assemble
        
    Returns:
        Assembled engine instance or None if assembly failed
    """
    try:
        # Use unified services for engine assembly
        engine_assembly_service = services.backtest.engine_assembly_service()
        
        # Delegate to the service - ensure we get the service instance
        engine = engine_assembly_service().assemble_backtest_engine(engine_id=id, *args, **kwargs)
        
        return engine
        
    except Exception as e:
        GLOG.ERROR(f"Failed to assemble backtest engine using unified services: {e}")
        # Fallback to original implementation for compatibility
        return _original_assembler_backtest_engine(id, *args, **kwargs)


def _original_assembler_backtest_engine(id: str, *args, **kwargs) -> BaseEngine:
    GLOG.WARN(f"Assembler_backtest_engine --> {id}")
    now = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    logger = GinkgoLogger(logger_name="engine_logger", file_names=[f"bt_{id}_{now}"], console_log=False)
    engine_service = container.engine_service()
    engine_df = engine_service.get_engine(id, as_dataframe=True)
    if engine_df.shape[0] == 0:
        GLOG.WARN(f"No engine found for id:{id}.")
        return

    engine_data = engine_df.iloc[0]
    engine_id = engine_data["uuid"]

    # Create Engine Instanse
    engine = HistoricEngine(engine_data["name"])
    engine.engine_id = engine_id
    engine.add_logger(logger)

    # Sim Match
    match = MatchMakingSim()
    engine.bind_matchmaking(match)
    engine.register(EVENT_TYPES.ORDERSUBMITTED, match.on_order_received)
    engine.register(EVENT_TYPES.PRICEUPDATE, match.on_price_received)
    # Data Feeder
    feeder = BacktestFeeder("ExampleFeeder")
    feeder.add_logger(logger)
    engine.bind_datafeeder(feeder)
    engine.register_time_hook(feeder.broadcast)

    # Get Portfolios
    portfolio_mapping = engine_service.get_engine_portfolio_mappings(engine_id=engine_id)
    if portfolio_mapping.shape[0] == 0:
        GLOG.WARN(f"No portfolios found for engine {engine_id}.")
        return
    print(portfolio_mapping)

    # Bind Portfolios
    GLOG.DEBUG("Bind Portfolios")
    for i, r in portfolio_mapping.iterrows():
        portfolio_id = r["portfolio_id"]
        portfolio_service = container.portfolio_service()
        portfolio_data = portfolio_service.get_portfolio(portfolio_id, as_dataframe=True)
        if portfolio_data.shape[0] == 0:
            GLOG.WARN(f"No portfolio found for id:{portfolio_id}.")
            continue
        # Multi Portfolios in One Engine, Engine date_range will contain all portfolios date_range
        date_start = portfolio_data.iloc[0]["backtest_start_date"]
        date_end = portfolio_data.iloc[0]["backtest_end_date"]
        if engine.start_date is None:
            engine.start_date = datetime_normalize(date_start)
        else:
            if engine.start_date > datetime_normalize(date_start):
                engine.start_date = datetime_normalize(date_start)
        if engine.end_date is None:
            engine.end_date = datetime_normalize(date_end)
        else:
            if engine.end_date < datetime_normalize(date_end):
                engine.end_date = datetime_normalize(date_end)
        portfolio = PortfolioT1Backtest()
        portfolio.add_logger(logger)
        portfolio.set_portfolio_name(portfolio_data.iloc[0]["name"])
        portfolio.set_portfolio_id(portfolio_id)
        # Get Related Files about portfolio
        # Add Strategy
        component_service = container.component_service()
        strategies = component_service.get_strategies_by_portfolio(portfolio_id)
        if len(strategies) == 0:
            GLOG.CRITICAL(f"No strategy found for portfolio {portfolio_id}.")
            return
        for i in strategies:
            i.add_logger(logger)
            portfolio.add_strategy(i)
        # Add Selector
        GLOG.DEBUG("Add Selector")
        selectors = component_service.get_selectors_by_portfolio(portfolio_id)
        selector = selectors[0]
        if selector is None:
            GLOG.ERROR(f"No selector found for portfolio {portfolio_id}.")
            import pdb

            pdb.set_trace()
            return
        portfolio.bind_selector(selector)
        # Add Sizer
        GLOG.DEBUG("Add Sizer")
        sizers = component_service.get_sizers_by_portfolio(portfolio_id)
        sizer = sizers[0]
        sizer.add_logger(logger)
        if sizer is None:
            GLOG.ERROR(f"No sizer found for portfolio {portfolio_id}.")
            import pdb

            pdb.set_trace()
            return
        portfolio.bind_sizer(sizer)
        # TODO: Add Risk Managers
        GLOG.DEBUG("Add Risk Managers")
        risk_managers = component_service.get_risk_managers_by_portfolio(portfolio_id)
        if len(risk_managers) == 0:
            GLOG.WARN(f"No risk manager found for portfolio {portfolio_id}. Backtest will go on without risk control.")
        else:
            for risk_manager in risk_managers:
                risk_manager.add_logger(logger)
                portfolio.add_risk_manager(risk_manager)
        # Add Analyzer
        GLOG.DEBUG("Add Analyzer.")
        analyzers = component_service.get_analyzers_by_portfolio(portfolio_id)
        if len(analyzers) == 0:
            GLOG.ERROR(f"No analyzer found for portfolio {portfolio_id}.")
            import pdb

            pdb.set_trace()
            return
        for i in analyzers:
            i.add_logger(logger)
            portfolio.add_analyzer(i)
        # Bind
        GLOG.DEBUG("Bind")
        engine.bind_portfolio(portfolio)
        # Register
        engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_received)
        engine.register(EVENT_TYPES.ORDERFILLED, portfolio.on_order_filled)
        engine.register(EVENT_TYPES.ORDERCANCELED, portfolio.on_order_canceled)
        engine.register(EVENT_TYPES.SIGNALGENERATION, portfolio.on_signal)

        # Regist to feeder
        feeder.add_subscriber(portfolio)
        print("Clear historic records for portfolio", portfolio_id)
        # Clean old analyzer records using service layer
        from ginkgo.data.crud.analyzer_record_crud import delete_analyzer_records_filtered
        delete_analyzer_records_filtered(portfolio_id=portfolio_id, engine_id=engine_id)
        # TODO Delete Order records
        # TODO Delete Signal records
        # TODO Delete Position records

    print("++++++++++")
    print("Final:")
    print(engine)
    engine.start()
