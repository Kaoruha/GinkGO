"""Tests for BacktestProcessor log ingestion after completion -- #4774.

worker（Kafka→BacktestWorker）派发的回测完成后，必须把运行日志灌入 ClickHouse，
否则 ``ginkgo logging logs/errors --task <id>`` 永远空查询。

灌入职责与 ``backtest_cli.py`` 本地同步路径（L287-296）对齐：worker 完成回调
``run()`` 在 ``report_completed`` 之后调用 ``_ingest_task_logs``，静默降级
（灌入失败不影响已完成状态）。
"""
import importlib
from threading import Event
from unittest.mock import MagicMock

import pytest


def _ingester_module():
    """ginkgo.services.logging 是 DynamicContainer（非真包），属性访问触发
    __getattr__ 找服务提供者而非子模块。须走 importlib.import_module
    拿到真实模块对象再 patch。见 [[arch_service_dict_wrapped_return]]。"""
    return importlib.import_module("ginkgo.services.logging.log_ingester")

try:
    from ginkgo.workers.backtest_worker.task_processor import BacktestProcessor
    from ginkgo.workers.backtest_worker.models import BacktestTask, BacktestConfig

    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


def _full_backtest_config(start: str = "2025-01-01", end: str = "2025-06-01") -> BacktestConfig:
    """ADR-018：BacktestConfig 删默认值后，进程内构造须显式传全 11 字段。"""
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


def _make_processor(task) -> BacktestProcessor:
    """构造最小可测处理器：跳过 __init__ 的 service 容器装配。"""
    proc = BacktestProcessor.__new__(BacktestProcessor)
    proc.task = task
    proc.worker_id = "w-test"
    proc.progress_tracker = MagicMock()
    proc._stop_event = Event()
    proc._engine = None
    proc._exception = None
    proc._result = {}
    return proc


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestProcessor not available")
@pytest.mark.tdd
class TestIngestTaskLogsOnCompletion:
    """#4774: worker 完成回调必须灌入日志到 ClickHouse。"""

    def test_calls_ingest_task_logs_with_task_uuid(self, monkeypatch):
        """完成回调触发 LogIngester.ingest_task_logs(task_uuid)。"""
        cfg = _full_backtest_config()
        task = BacktestTask.create(portfolio_uuid="ptid", name="t", config=cfg)
        proc = _make_processor(task)

        calls = []

        class FakeResult:
            inserted = 3
            skipped = 0
            errors = 0

        class FakeIngester:
            def __init__(self_inner):
                pass

            def ingest_task_logs(self_inner, task_uuid):
                calls.append(task_uuid)
                return FakeResult()

        monkeypatch.setattr(_ingester_module(), "LogIngester", FakeIngester)

        proc._ingest_task_logs()

        assert len(calls) == 1, f"expected one ingest call, got {calls}"
        assert calls[0] == task.task_uuid

    def test_ingest_failure_does_not_raise(self, monkeypatch):
        """灌入异常必须静默降级（不影响已完成的回测状态）。"""
        cfg = _full_backtest_config()
        task = BacktestTask.create(portfolio_uuid="ptid", name="t", config=cfg)
        proc = _make_processor(task)

        class BoomIngester:
            def __init__(self_inner):
                raise RuntimeError("boom-ingest")

        monkeypatch.setattr(_ingester_module(), "LogIngester", BoomIngester)

        # 不得抛出——回测已完成，日志灌入失败非致命
        proc._ingest_task_logs()
