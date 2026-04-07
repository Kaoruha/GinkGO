# Upstream: EngineAssemblyService, ComponentFactoryService, PortfolioBase
# Downstream: BaseStrategy, RandomSignalStrategy, StrategyMLBase, StrategyMLPredictor
# Role: 策略模块包，导出策略基类及ML策略等策略组件






# from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate  # Temporarily disabled due to import issues
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy

# Machine Learning Strategies
try:
    from ginkgo.trading.strategies.ml_strategy_base import StrategyMLBase
    from ginkgo.trading.strategies.ml_predictor import StrategyMLPredictor
    ML_STRATEGIES_AVAILABLE = True
except ImportError as e:
    # ML strategies are optional and require additional dependencies
    ML_STRATEGIES_AVAILABLE = False
    StrategyMLBase = None
    StrategyMLPredictor = None

