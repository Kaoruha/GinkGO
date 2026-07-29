"""#6845: 回测状态回写失败可见——不再撒谎。

_progress_tracker._write_status_to_db_ 当前 void + 双吞，DB 写失败时
report_completed 返回 None，调用方无法感知。本组测试要求：

- _write_status_to_db 返回 ServiceResult，report_* 传播之
- DB 异常（update_status 返 code=UPDATE_FAILED 或抛异常）→ 返回 error
- task 不存在（code=NOT_FOUND）→ 静默容错，返回 success（body: 算预期容许）
- 正常 success → 返回 success

通过 public report_* 接口验证行为（非私有实现细节）。
"""
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult
from ginkgo.workers.backtest_worker.models import BacktestTask
from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker

T = "8b7b8cd8d69444db9a59e01862e601d6"


def _mk_tracker(update_return=None, update_side_effect=None) -> tuple:
    task = BacktestTask(task_uuid=T, portfolio_uuid="P", name="n", config=None)
    task.completed_at = None
    svc = MagicMock()
    if update_side_effect is not None:
        svc.update_status.side_effect = update_side_effect
    else:
        svc.update_status.return_value = update_return
    tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=svc)
    return tracker, task


@pytest.mark.tdd
class TestReportCompletedPropagatesStatusWrite_6845:
    """#6845: report_completed 传播状态回写结果，不再 void 撒谎。"""

    def test_db_failure_returns_error(self):
        """DB 异常（update_status 返 code=UPDATE_FAILED）→ report_completed 返回 error。"""
        tracker, task = _mk_tracker(
            ServiceResult.error("Failed to update task status: boom", code="UPDATE_FAILED")
        )
        with patch("requests.post"):
            result = tracker.report_completed(task, result=None)
        assert result is not None, "应返回 ServiceResult，不再 void"
        assert isinstance(result, ServiceResult)
        assert not result.is_success(), "DB 失败应返回 error，而非 void 撒谎"

    def test_not_found_returns_success(self):
        """task 不存在（code=NOT_FOUND）→ 静默容错返回 success（body: 算预期容许）。"""
        tracker, task = _mk_tracker(
            ServiceResult.error("Backtest task not found: " + T, code="NOT_FOUND")
        )
        with patch("requests.post"):
            result = tracker.report_completed(task, result=None)
        assert result is not None, "应返回 ServiceResult"
        assert isinstance(result, ServiceResult)
        assert result.is_success(), "task 不存在属预期容许（未预建），应 success 非 error"

    def test_success_returns_success(self):
        """回写成功 → report_completed 返回 success。"""
        tracker, task = _mk_tracker(ServiceResult.success(message="updated"))
        with patch("requests.post"):
            result = tracker.report_completed(task, result=None)
        assert isinstance(result, ServiceResult), "应返回 ServiceResult"
        assert result.is_success(), "回写成功应返回 success"


@pytest.mark.tdd
class TestReportFailedCancelledPropagate_6845:
    """#6845: report_failed/report_cancelled 与 report_completed 对称传播回写结果。"""

    def test_report_failed_propagates_db_failure(self):
        """report_failed 的 DB 写失败须传播，不再 void（失败上报丢失致 task 卡 running）。"""
        tracker, task = _mk_tracker(ServiceResult.error("boom", code="UPDATE_FAILED"))
        with patch("requests.post"):
            result = tracker.report_failed(task, "some error")
        assert isinstance(result, ServiceResult), "应返回 ServiceResult，不再 void"
        assert not result.is_success(), "report_failed 应传播 DB 失败"

    def test_report_cancelled_propagates_db_failure(self):
        """report_cancelled 的 DB 写失败须传播（取消上报丢失致 task 卡 running/cancelled 不一致）。"""
        tracker, task = _mk_tracker(ServiceResult.error("boom", code="UPDATE_FAILED"))
        with patch("requests.post"):
            result = tracker.report_cancelled(task)
        assert isinstance(result, ServiceResult), "应返回 ServiceResult，不再 void"
        assert not result.is_success(), "report_cancelled 应传播 DB 失败"

    def test_report_failed_by_uuid_propagates_db_failure(self):
        """report_failed_by_uuid（node.py 畸形 payload 路径，活调用）DB 写失败须传播。"""
        tracker, _ = _mk_tracker(ServiceResult.error("boom", code="UPDATE_FAILED"))
        with patch("requests.post"):
            result = tracker.report_failed_by_uuid(T, "some error")
        assert isinstance(result, ServiceResult), "应返回 ServiceResult，不再 void"
        assert not result.is_success(), "report_failed_by_uuid 应传播 DB 失败"
