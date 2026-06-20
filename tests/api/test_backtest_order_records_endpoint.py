"""#5842: 新增 GET /{uuid}/order-records 端点，暴露完整订单状态流水。

/orders 已去重返回订单(最终态); /order-records 返回同一 order_id 的全部
状态变更记录。本测试覆盖 API 路由: 直调路由函数, mock task_service,
断言 /order-records 调用 list_order_records(非 list_orders)并原样透传完整流水。
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult


def _item_dict(order_id, status):
    return {"order_id": order_id, "status": status}


def _mock_item(order_id, status):
    m = MagicMock()
    m.dict.return_value = _item_dict(order_id, status)
    return m


class TestOrderRecordsEndpoint:
    """#5842: /{uuid}/order-records 端点返回完整流水。"""

    @pytest.mark.unit
    def test_order_records_returns_full_flow(self):
        from api.backtest import get_backtest_order_records

        full = [_mock_item("ord-A", 4), _mock_item("ord-A", 2), _mock_item("ord-A", 1)]
        sr = ServiceResult(success=True, data=full)
        sr.set_metadata("total", 3)

        task_service = MagicMock()
        task_service.list_order_records.return_value = sr

        with patch("api.backtest.get_backtest_task_service", return_value=task_service):
            resp = asyncio.run(get_backtest_order_records("any-uuid"))

        # 路由调用了 list_order_records, 透传完整 3 条流水
        task_service.list_order_records.assert_called_once_with("any-uuid")
        task_service.list_orders.assert_not_called()
        assert resp["data"] == [
            _item_dict("ord-A", 4), _item_dict("ord-A", 2), _item_dict("ord-A", 1),
        ]
        assert resp["meta"]["total"] == 3, "total 应反映完整流水数(3)"
