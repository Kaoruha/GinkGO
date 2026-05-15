# Upstream: Portfolio Manager (订单查询)、API Server (订单接口)、TradeGatewayAdapter (实盘订单状态)
# Downstream: BaseService (继承基类)、OrderCRUD (订单数据访问)、GLOG (日志)
# Role: OrderService订单业务服务层，编排OrderCRUD提供订单查询、更新、统计、清理等接口

from typing import Any, List, Optional

from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.libs import GLOG


class OrderService(BaseService):
    """订单业务服务层"""

    def __init__(self, crud_repo=None, **kwargs):
        super().__init__(crud_repo=crud_repo, **kwargs)

    # See #18: 从空壳改为真实实现，支持多状态查询
    def get_orders_by_status(self, status_list: List) -> ServiceResult:
        """
        根据状态列表获取订单。

        Args:
            status_list: 订单状态列表

        Returns:
            ServiceResult.data: 合并后的订单列表
        """
        if not status_list:
            return ServiceResult.error("status_list 不能为空")

        try:
            all_orders = []
            for status in status_list:
                orders = self._crud_repo.find(filters={"status": status})
                all_orders.extend(orders)
            return ServiceResult.success(data=all_orders)
        except Exception as e:
            GLOG.ERROR(f"查询订单失败: {e}")
            return ServiceResult.error(str(e))

    def get_orders_by_portfolio(
        self,
        portfolio_id: str,
        status: Any = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> ServiceResult:
        """
        按组合查询订单。

        Args:
            portfolio_id: 组合 UUID
            status: 可选状态过滤
            page: 页码
            page_size: 每页大小

        Returns:
            ServiceResult.data: 订单列表
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")

        try:
            kwargs = dict(portfolio_id=portfolio_id)
            if status is not None:
                kwargs["status"] = status
            if page is not None:
                kwargs["page"] = page
            if page_size is not None:
                kwargs["page_size"] = page_size

            orders = self._crud_repo.find_by_portfolio(**kwargs)
            return ServiceResult.success(data=orders)
        except Exception as e:
            GLOG.ERROR(f"查询组合订单失败: {e}")
            return ServiceResult.error(str(e))

    # See #18: 从空壳改为真实实现
    def update_order(self, order) -> ServiceResult:
        """
        更新订单状态。

        Args:
            order: 订单对象（需有 uuid 属性）

        Returns:
            ServiceResult
        """
        if not getattr(order, "uuid", None):
            return ServiceResult.error("订单缺少 uuid")

        try:
            updates = {}
            for attr in ("status", "transaction_price", "transaction_volume",
                         "remain", "fee", "exchange_order_id", "exchange_response"):
                val = getattr(order, attr, None)
                if val is not None:
                    updates[attr] = val

            self._crud_repo.modify(filters={"uuid": order.uuid}, updates=updates)
            return ServiceResult.success(message="订单更新成功")
        except Exception as e:
            GLOG.ERROR(f"更新订单失败: {e}")
            return ServiceResult.error(str(e))

    def get_order_summary(self, portfolio_id: str) -> ServiceResult:
        """
        订单统计分析。

        Args:
            portfolio_id: 组合 UUID

        Returns:
            ServiceResult.data: {"total_orders", "total_volume", "total_fee", ...}
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")

        try:
            total = self._crud_repo.count_by_portfolio(portfolio_id)
            orders = self._crud_repo.find_by_portfolio(portfolio_id=portfolio_id)

            total_volume = sum(getattr(o, "volume", 0) or 0 for o in orders)
            total_fee = sum(getattr(o, "fee", 0) or 0 for o in orders)
            filled = [o for o in orders if getattr(o, "status", 0) in (3, 4)]

            return ServiceResult.success(data={
                "total_orders": total,
                "total_volume": total_volume,
                "total_fee": float(total_fee),
                "filled_count": len(filled),
            })
        except Exception as e:
            GLOG.ERROR(f"获取订单统计失败: {e}")
            return ServiceResult.error(str(e))

    def delete_orders_by_portfolio(self, portfolio_id: str) -> ServiceResult:
        """
        删除指定组合的所有订单。

        Args:
            portfolio_id: 组合 UUID

        Returns:
            ServiceResult
        """
        if not portfolio_id:
            return ServiceResult.error("portfolio_id 不能为空")

        try:
            self._crud_repo.delete_by_portfolio(portfolio_id)
            return ServiceResult.success(message="订单删除成功")
        except Exception as e:
            GLOG.ERROR(f"删除组合订单失败: {e}")
            return ServiceResult.error(str(e))
