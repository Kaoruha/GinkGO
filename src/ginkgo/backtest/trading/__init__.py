"""
Trading Module - 交易层

作为 Ginkgo Backtest Framework 交易层模块

- matchmakings/: 撮合引擎
- handlers/: 处理器

统一的交易层接口和撮合机制
"""

# 撮合引擎
try:
    from .matchmakings.base_matchmaking import MatchMakingBase
    from .matchmakings.sim_matchmaking import MatchMakingSim
    from .matchmakings.live_matchmaking import LiveMatchMaking
except ImportError:
    pass

# 处理器
try:
    from .handlers.base_handler import HandlerBase
    from .handlers.handler_get_backtest_daybar import HandlerGetBacktestDaybar
    from .handlers.handler_live_price import HandlerLivePrice
    from .handlers.handler_record_analyzer import HandlerRecordAnalyzer
except ImportError:
    pass

__all__ = [
    # 撮合引擎
    "MatchMakingBase",
    "MatchMakingSim",
    "LiveMatchMaking",
    
    # 处理器
    "HandlerBase", 
    "HandlerGetBacktestDaybar",
    "HandlerLivePrice",
    "HandlerRecordAnalyzer",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 交易层模块"