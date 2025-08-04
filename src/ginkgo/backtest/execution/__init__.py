"""
Execution Module - 执行引擎层

作为 Ginkgo Backtest Framework 执行引擎层模块

- engines/: 引擎集合
- events/: 事件驱动引擎  
- portfolios/: 组合管理
- feeders/: 数据源

统一的引擎层接口和事件驱动架构
"""

# 引擎集合
# 分别导入以避免单个导入失败影响其他导入
try:
    from .engines.base_engine import BaseEngine
except ImportError:
    pass

try:
    from .engines.historic_engine import HistoricEngine
except ImportError:
    pass

try:
    from .engines.live_engine import LiveEngine
except ImportError:
    pass

try:
    from .engines.matrix_engine import MatrixEngine
except ImportError:
    pass

# 组合管理
try:
    from .portfolios.base_portfolio import BasePortfolio
    from .portfolios.portfolio_live import PortfolioLive
    from .portfolios.t1backtest import PortfolioT1Backtest
except ImportError:
    pass

# 事件处理
try:
    from .events.base_event import EventBase
except ImportError:
    pass

# 数据源
try:
    from .feeders.base_feeder import BaseFeeder
    from .feeders.backtest_feeder import BacktestFeeder
except ImportError:
    pass

__all__ = [
    # 引擎
    "BaseEngine",
    "HistoricEngine", 
    "LiveEngine",
    "MatrixEngine",
    
    # 组合管理
    "BasePortfolio",
    "PortfolioLive",
    "PortfolioT1Backtest",
    
    # 事件处理
    "EventBase",
    
    # 数据源
    "BaseFeeder",
    "BacktestFeeder",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 执行引擎层模块"