"""
#4853：回测任务孤儿治理。

两层防御：
1. 派发期（防新增）：producer.send 返回 False → start_task 标 task failed 并报错，
   不再 fire-and-forget 留下永久 running 孤儿。
2. 兜底（清存量）：cleanup_orphan_tasks 判定改为"running 任务不被任何活跃 worker
   心跳持有 → 孤儿 → 标 failed"（#6846）。不再用 start_time 超时（worker crash/
   丢消息场景下 start_time 无法区分"真在跑"与"已丢"）；心跳持有集才是"有 worker
   在管这事"的真实信号。Redis 不可达时跳过本轮，防基础设施抖动误杀全量。

参考既有 mock 模式：test_backtest_task_assignment_payload.py。
"""
import sys
import os
import json
from datetime import datetime, timedelta
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
    """cleanup_orphan_tasks: running 任务不被任何活跃 worker 心跳持有 → 孤儿 → 标 failed。"""

    def _set_held(self, service, held):
        """注入 _get_held_task_uuids 返回值（set=被持有集，None=Redis 不可达）。"""
        service._get_held_task_uuids = MagicMock(return_value=held)

    @pytest.mark.unit
    def test_orphan_not_held_marked_failed(self, service):
        """running + 不被任何活跃 worker 持有 → 标 failed。"""
        orphan = _make_task(status="running")
        orphan.uuid = "orphan-1"
        service._crud_repo.get_running_tasks.return_value = [orphan]
        self._set_held(service, set())
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_called_once()
        assert service.update_status.call_args.kwargs.get("status") == "failed"
        assert service.update_status.call_args.args[0] == "orphan-1"

    @pytest.mark.unit
    def test_held_running_not_touched(self, service):
        """running + 被活跃 worker 持有 → 不动。"""
        held_task = _make_task(status="running")
        held_task.uuid = "held-1"
        service._crud_repo.get_running_tasks.return_value = [held_task]
        self._set_held(service, {"held-1"})
        service.update_status = MagicMock()

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_not_called()

    @pytest.mark.unit
    def test_mixed_only_orphans_marked(self, service):
        """held 与 orphan 混合 → 仅 orphan 被标 failed。"""
        held = _make_task(status="running"); held.uuid = "held"
        orphan = _make_task(status="running"); orphan.uuid = "orphan"
        service._crud_repo.get_running_tasks.return_value = [held, orphan]
        self._set_held(service, {"held"})
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        service.cleanup_orphan_tasks()

        marked = [c.args[0] for c in service.update_status.call_args_list]
        assert marked == ["orphan"]

    @pytest.mark.unit
    def test_redis_down_skips_cleanup(self, service):
        """_get_held_task_uuids 返回 None（Redis 不可达）→ 跳过本轮，不误杀。"""
        orphan = _make_task(status="running"); orphan.uuid = "orphan-x"
        service._crud_repo.get_running_tasks.return_value = [orphan]
        self._set_held(service, None)
        service.update_status = MagicMock()

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_not_called()

    @pytest.mark.unit
    def test_failure_message_includes_business_timestamp(self, service):
        """告警消息含 business_timestamp，便于运维定位最后业务推进点。"""
        orphan = _make_task(
            status="running",
            business_timestamp=datetime(2026, 7, 28, 12, 0, 0),
        )
        orphan.uuid = "orphan-ts"
        service._crud_repo.get_running_tasks.return_value = [orphan]
        self._set_held(service, set())
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        service.cleanup_orphan_tasks()

        msg = service.update_status.call_args.kwargs.get("error_message", "")
        assert "2026-07-28" in msg

    # ---------- 宽限期:启动窗口竞态防误杀 ----------

    @pytest.mark.unit
    def test_grace_period_skips_fresh_running_task(self, service):
        """刚置 running(< 宽限期)且缺席心跳快照 → 跳过,不标 failed。

        场景:任务登记进 worker self.tasks 后,最长 10s 才随下一次心跳
        进持有集;Reaper 恰在此窗口扫描 → 误杀(2026-08-16 24ec2a63 实例)。
        """
        fresh = _make_task(status="running", start_time=datetime.now())
        fresh.uuid = "fresh-1"
        service._crud_repo.get_running_tasks.return_value = [fresh]
        self._set_held(service, set())
        service.update_status = MagicMock()

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_not_called()

    @pytest.mark.unit
    def test_grace_period_expired_marks_orphan(self, service):
        """start_time 超过宽限期且不被持有 → 照常标 failed(兜底使命不受影响)。"""
        stale = _make_task(status="running", start_time=datetime.now() - timedelta(seconds=120))
        stale.uuid = "stale-1"
        service._crud_repo.get_running_tasks.return_value = [stale]
        self._set_held(service, set())
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_called_once()
        assert service.update_status.call_args.kwargs.get("status") == "failed"

    @pytest.mark.unit
    def test_grace_none_start_time_still_marked(self, service):
        """start_time 缺失(None)不享受宽限 → 照常判定,数据缺失不得让兜底失效。"""
        no_st = _make_task(status="running", start_time=None)
        no_st.uuid = "nost-1"
        service._crud_repo.get_running_tasks.return_value = [no_st]
        self._set_held(service, set())
        service.update_status = MagicMock(return_value=ServiceResult.success({}, "ok"))

        result = service.cleanup_orphan_tasks()

        assert result.is_success()
        service.update_status.assert_called_once()


