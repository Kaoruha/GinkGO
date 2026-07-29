"""Tests for ProgressTracker -- #6174 / ADR-016 W1.

回测完成时必须回写 MBacktestTask.engine_id = task.uuid（ADR-016 铁律 2），
维持 engine_id ≡ task_id 不变量。否则 baseline 管线读空 engine_id → 查不到记录。
"""

import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker
    from ginkgo.workers.backtest_worker.models import BacktestTask

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ProgressTracker not available")
@pytest.mark.tdd
class TestReportCompletedWritesEngineId:
    """ADR-016 W1: report_completed 回写 engine_id = task_uuid。"""

    def test_completed_writes_engine_id_equals_task_uuid(self):
        """完成时 update_status 的 result_fields 含 engine_id == task_uuid。"""
        T = "8b7b8cd8d69444db9a59e01862e601d6"
        task = BacktestTask(
            task_uuid=T,
            portfolio_uuid="P",
            name="n",
            config=None,
        )
        task.completed_at = None  # report_completed 读 completed_at.isoformat()

        task_service = MagicMock()
        task_service.update_status.return_value = MagicMock(is_success=lambda: True)
        producer = MagicMock()

        tracker = ProgressTracker(worker_id="w1", kafka_producer=producer, task_service=task_service)

        with patch("requests.post"):
            tracker.report_completed(task, result={"total_pnl": 1.0})

        kwargs = task_service.update_status.call_args.kwargs
        assert kwargs.get("status") == "completed"
        # ADR-016 铁律 2: engine_id ≡ task.uuid（task_id 与 uuid 等价）
        assert kwargs.get("engine_id") == T, "完成时必须回写 engine_id = task_uuid"


@pytest.mark.skipif(not HAS_MODULE, reason="ProgressTracker not available")
@pytest.mark.tdd
class TestProgressReportNoSyncHttpNotify:
    """#5512/#5561: 进度/状态上报不应发起同步 HTTP 通知。"""

    def test_report_progress_does_not_call_requests_post(self):
        """report_progress 不发起同步 HTTP 通知。"""
        task_uuid = "8b7b8cd8d69444db9a59e01862e601d6"
        task = BacktestTask(task_uuid=task_uuid, portfolio_uuid="P", name="n", config=None)

        task_service = MagicMock()
        task_service.update_progress.return_value = MagicMock(success=True)
        tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)

        with patch("requests.post") as mock_post:
            tracker.report_progress(task, progress=50.0, current_date="2025-01-01")

        mock_post.assert_not_called()

    def test_report_completed_does_not_call_requests_post(self):
        """report_completed 状态变更不发起同步 HTTP 通知。"""
        task_uuid = "8b7b8cd8d69444db9a59e01862e601d6"
        task = BacktestTask(task_uuid=task_uuid, portfolio_uuid="P", name="n", config=None)
        task.completed_at = None

        task_service = MagicMock()
        task_service.update_status.return_value = MagicMock(is_success=lambda: True)
        tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)

        with patch("requests.post") as mock_post:
            tracker.report_completed(task, result={"total_pnl": 1.0})

        mock_post.assert_not_called()


@pytest.mark.skipif(not HAS_MODULE, reason="ProgressTracker not available")
@pytest.mark.tdd
class TestStatusWriteTruthful:
    """#6845: 状态回写失败必须可见——report_* 返回 ServiceResult，不再 void 吞掉。

    区分两种失败：
    - task 未预创建（not-found）→ 容错，返回 success（汇总/回测可继续）
    - DB 异常 → 返回 error（调用方可 WARN/告警，不再撒谎）
    """

    def test_report_completed_returns_success_when_db_write_ok(self):
        """DB 写成功时 report_completed 返回 is_success() 的 ServiceResult（非 None）。"""
        task = BacktestTask(
            task_uuid="8b7b8cd8d69444db9a59e01862e601d6",
            portfolio_uuid="P",
            name="n",
            config=None,
        )
        task.completed_at = None
        task_service = MagicMock()
        task_service.update_status.return_value = MagicMock(is_success=lambda: True)
        tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)

        with patch("requests.post"):
            result = tracker.report_completed(task, result={"total_pnl": 1.0})

        assert result is not None, "report_completed 不应返回 None（#6845：状态写结果须可见）"
        assert result.is_success(), "DB 写成功应返回 success"

    def test_report_completed_not_found_is_non_fatal_success(self):
        """task 未预创建（not-found）→ 容错返回 success（汇总/回测可继续，非致命）。

        区分点：update_status 返回 "Backtest task not found" 与 DB 异常 "Failed to update"
        必须区别对待——前者是预期容错，后者是真失败。
        """
        from ginkgo.data.services.base_service import ServiceResult

        task = BacktestTask(
            task_uuid="8b7b8cd8d69444db9a59e01862e601d6",
            portfolio_uuid="P",
            name="n",
            config=None,
        )
        task.completed_at = None
        task_service = MagicMock()
        task_service.update_status.return_value = ServiceResult.error(
            "Backtest task not found: deadbeef"
        )
        tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)

        with patch("requests.post"):
            result = tracker.report_completed(task, result={"total_pnl": 1.0})

        assert result.is_success(), "not-found 应容错为 success（任务可能未预创建，非致命）"

    def test_report_completed_db_error_returns_error(self):
        """DB 异常（update_status 抛异常）→ 返回 error 且不抛出（失败对调用方可见，不撒谎）。"""
        task = BacktestTask(
            task_uuid="8b7b8cd8d69444db9a59e01862e601d6",
            portfolio_uuid="P",
            name="n",
            config=None,
        )
        task.completed_at = None
        task_service = MagicMock()
        task_service.update_status.side_effect = Exception("OperationalError: connection lost")
        tracker = ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)

        with patch("requests.post"):
            result = tracker.report_completed(task, result={"total_pnl": 1.0})

        assert result is not None and not result.is_success(), "DB 异常应返回 error（可见），而非 None"
