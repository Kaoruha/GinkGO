"""
Backtest Module Container

Provides unified access to backtest components using dependency-injector,
similar to the data module's approach.

Usage Examples:

    from ginkgo.trading.core.containers import container
    
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
def _get_time_controlled_engine_class():
    """Lazy import for TimeControlledEventEngine class."""
    from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
    return TimeControlledEventEngine

# Analyzer classes
def _get_sharpe_analyzer_class():
    """Lazy import for SharpeRatio analyzer."""
    from ginkgo.trading.analysis.analyzers.sharpe_ratio import SharpeRatio
    return SharpeRatio

def _get_max_drawdown_analyzer_class():
    """Lazy import for MaxDrawdown analyzer."""
    from ginkgo.trading.analysis.analyzers.max_drawdown import MaxDrawdown  
    return MaxDrawdown

def _get_net_value_analyzer_class():
    """Lazy import for NetValue analyzer."""
    from ginkgo.trading.analysis.analyzers.net_value import NetValue
    return NetValue

def _get_profit_analyzer_class():
    """Lazy import for Profit analyzer."""
    from ginkgo.trading.analysis.analyzers.profit import Profit
    return Profit

# Strategy classes
def _get_dual_thrust_strategy_class():
    """Lazy import for DualThrust strategy."""
    from ginkgo.trading.strategies.dual_thrust import StrategyDualThrust
    return StrategyDualThrust

def _get_random_strategy_class():
    """Lazy import for Random strategy."""
    from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
    return RandomSignalStrategy

def _get_volume_activate_strategy_class():
    """Lazy import for VolumeActivate strategy."""
    from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate
    return StrategyVolumeActivate

def _get_trend_follow_strategy_class():
    """Lazy import for TrendFollow strategy."""
    from ginkgo.trading.strategies.trend_follow import StrategyTrendFollow
    return StrategyTrendFollow

# Portfolio classes
def _get_t1_portfolio_class():
    """Lazy import for T1 portfolio."""
    from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
    return PortfolioT1Backtest

def _get_live_portfolio_class():
    """Lazy import for Live portfolio."""
    from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
    return PortfolioLive

def _get_engine_assembly_service_class():
    """Lazy import for EngineAssemblyService class."""
    from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService
    return EngineAssemblyService


def _create_engine_assembly_service():
    """Create engine assembly service with all required dependencies."""
    from ginkgo.data.containers import container as data_container
    from ginkgo.trading.services.engine_assembly_service import EngineAssemblyService

    return EngineAssemblyService(
        engine_service=data_container.engine_service(),
        portfolio_service=data_container.portfolio_service(),
        file_service=data_container.file_service(),
        analyzer_record_crud=data_container.cruds.analyzer_record()
    )

def _get_matchmaking_class():
    """Lazy import for universal MatchMaking class (Broker-based)."""
    from ginkgo.trading.routing.router import Router
    return BrokerMatchMaking

def _get_broker_matchmaking_class():
    """Lazy import for BrokerMatchMaking class."""
    from ginkgo.trading.routing.router import Router
    return BrokerMatchMaking

def _get_sim_broker_class():
    """Lazy import for SimBroker class."""
    from ginkgo.trading.brokers.sim_broker import SimBroker
    return SimBroker

def _get_okx_broker_class():
    """Lazy import for OKXBroker class."""
    from ginkgo.trading.brokers.okx_broker import OKXBroker
    return OKXBroker

def _get_manual_broker_class():
    """Lazy import for ManualBroker class."""
    from ginkgo.trading.brokers.manual_broker import ManualBroker
    return ManualBroker

def _get_auto_broker_class():
    """Lazy import for AutoBroker class.""" 
    from ginkgo.trading.brokers.auto_broker import AutoBroker
    return AutoBroker

# def _get_demo_auto_broker_class():
#     """Lazy import for DemoAutoBroker class."""
#     from ginkgo.trading.brokers.demo_auto_broker import DemoAutoBroker
#     return DemoAutoBroker
#     # DISABLED: DemoAutoBroker file does not exist

def _create_broker_by_mode(execution_mode: str, config: dict):
    """
    根据执行模式创建对应的Broker实例
    
    Args:
        execution_mode: 执行模式 ('backtest', 'manual', 'live')
        config: Broker配置
        
    Returns:
        BaseBroker: 对应的Broker实例
    """
    mode_mapping = {
        'backtest': _get_sim_broker_class(),
        'simulation': _get_sim_broker_class(),  # alias
        'sim': _get_sim_broker_class(),  # alias
        
        'manual': _get_manual_broker_class(),
        'confirmation': _get_manual_broker_class(),  # alias
        
        'live': _get_auto_broker_class(),  # 使用AutoBroker (DemoAutoBroker不存在)
        'api': _get_auto_broker_class(),  # alias
        'auto': _get_auto_broker_class(),  # alias
        
        'okx': _get_okx_broker_class(),  # OKX实盘
        'okx_live': _get_okx_broker_class(),
    }
    
    broker_class = mode_mapping.get(execution_mode.lower())
    if not broker_class:
        raise ValueError(f"Unsupported execution mode: {execution_mode}")
    
    return broker_class(config)

def _get_feeder_class():
    """Lazy import for Feeder class."""
    from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
    return BacktestFeeder

# ============= T6 NEW PROVIDER FUNCTIONS =============

def _get_backtest_feeder_class():
    """Lazy import for BacktestFeeder class (enhanced version)."""
    from ginkgo.trading.feeders.backtest_feeder import BacktestFeeder
    return BacktestFeeder

def _get_live_feeder_class():
    """Lazy import for LiveFeeder class."""
    from ginkgo.trading.feeders.live_feeder import LiveDataFeeder
    return LiveDataFeeder

def _get_event_routing_center_class():
    """Lazy import for EventRoutingCenter class."""
    from ginkgo.trading.routing.center import EventRoutingCenter
    return EventRoutingCenter

# Execution services
# def _get_confirmation_handler_class():
#     """Lazy import for ConfirmationHandler class."""
#     # TODO: Move confirmation functionality to events module
#     # from ginkgo.trading.events.execution_confirmation import ConfirmationHandler
#     return ConfirmationHandler
#     # DISABLED: ConfirmationHandler class not implemented

def _get_portfolio_management_service_class():
    """Lazy import for PortfolioManagementService class."""
    from ginkgo.trading.services.portfolio_management_service import PortfolioManagementService
    return PortfolioManagementService

# def _get_executor_factory_class():
#     """Lazy import for ExecutorFactory class."""
#     # TODO: ExecutorFactory removed - functionality integrated into brokers
#     # from ginkgo.trading.brokers.executor_factory import ExecutorFactory
#     return ExecutorFactory
#     # DISABLED: ExecutorFactory removed - functionality integrated into brokers


class Container(containers.DeclarativeContainer):
    """
    Backtest module dependency injection container.
    
    Provides unified access to backtest components using FactoryAggregate,
    similar to data module's approach.
    """
    
    # ============= ENGINES =============
    # TimeControlled Engine Provider (统一引擎实现)
    time_controlled_engine = providers.Factory(_get_time_controlled_engine_class)
    
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
    # confirmation_handler = providers.Singleton(_get_confirmation_handler_class)  # DISABLED: not implemented
    portfolio_management_service = providers.Singleton(_get_portfolio_management_service_class)
    # executor_factory = providers.Singleton(_get_executor_factory_class)  # DISABLED: functionality integrated into brokers
    
    # Services aggregate
    services = providers.FactoryAggregate(
        engine_assembly_service=engine_assembly_service,
        # confirmation_handler=confirmation_handler,  # DISABLED: not implemented
        portfolio_management_service=portfolio_management_service,
        # executor_factory=executor_factory  # DISABLED: functionality integrated into brokers
    )
    
    # ============= ADDITIONAL COMPONENTS =============
    # Matchmaking
    matchmaking = providers.Factory(lambda: _get_matchmaking_class())
    broker_matchmaking = providers.Factory(_get_broker_matchmaking_class)
    
    # Brokers - 扩展支持多种执行模式（统一定义）
    sim_broker = providers.Factory(_get_sim_broker_class)
    okx_broker = providers.Factory(_get_okx_broker_class) 
    manual_broker = providers.Factory(_get_manual_broker_class)
    auto_broker = providers.Factory(_get_auto_broker_class)
    # demo_auto_broker = providers.Factory(_get_demo_auto_broker_class)  # DISABLED: file not found
    
    # Brokers aggregate - 符合Ginkgo的FactoryAggregate模式
    brokers = providers.FactoryAggregate(
        # 回测模式
        sim=sim_broker,
        backtest=sim_broker,  # alias
        
        # 人工确认模式  
        manual=manual_broker,
        confirmation=manual_broker,  # alias
        
        # 自动API模式
        auto=auto_broker,
        api=auto_broker,  # alias
        # demo_auto=demo_auto_broker,  # DISABLED: DemoAutoBroker not found
        
        # 实盘Broker
        okx=okx_broker,
        live=okx_broker  # alias
    )
    
    # Broker工厂 - 根据模式自动选择
    broker_factory = providers.Factory(_create_broker_by_mode)
    
    # Feeder
    feeder = providers.Factory(lambda: _get_feeder_class())

    # ============= T6 NEW PROVIDERS =============

    # Data Feeders - 统一接口与LiveFeeder
    backtest_feeder = providers.Factory(_get_backtest_feeder_class)
    live_feeder = providers.Factory(_get_live_feeder_class)
    
    # Feeders aggregate - 符合t6.md要求
    feeders = providers.FactoryAggregate(
        historical=backtest_feeder,
        backtest=backtest_feeder,  # alias
        live=live_feeder,
        realtime=live_feeder  # alias
    )
    
    # Event Routing Center Provider
    routing_center = providers.Singleton(_get_event_routing_center_class)
    
    # Routing aggregate
    routing = providers.FactoryAggregate(
        center=routing_center
    )
    
    # Engines aggregate - 只保留TimeControlledEventEngine
    engines = providers.FactoryAggregate(
        time_controlled=time_controlled_engine,
        default=time_controlled_engine  # 默认引擎
    )


# Create a singleton instance of the container, accessible throughout the application
container = Container()

# Backward compatibility - provide old access methods
def get_engine(engine_type: str = 'time_controlled'):
    """
    Get engine by type (backward compatibility)

    Note: All legacy engine types now return TimeControlledEventEngine.
    Use ExecutionMode parameter when creating the engine to specify backtest/live/paper mode.
    """
    # 所有引擎类型都返回TimeControlledEventEngine
    return container.engines.time_controlled()

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
        "engines": ["time_controlled"],  # 简化为只保留核心引擎
        "analyzers": ["sharpe", "max_drawdown", "drawdown", "net_value", "profit"],
        "strategies": ["dual_thrust", "random", "volume_activate", "trend_follow"],
        "portfolios": ["t1", "t1backtest", "live"],
        "services": ["engine_assembly_service", "portfolio_management_service"]
    }

# Bind backward compatibility methods to container
container.get_engine = get_engine
container.get_analyzer = get_analyzer
container.get_strategy = get_strategy
container.get_portfolio = get_portfolio
container.get_service_info = get_service_info

# Create alias for backward compatibility
backtest_container = container
