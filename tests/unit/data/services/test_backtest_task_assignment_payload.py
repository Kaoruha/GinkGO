"""
ADR-018 第②步：生产端 payload 契约（StartAssignment/StopAssignment/CancelAssignment.to_payload）

门：新旧 payload 字节级相等（除死字段 broker_type/broker_attitude/commission_min 停发）。
聚焦 payload 结构 + 死字段停发 + 11 字段齐全；config 值恢复细节由
test_backtest_task_start_config.py 覆盖（此处不重复）。

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
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka():
    mock_producer = MagicMock()
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


def _sent_payload(mock_producer):
    """producer.send(topic, payload) 的 payload（第二位置参数）。"""
    return mock_producer.send.call_args[0][1]


# ---------- start payload 契约 ----------

class TestStartPayload:
    DEAD_FIELDS = ("broker_type", "broker_attitude", "commission_min")

    @pytest.mark.unit
    def test_start_payload_structure(self, service):
        """start payload = StartAssignment.to_payload()：5 键 task_uuid/portfolio_uuid/name/command/config。"""
        task = _make_task()
        _setup_task(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234-5678")
        assert result.is_success()
        payload = _sent_payload(mp)
        assert set(payload.keys()) == {"task_uuid", "portfolio_uuid", "name", "command", "config"}
        assert payload["command"] == "start"
        assert payload["task_uuid"] == "task-abc"

    @pytest.mark.unit
    def test_dead_fields_not_sent(self, service):
        """ADR-018：死字段 broker_type/broker_attitude/commission_min 生产端停发，不进 wire config。"""
        snapshot = {
            "start_date": "2025-06-01", "end_date": "2026-06-01",
            "broker_type": "mock", "broker_attitude": "real", "commission_min": 5.0,
        }
        task = _make_task(config_snapshot=json.dumps(snapshot))
        _setup_task(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234-5678")
        assert result.is_success()
        config = _sent_payload(mp)["config"]
        for dead in self.DEAD_FIELDS:
            assert dead not in config, f"死字段 {dead} 不应进 wire payload"

    @pytest.mark.unit
    def test_config_has_eleven_fields(self, service):
        """config 唯一默认表归 DTO：snapshot 未给的 optional 由 DTO 构造期填默认，11 字段齐全。"""
        task = _make_task()  # snapshot 只给 start/end/initial_cash
        _setup_task(service, task)
        with _mock_kafka() as mp:
            result = service.start_task(uuid="uuid-1234-5678")
        assert result.is_success()
        config = _sent_payload(mp)["config"]
        expected = {"start_date", "end_date", "initial_cash", "commission_rate",
                    "slippage_rate", "benchmark_return", "max_position_ratio",
                    "stop_loss_ratio", "take_profit_ratio", "frequency", "analyzers"}
        assert set(config.keys()) == expected


# ---------- stop payload 契约 ----------

class TestStopPayload:
    @pytest.mark.unit
    def test_stop_payload_minimal(self, service):
        """stop payload = StopAssignment.to_payload()：仅 {task_uuid, command}。"""
        task = _make_task(status="running")
        _setup_task(service, task)
        with _mock_kafka() as mp:
            result = service.stop_task(uuid="uuid-1234-5678")
        assert result.is_success()
        assert _sent_payload(mp) == {"task_uuid": "task-abc", "command": "stop"}


# ---------- cancel payload 契约 ----------

class TestCancelPayload:
    @pytest.mark.unit
    def test_cancel_payload_minimal(self, service):
        """cancel payload = CancelAssignment.to_payload()：仅 {task_uuid, command}。"""
        task = _make_task(status="created")
        _setup_task(service, task)
        with _mock_kafka() as mp:
            result = service.cancel_task(uuid="uuid-1234-5678")
        assert result.is_success()
        assert _sent_payload(mp) == {"task_uuid": "task-abc", "command": "cancel"}
