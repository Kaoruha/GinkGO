"""
市场状态和时间相关事件

实现T5架构中定义的市场数据事件类型，包括：
- EventClockTick: 时钟节拍事件
- EventMarketStatus: 市场状态事件  
- EventBarClose: K线结束事件
- EventEndOfDay: 日终事件
"""

import datetime
from typing import Optional, Dict, Any
from enum import Enum

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES


class MarketStatus(Enum):
    """市场状态枚举"""
    PRE_MARKET = "PRE_MARKET"      # 盘前
    OPEN = "OPEN"                  # 开盘
    SUSPENDED = "SUSPENDED"        # 暂停交易
    CLOSED = "CLOSED"              # 收盘
    AFTER_HOURS = "AFTER_HOURS"    # 盘后
    HOLIDAY = "HOLIDAY"            # 休市
    
    
class EventClockTick(EventBase):
    """
    时钟节拍事件
    
    用于时间推进控制，是T5架构中TimeProgressionController的核心事件。
    在回测模式下，用于推进逻辑时间；在实盘模式下，用于心跳同步。
    """
    
    def __init__(self, timestamp: datetime.datetime, *args, **kwargs):
        super().__init__(name="ClockTick", *args, **kwargs)
        self.set_type(EVENT_TYPES.CLOCKTICK)
        self._tick_timestamp = timestamp
    
    @property
    def tick_timestamp(self) -> datetime.datetime:
        """获取时钟节拍时间"""
        return self._tick_timestamp
    
    @property
    def timestamp(self) -> datetime.datetime:
        """重写timestamp属性，返回时钟节拍时间"""
        return self._tick_timestamp
    
    def __repr__(self):
        return f"EventClockTick(timestamp={self._tick_timestamp})"


class EventMarketStatus(EventBase):
    """
    市场状态事件
    
    用于通知系统市场状态变化，如开盘、收盘、暂停交易等。
    """
    
    def __init__(self, 
                 status: MarketStatus, 
                 market: str = "SSE",
                 timestamp: Optional[datetime.datetime] = None,
                 *args, **kwargs):
        super().__init__(name="MarketStatus", *args, **kwargs)
        self.set_type(EVENT_TYPES.MARKETSTATUS)
        
        self._market_status = status
        self._market = market
        if timestamp:
            self.set_time(timestamp)
    
    @property
    def market_status(self) -> MarketStatus:
        """获取市场状态"""
        return self._market_status
    
    @property
    def market(self) -> str:
        """获取市场代码"""
        return self._market
    
    def __repr__(self):
        return f"EventMarketStatus(status={self._market_status.value}, market={self._market})"


class EventBarClose(EventBase):
    """
    K线结束事件
    
    标志着一个K线周期的结束，用于触发基于K线的策略计算。
    """
    
    def __init__(self, 
                 bar_type: str = "1min",
                 timestamp: Optional[datetime.datetime] = None,
                 *args, **kwargs):
        super().__init__(name="BarClose", *args, **kwargs)
        self.set_type(EVENT_TYPES.BARCLOSE)
        
        self._bar_type = bar_type
        if timestamp:
            self.set_time(timestamp)
    
    @property
    def bar_type(self) -> str:
        """获取K线类型（如1min, 5min, 1day等）"""
        return self._bar_type
    
    def __repr__(self):
        return f"EventBarClose(bar_type={self._bar_type}, timestamp={self.timestamp})"


class EventEndOfDay(EventBase):
    """
    日终事件
    
    标志着交易日的结束，用于触发日终处理流程，如：
    - 持仓结算
    - 风险评估  
    - 报表生成
    - 数据持久化
    """
    
    def __init__(self, 
                 trading_date: datetime.date,
                 market: str = "SSE",
                 settlement_info: Optional[Dict[str, Any]] = None,
                 *args, **kwargs):
        super().__init__(name="EndOfDay", *args, **kwargs)
        self.set_type(EVENT_TYPES.ENDOFDAY)
        
        self._trading_date = trading_date
        self._market = market
        self._settlement_info = settlement_info or {}
        
        # 设置事件时间为交易日收盘时间
        eod_time = datetime.datetime.combine(trading_date, datetime.time(15, 0))
        self.set_time(eod_time)
    
    @property
    def trading_date(self) -> datetime.date:
        """获取交易日期"""
        return self._trading_date
    
    @property
    def market(self) -> str:
        """获取市场代码"""
        return self._market
    
    @property 
    def settlement_info(self) -> Dict[str, Any]:
        """获取结算信息"""
        return self._settlement_info
    
    def add_settlement_info(self, key: str, value: Any):
        """添加结算信息"""
        self._settlement_info[key] = value
    
    def __repr__(self):
        return f"EventEndOfDay(date={self._trading_date}, market={self._market})"