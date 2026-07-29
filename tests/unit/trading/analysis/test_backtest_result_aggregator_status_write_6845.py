"""#6845: aggregator update_status 失败日志归因准确化。

原 line 138-141 对所有 update_status 失败一律 WARN "Backtest task may not exist"，
DB 真挂（code=UPDATE_FAILED）时误导操作者查"task 是否存在"而非查 DB——这才是
aggregator 层的"撒谎"。返回值保持 success（避免 orchestrator 透传 error 致回测
成功被标 FAILED 的回归，见 #6845 切片7 分析）；修的是日志措辞归因准确：
- NOT_FOUND → WARN "task 未预建，容许"
- UPDATE_FAILED → ERROR "DB 故障"（不再误导为 task 不存在）

返回值改 error 的副作用已排除：orchestrator.run:338 透传 → task_processor run:127
raise → 回测标 FAILED（成功被标失败）。故仅修日志，不动返回值契约。
"""
import types
from unittest.mock import MagicMock

import pytest

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator


def _make_aggregator(update_return=None, update_side_effect=None):
    task_svc = MagicMock()
    if update_side_effect is not None:
        task_svc.update_status.side_effect = update_side_effect
    else:
        task_svc.update_status.return_value = update_return
    agg = BacktestResultAggregator(analyzer_service=MagicMock(), backtest_task_service=task_svc)
    # 绕过 analyzer 读取（ClickHouse），聚焦 update_status 失败分支
    agg._aggregate_metrics = lambda *a, **k: {}
    agg._aggregate_stats = lambda *a, **k: {}
    return agg


def _kill_portfolio_sync(monkeypatch):
    """绕过 container.portfolio_service.update_performance（聚合副作用，与 status 无关）。"""
    portfolio_svc = MagicMock()
    portfolio_svc.update_performance.return_value = ServiceResult.success()
    boom = types.SimpleNamespace(portfolio_service=lambda: portfolio_svc)
    monkeypatch.setattr("ginkgo.data.containers.container", boom)


@pytest.mark.tdd
class TestAggregatorStatusWriteLogAttribution_6845:
    def test_not_found_logs_warn_and_returns_success(self, monkeypatch):
        """NOT_FOUND → WARN 'task 未预建'，返回 success（容许，不标回测失败）。"""
        agg = _make_aggregator(ServiceResult.error("Backtest task not found: t1", code="NOT_FOUND"))
        glog = MagicMock()
        monkeypatch.setattr("ginkgo.trading.analysis.backtest_result_aggregator.GLOG", glog)
        _kill_portfolio_sync(monkeypatch)

        result = agg.aggregate_and_save(task_id="t1", portfolio_id="p1", engine_id="e1", status="completed")

        assert result.is_success(), "NOT_FOUND 应容许返 success（不引回测误判回归）"
        warns = [c.args[0] for c in glog.WARN.call_args_list]
        assert any("not found" in w.lower() or "pre-created" in w.lower() for w in warns), (
            f"NOT_FOUND 应 WARN task 未预建，got {warns}"
        )

    def test_update_failed_logs_db_error_not_misleading(self, monkeypatch):
        """UPDATE_FAILED → ERROR 'DB 故障'，不再误导 WARN 'task may not exist'。"""
        agg = _make_aggregator(
            ServiceResult.error("OperationalError: connection lost", code="UPDATE_FAILED")
        )
        glog = MagicMock()
        monkeypatch.setattr("ginkgo.trading.analysis.backtest_result_aggregator.GLOG", glog)
        _kill_portfolio_sync(monkeypatch)

        result = agg.aggregate_and_save(task_id="t1", portfolio_id="p1", engine_id="e1", status="completed")

        assert result.is_success(), "返回值保持 success（避免回测成功被标 FAILED 回归）"
        errors = [c.args[0] for c in glog.ERROR.call_args_list]
        warns = [c.args[0] for c in glog.WARN.call_args_list]
        # DB 故障归因到 ERROR（含 DB/status write 语义）
        assert any("db" in e.lower() or "status write" in e.lower() for e in errors), (
            f"UPDATE_FAILED 应 ERROR DB 故障，got errors={errors}"
        )
        # 不再误导为 "task may not exist"（那是 NOT_FOUND 的措辞）
        assert not any("may not exist" in w.lower() for w in warns), (
            f"UPDATE_FAILED 不应误导为 'task 不存在'，got warns={warns}"
        )
