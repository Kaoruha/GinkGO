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
        """缺 portfolio_uuid（task.portfolio_id 也无）→ #5646 守卫在清理块之前早返回 ServiceResult.error，不进 Kafka。

        守卫恢复后拒绝发生在守卫（早返回），非 DTO 构造期；二者皆 service 层拒绝，不进 Kafka。
        """
        task = _make_task(
            portfolio_id=None,
            config_snapshot=json.dumps({"start_date": "2025-01-01", "end_date": "2025-12-31"}),
        )
        _setup(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234")  # 不传 portfolio_uuid
        assert not result.is_success(), f"缺 portfolio_uuid 应在 service 层被拒，got success"
        mp.send.assert_not_called()

    @pytest.mark.unit
    def test_missing_portfolio_rejects_before_cleanup(self, service):
        """#5646 守卫回归：孤儿任务（无 portfolio）重跑必须在清理块之前拒——
        9 表清理 CRUD.remove 不应被调用，否则历史数据在拒绝前被不可逆删除。
        （复现 PR 删守卫引入的回归：清理块在 DTO 拒绝前执行，删光 order/position/signal/analyzer 历史）
        """
        task = _make_task(
            portfolio_id=None,
            status="completed",  # 重跑场景：任务曾跑过，有历史数据
            config_snapshot=json.dumps({"start_date": "2025-01-01", "end_date": "2025-12-31"}),
        )
        _setup(service, task)
        # 注入 mock 清理 CRUD，验证清理块未执行（否则数据被删）
        cleanup = {
            "signal": MagicMock(), "position_record": MagicMock(),
            "analyzer_record": MagicMock(), "order_record": MagicMock(),
            "transfer_record": MagicMock(),  # ClickHouse 5
            "order": MagicMock(), "position": MagicMock(),
            "transfer": MagicMock(), "signal_tracker": MagicMock(),  # MySQL 4
        }
        service._signal_crud = cleanup["signal"]
        service._position_record_crud = cleanup["position_record"]
        service._analyzer_record_crud = cleanup["analyzer_record"]
        service._order_record_crud = cleanup["order_record"]
        service._transfer_record_crud = cleanup["transfer_record"]
        service._order_crud = cleanup["order"]
        service._position_crud = cleanup["position"]
        service._transfer_crud = cleanup["transfer"]
        service._signal_tracker_crud = cleanup["signal_tracker"]

        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234")  # 不传 portfolio_uuid

        assert not result.is_success(), "孤儿任务应在 service 层被拒"
        mp.send.assert_not_called()
        leaked = [n for n, c in cleanup.items() if c.remove.called]
        assert not leaked, f"#5646 守卫缺失：清理块在拒绝前执行，删除了 {leaked}"
