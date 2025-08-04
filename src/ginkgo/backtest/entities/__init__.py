"""
Entities Module - 业务实体对象

包含 Ginkgo Backtest 框架中的核心业务实体，这些是内存中的数据容器类，
用于在回测过程中传递和管理业务数据。

- 市场数据实体：Bar, Tick, StockInfo, TradeDay, Adjustfactor
- 交易相关实体：Order, Position, Signal, Transfer
- 辅助实体：TimeRelated

这些实体类继承自 Base 类，提供 UUID 管理和 DataFrame 转换能力，
与数据库模型（data.models）不同，专门用于业务逻辑处理。
"""

from .bar import Bar
from .order import Order
from .position import Position
from .signal import Signal
from .stockinfo import StockInfo
from .tick import Tick
from .tradeday import TradeDay
from .transfer import Transfer
from .adjustfactor import Adjustfactor
from .time_related import TimeRelated

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
    
    # 辅助实体
    "TimeRelated",
]

__version__ = "3.0.0"
__description__ = "Ginkgo Backtest 业务实体对象模块"