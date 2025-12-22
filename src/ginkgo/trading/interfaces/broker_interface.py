"""
统一Broker接口定义

支持回测、模拟盘、实盘三种模式的统一接口
使用现有Event系统处理订单生命周期
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable

from ginkgo.enums import ORDERSTATUS_TYPES, EVENT_TYPES
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck, EventOrderPartiallyFilled, EventOrderRejected,
    EventOrderExpired, EventOrderCancelAck
)
from ginkgo.trading.entities import Order


class BrokerExecutionResult:
    """Broker执行结果 - 包含生成事件所需的核心信息"""

    def __init__(
        self,
        status: ORDERSTATUS_TYPES,
        broker_order_id: str = None,
        filled_volume: int = 0,
        filled_price: float = 0.0,
        commission: float = 0.0,
        error_message: str = None,
        trade_id: str = None,
        order: Order = None
    ):
        self.status = status
        self.broker_order_id = broker_order_id
        self.filled_volume = filled_volume
        self.filled_price = filled_price
        self.commission = commission
        self.error_message = error_message
        self.trade_id = trade_id

        # 存储完整的Order对象（用于生成事件的payload）
        self.order = order

    def to_event(self, engine_id: str = None, run_id: str = None):
        """
        转换为对应的Event

        Args:
            engine_id: 引擎ID（由Router提供）
            run_id: 运行ID（由Router提供）

        Returns:
            Event: 转换后的事件对象
        """
        # 使用result中存储的order对象
        if not self.order:
            return None

        # 从order中获取portfolio_id
        portfolio_id = self.order.portfolio_id

        if self.status == ORDERSTATUS_TYPES.SUBMITTED:
            event = EventOrderAck(
                order=self.order,
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                run_id=run_id
            )
            event.broker_order_id = self.broker_order_id or ""
        elif self.status in [ORDERSTATUS_TYPES.PARTIAL_FILLED, ORDERSTATUS_TYPES.FILLED]:
            event = EventOrderPartiallyFilled(
                order=self.order,
                filled_quantity=self.filled_volume,
                fill_price=self.filled_price,
                trade_id=self.trade_id,
                commission=self.commission,
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                run_id=run_id
            )
        elif self.status == ORDERSTATUS_TYPES.CANCELED:
            event = EventOrderCancelAck(
                order=self.order,
                cancelled_quantity=self.filled_volume,
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                run_id=run_id
            )
        elif self.status == ORDERSTATUS_TYPES.REJECTED:
            event = EventOrderRejected(
                order=self.order,
                reject_reason=self.error_message or "Order rejected",
                portfolio_id=portfolio_id,
                engine_id=engine_id,
                run_id=run_id
            )
        else:
            return None

        return event

    def __repr__(self):
        return (f"BrokerExecutionResult(status={self.status.name}, "
                f"broker_order_id={self.broker_order_id}, "
                f"filled_volume={self.filled_volume})")


class IBroker(ABC):
    """统一Broker接口"""

    @abstractmethod
    def submit_order_event(self, event) -> BrokerExecutionResult:
        """提交订单事件"""
        pass

    @abstractmethod
    def validate_order(self, order: Order) -> bool:
        """验证订单"""
        pass

    def supports_immediate_execution(self) -> bool:
        """是否支持立即执行（回测模式）"""
        return False

    def requires_manual_confirmation(self) -> bool:
        """是否需要人工确认（模拟盘模式）"""
        return False

    def supports_api_trading(self) -> bool:
        """是否支持API交易（实盘模式）"""
        return False

    def set_result_callback(self, callback: Callable):
        """设置异步结果回调函数"""
        self._result_callback = callback

    def get_pending_orders(self):
        """获取待处理订单列表（模拟盘用）"""
        return []

    def confirm_execution(self, broker_order_id: str, filled_volume: int, filled_price: float):
        """手动确认成交（模拟盘用）"""
        pass

    def cancel_order(self, broker_order_id: str) -> BrokerExecutionResult:
        """撤销订单"""
        return BrokerExecutionResult(
            status=ORDERSTATUS_TYPES.NEW,
            error_message="Cancel order not implemented"
        )