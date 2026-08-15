# Issue: GET /api/v1/data/ticks 返回 meta.total=14365 但 data=[]（有总数无数据）
# Upstream: api.api.data.get_ticks
# Downstream: TickService.get() → {"data": list[MTick], "total": int}
# Role: 验证 service 返回的裸 list 不被端点丢弃

"""
data/ticks items 丢弃修复测试

根因：ADR-029 §Decision 9 后 TickCRUD.find 返回裸 list（无 to_entities），
get_ticks 端点的容器适配写成了 `else []`，把 service 返回的真实数据整体丢弃，
导致 data 恒空而 total 正常（count 独立查询不受影响）。

对照：bars 端点（data.py:426）正确写法是 `else bars_data`。
"""

import asyncio
from unittest.mock import patch, MagicMock
from datetime import datetime


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


def make_tick(uuid="t1", code="000002.SZ", price=12.34):
    """模拟 MTick（裸 ORM 行，无 to_entities）"""
    tick = MagicMock()
    tick.uuid = uuid
    tick.timestamp = datetime(2025, 8, 20, 9, 31, 0)
    tick.price = price
    tick.volume = 100
    tick.direction = 1
    del tick.to_entities
    return tick


class TestGetTicksItemsNotDropped:
    def test_items_returned_when_service_returns_plain_list(self):
        """TDD Red: service 返回裸 list（ADR-029）时 items 不应被丢弃为 []

        场景：service.get 返回 {"data": [2条tick], "total": 14365}。
        修复前：data=[]（list 无 to_entities → else [] 丢弃）。
        修复后：data 含 2 条摘要。
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(
            data={"data": [make_tick("t1"), make_tick("t2")], "total": 14365}
        )

        from api.data import get_ticks

        with patch("api.data.get_tick_service", return_value=mock_service):
            # Query 默认非 int，显式传 page/page_size（对齐 #5689 测试约束）
            result = run_async(get_ticks(
                code="000002.SZ", page=1, page_size=100,
                start_date="2025-08-01", end_date="2025-09-30",
            ))

        assert len(result["data"]) == 2, (
            f"items 应=service 返回的 2 条，实际 {len(result['data'])} 条"
            "（ADR-029 裸 list 被 else [] 丢弃）")
        assert result["meta"]["total"] == 14365
        first = result["data"][0]
        assert first["uuid"] == "t1"
        assert first["code"] == "000002.SZ"
        assert first["price"] == 12.34
        assert first["direction"] == 1
