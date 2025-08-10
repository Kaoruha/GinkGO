# from ginkgo.backtest.strategy.strategies.volume_activate import StrategyVolumeActivate  # Temporarily disabled due to import issues
from ginkgo.backtest.strategy.strategies.base_strategy import StrategyBase
# from ginkgo.backtest.strategy.strategies.random_choice import StrategyRandomChoice  # Temporarily disabled due to import issues

# Machine Learning Strategies
try:
    from ginkgo.backtest.strategy.strategies.ml_strategy_base import StrategyMLBase
    from ginkgo.backtest.strategy.strategies.ml_predictor import StrategyMLPredictor
    ML_STRATEGIES_AVAILABLE = True
except ImportError as e:
    # ML strategies are optional and require additional dependencies
    ML_STRATEGIES_AVAILABLE = False
    StrategyMLBase = None
    StrategyMLPredictor = None
