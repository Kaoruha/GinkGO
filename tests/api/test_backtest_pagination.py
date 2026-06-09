# Issue: web-ui 分页性能修复
# Upstream: api.api.backtest
# Downstream: BacktestTaskService.list_summaries()
# Role: 验证回测列表接口使用 Service 层 schema 方法，API handler 不直接访问 ORM

"""
回测列表接口分页测试

验证 list_backtests 使用 task_service.list_summaries() 返回 Pydantic schema，
API handler 不再直接访问 ORM 属性。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.backtest_task_schemas import BacktestTaskSummary
from ginkgo.data.services.base_service import ServiceResult


def run_async(coro):
    return asyncio.run(coro)


def _make_summary(**overrides):
    """构造一个默认的 BacktestTaskSummary"""
    defaults = dict(
        uuid="test-uuid", name="Test Backtest", portfolio_id="pf-1",
        portfolio_name="Test Portfolio", status="completed", progress=100,
        total_pnl=1000.0, total_orders=10, total_signals=20, total_positions=5,
        max_drawdown=0.1, sharpe_ratio=1.5, annual_return=0.2, win_rate=0.6,
        final_portfolio_value=1100000.0, created_at="2025-01-01T00:00:00",
        started_at="2025-01-01T00:00:00", completed_at="2025-01-02T00:00:00",
        backtest_start_date="2025-01-01", backtest_end_date="2025-12-31",
        error_message="",
    )
    defaults.update(overrides)
    return BacktestTaskSummary(**defaults)


def _make_service_result(summaries, total):
    """构造 list_summaries 的返回值"""
    sr = ServiceResult.success(data=summaries)
    sr.set_metadata("total", total)
    return sr


class TestBacktestListPagination:
    """回测列表分页测试"""

    def test_calls_list_summaries(self):
        """list_backtests 应调用 task_service.list_summaries()"""
        from api.backtest import list_backtests

        mock_svc = MagicMock()
        mock_svc.list_summaries.return_value = _make_service_result([], 0)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(list_backtests(page=2, page_size=10))

        mock_svc.list_summaries.assert_called_once()
        mock_svc.list.assert_not_called()
        mock_svc.get.assert_not_called()

    def test_passes_pagination_params(self):
        """list_backtests 应将 page/page_size 传给 service"""
        from api.backtest import list_backtests

        mock_svc = MagicMock()
        mock_svc.list_summaries.return_value = _make_service_result([], 0)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(list_backtests(page=3, page_size=15))

        call_args = mock_svc.list_summaries.call_args
        assert call_args.kwargs.get("page") == 2 or call_args[1].get("page") == 2  # 0-based
        assert call_args.kwargs.get("page_size") == 15 or call_args[1].get("page_size") == 15

    def test_returns_total_from_service(self):
        """list_backtests 应返回服务端计算的 total"""
        from api.backtest import list_backtests

        summaries = [_make_summary(uuid=f"t-{i}", name=f"Bt {i}") for i in range(3)]
        mock_svc = MagicMock()
        mock_svc.list_summaries.return_value = _make_service_result(summaries, 42)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(list_backtests(page=1, page_size=10))

        assert result["meta"]["total"] == 42
        assert len(result["data"]) == 3

    def test_returns_schema_dicts(self):
        """返回的 data 应是 schema 的 dict 序列化，不含 ORM 属性"""
        from api.backtest import list_backtests

        s = _make_summary(uuid="abc-123", name="My Test")
        mock_svc = MagicMock()
        mock_svc.list_summaries.return_value = _make_service_result([s], 1)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(list_backtests(page=1, page_size=10))

        item = result["data"][0]
        assert item["uuid"] == "abc-123"
        assert item["name"] == "My Test"
        # 确认是纯 dict，不是 ORM 对象
        assert isinstance(item, dict)

    def test_sort_params_passed(self):
        """排序参数应传给 service 层"""
        from api.backtest import list_backtests

        mock_svc = MagicMock()
        mock_svc.list_summaries.return_value = _make_service_result([], 0)

        with patch("api.backtest.get_backtest_task_service", return_value=mock_svc):
            result = run_async(list_backtests(
                page=1, page_size=10,
                sort_by="annual_return", sort_order="asc",
            ))

        call_args = mock_svc.list_summaries.call_args
        assert call_args.kwargs.get("sort_by") == "annual_return" or call_args[1].get("sort_by") == "annual_return"
        assert call_args.kwargs.get("sort_order") == "asc" or call_args[1].get("sort_order") == "asc"
