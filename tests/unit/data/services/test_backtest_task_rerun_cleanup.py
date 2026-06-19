"""
BacktestTaskService.start_task 重跑清理循环契约测试

覆盖 backtest_task_service.py:609-627 的重跑旧数据清理逻辑（DI 改造后由容器注入 9 个 CRUD）：
- 注入的 9 个 CRUD 全部以 filters={"task_id": ...} 调用 remove
- CRUD 为 None（容器未注入）时跳过，其余仍清理
- 单个 CRUD.remove 抛异常时不中断后续清理（容错，逐表 try-except）
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from contextlib import contextmanager

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


# 9 个清理 CRUD 的 kwargs 名（与 __init__ 签名 / 清理循环 _cleanup_cruds 一一对应）
_CLEANUP_KWARGS = [
    "signal_crud", "order_crud", "position_crud", "position_record_crud",
    "analyzer_record_crud", "order_record_crud", "transfer_record_crud",
    "transfer_crud", "signal_tracker_crud",
]


def _make_task(**overrides):
    """构建可重跑状态的 mock task（status=completed 在 startable_states 内）"""
    task = MagicMock()
    task.uuid = "uuid-1234"
    task.task_id = "task-abc-001"
    task.portfolio_id = "portfolio-001"
    task.name = "rerun_cleanup_test"
    task.backtest_start_date = None
    task.backtest_end_date = None
    task.status = "completed"
    task.config_snapshot = json.dumps({
        "start_date": "2025-06-01",
        "end_date": "2026-06-01",
        "initial_cash": 100000.0,
    })
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka_and_container():
    """mock Kafka producer 与 container，隔离清理循环之后的发送流程"""
    mock_producer = MagicMock()
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
         patch("ginkgo.data.containers.container", MagicMock()):
        yield mock_producer


def _make_service_with_cruds(crud_overrides=None):
    """
    构造注入 9 个 mock CRUD 的 service。

    crud_overrides: {kwarg_name: value}，可传 None 模拟「容器未注入」。
    返回 (svc, cruds)，cruds 为 kwargs_name → mock/None 映射，便于断言。
    """
    task = _make_task()
    crud_repo = MagicMock()
    crud_repo.get_by_uuid.return_value = task
    crud_repo.find.return_value = []

    kwargs = {"crud_repo": crud_repo}
    cruds = {}
    for name in _CLEANUP_KWARGS:
        val = (crud_overrides or {}).get(name, MagicMock())
        kwargs[name] = val
        cruds[name] = val

    svc = BacktestTaskService(**kwargs)
    svc.update_status = MagicMock(return_value=ServiceResult.success(task, "ok"))
    return svc, cruds


class TestRerunCleanupLoop:
    """start_task 重跑清理 9 张关联表（DI: CRUD 由容器注入）"""

    @pytest.mark.unit
    def test_all_nine_cruds_remove_called_with_task_id(self):
        """重跑时 9 个注入 CRUD 全部以 filters={"task_id": task_id} 调用 remove"""
        svc, cruds = _make_service_with_cruds()
        task = svc._crud_repo.get_by_uuid.return_value

        with _mock_kafka_and_container():
            svc.start_task(uuid="uuid-1234")

        for name, crud in cruds.items():
            assert crud.remove.called, f"{name} 未被清理"
            crud.remove.assert_called_once_with(filters={"task_id": task.task_id})

    @pytest.mark.unit
    def test_none_crud_skipped_others_still_cleaned(self):
        """CRUD 为 None（容器未注入）时跳过，其余 CRUD 仍正常清理"""
        svc, cruds = _make_service_with_cruds(
            crud_overrides={"order_crud": None, "transfer_crud": None}
        )

        with _mock_kafka_and_container():
            result = svc.start_task(uuid="uuid-1234")

        # None 的两个被跳过（不报错），其余 7 个仍调用 remove
        assert cruds["order_crud"] is None
        assert cruds["transfer_crud"] is None
        for name in _CLEANUP_KWARGS:
            crud = cruds[name]
            if crud is None:
                continue
            assert crud.remove.called, f"{name} 未被清理"
        # start_task 整体未因 None 崩溃
        assert result.success is True

    @pytest.mark.unit
    def test_partial_crud_failure_does_not_abort_cleanup(self):
        """中间某 CRUD.remove 抛异常时，后续 CRUD 仍被清理（逐表 try-except 容错）"""
        svc, cruds = _make_service_with_cruds()
        # 位于列表中段的 position_crud 抛异常
        cruds["position_crud"].remove.side_effect = Exception("position 表锁")

        with _mock_kafka_and_container():
            result = svc.start_task(uuid="uuid-1234")

        # 异常被吞，start_task 仍成功
        assert result.success is True
        # position_crud 确实尝试过清理
        cruds["position_crud"].remove.assert_called_once()
        # 位于其后的 analyzer_record / signal_tracker 仍被清理（未中断）
        assert cruds["analyzer_record_crud"].remove.called
        assert cruds["signal_tracker_crud"].remove.called
