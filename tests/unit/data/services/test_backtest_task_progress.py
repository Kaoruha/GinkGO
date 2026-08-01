"""
#6846：回测任务 business_timestamp 写入。

worker progress_tracker 每次上报 current_date（回测当前处理的业务日期），
但 update_progress 从未把该日期落到 task.business_timestamp —— 字段恒 None，
无法用作"业务推进"信号（issue #6846 前提之一）。

修复：update_progress(current_date=X) 同步写 business_timestamp=datetime_normalize(X)。

参考既有 mock 模式：test_backtest_task_orphan.py。
"""
import sys
import os
import json
from unittest.mock import MagicMock

import pytest

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.libs import datetime_normalize


def _make_task(**overrides):
    task = MagicMock()
    task.uuid = "uuid-1234-5678"
    task.task_id = "task-abc"
    task.portfolio_id = "portfolio-001"
    task.name = "test_backtest"
    task.status = "running"
    task.start_time = None
    task.business_timestamp = None
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@pytest.fixture
def service():
    crud = MagicMock()
    return BacktestTaskService(crud_repo=crud)


class TestUpdateProgressBusinessTimestamp:
    """update_progress 须把 current_date 落到 business_timestamp。"""

    @pytest.mark.unit
    def test_current_date_written_as_business_timestamp(self, service):
        """上报 current_date → modify 的 updates 含 business_timestamp = datetime_normalize(current_date)。"""
        task = _make_task()
        service._crud_repo.get_by_uuid.return_value = task
        service._crud_repo.modify.return_value = 1

        result = service.update_progress(
            uuid="uuid-1234-5678", current_date="2025-06-01"
        )

        assert result.is_success()
        call = service._crud_repo.modify.call_args
        updates = call.kwargs.get("updates")
        assert updates is not None
        assert "business_timestamp" in updates
        assert updates["business_timestamp"] == datetime_normalize("2025-06-01")

    @pytest.mark.unit
    def test_no_current_date_leaves_business_timestamp_absent(self, service):
        """回归：未传 current_date → 不动 business_timestamp（不强制清空）。"""
        task = _make_task()
        service._crud_repo.get_by_uuid.return_value = task
        service._crud_repo.modify.return_value = 1

        service.update_progress(uuid="uuid-1234-5678", progress=42.0)

        updates = service._crud_repo.modify.call_args.kwargs.get("updates")
        assert "business_timestamp" not in updates
