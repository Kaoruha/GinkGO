"""
Backtest Module Container

Provides unified access to backtest components using dependency-injector,
similar to the data module's approach.

Usage Examples:

    from ginkgo.backtest.core.containers import container
    
    # Access engines (similar to data.cruds)
    historic_engine = container.engines.historic()
    matrix_engine = container.engines.matrix()
    
    # Access analyzers
    sharpe_analyzer = container.analyzers.sharpe()
    drawdown_analyzer = container.analyzers.drawdown()
    
    # Access strategies
    dual_thrust = container.strategies.dual_thrust()
    
    # Access portfolios
    t1_portfolio = container.portfolios.t1()
    
    # For dependency injection:
    from dependency_injector.wiring import inject, Provide
    
    @inject
    def your_function(engine = Provide[Container.engines.historic]):
        # Use engine here
        pass
"""

from dependency_injector import containers, providers


# ============= LAZY IMPORT FUNCTIONS =============
def _get_historic_engine_class():
    """Lazy import for HistoricEngine class."""
    from ginkgo.backtest.execution.engines.historic_engine import HistoricEngine
    return HistoricEngine

def _get_matrix_engine_class():
    """Lazy import for MatrixEngine class.""" 
    from ginkgo.backtest.execution.engines.matrix_engine import MatrixEngine
    return MatrixEngine

def _get_live_engine_class():
    """Lazy import for LiveEngine class."""
    from ginkgo.backtest.execution.engines.live_engine import LiveEngine
    return LiveEngine

def _get_unified_engine_class():
    """Lazy import for UnifiedEngine class."""
    try:
        from ginkgo.backtest.execution.engines.unified_engine import UnifiedBacktestEngine
        return UnifiedBacktestEngine
    except ImportError:
        # Fallback to historic engine if unified not available
        return _get_historic_engine_class()

def _get_enhanced_historic_engine_class():
    """Lazy import for EnhancedHistoricEngine class."""
    from ginkgo.backtest.execution.engines.enhanced_historic_engine import EnhancedHistoricEngine
    return EnhancedHistoricEngine

# Analyzer classes
def _get_sharpe_analyzer_class():
    """Lazy import for SharpeRatio analyzer."""
    from ginkgo.backtest.analysis.analyzers.sharpe_ratio import SharpeRatio
    return SharpeRatio

def _get_max_drawdown_analyzer_class():
    """Lazy import for MaxDrawdown analyzer."""
    from ginkgo.backtest.analysis.analyzers.max_drawdown import MaxDrawdown  
    return MaxDrawdown

def _get_net_value_analyzer_class():
    """Lazy import for NetValue analyzer."""
    from ginkgo.backtest.analysis.analyzers.net_value import NetValue
    return NetValue

def _get_profit_analyzer_class():
    """Lazy import for Profit analyzer."""
    from ginkgo.backtest.analysis.analyzers.profit import Profit
    return Profit

# Strategy classes
def _get_dual_thrust_strategy_class():
    """Lazy import for DualThrust strategy."""
    from ginkgo.backtest.strategy.strategies.dual_thrust import StrategyDualThrust
    return StrategyDualThrust

def _get_random_strategy_class():
    """Lazy import for Random strategy."""
    from ginkgo.backtest.strategy.strategies.random_choice import StrategyRandomChoice
    return StrategyRandomChoice

def _get_volume_activate_strategy_class():
    """Lazy import for VolumeActivate strategy."""
    from ginkgo.backtest.strategy.strategies.volume_activate import StrategyVolumeActivate
    return StrategyVolumeActivate

def _get_trend_follow_strategy_class():
    """Lazy import for TrendFollow strategy."""
    from ginkgo.backtest.strategy.strategies.trend_follow import StrategyTrendFollow
    return StrategyTrendFollow

# Portfolio classes
def _get_t1_portfolio_class():
    """Lazy import for T1 portfolio."""
    from ginkgo.backtest.portfolios.t1backtest import PortfolioT1Backtest
    return PortfolioT1Backtest

def _get_live_portfolio_class():
    """Lazy import for Live portfolio."""
    from ginkgo.backtest.portfolios.portfolio_live import PortfolioLive
    return PortfolioLive

def _get_engine_assembly_service_class():
    """Lazy import for EngineAssemblyService class."""
    from ginkgo.backtest.services.engine_assembly_service import EngineAssemblyService
    return EngineAssemblyService


