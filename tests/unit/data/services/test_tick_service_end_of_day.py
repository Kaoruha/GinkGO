"""
#6000: data get tick 单日/区间查询返回空。
根因：tick_service `_build_tick_filters` / `get` 把 end_date 经 datetime_normalize
归一化为当日 00:00:00，作 inclusive `timestamp__lte` 上界，盘中 09:30–15:00 的
tick 全部 > 00:00:00 被排除 → 单日查询整天空、区间查询丢最后一天。

本测试 pin 的行为：end_date 作为闭区间上界必须覆盖到当日 23:59:59（end-of-day），
使单日/区间查询都能命中盘中 tick。
"""
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.tick_service import TickService


def _make_service(crud):
    """纯 mock 注入 TickService，不触达 Redis / Adjustfactor / DB。"""
    return TickService(
        data_source=Mock(),
        stockinfo_service=Mock(),
        crud_repo=crud,
        redis_service=Mock(),
        adjustfactor_service=Mock(),
    )


class TestTickSyncDateNonTradingDay:
    """周末无 tick 数据时不应进入数据源 retry（#4984）。"""

    @pytest.mark.unit
    def test_weekend_date_returns_no_data_without_fetching_source(self):
        crud = Mock()
        service = _make_service(crud)
        service._stockinfo_service.exists.return_value = True

        result = service.sync_date("000001.SZ", "20260606")

        assert result.success is True
        assert "No tick data available" in result.message
        assert result.data.records_skipped == 0
        assert result.data.records_failed == 0
        service._data_source.fetch_history_transaction_detail.assert_not_called()


class TestTickEndDateCoversFullDay:
    """end_date 闭区间上界须覆盖整天盘中时段（#6000）。"""

    @pytest.mark.unit
    def test_get_ticks_df_same_day_end_filter_is_end_of_day(self):
        """单日查询（start==end）的 timestamp__lte 必须到当日 23:59:59，
        否则盘中 tick 全被排除（#6000 根因）。"""
        crud = Mock()
        crud.find.return_value = None
        service = _make_service(crud)

        service.get_ticks_df(code="000001.SZ", start_date="20250605", end_date="20250605")

        filters = crud.find.call_args.kwargs["filters"]
        assert filters["timestamp__lte"] == datetime(2025, 6, 5, 23, 59, 59)

    @pytest.mark.unit
    def test_get_ticks_df_range_last_day_covers_intraday(self):
        """区间查询的最后一日也必须覆盖到 23:59:59（不能只到 00:00:00 丢整天）。"""
        crud = Mock()
        crud.find.return_value = None
        service = _make_service(crud)

        service.get_ticks_df(code="000001.SZ", start_date="20250601", end_date="20250610")

        filters = crud.find.call_args.kwargs["filters"]
        assert filters["timestamp__gte"] == datetime(2025, 6, 1, 0, 0)
        assert filters["timestamp__lte"] == datetime(2025, 6, 10, 23, 59, 59)

    @pytest.mark.unit
    def test_get_same_day_end_filter_is_end_of_day(self):
        """get()（API 路径，独立构建 filters）同样须覆盖到当日 23:59:59（#6000）。"""
        crud = Mock()
        crud.find.return_value = None
        service = _make_service(crud)

        service.get(code="000001.SZ", start_date="20250605", end_date="20250605")

        filters = crud.find.call_args.kwargs["filters"]
        assert filters["timestamp__lte"] == datetime(2025, 6, 5, 23, 59, 59)

    @pytest.mark.unit
    def test_get_ticks_df_precise_datetime_end_is_respected(self):
        """传入带时间分量的精确 datetime（如 API 层 fromisoformat）须保持精度，
        不被错误延展到 23:59:59（API 层 data.py:411 传 datetime 对象）。"""
        crud = Mock()
        crud.find.return_value = None
        service = _make_service(crud)

        service.get_ticks_df(
            code="000001.SZ",
            start_date="2025-06-05",
            end_date=datetime(2025, 6, 5, 14, 30, 0),
        )

        filters = crud.find.call_args.kwargs["filters"]
        assert filters["timestamp__lte"] == datetime(2025, 6, 5, 14, 30, 0)
