# Issue: dashboard 加载 10k portfolio 行做 Python 聚合
# Upstream: api.api.dashboard.get_dashboard_stats
# Downstream: PortfolioService.get_stats()
# Role: 验证 dashboard 使用 SQL 聚合而非加载全量数据

"""
dashboard 聚合测试

验证 dashboard 统计数据通过 SQL 聚合获取，
不加载全量 portfolio 数据到 Python。
"""

import asyncio
import pytest
from unittest.mock import patch, MagicMock


def run_async(coro):
    return asyncio.run(coro)


class TestDashboardAggregation:
    """dashboard 聚合测试"""

    def test_uses_get_stats_not_get_10k(self):
        """TDD Red: dashboard 应调用 get_stats() 而非 get(page_size=10000)"""

        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get_stats.return_value = MagicMock(
            is_success=lambda: True,
            data={
                "total": 10,
                "running": 3,
                "total_assets": 5000000.0,
                "avg_net_value": 1.0,
            },
        )

        mock_backtest_service = MagicMock()
        mock_backtest_service.list.return_value = MagicMock(
            is_success=lambda: True,
            data={"total": 25},
        )

        mock_container = MagicMock()
        mock_container.portfolio_service.return_value = mock_portfolio_service
        mock_container.backtest_task_service.return_value = mock_backtest_service

        mock_request = MagicMock()

        from api.dashboard import get_dashboard_stats

        with patch("ginkgo.data.containers.container", mock_container), \
             patch("api.dashboard._check_health", return_value=[]):
            result = run_async(get_dashboard_stats(request=mock_request))

        # 应调用 get_stats 聚合方法
        mock_portfolio_service.get_stats.assert_called_once()
        # 不应调 get(page_size=10000)
        mock_portfolio_service.get.assert_not_called()

    def test_values_from_aggregation(self):
        """TDD Red: 统计值应来自 SQL 聚合"""

        mock_portfolio_service = MagicMock()
        mock_portfolio_service.get_stats.return_value = MagicMock(
            is_success=lambda: True,
            data={
                "total": 42,
                "running": 7,
                "total_assets": 9999999.99,
                "avg_net_value": 1.05,
            },
        )

        mock_backtest_service = MagicMock()
        mock_backtest_service.list.return_value = MagicMock(
            is_success=lambda: True,
            data={"total": 100},
        )

        mock_container = MagicMock()
        mock_container.portfolio_service.return_value = mock_portfolio_service
        mock_container.backtest_task_service.return_value = mock_backtest_service

        mock_request = MagicMock()

        from api.dashboard import get_dashboard_stats

        with patch("ginkgo.data.containers.container", mock_container), \
             patch("api.dashboard._check_health", return_value=[]):
            result = run_async(get_dashboard_stats(request=mock_request))

        assert result["data"]["total_asset"] == 9999999.99
        assert result["data"]["running_strategies"] == 7
        assert result["data"]["portfolio_count"] == 42
