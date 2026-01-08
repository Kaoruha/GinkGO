"""
Order Service - Phase 3 占位实现

Phase 3: MVP阶段，使用占位实现
Phase 4: 真实订单持久化实现
"""

from typing import List, Optional
from ginkgo.data.services.base_service import BaseService


class OrderService(BaseService):
    """订单服务 - Phase 3 占位实现"""

    def get_orders_by_status(self, status_list: List) -> List:
        """
        根据状态获取订单列表（Phase 3 占位实现）

        Args:
            status_list: 订单状态列表

        Returns:
            空列表（Phase 3 不支持订单持久化）
        """
        # Phase 3: 返回空列表
        return []

    def update_order(self, order) -> bool:
        """
        更新订单（Phase 3 占位实现）

        Args:
            order: 订单对象

        Returns:
            False（Phase 3 不支持订单持久化）
        """
        # Phase 3: 不支持更新
        return False


# 创建全局实例（模块加载时立即创建，支持直接导入使用）
_order_service_instance = None


def _get_order_service_instance() -> OrderService:
    """
    获取 OrderService 单例（内部函数）

    Returns:
        OrderService: 订单服务实例
    """
    global _order_service_instance
    if _order_service_instance is None:
        _order_service_instance = OrderService()
    return _order_service_instance


# 导出实例（支持 order_service.get_orders_by_status() 调用方式）
order_service = _get_order_service_instance()
