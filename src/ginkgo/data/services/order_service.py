# Upstream: Portfolio Manager (订单查询)、API Server (订单接口)、TradeGatewayAdapter (实盘订单状态)
# Downstream: BaseService (继承基类)、OrderCRUD (订单数据访问)、OrderMapper (Entity↔ORM 收敛)、GLOG (日志)
# Role: OrderService订单业务服务层，编排OrderCRUD提供订单查询、更新、统计、清理等接口

from typing import Any, List, Optional

import pandas as pd

from ginkgo.data.mappers import OrderMapper, models_to_dataframe
from ginkgo.data.services.base_service import BaseService, ServiceResult
from ginkgo.entities import Order
from ginkgo.libs import GLOG, retry


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
            ServiceResult.data: list
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

        ADR-010：API/CLI 消费 DataFrame 语义时走此出口，不接触 ORM list、
        不再绕 ``result.data.to_dataframe()``。内部 find 返 list 后调
        ``models_to_dataframe``；空结果返空 ``pd.DataFrame()``。

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
            df = models_to_dataframe(model_list) if model_list else pd.DataFrame()
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

    def upsert_order(self, order: Order, status_override=None) -> ServiceResult:
        """ADR-029 Task 7 upsert seam + Task 8 ``status_override``（回测 4 态接线）。

        存在判断：``order_crud.get_by_uuid(order.uuid)``（``find({"uuid":..., "is_del": False})``）。
          - 存在 → modify 语义（仅更可变字段：status / transaction_* / remain / fee /
            exchange_*）
          - 不存在 → ``OrderMapper.entity_to_model(order)`` → ``order_crud.add(model)``
            （入站经 mapper 收敛转换，退役 ``_convert_input_item`` hook）

        ``status_override``（Task 8）：回测事件链中 ``order.status`` 是**事件前状态**
        （如 NEW/SUBMITTED），而 MOrder 须写**事件后状态**（FILLED/REJECTED/CANCELED）。
        传入 ``status_override`` 显式指定目标状态；``None`` 时回退 ``order.status``。
        回测 4 态天然分支：NEW→new uuid→insert；FILLED/REJECTED/CANCELED→同 uuid→update。

        设计选择（存在判断）：用 ``get_by_uuid`` 而非 ``modify`` 返 affected_rows。
        原因：``BaseCRUD.modify`` 公开签名是 ``-> None``（``_do_modify`` 虽返 rowcount
        但 ``order_crud.modify`` override 不传播）；改 ``modify`` 签名会侵入 BaseCRUD
        契约（ADR-029 §Decision 8 仅允许 Task 1-10 微调 BaseCRUD 本体）。``get_by_uuid``
        是显式存在判断，语义清晰，多一次 SELECT 但避开签名破坏。

        Args:
            order: Order Entity（需有 uuid）
            status_override: 目标状态（ORDERSTATUS_TYPES）；None 用 order.status

        Returns:
            ServiceResult.data: {"uuid": 写入/更新 model.uuid, "action": "insert"|"update"}
        """
        if not getattr(order, "uuid", None):
            return ServiceResult.error("订单缺少 uuid")

        effective_status = (
            status_override if status_override is not None
            else getattr(order, "status", None)
        )

        try:
            existing = self._crud_repo.get_by_uuid(order.uuid)
            if existing is not None:
                # modify 语义：构造 updates（status 用 effective_status，
                # 不走 update_order 因其硬读 order.status 无法 override）
                updates = {}
                if effective_status is not None:
                    updates["status"] = effective_status
                for attr in ("transaction_price", "transaction_volume",
                             "remain", "fee", "exchange_order_id", "exchange_response"):
                    val = getattr(order, attr, None)
                    if val is not None:
                        updates[attr] = val

                self._crud_repo.modify(filters={"uuid": order.uuid}, updates=updates)
                return ServiceResult.success(
                    data={"uuid": order.uuid, "action": "update"},
                    message=f"Order upserted (update): {order.uuid}",
                )

            # insert 语义：Order Entity → mapper → crud.add（status 用 effective）
            model = OrderMapper.entity_to_model(order)
            if effective_status is not None:
                model.status = effective_status
            self._crud_repo.add(model)
            return ServiceResult.success(
                data={"uuid": model.uuid, "action": "insert"},
                message=f"Order upserted (insert): {model.uuid}",
            )
        except Exception as e:
            GLOG.ERROR(f"upsert_order failed: {e}")
            return ServiceResult.error(str(e))

    @retry(max_try=3)
    def create_order_record(self, *, signal_id: str, **kwargs) -> ServiceResult:
        """ADR-029 Task 8：MOrderRecord 写入收敛到 OrderService。

        原 ``result_service.create_order_record:648`` 写逻辑迁此。``result_service``
        改 thin delegate 委托本方法——签名 ``**kwargs`` 不变以保调用方透明
        （``trade_gateway:338`` / ``t1backtest:522``）。

        OrderService 统管 MOrder（``upsert_order``）+ MOrderRecord（本方法），
        但 ``OrderRecordCRUD`` 不经构造注入（避免 container wiring 改动），
        走懒 import——与原 ``result_service`` 写路径同模式。

        Args:
            signal_id: 血缘字段,keyword-only 显式必传。三态行(NEW/SUBMITTED/FILLED)
                全覆盖;回测订单必有值,手工/外部单传空串。显式签名让漏传在调用
                瞬间 TypeError,而非 CRUD 校验失败后经 retry 放大才在日志暴露
            **kwargs: MOrderRecord 字段（order_id/portfolio_id/engine_id/task_id/
                code/direction/order_type/status/volume/limit_price/frozen_money/
                frozen_volume/transaction_price/transaction_volume/remain/fee/
                timestamp/business_timestamp）

        Returns:
            ServiceResult: 创建结果
        """
        try:
            from ginkgo.data.crud.order_record_crud import OrderRecordCRUD
            order_record_crud = OrderRecordCRUD()

            # signal_id 是 keyword-only 显式参数,不在 **kwargs 内,须显式传递
            order_record_crud.create(signal_id=signal_id, **kwargs)

            GLOG.INFO(f"订单记录创建成功: code={kwargs.get('code')} task_id={kwargs.get('task_id')}")
            return ServiceResult.success({"message": "Order record created"})

        except Exception as e:
            GLOG.ERROR(f"创建订单记录失败: {e}")
            return ServiceResult.error(f"创建订单记录失败: {e}")

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
