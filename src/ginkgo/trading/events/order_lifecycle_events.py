# Upstream: Backtest Engines(订单状态变化时创建事件)、Portfolio Manager(接收订单生命周期事件更新持仓)
# Downstream: EventBase/EventOrderRelated(继承提供事件基础能力)、EVENT_TYPES(订单事件枚举ORDERACK/ORDERPARTIALLYFILLED/ORDERREJECTED/ORDEREXPIRED/ORDERCANCELACK)、Order实体(订单对象)
# Role: 订单生命周期事件模块定义确认/成交/拒绝/过期/取消等事件类支持交易系统功能和组件集成提供完整业务支持






"""
订单生命周期事件

实现T5架构中定义的完整订单生命周期事件，与真实交易所对齐：
- EventOrderSubmitted: 订单提交事件
- EventOrderAck: 订单确认事件
- EventOrderPartiallyFilled: 部分成交事件
- EventOrderRejected: 订单拒绝事件
- EventOrderExpired: 订单过期事件

这些事件确保回测与实盘交易的一致性体验。
"""

import datetime
from typing import Optional, Dict, Any
from decimal import Decimal

from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.order_related import EventOrderRelated
from ginkgo.trading.entities import Order
from ginkgo.enums import EVENT_TYPES


class EventOrderAck(EventBase):
    """
    订单确认事件
    
    当交易所/Broker确认接收订单时触发。
    这是订单从SUBMITTED状态转为ACCEPTED状态的关键事件。
    """
    
    def __init__(self,
                 order: Order,
                 timestamp: Optional[datetime.datetime] = None,
                 ack_message: str = "Order accepted",
                 portfolio_id: Optional[str] = None,
                 engine_id: Optional[str] = None,
                 run_id: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(name="OrderAck", *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERACK)

        # 设置context信息
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        self._order = order
        self._broker_order_id = ""  # 初始化为空，后续设置
        self._ack_message = ack_message

        # 统一使用payload
        self.payload = order

        if timestamp:
            self.set_time(timestamp)
    
    @property
    def order(self) -> Order:
        """获取订单对象"""
        return self._order
    
    @property
    def broker_order_id(self) -> str:
        """获取交易所分配的订单ID"""
        return self._broker_order_id

    @broker_order_id.setter
    def broker_order_id(self, value: str):
        """设置交易所分配的订单ID"""
        self._broker_order_id = value
    
    @property
    def ack_message(self) -> str:
        """获取确认消息"""
        return self._ack_message
    
    @property
    def code(self) -> str:
        """获取股票代码"""
        return self._order.code if self._order else ""
    
    @property
    def order_id(self) -> str:
        """获取客户端订单ID"""
        return self._order.uuid if self._order else ""
    
    def __repr__(self):
        return f"EventOrderAck(order_id={self.order_id[:8]}, broker_id={self._broker_order_id})"


class EventOrderPartiallyFilled(EventOrderRelated):
    """
    部分成交事件

    当订单发生部分成交时触发。包含本次成交的详细信息。
    """

    def __init__(self,
                 order: Order,
                 filled_quantity: float,
                 fill_price: float,
                 timestamp: Optional[datetime.datetime] = None,
                 trade_id: Optional[str] = None,
                 commission: Optional[Decimal] = None,
                 portfolio_id: Optional[str] = None,
                 engine_id: Optional[str] = None,
                 run_id: Optional[str] = None,
                 *args, **kwargs):
        # 调用EventOrderRelated构造函数，自动设置payload = order
        super().__init__(order=order, name="OrderPartiallyFilled", *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERPARTIALLYFILLED)

        # 设置context信息（覆盖order中的默认值）
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        # 部分成交特有信息
        self._filled_quantity = float(filled_quantity)
        self._fill_price = float(fill_price)
        self._trade_id = trade_id
        self._commission = commission or Decimal('0')

        if timestamp:
            self.set_time(timestamp)
    
    @property
    def order(self) -> Order:
        """获取订单对象"""
        return self._order
    
    @property
    def filled_quantity(self) -> float:
        """获取本次成交数量"""
        return self._filled_quantity
    
    @property
    def fill_price(self) -> float:
        """获取成交价格"""
        return self._fill_price
    
    @property
    def trade_id(self) -> Optional[str]:
        """获取成交记录ID"""
        return self._trade_id
    
    @property
    def commission(self) -> Decimal:
        """获取手续费"""
        return self._commission
    
    @property
    def fill_amount(self) -> float:
        """获取成交金额"""
        return self._filled_quantity * self._fill_price
    
    @property
    def code(self) -> str:
        """获取股票代码"""
        return self._order.code if self._order else ""
    
    @property
    def order_id(self) -> str:
        """获取订单ID"""
        return self._order.uuid if self._order else ""
    
    @property
    def remaining_quantity(self) -> float:
        """获取剩余未成交数量"""
        if self._order:
            return self._order.volume - self._order.transaction_volume - self._filled_quantity
        return 0.0
    
    def __repr__(self):
        return (f"EventOrderPartiallyFilled(order_id={self.order_id[:8]}, "
                f"filled={self._filled_quantity}@{self._fill_price})")


class EventOrderRejected(EventBase):
    """
    订单拒绝事件
    
    当订单被交易所/Broker拒绝时触发。包含拒绝原因。
    """
    
    def __init__(self,
                 order: Order,
                 reject_reason: str,
                 timestamp: Optional[datetime.datetime] = None,
                 reject_code: Optional[str] = None,
                 portfolio_id: Optional[str] = None,
                 engine_id: Optional[str] = None,
                 run_id: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(name="OrderRejected", *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERREJECTED)

        # 设置context信息
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        self._order = order
        self._reject_reason = reject_reason
        self._reject_code = reject_code

        if timestamp:
            self.set_time(timestamp)
    
    @property
    def order(self) -> Order:
        """获取订单对象"""
        return self._order
    
    @property
    def reject_reason(self) -> str:
        """获取拒绝原因"""
        return self._reject_reason
    
    @property
    def reject_code(self) -> Optional[str]:
        """获取拒绝代码"""
        return self._reject_code
    
    @property
    def code(self) -> str:
        """获取股票代码"""
        return self._order.code if self._order else ""
    
    @property
    def order_id(self) -> str:
        """获取订单ID"""
        return self._order.uuid if self._order else ""
    
    def __repr__(self):
        return f"EventOrderRejected(order_id={self.order_id[:8]}, reason='{self._reject_reason}')"


class EventOrderExpired(EventBase):
    """
    订单过期事件
    
    当订单达到过期时间或条件时触发。
    常见于限价单、条件单等有时效性的订单类型。
    """
    
    def __init__(self,
                 order: Order,
                 timestamp: Optional[datetime.datetime] = None,
                 expire_reason: str = "Time expired",
                 portfolio_id: Optional[str] = None,
                 engine_id: Optional[str] = None,
                 run_id: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(name="OrderExpired", *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDEREXPIRED)

        # 设置context信息
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        self._order = order
        self._expire_reason = expire_reason

        if timestamp:
            self.set_time(timestamp)
    
    @property
    def order(self) -> Order:
        """获取订单对象"""
        return self._order
    
    @property
    def expire_reason(self) -> str:
        """获取过期原因"""
        return self._expire_reason
    
    @property
    def code(self) -> str:
        """获取股票代码"""
        return self._order.code if self._order else ""
    
    @property
    def order_id(self) -> str:
        """获取订单ID"""
        return self._order.uuid if self._order else ""
    
    @property
    def expired_quantity(self) -> float:
        """获取过期的未成交数量"""
        if self._order:
            return self._order.volume - self._order.transaction_volume
        return 0.0
    
    def __repr__(self):
        return (f"EventOrderExpired(order_id={self.order_id[:8]}, "
                f"expired_qty={self.expired_quantity}, reason='{self._expire_reason}')")


class EventOrderCancelAck(EventBase):
    """
    订单撤销确认事件
    
    当撤销订单请求被确认时触发。
    """
    
    def __init__(self,
                 order: Order,
                 cancelled_quantity: float,
                 timestamp: Optional[datetime.datetime] = None,
                 cancel_reason: str = "User cancelled",
                 portfolio_id: Optional[str] = None,
                 engine_id: Optional[str] = None,
                 run_id: Optional[str] = None,
                 *args, **kwargs):
        super().__init__(name="OrderCancelAck", *args, **kwargs)
        self.set_type(EVENT_TYPES.ORDERCANCELACK)

        # 设置context信息
        if portfolio_id is not None:
            self.portfolio_id = portfolio_id
        if engine_id is not None:
            self.engine_id = engine_id
        if run_id is not None:
            self.run_id = run_id

        self._order = order
        self._cancelled_quantity = float(cancelled_quantity)
        self._cancel_reason = cancel_reason

        if timestamp:
            self.set_time(timestamp)
    
    @property
    def order(self) -> Order:
        """获取订单对象"""
        return self._order
    
    @property
    def cancelled_quantity(self) -> float:
        """获取撤销数量"""
        return self._cancelled_quantity
    
    @property
    def cancel_reason(self) -> str:
        """获取撤销原因"""
        return self._cancel_reason
    
    @property
    def code(self) -> str:
        """获取股票代码"""
        return self._order.code if self._order else ""
    
    @property
    def order_id(self) -> str:
        """获取订单ID"""
        return self._order.uuid if self._order else ""
    
    def __repr__(self):
        return (f"EventOrderCancelAck(order_id={self.order_id[:8]}, "
                f"cancelled_qty={self._cancelled_quantity})")