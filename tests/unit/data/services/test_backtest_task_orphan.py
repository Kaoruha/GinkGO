"""
#4853：回测任务孤儿治理。

两层防御：
1. 派发期（防新增）：producer.send 返回 False → start_task 标 task failed 并报错，
   不再 fire-and-forget 留下永久 running 孤儿。
2. 兜底（清存量）：cleanup_orphan_tasks 扫描 running 超 N 分钟无进展的任务标 failed，
   处理历史孤儿与 Worker 重启丢消息场景。

参考既有 mock 模式：test_backtest_task_assignment_payload.py。
"""
import sys
import os
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

import pytest

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


def _make_task(**overrides):
    task = MagicMock()
    task.uuid = "uuid-1234-5678"
    task.task_id = "task-abc"
    task.portfolio_id = "portfolio-001"
    task.name = "test_backtest"
    task.backtest_start_date = None
    task.backtest_end_date = None
    task.status = "completed"
    task.config_snapshot = json.dumps({
        "start_date": "2025-06-01",
        "end_date": "2026-06-01",
        "initial_cash": 200000.0,
    })
    task.start_time = None
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka(send_return=True):
    """Mock GinkgoProducer；send_return 控制 send() 返回值（True=送达，False=失败）。"""
    mock_producer = MagicMock()
    mock_producer.send.return_value = send_return
    mock_container = MagicMock()
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
         patch("ginkgo.data.containers.container", mock_container):
        yield mock_producer


@pytest.fixture
def service():
    crud = MagicMock()
    return BacktestTaskService(crud_repo=crud)


def _setup_task(service, task):
    service._crud_repo.get_by_uuid.return_value = task
    service._crud_repo.find.return_value = []
    service.update_status = MagicMock(return_value=ServiceResult.success(task, "ok"))


# ---------- 派发期：防新增孤儿 ----------

class TestStartDispatchFailure:
    """producer.send 返回 False 时，start_task 必须标记 task failed 并报错。"""

    @pytest.mark.unit
    def test_send_false_marks_task_failed(self, service):
        """send=False → start_task 返回 error，update_status(failed) 被调。"""
        task = _make_task()
        _setup_task(service, task)
        with _mock_kafka(send_return=False):
            result = service.start_task(uuid="uuid-1234-5678")

        assert not result.is_success()
        statuses = [c.kwargs.get("status") for c in service.update_status.call_args_list]
        assert "failed" in statuses

    @pytest.mark.unit
    def test_send_true_returns_success_no_failed(self, service):
        """回归：send=True → start_task 成功，update_status 不含 failed（仅 pending）。"""
        task = _make_task()
        _setup_task(service, task)
        with _mock_kafka(send_return=True):
            result = service.start_task(uuid="uuid-1234-5678")

        assert result.is_success()
        statuses = [c.kwargs.get("status") for c in service.update_status.call_args_list]
        assert "failed" not in statuses


# ---------- 兜底：清存量孤儿 ----------

class TestCleanupOrphanTasks:
    """cleanup_orphan_tasks 扫描 running 超 N 分钟无进展的任务标 failed。"""

    @pytest.mark.unit
    def test_stale_running_marked_failed(self, service):
        """running + start_time 早于阈值 → 标 failed。"""
        now = datetime.now(timezone.utc)
        stale = _make_task(
            status="running",
            start_time=now - timedelta(minutes=60),
        )
        stale.uuid = "stale-uuid"
        service._crud_repo.get_running_tasks.return_value = [stale]
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        result = service.cleanup_orphan_tasks(timeout_minutes=30)

        assert result.is_success()
        service.update_status.assert_called_once()
        assert service.update_status.call_args.kwargs.get("status") == "failed"
        assert "stale-uuid" == service.update_status.call_args.args[0]

    @pytest.mark.unit
    def test_fresh_running_not_touched(self, service):
        """running + start_time 新鲜 → 不动。"""
        now = datetime.now(timezone.utc)
        fresh = _make_task(
            status="running",
            start_time=now - timedelta(minutes=5),
        )
        service._crud_repo.get_running_tasks.return_value = [fresh]
        service.update_status = MagicMock()

        result = service.cleanup_orphan_tasks(timeout_minutes=30)

        assert result.is_success()
        service.update_status.assert_not_called()

    @pytest.mark.unit
    def test_running_without_start_time_skipped(self, service):
        """running 但 start_time=None（数据残缺）→ 跳过不崩。"""
        no_time = _make_task(status="running", start_time=None)
        service._crud_repo.get_running_tasks.return_value = [no_time]
        service.update_status = MagicMock()

        result = service.cleanup_orphan_tasks(timeout_minutes=30)

        assert result.is_success()
        service.update_status.assert_not_called()
