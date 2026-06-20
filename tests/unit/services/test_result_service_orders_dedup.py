"""#5842: order 与 order_record 在接口上区分开。

根因: result_service.get_orders 直接把 order_record_crud.find 的全部
状态流转记录(NEW→SUBMITTED→FILLED，每条变更一行)当作"订单"返回，
导致 /orders 端点把同一 order_id 的多条流水当成多个订单(实测 624 条流水
对 208 个唯一订单)。

修复在 service 层做接口分离:
- get_orders        按 order_id 去重，保留时间最新的最终态(=订单语义)
- get_order_records 不去重，返回完整状态流水(=订单记录语义)

CRUD 层不掺业务去重逻辑(符合 API→Service→CRUD→DB 分层边界)。
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.result_service import ResultService


def _rec(order_id: str, status: int, day: int, code: str = "000001.SZ"):
    """模拟一条 order_record(find 按 timestamp desc 返回，调用方负责乱序)。"""
    ts = datetime.datetime(2025, 6, day, 9, 30)
    return SimpleNamespace(
        order_id=order_id, status=status, timestamp=ts, code=code,
        direction=1, order_type=1, volume=100, limit_price=10.0,
        transaction_price=0.0, transaction_volume=0, fee=0.0,
    )


class TestGetOrdersDedup:
    """#5842: get_orders 每个 order_id 只保留最终态。"""

    @pytest.mark.unit
    def test_dedup_keeps_latest_terminal_state_per_order_id(self):
        svc = ResultService(MagicMock())

        # order_id=ord-A: NEW(d1)→SUBMITTED(d2)→FILLED(d3)，最终态 FILLED
        # order_id=ord-B: NEW(d1)→CANCELED(d2)，最终态 CANCELED(失败单也保留)
        # find 按 timestamp desc 交错返回:
        raw = [
            _rec("ord-A", 4, 3),   # FILLED @ d3  ← ord-A 最新
            _rec("ord-A", 2, 2),   # SUBMITTED @ d2
            _rec("ord-B", 5, 2),   # CANCELED @ d2  ← ord-B 最新
            _rec("ord-A", 1, 1),   # NEW @ d1
            _rec("ord-B", 1, 1),   # NEW @ d1
        ]

        crud = MagicMock()
        crud.find.return_value = raw
        crud.count.return_value = len(raw)

        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD", return_value=crud):
            out = svc.get_orders(task_id="task-1")

        assert out.is_success()
        data = out.data["data"]
        total = out.data["total"]
        # 去重后 2 个唯一订单，total 与 data 一致
        assert len(data) == 2, f"expected 2 unique orders, got {len(data)}"
        assert total == 2, f"total must match deduped count, got {total}"

        by_oid = {r.order_id: r for r in data}
        # ord-A 取最终态 FILLED(4)，不是 NEW(1)
        assert by_oid["ord-A"].status == 4, "ord-A 应保留 FILLED 最终态"
        # ord-B 失败单也保留，最终态 CANCELED(5)，不被丢失
        assert by_oid["ord-B"].status == 5, "ord-B 失败单应保留 CANCELED 终态"


class TestGetOrderRecordsFullFlow:
    """#5842: get_order_records 返回完整状态流水，不去重。"""

    @pytest.mark.unit
    def test_returns_all_status_transitions(self):
        svc = ResultService(MagicMock())

        raw = [
            _rec("ord-A", 4, 3),
            _rec("ord-A", 2, 2),
            _rec("ord-A", 1, 1),
        ]
        crud = MagicMock()
        crud.find.return_value = raw

        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD", return_value=crud):
            out = svc.get_order_records(task_id="task-1")

        assert out.is_success()
        data = out.data["data"]
        total = out.data["total"]
        # 完整流水: 3 条状态变更全部保留
        assert len(data) == 3, f"order-records 应保留全部流水, got {len(data)}"
        assert total == 3
        statuses = [r.status for r in data]
        assert statuses == [4, 2, 1], "完整流水按 timestamp desc 保留所有状态"
