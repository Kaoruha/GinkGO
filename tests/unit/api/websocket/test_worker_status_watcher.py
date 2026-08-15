"""WorkerStatusWatcher 单测：_diff 纯函数表驱动 + 首轮播种不广播。"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import asyncio

import pytest

import services.worker_status_watcher as wsw
from services.worker_status_watcher import WorkerStatusWatcher, _diff


def _row(id, status="running", type="backtest_worker"):
    return {"id": id, "type": type, "status": status}


# ---------- _diff 纯函数 ----------


@pytest.mark.unit
def test_diff_no_change():
    prev = {"w1": _row("w1")}
    cur = {"w1": _row("w1")}
    assert _diff(prev, cur) == []


@pytest.mark.unit
def test_diff_added_worker():
    prev = {}
    cur = {"w1": _row("w1")}
    changes = _diff(prev, cur)
    assert len(changes) == 1
    assert changes[0]["id"] == "w1"
    assert changes[0]["status"] == "running"
    assert changes[0]["data"]["previous_status"] is None


@pytest.mark.unit
def test_diff_status_change():
    prev = {"w1": _row("w1", status="running")}
    cur = {"w1": _row("w1", status="idle")}
    changes = _diff(prev, cur)
    assert len(changes) == 1
    assert changes[0]["status"] == "idle"
    assert changes[0]["data"]["previous_status"] == "running"


@pytest.mark.unit
def test_diff_removed_worker_goes_offline():
    prev = {"w1": _row("w1", status="running")}
    cur = {}
    changes = _diff(prev, cur)
    assert len(changes) == 1
    assert changes[0]["id"] == "w1"
    assert changes[0]["status"] == "offline"
    assert changes[0]["data"]["previous_status"] == "running"


# ---------- watch loop 首轮行为 ----------


@pytest.mark.unit
def test_first_pass_seeds_without_broadcast():
    """首轮只播种：快照变化发生在第二轮才广播。"""
    broadcasted = []

    async def _fake_broadcast(event, entity, id, status=None, data=None):
        broadcasted.append({"id": id, "status": status})

    original = wsw.broadcast_event
    wsw.broadcast_event = _fake_broadcast

    snapshots = iter([
        {"w1": _row("w1", status="running")},
        {"w1": _row("w1", status="running")},   # 第二轮相同 → 不广播
        {"w1": _row("w1", status="idle")},      # 第三轮变化 → 广播
        {"w1": _row("w1", status="idle")},      # 冗余：线程冷启动慢时窗口内多轮
        {"w1": _row("w1", status="idle")},
    ])
    wsw._snapshot_sync = lambda: next(snapshots, {"w1": _row("w1", status="idle")})

    watcher = WorkerStatusWatcher()
    watcher.INTERVAL = 0.01

    async def _bounded():
        await watcher.start()
        await asyncio.sleep(0.3)
        await watcher.stop()

    try:
        asyncio.run(_bounded())
    finally:
        wsw.broadcast_event = original

    assert broadcasted == [{"id": "w1", "status": "idle"}]
