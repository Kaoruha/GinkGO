# Issue: web-ui 分页性能修复
# Upstream: api.api.backtest
# Downstream: BacktestTaskService.list()
# Role: 验证回测列表接口使用服务端分页而非 Python 全量加载+切片

"""
回测列表接口分页测试

验证 list_backtests 使用 task_service.list() 实现服务端分页，
不再全量加载后在 Python 中排序和切片。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


@pytest.fixture
def mock_task_service():
    """Mock BacktestTaskService"""
    svc = MagicMock()
    svc.list.return_value = MagicMock(
        is_success=lambda: True,
        data={
            "data": [],
            "total": 0,
            "page": 0,
            "page_size": 20,
        },
    )
    return svc


@pytest.fixture
def mock_portfolio_service():
    """Mock PortfolioService"""
    svc = MagicMock()
    svc.get_names_by_ids.return_value = {}
    return svc


def run_async(coro):
    return asyncio.run(coro)


class TestBacktestListPagination:
    """回测列表分页测试"""

    def test_calls_list_not_get(self, mock_task_service, mock_portfolio_service):
        """TDD Red: list_backtests 应调用 task_service.list() 而非 get()"""
        from api.backtest import list_backtests

        with patch("api.backtest.get_backtest_task_service", return_value=mock_task_service), \
             patch("api.backtest.get_portfolio_service", return_value=mock_portfolio_service):
            result = run_async(list_backtests(page=2, page_size=10))

        # 应调用 list() 而非 get()
        mock_task_service.list.assert_called_once()
        mock_task_service.get.assert_not_called()

    def test_passes_pagination_params(self, mock_task_service, mock_portfolio_service):
        """TDD Red: list_backtests 应将 page/page_size 传给 service"""
        from api.backtest import list_backtests

        with patch("api.backtest.get_backtest_task_service", return_value=mock_task_service), \
             patch("api.backtest.get_portfolio_service", return_value=mock_portfolio_service):
            result = run_async(list_backtests(page=3, page_size=15))

        call_args = mock_task_service.list.call_args
        assert call_args.kwargs.get("page") == 2 or call_args[1].get("page") == 2  # 0-based
        assert call_args.kwargs.get("page_size") == 15 or call_args[1].get("page_size") == 15

    def test_returns_total_from_service(self, mock_task_service, mock_portfolio_service):
        """TDD Red: list_backtests 应返回服务端计算的 total"""
        from api.backtest import list_backtests

        mock_task_service.list.return_value = MagicMock(
            is_success=lambda: True,
            data={
                "data": [],
                "total": 42,
                "page": 2,
                "page_size": 10,
            },
        )

        with patch("api.backtest.get_backtest_task_service", return_value=mock_task_service), \
             patch("api.backtest.get_portfolio_service", return_value=mock_portfolio_service):
            result = run_async(list_backtests(page=3, page_size=10))

        assert result["meta"]["total"] == 42

    def test_no_python_sort_on_full_dataset(self, mock_task_service, mock_portfolio_service):
        """TDD Red: 排序应通过 service 层完成，不在 API 层全量排序"""
        from api.backtest import list_backtests

        # 构造 50 条数据，如果全量排序会破坏 order
        fake_tasks = []
        for i in range(50):
            task = MagicMock()
            task.uuid = f"task-{i}"
            task.name = f"Backtest {i}"
            task.portfolio_id = f"pf-{i}"
            task.status = "completed"
            task.progress = 100
            task.total_pnl = float(i * 100)
            task.total_orders = i
            task.total_signals = i * 2
            task.total_positions = i
            task.max_drawdown = 0.1
            task.sharpe_ratio = float(i) / 10
            task.annual_return = float(i) / 5
            task.win_rate = 0.5
            task.final_portfolio_value = 1000000.0
            task.create_at = f"2025-01-{i+1:02d}T00:00:00"
            task.start_time = None
            task.end_time = None
            task.error_message = ""
            task.backtest_start_date = None
            task.backtest_end_date = None
            fake_tasks.append(task)

        mock_task_service.list.return_value = MagicMock(
            is_success=lambda: True,
            data={
                "data": fake_tasks[:10],  # service 只返回当前页
                "total": 50,
                "page": 0,
                "page_size": 10,
            },
        )

        with patch("api.backtest.get_backtest_task_service", return_value=mock_task_service), \
             patch("api.backtest.get_portfolio_service", return_value=mock_portfolio_service):
            result = run_async(list_backtests(page=1, page_size=10, sort_by="annual_return"))

        # 验证只拿到当前页 10 条，不是全量 50 条
        assert len(result["data"]) == 10
        assert result["meta"]["total"] == 50
