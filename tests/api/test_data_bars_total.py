# Issue: #5689 — GET /api/v1/data/bars 的 meta.total 返回当前页条数而非 DB 总记录数
# Upstream: api.api.data.get_bars
# Downstream: BarService.get() (分页 items) + BarService.count() (DB 总数)
# Role: 验证 total 来自独立 count 查询，与 page_size 解耦

"""
data/bars total 字段修复测试（#5689）

根因：get_bars 端点 total=len(bar_summaries)，bar_summaries 是已分页结果，
len() 随 page_size 变化，非 DB 总记录数。

修复：仿 stocks 端点（data.py:271）单独调 bar_service.count()，
total 来自 count 结果，与分页 items 数解耦。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime


def run_async(coro):
    return asyncio.run(coro)


def make_mock_result(data=None, success=True):
    result = MagicMock()
    result.is_success.return_value = success
    result.data = data
    return result


def make_bar(uuid="b1", code="000001.SZ"):
    """模拟 MBar（有 uuid/code/timestamp/OHLCV，无 to_entities）"""
    bar = MagicMock()
    bar.uuid = uuid
    bar.code = code
    bar.timestamp = datetime(2025, 1, 1)
    bar.open = 1.0
    bar.high = 2.0
    bar.low = 0.5
    bar.close = 1.5
    bar.volume = 100.0
    bar.amount = 200.0
    del bar.to_entities
    return bar


class TestGetBarsTotalFromDB:
    """#5689: meta.total 来自 DB count，不随 page_size 变化"""

    def test_total_from_db_count_not_items_count(self):
        """TDD Red: total 应来自 bar_service.count()，而非 len(items)

        场景：当前页返回 2 条，但 DB 共 50 条匹配。
        修复前：total=len(bar_summaries)=2（错）
        修复后：total=bar_service.count()=50（对）
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(
            data=[make_bar("b1"), make_bar("b2")]
        )
        # DB 总数 50，远大于当前页 2 条
        mock_service.count.return_value = make_mock_result(data=50)

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            # 显式传 page/page_size：直接调端点时 Query(default=100,ge=1,le=500)
            # 默认是 Query 对象非 int（#5689 测试约束，对齐 arch_api_test_query_default_direct_await）
            result = run_async(get_bars(code="000001.SZ", page=1, page_size=100))

        assert result["meta"]["total"] == 50, (
            f"total 应=DB count(50)，非 len(items)(2)，实际 {result['meta']['total']}")

    def test_total_invariant_across_page_sizes(self):
        """验收1: 同 code+日期范围，不同 page_size 返回相同 total

        这是 #5689 的核心验收标准。修复前 page_size=5→total=5，
        page_size=100→total=100（随页大小变化）。修复后两者都=DB 总数。
        """
        def _run(page_size):
            mock_service = MagicMock()
            mock_service.get.return_value = make_mock_result(data=[make_bar("b1")])
            mock_service.count.return_value = make_mock_result(data=50)

            from api.data import get_bars
            with patch("api.data.get_bar_service", return_value=mock_service):
                return run_async(get_bars(code="000001.SZ", page=1, page_size=page_size))

        total_small = _run(page_size=10)["meta"]["total"]
        total_large = _run(page_size=100)["meta"]["total"]

        assert total_small == total_large == 50, (
            f"不同 page_size total 应相同(=DB 50)，实际 ps=10→{total_small}, ps=100→{total_large}")

    def test_count_uses_same_filters_as_get(self):
        """验收2: count 查询与列表查询共用同一 where 条件

        count 须收到与 get 相同的 code/frequency/start_date/end_date，
        否则 total 与 items 条件不匹配（如按 code 过滤的 total 包含其他 code）。
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(data=[make_bar("b1")])
        mock_service.count.return_value = make_mock_result(data=50)

        from api.data import get_bars
        with patch("api.data.get_bar_service", return_value=mock_service):
            run_async(get_bars(
                code="000001.SZ", page=1, page_size=100,
                start_date="2025-01-01", end_date="2025-12-31",
            ))

        count_kwargs = mock_service.count.call_args.kwargs
        assert count_kwargs.get("code") == "000001.SZ", (
            f"count 须收 code 过滤，实际 {count_kwargs.get('code')}")
        assert count_kwargs.get("start_date") is not None, "count 须收 start_date 过滤"
        assert count_kwargs.get("end_date") is not None, "count 须收 end_date 过滤"

    def test_count_failure_falls_back_to_items_len(self):
        """降级: count 查询失败时 total 回退为 len(items)（旧行为），不抛 500

        设计意图：count 是独立 DB 查询，可能因连接/超时失败。
        失败时降级而非 500，保证列表仍可用（total 暂时不准但数据不丢）。
        """
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(
            data=[make_bar("b1"), make_bar("b2")]
        )
        # count 失败
        mock_service.count.return_value = make_mock_result(success=False, data=None)

        from api.data import get_bars
        with patch("api.data.get_bar_service", return_value=mock_service):
            result = run_async(get_bars(code="000001.SZ", page=1, page_size=100))

        assert result.get("code") == 0, "count 失败不应致 500，列表仍可返回"
        assert result["meta"]["total"] == 2, (
            f"count 失败应降级为 len(items)=2，实际 {result['meta']['total']}")
