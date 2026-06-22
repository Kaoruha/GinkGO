"""#5787: 回测订单 limit_price 序列化市价单→None 而非 '0'。

list_orders / list_order_records 两入口应复用 OrderMapper._price_to_dto 的
0→None 市价单哨兵语义, 而非直接 str() 化 (旧实现 str(0)→'0')。
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


def _make_order(limit_price=0.0, order_type=1, status=4):
    """构造回测订单快照。order_type=1 市价单, limit_price=0 表无价哨兵。"""
    return SimpleNamespace(
        uuid="u-1", order_id="ord-1",
        portfolio_id="port-1", engine_id="eng-1", task_id="task-1",
        code="000001.SZ", direction=1, order_type=order_type, status=status,
        volume=100, limit_price=limit_price, transaction_price=10.0,
        transaction_volume=100, fee=5.0,
        timestamp=datetime.datetime(2025, 6, 3, 9, 30),
    )


def _svc_with_orders(orders):
    """装配 BacktestTaskService, mock result_service.get_orders 返回给定订单。"""
    svc = BacktestTaskService(MagicMock())
    result_svc = MagicMock()
    result_svc.get_orders.return_value = ServiceResult(
        success=True, data={"data": orders, "total": len(orders)})
    result_svc.get_order_records.return_value = ServiceResult(
        success=True, data={"data": orders, "total": len(orders)})
    container = MagicMock()
    container.result_service.return_value = result_svc
    return svc, container


class TestListOrdersLimitPriceSerialization:
    """#5787: limit_price 市价单→None, 限价单→str(价格)。"""

    @pytest.mark.unit
    def test_market_order_limit_price_is_null_not_zero(self):
        """市价单(limit_price=0)序列化为 None, 非字符串 '0'。"""
        svc, container = _svc_with_orders([_make_order(limit_price=0, order_type=1)])
        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            result = svc.list_orders("any-uuid")
        assert result.is_success()
        # #5787: 旧实现 str(0)→'0'; 修复后应 None
        assert result.data[0].limit_price is None, \
            f"市价单 limit_price 应为 None, 实际 {result.data[0].limit_price!r}"

    @pytest.mark.unit
    def test_limit_order_limit_price_is_str(self):
        """限价单(limit_price=19.81)序列化为 '19.81'。"""
        svc, container = _svc_with_orders([_make_order(limit_price=19.81, order_type=2)])
        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            result = svc.list_orders("any-uuid")
        assert result.is_success()
        assert result.data[0].limit_price == "19.81"


class TestListOrderRecordsLimitPriceSerialization:
    """#5787: list_order_records 路径同样复用 _price_to_dto。"""

    @pytest.mark.unit
    def test_market_order_limit_price_is_null_not_zero(self):
        """市价单 limit_price=0 序列化为 None, 非字符串 '0'。"""
        svc, container = _svc_with_orders([_make_order(limit_price=0, order_type=1)])
        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            result = svc.list_order_records("any-uuid")
        assert result.is_success()
        assert result.data[0].limit_price is None, \
            f"市价单 limit_price 应为 None, 实际 {result.data[0].limit_price!r}"
