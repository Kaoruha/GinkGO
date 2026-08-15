"""事件信封单测：canonical_status 归一 + build_event 形状。"""

import os

# #5464: api.core import 链触发 config.py 全局 Settings()，需合法 SECRET_KEY。
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-jwt-security-tests")

import pytest

from websocket.events import build_event, canonical_status


# ---------- canonical_status ----------


@pytest.mark.unit
def test_canonical_status_maps_all_worker_states():
    """worker 大写枚举 → 规范小写；中间态归入 running。"""
    assert canonical_status("PENDING") == "pending"
    assert canonical_status("DATA_PREPARING") == "running"
    assert canonical_status("ENGINE_BUILDING") == "running"
    assert canonical_status("RUNNING") == "running"
    assert canonical_status("COMPLETED") == "completed"
    assert canonical_status("FAILED") == "failed"
    assert canonical_status("CANCELLED") == "stopped"


@pytest.mark.unit
def test_canonical_status_unknown_passthrough_lowercase():
    assert canonical_status("SomeNewState") == "somenewstate"


@pytest.mark.unit
def test_canonical_status_none_uses_default():
    assert canonical_status(None) == "running"
    assert canonical_status("") == "running"
    assert canonical_status(None, default="pending") == "pending"


# ---------- build_event ----------


@pytest.mark.unit
def test_build_event_shape():
    msg = build_event("backtest.failed", "backtest_task", "uuid-1", "failed", {"error": "boom"})
    assert msg["type"] == "event"
    assert msg["event"] == "backtest.failed"
    assert msg["entity"] == "backtest_task"
    assert msg["id"] == "uuid-1"
    assert msg["status"] == "failed"
    assert msg["data"] == {"error": "boom"}
    assert "timestamp" in msg


@pytest.mark.unit
def test_build_event_status_omitted_when_none():
    """无语义状态（如 notification）不携带 status 键。"""
    msg = build_event("notification", "notification", "nid", None, {"content": "hi"})
    assert "status" not in msg


@pytest.mark.unit
def test_build_event_data_defaults_empty():
    msg = build_event("backtest.stopped", "backtest_task", "uuid-2", "stopped")
    assert msg["data"] == {}
