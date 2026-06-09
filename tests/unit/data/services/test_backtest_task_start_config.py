"""
#5839: BacktestTaskService.start_task 从 config_snapshot 恢复完整配置

覆盖：
- start_task 从 config_snapshot 恢复 start_date/end_date（解决 Missing dates）
- start_task 从 config_snapshot 恢复 commission_rate/slippage_rate 等字段
- 显式传入参数覆盖 config_snapshot 中的值
- config_snapshot 为空时回退到默认值
"""

import sys
import os
import json
import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from contextlib import contextmanager

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


def _make_task(**overrides):
    """构建 mock task 对象"""
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
        "commission_rate": 0.0005,
        "slippage_rate": 0.0002,
        "frequency": "DAY",
    })
    for k, v in overrides.items():
        setattr(task, k, v)
    return task


@contextmanager
def _mock_kafka_and_container():
    """统一 mock Kafka producer 和 container（旧数据清理）"""
    mock_producer = MagicMock()
    mock_container = MagicMock()
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer), \
         patch("ginkgo.data.containers.container", mock_container):
        yield mock_producer


@pytest.fixture
def service():
    crud = MagicMock()
    svc = BacktestTaskService(crud_repo=crud)
    return svc


def _setup_task(service, task):
    """配置 service mock 以支持 start_task 流程"""
    service._crud_repo.get_by_uuid.return_value = task
    service._crud_repo.find.return_value = []
    service.update_status = MagicMock(return_value=ServiceResult.success(task, "ok"))


def _get_kafka_config(mock_producer):
    """从 Kafka producer.send 调用中提取 config dict"""
    send_call = mock_producer.send.call_args
    return send_call[0][1]["config"]


class TestStartTaskRestoresConfigFromSnapshot:
    """start_task 从 config_snapshot 恢复配置"""

    @pytest.mark.unit
    def test_restores_dates_from_config_snapshot(self, service):
        """config_snapshot 中的日期应被恢复到 Kafka config"""
        task = _make_task(backtest_start_date=None, backtest_end_date=None)
        _setup_task(service, task)

        with _mock_kafka_and_container() as mock_producer:
            result = service.start_task(uuid="uuid-1234-5678")

        assert result.is_success(), f"start_task failed: {result.error}"
        config = _get_kafka_config(mock_producer)
        assert config["start_date"] == "2025-06-01"
        assert config["end_date"] == "2026-06-01"

    @pytest.mark.unit
    def test_restores_all_fields_from_config_snapshot(self, service):
        """config_snapshot 中的所有配置字段应被恢复"""
        task = _make_task()
        _setup_task(service, task)

        with _mock_kafka_and_container() as mock_producer:
            result = service.start_task(uuid="uuid-1234-5678")

        assert result.is_success()
        config = _get_kafka_config(mock_producer)
        assert config["initial_cash"] == 200000.0
        assert config["commission_rate"] == 0.0005
        assert config["slippage_rate"] == 0.0002
        assert config["frequency"] == "DAY"

    @pytest.mark.unit
    def test_explicit_params_override_config_snapshot(self, service):
        """显式传入的参数应覆盖 config_snapshot 中的值"""
        task = _make_task()
        _setup_task(service, task)

        with _mock_kafka_and_container() as mock_producer:
            result = service.start_task(
                uuid="uuid-1234-5678",
                start_date="2026-01-01",
                end_date="2026-12-31",
                initial_cash=500000.0,
            )

        assert result.is_success()
        config = _get_kafka_config(mock_producer)
        assert config["start_date"] == "2026-01-01"
        assert config["end_date"] == "2026-12-31"
        assert config["initial_cash"] == 500000.0
        # config_snapshot 中的其他字段保留
        assert config["commission_rate"] == 0.0005

    @pytest.mark.unit
    def test_fallback_when_config_snapshot_empty(self, service):
        """config_snapshot 为空时回退到默认值"""
        task = _make_task(config_snapshot="{}", backtest_start_date=None, backtest_end_date=None)
        _setup_task(service, task)

        with _mock_kafka_and_container() as mock_producer:
            result = service.start_task(uuid="uuid-1234-5678")

        assert result.is_success()
        config = _get_kafka_config(mock_producer)
        assert config["start_date"] == ""
        assert config["end_date"] == ""
        assert config["initial_cash"] == 100000.0
