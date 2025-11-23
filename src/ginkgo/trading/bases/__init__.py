"""
组件基类模块

提供各种组件的基类，组合所需的Mixin能力：
- SignalBase: 信号组件基类
- EventBase: 事件组件基类
- OrderBase: 订单组件基类
- PositionBase: 持仓组件基类
- PortfolioBase: 投资组合基类
- StrategyBase: 策略基类
- SelectorBase: 选股组件基类
- RiskBase: 风控组件基类
- SizerBase: 资金管理组件基类
"""

from .signal_base import SignalBase
from .event_base import EventBase
from .order_base import OrderBase
from .position_base import PositionBase
from .portfolio_base import PortfolioBase
from .strategy_base import StrategyBase
from .selector_base import SelectorBase
from .risk_base import RiskBase
from .sizer_base import SizerBase

__all__ = [
    "SignalBase",
    "EventBase",
    "OrderBase",
    "PositionBase",
    "PortfolioBase",
    "StrategyBase",
    "SelectorBase",
    "RiskBase",
    "SizerBase",
]