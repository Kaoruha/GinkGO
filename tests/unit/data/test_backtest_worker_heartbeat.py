"""
#6846：BacktestWorker 心跳须携带当前持有的 task_uuids。

此前心跳只有 running_tasks 计数（int），无法判定"某个 running 任务是否被某
活跃 worker 持有"。孤儿治理（cleanup_orphan_tasks）改心跳判定后，需要从
心跳 union 出"活跃 worker 持有的 task 集合"，故心跳结构须带上 task_uuids。

向后兼容：旧心跳 JSON（无 task_uuids）反序列化不崩，默认空列表。
"""
import sys
import os
import json

import pytest

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.redis_schema import BacktestWorkerHeartbeat, WorkerStatus


class TestHeartbeatCarriesTaskUuids:
    """create 携带 task_uuids，to_json 落盘，from_json 可还原。"""

    @pytest.mark.unit
    def test_create_carries_task_uuids(self):
        hb = BacktestWorkerHeartbeat.create(
            worker_id="bw-1", status=WorkerStatus.RUNNING,
            running_tasks=2, task_uuids=["task-a", "task-b"],
        )
        assert hb.task_uuids == ["task-a", "task-b"]

    @pytest.mark.unit
    def test_to_json_contains_task_uuids(self):
        hb = BacktestWorkerHeartbeat.create(
            worker_id="bw-1", status=WorkerStatus.RUNNING,
            task_uuids=["task-a"],
        )
        payload = json.loads(hb.to_json())
        assert payload["task_uuids"] == ["task-a"]

    @pytest.mark.unit
    def test_from_json_roundtrip(self):
        hb = BacktestWorkerHeartbeat.create(
            worker_id="bw-1", status=WorkerStatus.RUNNING,
            running_tasks=1, task_uuids=["task-x"],
        )
        restored = BacktestWorkerHeartbeat.from_json(hb.to_json())
        assert restored.task_uuids == ["task-x"]

    @pytest.mark.unit
    def test_from_json_legacy_payload_without_task_uuids(self):
        """旧心跳（无 task_uuids 字段）反序列化默认 []，不崩。"""
        legacy = {
            "worker_id": "bw-1",
            "status": "running",
            "timestamp": "2026-07-29T00:00:00",
            "running_tasks": 1,
            "max_tasks": 5,
            "started_at": "2026-07-29T00:00:00",
            "last_heartbeat": "2026-07-29T00:00:00",
        }
        restored = BacktestWorkerHeartbeat.from_json(json.dumps(legacy))
        assert restored.task_uuids == []

    @pytest.mark.unit
    def test_create_default_empty_task_uuids(self):
        hb = BacktestWorkerHeartbeat.create(
            worker_id="bw-1", status=WorkerStatus.RUNNING,
        )
        assert hb.task_uuids == []
