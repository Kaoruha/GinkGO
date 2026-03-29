# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Bases基础组件模块导出交易基础类公共接口支持组件开发和扩展支持交易系统功能和组件集成提供完整业务支持






"""
组件基类模块

提供各种组件的基类，组合所需的Mixin能力：
- SignalBase: 信号组件基类
- OrderBase: 订单组件基类
- PositionBase: 持仓组件基类
- PortfolioBase: 投资组合基类
- SelectorBase: 选股组件基类
- RiskBase: 风控组件基类
- SizerBase: 资金管理组件基类
"""

from .signal_base import SignalBase
from .order_base import OrderBase
from .position_base import PositionBase
from .portfolio_base import PortfolioBase
from .selector_base import SelectorBase
from .risk_base import RiskBase
from .sizer_base import SizerBase

__all__ = [
    "SignalBase",
    "OrderBase",
    "PositionBase",
    "PortfolioBase",
    "SelectorBase",
    "RiskBase",
    "SizerBase",
]