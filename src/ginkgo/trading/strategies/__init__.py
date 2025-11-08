# from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate  # Temporarily disabled due to import issues
from ginkgo.trading.strategies.base_strategy import BaseStrategy
# from ginkgo.trading.strategies.random_choice import StrategyRandomChoice  # Temporarily disabled due to import issues

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
