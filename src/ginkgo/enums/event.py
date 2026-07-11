"""事件链路域枚举：事件类型（PriceUpdate→Strategy→Signal→Portfolio→Order→Fill）。

从 ginkgo/enums.py 拆分（#3838）。聚合 re-export 入口：ginkgo/enums/__init__.py。
"""

from .base import EnumBase


class EVENT_TYPES(EnumBase):
    """
    Types of Events. Extended for unified event-driven architecture.
    """

    VOID = -1
    OTHER = 0
    
    # Market Data Events (1-19)
    PRICEUPDATE = 1
    CLOCKTICK = 2
    MARKETSTATUS = 3
    BARCLOSE = 4
    ENDOFDAY = 5
    
    # Order Lifecycle Events (20-39) 
    ORDERSUBMITTED = 20
    ORDERACK = 21
    ORDERPARTIALLYFILLED = 22
    ORDERFILLED = 23           # 完全成交（兼容旧版，实际使用ORDERPARTIALLYFILLED）
    ORDERREJECTED = 24
    ORDERCANCELACK = 25
    ORDEREXPIRED = 26
    
    # Portfolio Events (40-59)
    POSITIONUPDATE = 40
    CAPITALUPDATE = 41
    PORTFOLIOUPDATE = 42
    INTERESTUPDATE = 43
    
    # Risk Management Events (60-79)
    RISKBREACH = 60
    POSITIONLIMITEXCEEDED = 61
    DAILYLOSSLIMITEXCEEDED = 62
    
    # System Events (80-99)
    NEXTPHASE = 80
    TIME_ADVANCE = 81  # 时间推进事件类型
    COMPONENT_TIME_ADVANCE = 82  # 组件时间推进事件类型
    ENGINESTART = 83
    ENGINESTOP = 84
    
    # Strategy Events (100-119)
    SIGNALGENERATION = 100
    
    # News and External Events (120-139)
    NEWSRECIEVE = 120


__all__ = ['EVENT_TYPES']
