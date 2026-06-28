"""ADR-018 第⑤步：#5646 预校验收敛进 DTO 构造。

门（L95）：缺字段任务在 service 层即 ServiceResult.error，不进 Kafka。
- 空 dates → DTO BacktestAssignmentConfig Field(min_length=1) 构造期 ValidationError
  （补第③步删 worker 字面校验后的真空——空串 dates 现由 DTO 构造期拒）
- 缺 portfolio_uuid → DTO StartAssignment required str 构造期 ValidationError
  （删 service :604-611 手写 portfolio_uuid if，DTO 构造期校验取代，校验更严）

详见 docs/adrs/ADR-018-backtest-assignment-contract.md
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


def _make_task(**overrides):
    task = MagicMock()
    task.uuid = "uuid-1234"
    task.task_id = "task-abc"
    task.portfolio_id = "portfolio-001"
    task.name = "test"
    task.backtest_start_date = None
    task.backtest_end_date = None
    task.status = "created"
    task.config_snapshot = json.dumps({"start_date": "2025-01-01", "end_date": "2025-12-31"})
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka():
    mp = MagicMock()
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mp), \
         patch("ginkgo.data.containers.container", MagicMock()):
        yield mp


@pytest.fixture
def service():
    return BacktestTaskService(crud_repo=MagicMock())


def _setup(service, task):
    service._crud_repo.get_by_uuid.return_value = task
    service._crud_repo.find.return_value = []
    service.update_status = MagicMock(return_value=ServiceResult.success(task, "ok"))


class TestStartTaskValidationInDto:
    """#5646 预校验收敛：缺字段在 service 层 DTO 构造期即拒，不进 Kafka。"""

    @pytest.mark.unit
    def test_empty_dates_returns_error_no_kafka(self, service):
        """空 dates → DTO 构造期 ValidationError → ServiceResult.error，producer.send 不调。"""
        task = _make_task(config_snapshot=json.dumps({"start_date": "", "end_date": "2025-12-31"}))
        _setup(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234")
        assert not result.is_success(), f"空 dates 应在 service 层被拒，got success: {result.error}"
        mp.send.assert_not_called()

    @pytest.mark.unit
    def test_missing_portfolio_returns_error_no_kafka(self, service):
        """缺 portfolio_uuid（task.portfolio_id 也无）→ DTO StartAssignment required str → ServiceResult.error，不进 Kafka。"""
        task = _make_task(
            portfolio_id=None,
            config_snapshot=json.dumps({"start_date": "2025-01-01", "end_date": "2025-12-31"}),
        )
        _setup(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234")  # 不传 portfolio_uuid
        assert not result.is_success(), f"缺 portfolio_uuid 应在 service 层被拒，got success"
        mp.send.assert_not_called()
