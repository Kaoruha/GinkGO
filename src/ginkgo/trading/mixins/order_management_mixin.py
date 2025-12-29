# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Order Management Mixin混入类提供OrderManagementMixin订单管理功能扩展






"""
订单管理Mixin - 内存版本

专注于回测过程中的内存订单状态管理，不涉及数据库操作。
提供统一的订单队列、跟踪和状态管理功能。
"""

from typing import List, Dict, Any, Optional
from datetime import datetime

from ginkgo.trading.entities.order import Order


class OrderManagementMixin:
    """
    订单管理Mixin

    提供内存中的订单队列管理和跟踪功能，专注于回测过程中的状态管理。
    不涉及任何数据库操作，纯内存操作以保证性能。
    """

    def __init__(self):
        """初始化订单管理数据结构"""
        super().__init__()

        # 待处理订单队列 - 按照FIFO顺序处理
        self._pending_orders: List[Order] = []

        # 处理中订单跟踪 - broker_order_id: order_info
        self._processing_orders: Dict[str, Dict[str, Any]] = {}

        # 执行历史记录 - 用于调试和分析
        self._execution_history: List[Dict[str, Any]] = []

    def add_pending_order(self, order: Order) -> None:
        """
        添加待处理订单到队列

        Args:
            order: 待处理的订单对象
        """
        if hasattr(order, 'log'):
            order.log("DEBUG", f"Order added to pending queue: {order.uuid[:8]}")
        self._pending_orders.append(order)

    def get_pending_orders(self) -> List[Order]:
        """
        获取所有待处理订单的副本

        Returns:
            List[Order]: 待处理订单列表
        """
        return list(self._pending_orders)

    def get_pending_order_count(self) -> int:
        """
        获取待处理订单数量

        Returns:
            int: 待处理订单数量
        """
        return len(self._pending_orders)

    def clear_pending_orders(self) -> None:
        """清空待处理订单队列"""
        if hasattr(self, 'log'):
            self.log("DEBUG", f"Cleared {len(self._pending_orders)} pending orders")
        self._pending_orders.clear()

    def track_order(self, broker_order_id: str, order_info: Dict[str, Any]) -> None:
        """
        跟踪已提交的订单

        Args:
            broker_order_id: Broker分配的订单ID
            order_info: 订单信息字典，包含订单对象、提交时间等
        """
        self._processing_orders[broker_order_id] = {
            'order': order_info.get('order'),
            'submit_time': order_info.get('submit_time', datetime.now()),
            'result': order_info.get('result'),
            'broker': order_info.get('broker'),
        }

        if hasattr(self, 'log'):
            self.log("DEBUG", f"Started tracking order: {broker_order_id}")

    def get_tracked_order(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """
        获取跟踪的订单信息

        Args:
            broker_order_id: Broker订单ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，如果不存在返回None
        """
        return self._processing_orders.get(broker_order_id)

    def remove_tracked_order(self, broker_order_id: str) -> Optional[Dict[str, Any]]:
        """
        移除并返回跟踪的订单信息

        Args:
            broker_order_id: Broker订单ID

        Returns:
            Optional[Dict[str, Any]]: 被移除的订单信息，如果不存在返回None
        """
        order_info = self._processing_orders.pop(broker_order_id, None)

        if order_info and hasattr(self, 'log'):
            self.log("DEBUG", f"Stopped tracking order: {broker_order_id}")

        return order_info

    def get_tracked_orders(self) -> Dict[str, Dict[str, Any]]:
        """
        获取所有跟踪订单的副本

        Returns:
            Dict[str, Dict[str, Any]]: 跟踪订单字典的副本
        """
        return dict(self._processing_orders)

    def get_tracked_order_count(self) -> int:
        """
        获取跟踪订单数量

        Returns:
            int: 跟踪订单数量
        """
        return len(self._processing_orders)

    def add_execution_record(self, order: Order, result, broker: Any = None) -> None:
        """
        添加执行历史记录

        Args:
            order: 执行的订单
            result: 执行结果
            broker: 使用的Broker（可选）
        """
        record = {
            'timestamp': datetime.now(),
            'order_uuid': order.uuid,
            'order_code': order.code,
            'order_direction': order.direction,
            'order_volume': order.volume,
            'result_status': result.status if hasattr(result, 'status') else None,
            'result_broker_order_id': getattr(result, 'broker_order_id', None),
            'broker': broker.__class__.__name__ if broker else None,
        }

        self._execution_history.append(record)

        # 限制历史记录数量，避免内存无限增长
        if len(self._execution_history) > 10000:
            self._execution_history = self._execution_history[-5000:]

    def get_execution_history(self) -> List[Dict[str, Any]]:
        """
        获取执行历史记录

        Returns:
            List[Dict[str, Any]]: 执行历史记录
        """
        return list(self._execution_history)

    def get_execution_history_count(self) -> int:
        """
        获取执行历史记录数量

        Returns:
            int: 执行历史记录数量
        """
        return len(self._execution_history)

    def clear_execution_history(self) -> None:
        """清空执行历史记录"""
        self._execution_history.clear()

        if hasattr(self, 'log'):
            self.log("DEBUG", "Cleared execution history")

    def get_order_status_summary(self) -> Dict[str, int]:
        """
        获取订单状态摘要

        Returns:
            Dict[str, int]: 各状态订单数量统计
        """
        return {
            'pending_orders': len(self._pending_orders),
            'processing_orders': len(self._processing_orders),
            'execution_history': len(self._execution_history),
        }