# Issue: #5599 / #5610 — GET /api/v1/data/bars 返回 500 (list.count() 无参 + 数据丢失)
# Upstream: api.api.data.get_bars
# Downstream: BarService.get() — result.data 在真实环境为裸 list[MBar]（无 to_entities）
# Role: 验证 get_bars 在 result.data 为裸 list 时既不抛 TypeError，也不丢数据

"""
data/bars 500 修复测试

真实场景：bar_service.get().data 返回裸 list[MBar]（无 to_entities 方法）。

根因（双 bug）：
1. data.py:339 `else []` — 裸 list 无 to_entities → bars_list=[] 数据全部丢失
2. data.py:358 `bars_data.count()` — list 有 count 方法但需参数，hasattr 判断恒 True
   对裸 list 无参调用抛 TypeError → except 捕获 → HTTPException(500)

修复：339 行裸 list 本身即 entities（`else bars_data`）；358 行 total 取 len(bar_summaries)。
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
    """模拟真实 MBar（有 uuid/code/timestamp/open 等，无 to_entities）"""
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
    # 真实 MBar 无 to_entities（关键：触发裸 list 分支）
    del bar.to_entities
    return bar


class TestGetBarsBareListFix:
    """#5599 #5610: get_bars 处理裸 list[MBar] 不崩溃、不丢数据"""

    def test_bare_list_does_not_raise_500(self):
        """TDD Red: result.data 为裸 list[MBar]（非空、无 to_entities）时不抛 500"""
        mock_service = MagicMock()
        # 真实环境 bar_service.get().data 是裸 list（非空，无 to_entities）
        mock_service.get.return_value = make_mock_result(data=[make_bar()])

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            # 修复前：line 339 bars_list=[] → line 358 [bar].count() TypeError → 500
            result = run_async(get_bars())

        assert result.get("code") == 0

    def test_bare_list_does_not_lose_data(self):
        """TDD Red: 裸 list 的 bars 必须完整出现在返回 items 中（修复 line 339 丢数据）"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(
            data=[make_bar("b1", "000001.SZ"), make_bar("b2", "000002.SZ")]
        )

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            result = run_async(get_bars())

        # 修复前：line 339 bars_list=[] → items=[]（数据丢失）
        assert result.get("code") == 0
        assert len(result["data"]) == 2
        assert result["data"][0]["code"] == "000001.SZ"

    def test_total_matches_items_for_bare_list(self):
        """TDD Red: total 应等于 len(bar_summaries)，不调用 list.count()"""
        mock_service = MagicMock()
        mock_service.get.return_value = make_mock_result(
            data=[make_bar("b1"), make_bar("b2")]
        )

        from api.data import get_bars

        with patch("api.data.get_bar_service", return_value=mock_service):
            result = run_async(get_bars())

        assert result.get("code") == 0
        assert result["meta"]["total"] == 2
