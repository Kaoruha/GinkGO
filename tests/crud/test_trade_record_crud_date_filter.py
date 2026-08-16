# Issue: get_trades_by_account/get_trades_by_portfolio 的 date_filter 组装后未传入 find，时间过滤不生效
# Upstream: TradeRecordCRUD.get_trades_by_account / get_trades_by_portfolio
# Downstream: TradeRecordService.get_trades（trades 端点日期过滤依赖此修复）
# Role: 回归——日期条件必须以 trade_time__gte/__lte 进入 find 的 filters

"""
trade_record CRUD 日期过滤回归测试

验证 start_date/end_date 以比较算子进入 find(filters=...)，
不再是被组装后遗忘的 date_filter 死代码。
"""

from datetime import datetime
from unittest.mock import patch


DT_START = datetime(2026, 1, 1, 0, 0, 0)
DT_END = datetime(2026, 1, 31, 23, 59, 59)


def _make_crud():
    from ginkgo.data.crud.trade_record_crud import TradeRecordCRUD
    return TradeRecordCRUD()


class TestTradeRecordDateFilter:
    """日期过滤进入 find"""

    def test_account_trades_pass_date_filters(self):
        crud = _make_crud()
        with patch.object(crud, "find", return_value=[]) as mock_find:
            crud.get_trades_by_account("acc-1", start_date=DT_START, end_date=DT_END)

        filters = mock_find.call_args.kwargs["filters"]
        assert filters["trade_time__gte"] == DT_START
        assert filters["trade_time__lte"] == DT_END
        assert filters["live_account_id"] == "acc-1"
        assert filters["is_del"] is False

    def test_account_trades_without_dates_has_no_time_keys(self):
        crud = _make_crud()
        with patch.object(crud, "find", return_value=[]) as mock_find:
            crud.get_trades_by_account("acc-1")

        filters = mock_find.call_args.kwargs["filters"]
        assert "trade_time__gte" not in filters
        assert "trade_time__lte" not in filters

    def test_portfolio_trades_pass_date_filters(self):
        crud = _make_crud()
        with patch.object(crud, "find", return_value=[]) as mock_find:
            crud.get_trades_by_portfolio("pf-1", start_date=DT_START, end_date=DT_END)

        filters = mock_find.call_args.kwargs["filters"]
        assert filters["trade_time__gte"] == DT_START
        assert filters["trade_time__lte"] == DT_END
        assert filters["portfolio_id"] == "pf-1"

    def test_date_operators_parse_to_comparisons(self):
        """trade_time__gte/__lte 经 _parse_filters 生成 >=/<= 比较（而非等值）"""
        crud = _make_crud()
        conditions = crud._parse_filters({
            "live_account_id": "acc-1",
            "trade_time__gte": DT_START,
            "trade_time__lte": DT_END,
        })
        joined = " AND ".join(str(c) for c in conditions)
        assert ">=" in joined
        assert "<=" in joined
