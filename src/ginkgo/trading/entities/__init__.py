# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 实体模块导出K线/Tick/信号/订单/持仓/转账/资金调整等业务实体类支持交易系统功能和组件集成提供完整业务支持






"""
Entities Module - 业务实体对象

包含 Ginkgo Backtest 框架中的核心业务实体，这些是内存中的数据容器类，
用于在回测过程中传递和管理业务数据。

- 市场数据实体：Bar, Tick, StockInfo, TradeDay, Adjustfactor
- 交易相关实体：Order, Position, Signal, Transfer, CapitalAdjustment
- 辅助实体：TimeRelated

这些实体类继承自 Base 类，提供 UUID 管理和 DataFrame 转换能力，
与数据库模型（data.models）不同，专门用于业务逻辑处理。
"""

from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.stockinfo import StockInfo
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.entities.tradeday import TradeDay
from ginkgo.trading.entities.transfer import Transfer
from ginkgo.trading.entities.adjustfactor import Adjustfactor
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.entities.capital_adjustment import CapitalAdjustment
from ginkgo.trading.entities.mapping import Mapping

__all__ = [
    # 市场数据实体
    "Bar",
    "Tick",
    "StockInfo",
    "TradeDay",
    "Adjustfactor",

    # 交易相关实体
    "Order",
    "Position",
    "Signal",
    "Transfer",
    "CapitalAdjustment",

    # 辅助实体
    "TimeMixin",

    # 通用映射实体
    "Mapping",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 业务实体对象模块"