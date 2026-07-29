"""Tests for ProgressTracker -- #6174 / ADR-016 W1.

回测完成时必须回写 MBacktestTask.engine_id = task.uuid（ADR-016 铁律 2），
维持 engine_id ≡ task_id 不变量。否则 baseline 管线读空 engine_id → 查不到记录。
"""

import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.workers.backtest_worker.progress_tracker import ProgressTracker
    from ginkgo.workers.backtest_worker.models import BacktestTask
    from ginkgo.data.services.base_service import ServiceResult

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


def _make_task(task_uuid: str) -> BacktestTask:
    """最小 BacktestTask（completed_at=None 防 isoformat 报错）。"""
    task = BacktestTask(task_uuid=task_uuid, portfolio_uuid="P", name="n", config=None)
    task.completed_at = None
    return task


def _make_tracker(task_service) -> ProgressTracker:
    """装配受控 tracker（task_service 由调用方按用例 mock 返回值/异常）。"""
    return ProgressTracker(worker_id="w1", kafka_producer=MagicMock(), task_service=task_service)


@pytest.mark.skipif(not HAS_MODULE, reason="ProgressTracker not available")
@pytest.mark.tdd
class TestReportCompletedHonestOnStatusWriteFailure:
    """#6845: 状态回写失败必须可见——不再撒谎。

    report_completed 在 DB 写失败时返回 failure（而非 void 吞异常），
    使调用方（task_processor）能 WARN 告警而非无脑打 "completed successfully"。
    """

    def test_db_exception_propagated_as_failure(self):
        """task_service.update_status 抛异常 → report_completed 返回 is_failure()。"""
        task_service = MagicMock()
        task_service.update_status.side_effect = RuntimeError("connection lost")

        with patch("requests.post"):
            result = _make_tracker(task_service).report_completed(
                _make_task("8b7b8cd8d69444db9a59e01862e601d6"), result={"total_pnl": 1.0}
            )

        assert result is not None, "必须返回 ServiceResult，None=吞异常=撒谎"
        assert not result.is_success(), "DB 异常须如实返回 failure"
        # ServiceResult.error(msg) 的 message 默认 = error（base_service.py），断一处即可
        assert "connection lost" in result.message

    def test_success_path_returns_success(self):
        """update_status 成功 → report_completed 返回 is_success()。"""
        T = "9c8c9de9e7a555ecab6af12973f712e7"
        task_service = MagicMock()
        task_service.update_status.return_value = ServiceResult.success({"uuid": T}, "updated")

        with patch("requests.post"):
            result = _make_tracker(task_service).report_completed(_make_task(T), result={"total_pnl": 1.0})

        assert result is not None
        assert result.is_success(), "成功路径须返回 success"

    def test_task_not_found_is_tolerable_success(self):
        """任务不存在（code=NOT_FOUND）→ report_completed 返回 success（预期容许，非故障）。

        #6845 验收：task 不存在算预期容许（任务可能未预先创建），不告警。
        """
        T = "ad9dae0af8b666fdbc7b023a84f823f8"
        task_service = MagicMock()
        # 模拟 update_status 真实返回：not-found 带 code=NOT_FOUND
        task_service.update_status.return_value = ServiceResult.error(
            f"Backtest task not found: {T}", code="NOT_FOUND"
        )

        with patch("requests.post"):
            result = _make_tracker(task_service).report_completed(_make_task(T), result={"total_pnl": 1.0})

        assert result is not None
        assert result.is_success(), "任务不存在须容许为 success（非 DB 故障），否则假告警"
