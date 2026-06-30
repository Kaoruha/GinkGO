"""Tests for BacktestProcessor error-handling logging -- #6031.

两个异常处理反模式必须对齐到本文件既定的 GLOG 范式（参考 L128
``GLOG.ERROR(traceback.format_exc())``）：

1. ``_on_progress`` 进度统计失败时 ``except: pass`` 完全静默 -> 必须发 WARN。
2. ``_aggregate_and_save_results`` 汇总失败时 ``traceback.print_exc()`` 输出到
   控制台流（stderr），后台 worker 模式下不被捕获 -> 必须经 GLOG.ERROR 落库。

行为契约：异常发生时诊断信息进入结构化日志（GLOG），而非被吞掉或泄漏到
控制台。控制流保持非致命（不影响主流程）。
"""
import types
from datetime import datetime
from threading import Event
from unittest.mock import MagicMock

import pytest

try:
    from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
    from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestConfig

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _make_processor(task) -> BacktestProcessor:
    """构造最小可测处理器：跳过 __init__ 的 service 容器装配，
    仅设置被测方法（_on_progress / _aggregate_and_save_results）读取的属性。
    方法体真实运行。"""
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = task
    proc.worker_id = "w-test"
    proc.progress_tracker = MagicMock()
    proc._stop_event = Event()
    proc._engine = None
    proc._exception = None
    proc._result = {}
    return proc


def _full_backtest_config(start: str = "2025-01-01", end: str = "2025-06-01") -> BacktestConfig:
    """ADR-018：BacktestConfig 删默认值后，进程内构造须显式传全 11 字段。
    config 内容对 task_processor 测试无关，集中此 helper 避免每处重复。"""
    return BacktestConfig(
        start_date=start,
        end_date=end,
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


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestProcessor not available")
@pytest.mark.tdd
class TestOnProgressLogsOnStatsFailure:
    """#6031-A: _on_progress 统计获取失败时必须发 WARN，而非静默 pass。"""

    def test_warns_when_portfolio_stats_gather_raises(self, monkeypatch):
        cfg = _full_backtest_config()
        task = BacktestTask.create(portfolio_uuid="ptid", name="t", config=cfg)
        proc = _make_processor(task)

        # 毒丸 portfolio：worth 为非数值对象 -> float(object()) 抛 TypeError 进入 except
        poison = types.SimpleNamespace(
            uuid="ptid", worth=object(), cash=1000.0, strategies=[], positions={}
        )
        proc._engine = types.SimpleNamespace(portfolios=[poison])

        warned = []
        spy = types.SimpleNamespace(
            WARN=lambda msg: warned.append(msg),
            ERROR=lambda msg: None,
            INFO=lambda msg: None,
            DEBUG=lambda msg: None,
        )
        monkeypatch.setattr(
            "ginkgo.workers.backtest_worker.task_processor.GLOG", spy
        )

        # 不应抛出（统计失败非致命），且必须发一条 WARN
        proc._on_progress(0.5, "2025-01-02")

        assert len(warned) == 1, f"expected one WARN, got {warned}"
        # WARN 必须带 task 上下文，便于 grep 定位
        assert task.task_uuid[:8] in warned[0]


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestProcessor not available")
@pytest.mark.tdd
class TestAggregateResultsRoutesTracebackToGlog:
    """#6031-B: _aggregate_and_save_results 汇总失败时，完整 traceback 必须经
    GLOG.ERROR 落库，而非 print_exc() 泄漏到控制台流（后台 worker 不捕获）。"""

    def test_traceback_logged_not_printed(self, monkeypatch, capsys):
        cfg = _full_backtest_config()
        task = BacktestTask.create(portfolio_uuid="ptid", name="t", config=cfg)
        task.started_at = datetime(2025, 1, 1)
        task.completed_at = datetime(2025, 1, 2)
        proc = _make_processor(task)

        errors = []
        spy = types.SimpleNamespace(
            WARN=lambda msg: None,
            ERROR=lambda msg: errors.append(msg),
            INFO=lambda msg: None,
            DEBUG=lambda msg: None,
        )
        monkeypatch.setattr(
            "ginkgo.workers.backtest_worker.task_processor.GLOG", spy
        )

        # 让汇总入口 analyzer_service() 抛异常，触发外层 except
        boom = types.SimpleNamespace(
            analyzer_service=lambda: (_ for _ in ()).throw(
                RuntimeError("boom-aggregation")
            ),
            backtest_task_service=lambda: None,
        )
        monkeypatch.setattr("ginkgo.data.containers.container", boom)

        # 不应抛出（异常已被 except 捕获）
        proc._aggregate_and_save_results()

        captured = capsys.readouterr()
        console = captured.out + captured.err

        # 完整 traceback 不得泄漏到控制台流（stdout/stderr）
        assert "Traceback" not in console, "traceback 泄漏到控制台"
        # 必须经 GLOG.ERROR 落库（含完整 traceback 字符串）
        assert any("Traceback" in m for m in errors), (
            f"GLOG.ERROR 未收到 traceback，收到: {errors}"
        )
