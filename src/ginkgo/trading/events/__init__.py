"""
Ginkgo Trading Events Module

统一的T5事件驱动架构 - 完整事件体系导出
"""

# === 基础事件类 ===
from ginkgo.trading.events.base_event import EventBase

# === 市场数据事件 (T5新增) ===
from ginkgo.trading.events.market_events import (
    EventClockTick,
    EventMarketStatus,
    EventBarClose,
    EventEndOfDay,
    MarketStatus
)

# === 订单生命周期事件 (T5新增) ===
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck,
    EventOrderPartiallyFilled,
    EventOrderRejected,
    EventOrderExpired,
    EventOrderCancelAck
)

# === 投资组合事件 (T5新增) ===
from ginkgo.trading.events.portfolio_events import (
    EventPortfolioUpdate,
    EventRiskBreach,
    PortfolioSnapshot,
    RiskBreachDetails
)

# === 兴趣标的事件（去订阅/广播） ===
from ginkgo.trading.events.interest_update import EventInterestUpdate

# === 保留的原有事件类 ===
from ginkgo.trading.events.capital_update import EventCapitalUpdate
from ginkgo.trading.events.order_related import EventOrderRelated
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.position_update import EventPositionUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.next_phase import EventNextPhase
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.events.component_time_advance import (
    EventComponentTimeAdvance,
    ComponentTimeAdvanceInfo
)
from ginkgo.trading.events.execution_confirmation import (
    EventExecutionConfirmed,
    EventExecutionRejected,
    EventExecutionTimeout,
    EventExecutionCanceled
)


# === 导出所有事件类 ===
__all__ = [
    # 基础事件类
    "EventBase",
    
    # T5新增事件类
    # 市场数据事件
    "EventClockTick",
    "EventMarketStatus", 
    "EventBarClose",
    "EventEndOfDay",
    "MarketStatus",
    
    # 订单生命周期事件
    "EventOrderAck",
    "EventOrderPartiallyFilled", 
    "EventOrderRejected",
    "EventOrderExpired",
    "EventOrderCancelAck",
    
    # 投资组合事件
    "EventPortfolioUpdate",
    "EventRiskBreach",
    "PortfolioSnapshot",
    "RiskBreachDetails",
    "EventInterestUpdate",
    
    # 保留的原有事件类
    "EventCapitalUpdate",
    "EventOrderRelated",
    "EventPriceUpdate",
    "EventPositionUpdate",
    "EventSignalGeneration",
    "EventNextPhase",
    "EventTimeAdvance",
    "EventComponentTimeAdvance",
    "ComponentTimeAdvanceInfo",
    "EventExecutionConfirmed",
    "EventExecutionRejected",
    "EventExecutionTimeout",
    "EventExecutionCanceled",
]