# ---------- 状态机守卫:正向迁移白名单(2026-08-16 竞态实证) ----------

class TestStatusTransitionGuard:
    """update_status 拒绝非法回退。实例:API 置 pending 与 worker 置 running
    并发提交序不可控,running 曾被 pending 反向覆盖 → 任务卡"排队中"但进度在走。"""

    def _task_with_status(self, service, status):
        task = _make_task(status=status)
        task.uuid = "uuid-1234-5678"
        service._crud_repo.get_by_uuid.return_value = task
        service._crud_repo.update_task_status.return_value = 1

    @pytest.mark.unit
    def test_running_to_pending_rejected(self, service):
        """核心竞态案例:running→pending 反向覆盖必须被拒。"""
        self._task_with_status(service, "running")
        r = service.update_status("uuid-1234-5678", status="pending")
        assert not r.is_success()
        service._crud_repo.update_task_status.assert_not_called()

    @pytest.mark.unit
    def test_terminal_to_terminal_rejected(self, service):
        """终态互转拒绝:failed→completed(旧'自愈'路径,实为误标症状的掩盖)。"""
        self._task_with_status(service, "failed")
        r = service.update_status("uuid-1234-5678", status="completed")
        assert not r.is_success()

    @pytest.mark.unit
    def test_legal_transitions_pass(self, service):
        """合法正向迁移全部放行:start/重跑/认领/完成/失败/停止。"""
        for current, target in [
            ("created", "pending"),      # start
            ("completed", "pending"),    # 重跑
            ("pending", "running"),      # worker 认领
            ("created", "running"),      # 直达(容忍)
            ("running", "completed"),    # 完成
            ("pending", "completed"),    # 竞态快的完成
            ("running", "failed"),       # 失败
            ("created", "failed"),       # 派发失败
            ("running", "stopped"),      # 停止
        ]:
            self._task_with_status(service, current)
            r = service.update_status("uuid-1234-5678", status=target)
            assert r.is_success(), f"{current}->{target} should be legal"

    @pytest.mark.unit
    def test_same_status_idempotent_write_passes(self, service):
        """同值写放行(重试幂等):completed→completed 不视为非法迁移。"""
        self._task_with_status(service, "completed")
        r = service.update_status("uuid-1234-5678", status="completed")
        assert r.is_success()
        service._crud_repo.update_task_status.assert_called_once()
