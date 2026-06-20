"""#5842: task_service 层 order/order_record 双语义分流。

list_orders       → result_service.get_orders (去重, 订单语义)
list_order_records → result_service.get_order_records (完整流水, 记录语义)

本测试固定分流契约: 同一原始流水经两条入口返回不同数量,
证明 /orders 端点拿到的是去重订单, /order-records 拿到的是完整记录。
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


def _rec(order_id: str, status: int, day: int):
    return SimpleNamespace(
        uuid=f"u-{order_id}-{status}", order_id=order_id,
        portfolio_id="port-1", engine_id="eng-1", task_id="task-1",
        code="000001.SZ", direction=1, order_type=1, status=status,
        volume=100, limit_price=10.0, transaction_price=10.0,
        transaction_volume=100, fee=5.0,
        timestamp=datetime.datetime(2025, 6, day, 9, 30),
    )


class TestListOrdersDedupRouting:
    """#5842: list_orders 与 list_order_records 分流到去重/完整两个源。"""

    @pytest.mark.unit
    def test_list_orders_deduped_and_list_order_records_full(self):
        svc = BacktestTaskService(MagicMock())

        full = [_rec("ord-A", 4, 3), _rec("ord-A", 2, 2), _rec("ord-A", 1, 1)]
        deduped = [_rec("ord-A", 4, 3)]  # 仅最终态一条

        result_svc = MagicMock()
        result_svc.get_orders.return_value = ServiceResult(
            success=True, data={"data": deduped, "total": 1})
        result_svc.get_order_records.return_value = ServiceResult(
            success=True, data={"data": full, "total": 3})

        container = MagicMock()
        container.result_service.return_value = result_svc

        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            orders = svc.list_orders("any-uuid")
            records = svc.list_order_records("any-uuid")

        assert orders.is_success()
        assert records.is_success()
        # /orders 入口 → 去重订单(1 个唯一订单)
        assert len(orders.data) == 1, "list_orders 应返回去重后订单"
        assert orders.metadata.get("total") == 1
        # /order-records 入口 → 完整流水(3 条状态变更)
        assert len(records.data) == 3, "list_order_records 应返回完整流水"
        assert records.metadata.get("total") == 3
