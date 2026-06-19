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
            task_uuid=T, portfolio_uuid="P", name="n", config=None,
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
