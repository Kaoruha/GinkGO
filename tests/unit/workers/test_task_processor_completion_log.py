"""Tests for BacktestProcessor completion honest-logging -- #6845.

回测引擎成功后回写任务状态：写失败（DB 异常）必须 WARN，不再无脑打
``"Backtest completed successfully"`` 撒谎。任务不存在（tolerable）仍记成功日志。

行为契约（经公开 run() 调用的 _report_completion seam）：
- DB 写失败 → WARN（含 status write 标记），且不打 "completed successfully"
- 写成功 / 任务不存在 → INFO "completed successfully"，无 WARN
"""
import types
from threading import Event
from unittest.mock import MagicMock

import pytest

try:
    from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
    from ginkgo.workers.backtest_worker.models import BacktestTask
    from ginkgo.data.services.base_service import ServiceResult

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _make_processor(task_uuid: str = "8b7b8cd8d69444db9a59e01862e601d6") -> BacktestProcessor:
    """构造最小可测处理器：跳过 __init__ 容器装配，仅设置 _report_completion 读取的属性。"""
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = BacktestTask(task_uuid=task_uuid, portfolio_uuid="P", name="n", config=None)
    proc.progress_tracker = MagicMock()
    proc._ingest_task_logs = lambda: None  # 不测灌日志，隔离被测行为
    return proc


def _glog_spy():
    """GLOG spy：捕获 WARN/INFO 调用文本。"""
    captured = {"warn": [], "info": []}
    spy = types.SimpleNamespace(
        WARN=lambda m: captured["warn"].append(m),
        INFO=lambda m: captured["info"].append(m),
        ERROR=lambda m: None,
        DEBUG=lambda m: None,
    )
    return spy, captured


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestProcessor not available")
@pytest.mark.tdd
class TestCompletionLogHonestOnStatusWriteFailure:
    """#6845: 状态写失败可见——完成日志不再撒谎。"""

    def test_warns_when_status_write_failed(self, monkeypatch):
        """report_completed 返回 failure → WARN（status write 标记），不打 completed successfully。"""
        proc = _make_processor()
        proc.progress_tracker.report_completed.return_value = ServiceResult.error(
            "connection lost"
        )
        spy, captured = _glog_spy()
        monkeypatch.setattr("ginkgo.workers.backtest_worker.task_processor.GLOG", spy)

        proc._report_completion()

        assert captured["warn"], "DB 写失败必须 WARN（不能再撒谎）"
        assert any("status write" in m.lower() for m in captured["warn"]), \
            "WARN 须含 status write 标记，便于 grep 诊断"
        assert not any("completed successfully" in m for m in captured["info"]), \
            "写失败时不应打 completed successfully（撒谎）"

    def test_logs_completed_when_status_write_ok(self, monkeypatch):
        """report_completed 返回 success → INFO completed successfully，无 WARN。"""
        proc = _make_processor()
        proc.progress_tracker.report_completed.return_value = ServiceResult.success(
            {"uuid": "8b7b8cd8"}, "updated"
        )
        spy, captured = _glog_spy()
        monkeypatch.setattr("ginkgo.workers.backtest_worker.task_processor.GLOG", spy)

        proc._report_completion()

        assert any("completed successfully" in m for m in captured["info"]), \
            "写成功须打 completed successfully"
        assert not captured["warn"], "写成功时不应 WARN"

    def test_logs_completed_when_task_not_found(self, monkeypatch):
        """任务不存在（tolerable）→ 视为 success，打 completed successfully，无 WARN。"""
        proc = _make_processor()
        proc.progress_tracker.report_completed.return_value = ServiceResult.success(
            message="Task not found, status write skipped (tolerable): ..."
        )
        spy, captured = _glog_spy()
        monkeypatch.setattr("ginkgo.workers.backtest_worker.task_processor.GLOG", spy)

        proc._report_completion()

        assert any("completed successfully" in m for m in captured["info"]), \
            "任务不存在须容许为成功日志（非假告警）"
        assert not captured["warn"], "任务不存在不应 WARN"
