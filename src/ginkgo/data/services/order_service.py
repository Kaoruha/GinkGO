# Upstream: Portfolio Manager (订单查询)、API Server (订单接口)、TradeGatewayAdapter (实盘订单状态)
# Downstream: BaseService (继承基类)、OrderCRUD (订单数据访问)、GLOG (日志)
# Role: OrderService订单业务服务层，编排OrderCRUD提供订单查询、更新、统计、清理等接口

from typing import Any, List, Optional

import pandas as pd

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

    def get_orders(
        self,
        portfolio_id: Optional[str] = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """
        查询订单记录。

        Args:
            portfolio_id: 组合 ID（可选，为空则返回全部）
            page_size: 返回数量限制，0 表示全部

        Returns:
            ServiceResult.data: ModelList
        """
        try:
            filters = {"is_del": False}
            if portfolio_id:
                filters["portfolio_id"] = portfolio_id

            results = self._crud_repo.find(
                filters=filters,
                page_size=page_size if page_size and page_size > 0 else None,  # None 守卫：0=全量下推 None，裸 >0 对 None 报 TypeError
            )
            return ServiceResult.success(data=results)
        except Exception as e:
            GLOG.ERROR(f"查询订单失败: {e}")
            return ServiceResult.error(str(e))

    def _build_order_filters(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> dict:
        """从业务参数构造 Order CRUD filters。get_orders_df 独立使用（DRY）。

        filter 域与 Signal/Position 对称（portfolio_id/engine_id/task_id），
        固定排除 is_del=True。未抽改 get_orders()，保持纯增量。
        """
        filters = {"is_del": False}
        if portfolio_id:
            filters["portfolio_id"] = portfolio_id
        if engine_id:
            filters["engine_id"] = engine_id
        if task_id:
            filters["task_id"] = task_id
        return filters

    def get_orders_df(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        task_id: Optional[str] = None,
        page: int = None,
        page_size: int = 50,
    ) -> ServiceResult:
        """出口①：data 是 pandas.DataFrame（类型即契约）。

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM ModelList、
        不再绕 ``result.data.to_dataframe()``。内部 find 返 ModelList 后调
        ``to_dataframe()``；空结果返空 ``pd.DataFrame()``。

        #5009：page（0-based）/page_size 分页；MOrder 为 MySQL，order_by=create_at
        desc 保证分页确定性。
        """
        try:
            filters = self._build_order_filters(
                portfolio_id=portfolio_id, engine_id=engine_id, task_id=task_id,
            )
            model_list = self._crud_repo.find(
                filters=filters,
                page=page,
                page_size=page_size if page_size and page_size > 0 else None,  # None 守卫：0=全量下推 None，裸 >0 对 None 报 TypeError
                order_by="create_at",
                desc_order=True,
            )
            df = model_list.to_dataframe() if model_list else pd.DataFrame()
            return ServiceResult.success(
                data=df,
                message=f"Retrieved {len(df)} order records (DataFrame)",
            )
        except Exception as e:
            GLOG.ERROR(f"查询订单(df)失败: {str(e)}")
            return ServiceResult.error(f"查询订单(df)失败: {str(e)}")

    def count_orders(
        self,
        portfolio_id: Optional[str] = None,
        engine_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> ServiceResult:
        """统计匹配订单总数（#5009：metadata.total 真实总数，非 len(df)）。"""
        try:
            filters = self._build_order_filters(
                portfolio_id=portfolio_id, engine_id=engine_id, task_id=task_id,
            )
            count = self._crud_repo.count(filters=filters)
            return ServiceResult.success({"count": count}, f"Successfully counted orders: {count}")
        except Exception as e:
            GLOG.ERROR(f"统计订单失败: {str(e)}")
            return ServiceResult.error(f"统计订单失败: {str(e)}")

    def get_orders_by_portfolio(
        self,
        portfolio_id: str,
        status: Any = None,
        page: Optional[int] = None,
        page_size: Optional[int] = None,
        start_date: Optional[Any] = None,
        end_date: Optional[Any] = None,
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
            if start_date is not None:
                kwargs["start_date"] = start_date
            if end_date is not None:
                kwargs["end_date"] = end_date

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
