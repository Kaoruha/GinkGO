# Upstream: 引擎、组合、策略、风控等组件的具体实现类
# Downstream: bases.portfolio_base, bases.selector_base, bases.risk_base, bases.sizer_base
# Role: 交易组件基类模块包入口，导出Portfolio/Selector/Risk/Sizer四大组件抽象基类（Signal/Order/Position空壳ABC已删，能力由Mixin直接组合提供）






"""
组件基类模块

提供各种组件的基类，组合所需的Mixin能力：
- PortfolioBase: 投资组合基类
- SelectorBase: 选股组件基类
- RiskBase: 风控组件基类
- SizerBase: 资金管理组件基类
"""

from .portfolio_base import PortfolioBase
from .selector_base import SelectorBase
from .risk_base import RiskBase
from .sizer_base import SizerBase

__all__ = [
    "PortfolioBase",
    "SelectorBase",
    "RiskBase",
    "SizerBase",
]
