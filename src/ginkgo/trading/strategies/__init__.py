# Upstream: EngineAssemblyService, ComponentLoader, PortfolioBase
# Downstream: BaseStrategy, RandomSignalStrategy, MLStrategyBase, StrategyMLPredictor
# Role: 策略模块包，导出策略基类及ML策略等策略组件
#
# ===== 组件边界 =====
# 职责: 根据行情事件生成交易信号（方向 + 权重）
# 输入: portfolio_info(dict), event(EventPriceUpdate)
# 输出: List[Signal]
# 禁止:
#   - 选股（由 Selector 负责）
#   - 止损止盈（由 RiskManager 负责）
#   - 计算开仓手数（由 Sizer 负责）
# 允许:
#   - 读取 portfolio_info["positions"] 判断持仓状态，决定是否生成信号
# 已知违规（逐步修复）:
#   - DualThrust/TrendReverse: 读取持仓判断信号（合理用法，可保留）






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
    from ginkgo.trading.strategies.ml_strategy_base import MLStrategyBase
    from ginkgo.trading.strategies.ml_predictor import StrategyMLPredictor
    ML_STRATEGIES_AVAILABLE = True
except ImportError as e:
    # ML strategies are optional and require additional dependencies
    ML_STRATEGIES_AVAILABLE = False
    MLStrategyBase = None
    StrategyMLPredictor = None

