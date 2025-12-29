# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: 经纪商模块公共接口导出模拟/手动/实盘/A股等经纪商实现支持交易系统功能支持订单执行和交易模拟提供多市场支持






"""
交易代理模块

提供统一的交易代理接口和实现，支持：
- 模拟交易代理(SimBroker)
- 实盘交易代理(LiveBroker) 
- 人工确认代理(ManualBroker)
- 纸面交易代理(PaperBroker)
"""

from .interfaces import (
    IBroker,
    BrokerType,
    OrderType,
    OrderSide,
    OrderStatus,
    PositionSide,
    ManualConfirmationRequired,
    TradingOrder,
    Position,
    Trade,
    AccountBalance,
    BrokerStats
)

from .base_broker import BaseBroker
# from .sim_broker import SimBroker
# from .manual_broker import ManualBroker  
# from .paper_broker import PaperBroker

__all__ = [
    # 接口和枚举
    'IBroker',
    'BrokerType',
    'OrderType',
    'OrderSide', 
    'OrderStatus',
    'PositionSide',
    'ManualConfirmationRequired',
    
    # 数据类
    'TradingOrder',
    'Position',
    'Trade',
    'AccountBalance',
    'BrokerStats',
    
    # 实现类
    'BaseBroker',
    # 'SimBroker',
    # 'ManualBroker',
    # 'PaperBroker'
]