# Upstream: 引擎、组合、策略、风控等组件的具体实现类
# Downstream: bases.signal_base, bases.order_base, bases.position_base, bases.portfolio_base, bases.selector_base, bases.risk_base, bases.sizer_base
# Role: 交易组件基类模块包入口，导出Signal/Order/Position/Portfolio/Selector/Risk/Sizer七大组件抽象基类






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
