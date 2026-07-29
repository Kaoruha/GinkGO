"""Tests for BacktestResultAggregator status-write truthfulness -- #6845.

aggregate_and_save 的 update_status 失败时不再无条件 return success：
- task 未预创建（not-found）→ 容错，return success（合法场景，无告警）
- DB 异常 / 写失败 → return error（不再撒谎，让 orchestrator 据实判定）
"""

import types
from unittest.mock import MagicMock

import pytest

try:
    from ginkgo.data.services.base_service import ServiceResult
    from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _make_aggregator(update_behavior) -> "BacktestResultAggregator":
    """analyzer_service=None → _aggregate_* 走默认值守卫，跳过真实查询。"""
    agg = BacktestResultAggregator(analyzer_service=None, backtest_task_service=MagicMock())
    agg._backtest_task_service.update_status = update_behavior
    return agg


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestResultAggregator not available")
@pytest.mark.tdd
class TestAggregateSaveStatusWriteTruthful:
    """#6845: aggregate_and_save 的 update_status 失败据实返回，不再撒谎。"""

    def test_returns_error_when_db_write_fails(self, monkeypatch):
        """DB 异常 → aggregate_and_save 不再 return success（让 orchestrator 据实判定）。"""
        monkeypatch.setattr("ginkgo.data.containers.container", MagicMock())
        agg = _make_aggregator(
            MagicMock(return_value=ServiceResult.error("Failed to update task status: connection lost"))
        )

        result = agg.aggregate_and_save(
            task_id="t1", portfolio_id="p1", engine_id="e1", status="completed"
        )

        assert not result.is_success(), "DB 异常时不应 return success（#6845 不撒谎）"

    def test_silent_success_when_task_not_found(self, monkeypatch):
        """task 未预创建（not-found）→ 容错 return success，且静默（无 WARN/ERROR 告警）。"""
        monkeypatch.setattr("ginkgo.data.containers.container", MagicMock())
        warned, errored = [], []
        spy = types.SimpleNamespace(
            WARN=lambda m: warned.append(m),
            ERROR=lambda m: errored.append(m),
            INFO=lambda m: None,
            DEBUG=lambda m: None,
        )
        monkeypatch.setattr("ginkgo.trading.analysis.backtest_result_aggregator.GLOG", spy)
        agg = _make_aggregator(
            MagicMock(return_value=ServiceResult.error("Backtest task not found: t1"))
        )

        result = agg.aggregate_and_save(
            task_id="t1", portfolio_id="p1", engine_id="e1", status="completed"
        )

        assert result.is_success(), "not-found 应容错 return success（任务可能未预创建）"
        assert not warned and not errored, (
            f"not-found 应静默（无 WARN/ERROR 告警），收到 warn={warned} err={errored}"
        )
