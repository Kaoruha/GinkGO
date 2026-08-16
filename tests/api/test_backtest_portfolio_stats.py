# Issue: 前端 GET /backtests/portfolio-stats/{pid} 404——BacktestTaskService.get_portfolio_stats 未暴露
# Upstream: api.api.backtest.get_portfolio_backtest_stats
# Downstream: BacktestTaskService.get_portfolio_stats (backtest_task_service.py:1262)
# Role: 端点薄壳——service 结果直通透传，字段契约与前端 PortfolioBacktestStats 一致

"""
portfolio-stats 端点测试

验证 GET /api/v1/backtests/portfolio-stats/{portfolio_id}：
1. 成功路径透传 service dict（含 latest_completed 嵌套）
2. service 失败 → BusinessError
3. 路由声明顺序：静态段 /portfolio-stats/{pid} 在 /{uuid} 之前（文件惯例）
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


def _fake_stats():
    return {
        "portfolio_id": "pid-1",
        "total_backtests": 5,
        "completed_backtests": 3,
        "avg_nav": 1.234,
        "best_nav": 1.5,
        "worst_nav": 0.9,
        "avg_max_drawdown": 0.12,
        "worst_max_drawdown": 0.2,
        "best_max_drawdown": 0.05,
        "avg_sharpe_ratio": 1.1,
        "best_sharpe_ratio": 1.8,
        "avg_annual_return": 0.15,
        "avg_win_rate": 0.55,
        "latest_completed": {
            "uuid": "bt-1",
            "name": "run1",
            "created_at": "2026-08-01T00:00:00",
            "nav": 1.5,
            "max_drawdown": 0.05,
            "sharpe_ratio": 1.8,
            "annual_return": 0.2,
            "win_rate": 0.6,
        },
    }


class TestPortfolioStatsEndpoint:
    """GET /backtests/portfolio-stats/{portfolio_id}"""

    def test_success_passes_service_dict(self):
        """成功：信封 code=0，data 为 service dict 本身（同引用不重组）"""
        from ginkgo.data.services.base_service import ServiceResult

        fake = _fake_stats()
        mock_service = MagicMock()
        mock_service.get_portfolio_stats.return_value = ServiceResult.success(data=fake)

        from api.backtest import get_portfolio_backtest_stats

        with patch("api.backtest.get_backtest_task_service", return_value=mock_service):
            result = run_async(get_portfolio_backtest_stats("pid-1"))

        assert result["code"] == 0
        assert result["data"] is fake
        assert result["data"]["latest_completed"]["uuid"] == "bt-1"
        mock_service.get_portfolio_stats.assert_called_once_with("pid-1")

    def test_service_error_raises_business_error(self):
        """service 失败 → BusinessError（不吞成 200 空数据）"""
        from ginkgo.data.services.base_service import ServiceResult
        from core.exceptions import BusinessError

        mock_service = MagicMock()
        mock_service.get_portfolio_stats.return_value = ServiceResult.error("no such portfolio")

        from api.backtest import get_portfolio_backtest_stats

        with patch("api.backtest.get_backtest_task_service", return_value=mock_service):
            with pytest.raises(BusinessError):
                run_async(get_portfolio_backtest_stats("pid-x"))

    def test_static_route_declared_before_uuid_route(self):
        """路由顺序：/portfolio-stats/{portfolio_id} 必须先于 /{uuid} 声明（静态段惯例）"""
        from api.backtest import router

        paths = [getattr(r, "path", "") for r in router.routes]
        assert "/portfolio-stats/{portfolio_id}" in paths
        assert paths.index("/portfolio-stats/{portfolio_id}") < paths.index("/{uuid}")


class TestGetPortfolioStatsService:
    """service 层多任务聚合（datetime 比较回归）"""

    def _task(self, uuid, created, status="completed"):
        from types import SimpleNamespace

        return SimpleNamespace(
            uuid=uuid, name=f"bt-{uuid}", status=status, create_at=created,
            final_portfolio_value=110000.0, config_snapshot='{"initial_cash": 100000}',
            max_drawdown=0.1, sharpe_ratio=1.5, annual_return=0.2, win_rate=0.6,
        )

    def test_latest_completed_picks_newest_across_tasks(self):
        """两个 completed 任务：create_at 新者在 latest_completed。

        回归：原实现首轮存 _format_dt 后的 str，次轮拿 raw datetime
        与 str 比较抛 TypeError（'>' not supported）。
        """
        from datetime import datetime

        from ginkgo.data.services.backtest_task_service import BacktestTaskService

        svc = BacktestTaskService.__new__(BacktestTaskService)  # 绕过构造依赖
        t_old = self._task("bt-old", datetime(2026, 1, 1))
        t_new = self._task("bt-new", datetime(2026, 6, 1))
        with patch.object(BacktestTaskService, "list", return_value=MagicMock(
            is_success=lambda: True, data={"data": [t_old, t_new]},
        )):
            result = svc.get_portfolio_stats("pid-1")

        assert result.is_success()
        assert result.data["latest_completed"]["uuid"] == "bt-new"
        assert result.data["total_backtests"] == 2
        assert result.data["avg_nav"] == 1.1
