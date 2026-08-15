"""BacktestProgressConsumer 五个 _update_* 的 WS 事件广播单测（ADR-046）。

验证：状态先落库落缓存后广播；事件名/信封字段正确；
大写 state 归一小写（CANCELLED→stopped、DATA_PREPARING→running）。
"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import asyncio

import pytest

import services.backtest_progress_consumer as bpc
from services.backtest_progress_consumer import BacktestProgressConsumer


class _OkResult:
    def is_success(self):
        return True


class _FakeTaskService:
    def update_progress(self, *args, **kwargs):
        return _OkResult()

    def update_status(self, *args, **kwargs):
        return _OkResult()


@pytest.fixture()
def captured():
    """monkeypatch 掉 DB/Redis/广播，捕获 broadcast_event 调用。"""
    calls = []

    async def _fake_broadcast(event, entity, id, status=None, data=None):
        calls.append({"event": event, "entity": entity, "id": id,
                      "status": status, "data": data})

    async def _fake_set_progress(*args, **kwargs):
        pass

    bpc._get_task_service = lambda: _FakeTaskService()
    bpc.set_backtest_progress = _fake_set_progress
    bpc.broadcast_event = _fake_broadcast
    yield calls
    # monkeypatch 由 fixture 生命周期管理；此处手工恢复以防跨用例泄漏
    import importlib
    importlib.reload(bpc)


def _run(coro):
    return asyncio.run(coro)


@pytest.mark.unit
def test_update_progress_broadcasts_with_canonical_status(captured):
    _run(BacktestProgressConsumer()._update_progress(
        "task-1", 42.5, "2025-06-01", "DATA_PREPARING"))

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == "backtest.progress"
    assert ev["entity"] == "backtest_task"
    assert ev["id"] == "task-1"
    assert ev["status"] == "running"  # DATA_PREPARING → running
    assert ev["data"]["progress"] == 42.5
    assert ev["data"]["state"] == "data_preparing"


@pytest.mark.unit
def test_update_stage_broadcasts_running(captured):
    _run(BacktestProgressConsumer()._update_stage(
        "task-2", "data_prepare", "正在准备数据"))

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == "backtest.stage"
    assert ev["status"] == "running"
    assert ev["data"] == {"stage": "data_prepare", "message": "正在准备数据"}


@pytest.mark.unit
def test_update_completed_broadcasts_thin_result(captured):
    _run(BacktestProgressConsumer()._update_completed("task-3", {
        "total_pnl": 123.4, "sharpe_ratio": 1.5, "annual_return": 0.2,
        "win_rate": 0.6, "max_drawdown": 0.1,
        "unknown_field": "should-pass-through",
    }))

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == "backtest.completed"
    assert ev["status"] == "completed"
    assert ev["data"]["progress"] == 100
    assert ev["data"]["total_pnl"] == 123.4
    assert ev["data"]["sharpe_ratio"] == 1.5


@pytest.mark.unit
def test_update_failed_broadcasts_error(captured):
    _run(BacktestProgressConsumer()._update_failed("task-4", "engine crash"))

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == "backtest.failed"
    assert ev["status"] == "failed"
    assert ev["data"] == {"error": "engine crash"}


@pytest.mark.unit
def test_update_cancelled_broadcasts_stopped(captured):
    _run(BacktestProgressConsumer()._update_cancelled("task-5"))

    assert len(captured) == 1
    ev = captured[0]
    assert ev["event"] == "backtest.stopped"
    assert ev["status"] == "stopped"  # cancelled → stopped（DB 词汇）
    assert ev["data"] == {}


@pytest.mark.unit
def test_broadcast_failure_does_not_raise(captured):
    """广播异常不得打断消费循环（handler 外层 try/except 兜底）。"""

    async def _boom(*args, **kwargs):
        raise RuntimeError("ws down")

    bpc.broadcast_event = _boom

    # 不抛异常即通过
    _run(BacktestProgressConsumer()._update_cancelled("task-6"))