def _create_engine_assembly_service():
    """Create engine assembly service with all required dependencies."""
    from ginkgo.data.containers import container as data_container
    from ginkgo.backtest.services.engine_assembly_service import EngineAssemblyService
    
    return EngineAssemblyService(
        engine_service=data_container.engine_service(),
        portfolio_service=data_container.portfolio_service(),
        component_service=data_container.component_service(),
        analyzer_record_crud=data_container.cruds.analyzer_record()
    )

def _get_matchmaking_class():
    """Lazy import for MatchMaking class."""
    from ginkgo.backtest.trading.matchmakings.sim_matchmaking import MatchMakingSim
    return MatchMakingSim

def _get_broker_matchmaking_class():
    """Lazy import for BrokerMatchMaking class."""
    from ginkgo.backtest.trading.matchmakings.broker_matchmaking import BrokerMatchMaking
    return BrokerMatchMaking

def _get_sim_broker_class():
    """Lazy import for SimBroker class."""
    from ginkgo.backtest.trading.brokers.sim_broker import SimBroker
    return SimBroker

def _get_okx_broker_class():
    """Lazy import for OKXBroker class."""
    from ginkgo.backtest.trading.brokers.okx_broker import OKXBroker
    return OKXBroker

def _get_feeder_class():
    """Lazy import for Feeder class."""
    from ginkgo.backtest.feeders.backtest_feeder import BacktestFeeder
    return BacktestFeeder

# Execution services
def _get_confirmation_handler_class():
    """Lazy import for ConfirmationHandler class."""
    from ginkgo.backtest.execution.confirmation.confirmation_handler import ConfirmationHandler
    return ConfirmationHandler

def _get_portfolio_management_service_class():
    """Lazy import for PortfolioManagementService class."""
    from ginkgo.backtest.services.portfolio_management_service import PortfolioManagementService
    return PortfolioManagementService

def _get_executor_factory_class():
    """Lazy import for ExecutorFactory class."""
    from ginkgo.backtest.execution.executors.executor_factory import ExecutorFactory
    return ExecutorFactory


class Container(containers.DeclarativeContainer):
    """
    Backtest module dependency injection container.
    
    Provides unified access to backtest components using FactoryAggregate,
    similar to data module's approach.
    """
    
    # ============= ENGINES =============
    # Engine factories
    historic_engine = providers.Factory(_get_historic_engine_class)
    matrix_engine = providers.Factory(_get_matrix_engine_class)
    live_engine = providers.Factory(_get_live_engine_class)
    unified_engine = providers.Factory(_get_unified_engine_class)
    enhanced_historic_engine = providers.Factory(_get_enhanced_historic_engine_class)
    
    # Engines aggregate - similar to data module's cruds
    engines = providers.FactoryAggregate(
        historic=historic_engine,
        matrix=matrix_engine, 
        live=live_engine,
        unified=unified_engine,
        enhanced_historic=enhanced_historic_engine
    )
    
    # ============= ANALYZERS =============
    # Analyzer factories
    sharpe_analyzer = providers.Factory(_get_sharpe_analyzer_class)
    max_drawdown_analyzer = providers.Factory(_get_max_drawdown_analyzer_class)
    net_value_analyzer = providers.Factory(_get_net_value_analyzer_class)
    profit_analyzer = providers.Factory(_get_profit_analyzer_class)
    
    # Analyzers aggregate
    analyzers = providers.FactoryAggregate(
        sharpe=sharpe_analyzer,
        max_drawdown=max_drawdown_analyzer,
        drawdown=max_drawdown_analyzer,  # alias
        net_value=net_value_analyzer,
        profit=profit_analyzer
    )
    
    # ============= STRATEGIES =============
    # Strategy factories  
    dual_thrust_strategy = providers.Factory(_get_dual_thrust_strategy_class)
    random_strategy = providers.Factory(_get_random_strategy_class)
    volume_activate_strategy = providers.Factory(_get_volume_activate_strategy_class)
    trend_follow_strategy = providers.Factory(_get_trend_follow_strategy_class)
    
    # Strategies aggregate
    strategies = providers.FactoryAggregate(
        dual_thrust=dual_thrust_strategy,
        random=random_strategy,
        volume_activate=volume_activate_strategy,
        trend_follow=trend_follow_strategy
    )
    
    # ============= PORTFOLIOS =============
    # Portfolio factories
    t1_portfolio = providers.Factory(_get_t1_portfolio_class)
    live_portfolio = providers.Factory(_get_live_portfolio_class)
    
    # Portfolios aggregate
    portfolios = providers.FactoryAggregate(
        t1=t1_portfolio,
        t1backtest=t1_portfolio,  # alias
        live=live_portfolio
    )
    
    # ============= SERVICES =============  
    # Engine Assembly Service - initialize with all dependencies
    engine_assembly_service = providers.Factory(_create_engine_assembly_service)
    
    # Execution services
    confirmation_handler = providers.Singleton(_get_confirmation_handler_class)
    portfolio_management_service = providers.Singleton(_get_portfolio_management_service_class)
    executor_factory = providers.Singleton(_get_executor_factory_class)
    
    # Services aggregate
    services = providers.FactoryAggregate(
        engine_assembly_service=engine_assembly_service,
        confirmation_handler=confirmation_handler,
        portfolio_management_service=portfolio_management_service,
        executor_factory=executor_factory
    )
    
    # ============= ADDITIONAL COMPONENTS =============
    # Matchmaking
    matchmaking = providers.Factory(lambda: _get_matchmaking_class())
    broker_matchmaking = providers.Factory(_get_broker_matchmaking_class)
    
    # Brokers
    sim_broker = providers.Factory(_get_sim_broker_class)
    okx_broker = providers.Factory(_get_okx_broker_class)
    
    # Brokers aggregate - 符合Ginkgo的FactoryAggregate模式
    brokers = providers.FactoryAggregate(
        sim=sim_broker,
        okx=okx_broker
    )
    
    # Feeder
    feeder = providers.Factory(lambda: _get_feeder_class())


