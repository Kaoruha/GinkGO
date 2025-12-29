# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 策略模块导出基类/均线交叉/双向突破/均值回归/价格行为等策略支持交易系统功能和组件集成提供完整业务支持






# from ginkgo.trading.strategies.volume_activate import StrategyVolumeActivate  # Temporarily disabled due to import issues
from ginkgo.trading.strategies.base_strategy import BaseStrategy
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
