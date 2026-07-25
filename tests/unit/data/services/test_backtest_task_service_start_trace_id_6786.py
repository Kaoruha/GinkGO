# Issue #6786: service 层 start_task 派发 Kafka 携带 trace_id header（派发第二入口）
#
# api/api/backtest.py 有两条 Kafka 派发路径：
#   1. POST "" create_backtest → send_task_to_kafka（已写 headers，见 test_backtest_dispatch_trace_id_6786.py）
#   2. POST /{uuid}/start → task_service.start_task（本测试覆盖）
# 两条都在 API 进程内（FastAPI handler 经 #6784 TraceIdMiddleware 注入 GLOG contextvars），
# start_task 同进程同步调用继承 contextvars，须取 trace_id 写 header，
# 否则 /start 入口派发的回测在 worker 侧无 trace_id，全链路日志断链。

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
    """构建 mock task 对象（config_snapshot 完整，驱动 start_task 到 Kafka 派发）。"""
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
def _mock_kafka_and_container():
    """统一 mock Kafka producer 和 container（旧数据清理 / DTO 构造）。"""
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


class TestStartTaskPropagatesTraceIdHeader:
    """#6786: service 层 start_task 派发携带 trace_id header（POST /{uuid}/start 入口）"""

    @pytest.mark.unit
    def test_start_task_propagates_trace_id_header(self, service):
        """GLOG contextvars 有 trace_id 时，start_task 的 producer.send 收到 headers=[("trace_id", bytes)]。"""
        from ginkgo.libs import GLOG

        task = _make_task()
        _setup_task(service, task)

        with _mock_kafka_and_container() as mock_producer, \
             GLOG.with_trace_id("tid-svc-789"):
            result = service.start_task(uuid="uuid-1234-5678")

        assert result.is_success(), f"start_task failed: {result.error}"
        mock_producer.send.assert_called_once()
        headers = mock_producer.send.call_args.kwargs.get("headers")
        assert headers == [("trace_id", b"tid-svc-789")]

    @pytest.mark.unit
    def test_start_task_no_trace_id_no_header(self, service):
        """无 trace_id 上下文时 headers=None（向后兼容，不污染消息，不破坏既有 start_task 测试）。"""
        from ginkgo.libs.core.logger import _trace_id_ctx

        task = _make_task()
        _setup_task(service, task)

        # 显式隔离 contextvars（防前序测试 with_trace_id 残留）
        token = _trace_id_ctx.set(None)
        try:
            with _mock_kafka_and_container() as mock_producer:
                result = service.start_task(uuid="uuid-1234-5678")
        finally:
            _trace_id_ctx.reset(token)

        assert result.is_success()
        headers = mock_producer.send.call_args.kwargs.get("headers")
        assert headers is None
