"""#5429: result_service.get_orders 去重后内存分页核心逻辑。

get_orders 不能像 get_signals 那样把分页下推到 crud.find——按 order_id 取最新
终态的去重必须基于全量流水, 否则按流水切片会切断同一 order_id 的多条状态记录,
跨页去重丢失订单。本测试在 CRUD 入口(_find_order_records 的 OrderRecordCRUD.find)
注入流水, 验证"去重 → 再分页"的完整交互(total 独立、切片边界正确)。
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.result_service import ResultService


def _rec(order_id: str, status: int, day: int):
    """构造一条订单流水(timestamp 由 day 决定, 控制去重时的'最新态'顺序)。"""
    return SimpleNamespace(
        uuid=f"u-{order_id}-{status}", order_id=order_id,
        portfolio_id="port-1", engine_id="eng-1", task_id="task-1",
        code="000001.SZ", direction=1, order_type=1, status=status,
        volume=100, limit_price=10.0, transaction_price=10.0,
        transaction_volume=100, fee=5.0,
        timestamp=datetime.datetime(2025, 6, day, 9, 30),
    )


# 5 条流水, 3 个唯一 order_id(A 各 2 条, B 各 2 条, C 1 条)
# find 按 timestamp desc 返回; 去重后 unique = [C, B, A]
FLOW = [
    _rec("ord-C", 4, 5),   # day5 最新
    _rec("ord-B", 4, 4),
    _rec("ord-A", 4, 3),
    _rec("ord-B", 1, 2),   # B 的旧态, 去重丢弃
    _rec("ord-A", 2, 1),   # A 的旧态, 去重丢弃
]
EXPECTED_UNIQUE_IDS = ["ord-C", "ord-B", "ord-A"]


class TestGetOrdersPaginateAfterDedup:
    """#5429: get_orders 先按 order_id 去重, 再对 unique 列表分页。"""

    @pytest.mark.unit
    def test_page_one_returns_first_slice_with_full_total(self):
        svc = ResultService(MagicMock())
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD.find", return_value=FLOW):
            result = svc.get_orders("task-1", page=1, page_size=2)

        assert result.is_success()
        data = result.data["data"]
        total = result.data["total"]
        # 去重后 3 个 unique; page_size=2 切前 2 条
        assert total == 3, "total 必须是去重后唯一订单数, 非流水数(5)也非当前页条数(2)"
        assert len(data) == 2
        assert [getattr(r, "order_id") for r in data] == ["ord-C", "ord-B"]

    @pytest.mark.unit
    def test_page_two_returns_remainder_with_same_total(self):
        """翻页 total 不变(独立于 page), 第 2 页返回剩余 unique。"""
        svc = ResultService(MagicMock())
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD.find", return_value=FLOW):
            result = svc.get_orders("task-1", page=2, page_size=2)

        assert result.is_success()
        data = result.data["data"]
        assert result.data["total"] == 3, "第 2 页 total 必须仍为 3(去重总数), 非当前页条数"
        assert len(data) == 1
        assert getattr(data[0], "order_id") == "ord-A"

    @pytest.mark.unit
    def test_large_page_size_returns_all_unique(self):
        """page_size >= unique 数时返回全部 unique(等价旧行为), total 仍独立。"""
        svc = ResultService(MagicMock())
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD.find", return_value=FLOW):
            result = svc.get_orders("task-1", page=1, page_size=50)

        data = result.data["data"]
        assert len(data) == 3
        assert [getattr(r, "order_id") for r in data] == EXPECTED_UNIQUE_IDS
        assert result.data["total"] == 3

    @pytest.mark.unit
    def test_total_independent_of_page_size(self):
        """不同 page_size 必须返回相同 total(关键分页语义, brief 验收点)。"""
        svc = ResultService(MagicMock())
        totals = []
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD.find", return_value=FLOW):
            for ps in (1, 2, 3, 50):
                r = svc.get_orders("task-1", page=1, page_size=ps)
                totals.append(r.data["total"])
        assert len(set(totals)) == 1 and totals[0] == 3, \
            f"total 必须与 page_size 无关, 实测: {totals}"

    @pytest.mark.unit
    def test_default_page_size_returns_all_unique(self):
        """page_size 默认 0=全量(向后兼容 engine.py 分析引擎/CLI --trades 全量调用)。

        这两处内部调用方不传分页参数, 依赖 get_orders 默认返回全部去重订单。
        端点层(Query 默认 50)才显式分页。改此默认会破坏分析引擎完整性。
        """
        svc = ResultService(MagicMock())
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD.find", return_value=FLOW):
            result = svc.get_orders("task-1")  # 不传 page/page_size

        data = result.data["data"]
        assert len(data) == 3, "默认(page_size=0)应返回全部 unique, 非 50 切片"
        assert [getattr(r, "order_id") for r in data] == EXPECTED_UNIQUE_IDS