# Create a singleton instance of the container, accessible throughout the application
container = Container()

# Backward compatibility - provide old access methods
def get_engine(engine_type: str):
    """Get engine by type (backward compatibility)"""
    engine_mapping = {
        'historic': container.engines.historic,
        'matrix': container.engines.matrix,
        'live': container.engines.live,
        'unified': container.engines.unified,
        'enhanced_historic': container.engines.enhanced_historic
    }
    
    if engine_type in engine_mapping:
        return engine_mapping[engine_type]()
    else:
        raise ValueError(f"Unknown engine type: {engine_type}")

def get_analyzer(analyzer_type: str):
    """Get analyzer by type (backward compatibility)"""
    analyzer_mapping = {
        'sharpe': container.analyzers.sharpe,
        'max_drawdown': container.analyzers.max_drawdown,
        'drawdown': container.analyzers.drawdown,
        'net_value': container.analyzers.net_value,
        'profit': container.analyzers.profit
    }
    
    if analyzer_type in analyzer_mapping:
        return analyzer_mapping[analyzer_type]()
    else:
        raise ValueError(f"Unknown analyzer type: {analyzer_type}")

def get_strategy(strategy_type: str):
    """Get strategy by type (backward compatibility)"""
    strategy_mapping = {
        'dual_thrust': container.strategies.dual_thrust,
        'random': container.strategies.random,
        'volume_activate': container.strategies.volume_activate,
        'trend_follow': container.strategies.trend_follow
    }
    
    if strategy_type in strategy_mapping:
        return strategy_mapping[strategy_type]()
    else:
        raise ValueError(f"Unknown strategy type: {strategy_type}")

def get_portfolio(portfolio_type: str):
    """Get portfolio by type (backward compatibility)"""
    portfolio_mapping = {
        't1': container.portfolios.t1,
        't1backtest': container.portfolios.t1backtest,
        'live': container.portfolios.live
    }
    
    if portfolio_type in portfolio_mapping:
        return portfolio_mapping[portfolio_type]()
    else:
        raise ValueError(f"Unknown portfolio type: {portfolio_type}")

def get_service_info():
    """Get service information (backward compatibility)"""
    return {
        "engines": ["historic", "matrix", "live", "unified", "enhanced_historic"],
        "analyzers": ["sharpe", "max_drawdown", "drawdown", "net_value", "profit"],
        "strategies": ["dual_thrust", "random", "volume_activate", "trend_follow"],
        "portfolios": ["t1", "t1backtest", "live"],
        "services": ["engine_assembly_service", "confirmation_handler", "portfolio_management_service", "executor_factory"]
    }

# Bind backward compatibility methods to container
container.get_engine = get_engine
container.get_analyzer = get_analyzer
container.get_strategy = get_strategy
container.get_portfolio = get_portfolio
container.get_service_info = get_service_info

# Create alias for backward compatibility
backtest_container = container