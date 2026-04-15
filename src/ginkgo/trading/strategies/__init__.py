# Upstream: EngineAssemblyService, ComponentFactoryService, PortfolioBase
# Downstream: BaseStrategy, RandomSignalStrategy, StrategyMLBase, StrategyMLPredictor
# Role: 策略模块包，导出策略基类及ML策略等策略组件






# from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate  # Temporarily disabled due to import issues
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.trading.strategies.random_signal_strategy import RandomSignalStrategy
from ginkgo.trading.strategies.moving_average_crossover import MovingAverageCrossover
from ginkgo.trading.strategies.trend_follow import StrategyTrendFollow
from ginkgo.trading.strategies.dual_thrust import StrategyDualThrust
from ginkgo.trading.strategies.mean_reversion import MeanReversion
from ginkgo.trading.strategies.trend_reverse import TrendFollow
from ginkgo.trading.strategies.momentum import Momentum

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

