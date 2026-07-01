"""#6483: 回测超时时 task_processor 应将任务标 FAILED（而非静默 COMPLETED）。

契约链：orchestrator 超时返回 success=False → task_processor.run L107
``if not result.is_success(): raise`` → except 分支 state=FAILED + report_failed。

修复前 orchestrator 超时仍返回 success=True，task_processor 据此标 COMPLETED，
配合 _aggregate_results 硬编码 status="completed" 双重吞掉超时，~600 行截断的
回测显示"已完成"。本测试锁定修复后的端到端契约，防回归。
"""
from threading import Event
from unittest.mock import MagicMock

import pytest

try:
    from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
    from ginkgo.workers.backtest_worker.models import (
        BacktestTask,
        BacktestConfig,
        BacktestTaskState,
    )
    from ginkgo.trading.services.backtest_orchestrator import OrchestratorResult

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _full_backtest_config() -> BacktestConfig:
    """ADR-018：BacktestConfig 删默认值后须显式传全 11 字段。"""
    return BacktestConfig(
        start_date="2025-01-01",
        end_date="2025-12-31",
        initial_cash=100000.0,
        commission_rate=0.0003,
        slippage_rate=0.0001,
        benchmark_return=0.0,
        max_position_ratio=0.3,
        stop_loss_ratio=0.05,
        take_profit_ratio=0.15,
        frequency="DAY",
        analyzers=[],
    )


def _make_processor(task: BacktestTask) -> BacktestProcessor:
    """构造最小可测处理器：跳过 __init__ 的 service 容器装配。"""
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = task
    proc.worker_id = "w-test"
    proc.progress_tracker = MagicMock()
    proc._stop_event = Event()
    proc._engine = None
    proc._exception = None
    proc._result = {}
    proc._assembly_service = MagicMock()
    proc._portfolio_service = MagicMock()
    return proc


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestProcessor not available")
class TestProcessorMarksTimeoutAsFailed:
    """#6483: orchestrator 返回超时失败时，task 必须转 FAILED。"""

    def test_orchestrator_timeout_failure_marks_task_failed(self, monkeypatch):
        cfg = _full_backtest_config()
        task = BacktestTask.create(portfolio_uuid="ptid", name="t", config=cfg)
        proc = _make_processor(task)

        # 跳过 run() 开头的 sleep，加速测试
        monkeypatch.setattr(
            "ginkgo.workers.backtest_worker.task_processor.time.sleep",
            lambda *_: None,
        )

        # mock data_container（run() 内函数级 import）
        mock_container = MagicMock()
        mock_container.analyzer_service.return_value = MagicMock()
        mock_container.backtest_task_service.return_value = MagicMock()
        monkeypatch.setattr("ginkgo.data.containers.container", mock_container)

        # mock BacktestOrchestrator：run() 返回超时失败（#6483 修复后行为）
        timeout_result = OrchestratorResult(
            success=False,
            error=(
                "Backtest timed out: engine did not finish within the "
                "wall-clock limit (data may be truncated)"
            ),
        )
        mock_orch_instance = MagicMock()
        mock_orch_instance.run.return_value = timeout_result
        mock_orch_class = MagicMock(return_value=mock_orch_instance)
        monkeypatch.setattr(
            "ginkgo.trading.services.backtest_orchestrator.BacktestOrchestrator",
            mock_orch_class,
        )

        proc.run()  # 同步执行 Thread.run

        assert proc.task.state == BacktestTaskState.FAILED, (
            "#6483: 超时应标 FAILED，非静默 COMPLETED"
        )
        assert proc.task.error and "timed out" in proc.task.error.lower(), (
            f"task.error 应含 'timed out'，实际: {proc.task.error!r}"
        )
        proc.progress_tracker.report_failed.assert_called_once()
        # 绝不能标完成
        proc.progress_tracker.report_completed.assert_not_called()
