"""Tests for BacktestResultAggregator honest return on status-write failure -- #6845.

aggregate_and_save 在 backtest_task_service.update_status 失败时不能再撒谎返回 success。
区分两类失败：
- DB 写失败（非 NOT_FOUND）：返回 error（真故障，上层须感知）
- 任务不存在（code=NOT_FOUND）：容许返回 success（任务可能未预先创建，原注释意图）
"""
from unittest.mock import MagicMock

import pytest

try:
    from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator
    from ginkgo.data.services.base_service import ServiceResult
    import ginkgo.data.containers as dc_mod

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _make_aggregator(update_status_return) -> BacktestResultAggregator:
    """构造最小 aggregator：analyzer_service=None 跳过指标读取，backtest_task_service 受控。"""
    task_svc = MagicMock()
    task_svc.update_status.return_value = update_status_return
    return BacktestResultAggregator(analyzer_service=None, backtest_task_service=task_svc)


def _neutralize_portfolio_sync(monkeypatch):
    """aggregate_and_save 内部会 data_container.portfolio_service().update_performance()
    做绩效同步（重副作用）——本测试不关心，mock 成 success 隔离。"""
    fake_svc = MagicMock()
    fake_svc.update_performance.return_value = ServiceResult.success()
    monkeypatch.setattr(dc_mod.container, "portfolio_service", lambda: fake_svc)


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestResultAggregator not available")
@pytest.mark.tdd
class TestAggregateAndSaveHonestOnStatusWriteFailure:
    """#6845: 结果汇总在状态写失败时不再撒谎返回 success。"""

    def test_db_write_failure_returns_error(self, monkeypatch):
        """update_status 返回 failure（非 NOT_FOUND）→ aggregate_and_save 返回 error。"""
        _neutralize_portfolio_sync(monkeypatch)
        agg = _make_aggregator(
            ServiceResult.error("Failed to update task status: connection lost")
        )

        result = agg.aggregate_and_save(task_id="T1", portfolio_id="P1")

        assert result is not None
        assert not result.is_success(), "DB 写失败须诚实返回 error（原 BUG：仍 return success）"

    def test_task_not_found_returns_success(self, monkeypatch):
        """任务不存在（code=NOT_FOUND）→ 容许返回 success（任务可能未预先创建）。"""
        _neutralize_portfolio_sync(monkeypatch)
        agg = _make_aggregator(
            ServiceResult.error("Backtest task not found: T2", code="NOT_FOUND")
        )

        result = agg.aggregate_and_save(task_id="T2", portfolio_id="P2")

        assert result is not None
        assert result.is_success(), "任务不存在须容许为 success（非 DB 故障），否则假报错"

    def test_success_returns_success(self, monkeypatch):
        """update_status 成功 → aggregate_and_save 返回 success（回归基线）。"""
        _neutralize_portfolio_sync(monkeypatch)
        agg = _make_aggregator(ServiceResult.success({"uuid": "T3"}, "updated"))

        result = agg.aggregate_and_save(task_id="T3", portfolio_id="P3")

        assert result is not None
        assert result.is_success()
