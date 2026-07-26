"""#6787: deploy 派发 Kafka 携带 trace_id header（可观测层 3/4, AC1）

deploy 链路派发 ControlCommand.deploy 到 CONTROL_COMMANDS topic。
deployment_service._dispatch_deploy_command 从 GLOG contextvars 取 #6784 中间件
注入的 trace_id，写 Kafka header，使 paper/live worker 消费端可恢复（AC2/AC3）。
无 trace_id 时 headers=None（向后兼容，不破坏既有派发）。
"""
import sys
import os
import pytest
from unittest.mock import MagicMock, patch

_path = os.path.join(os.path.dirname(__file__), '..', '..', '..')
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.services.deployment_service import DeploymentService


@pytest.fixture
def service():
    return DeploymentService(deployment_crud=MagicMock())


class TestDispatchDeployCommandPropagatesTraceId:
    """#6787 AC1: deploy 派发携带 trace_id Kafka header"""

    @pytest.mark.unit
    def test_propagates_trace_id_header(self, service):
        """GLOG contextvars 有 trace_id 时，producer.send 收到 headers=[("trace_id", bytes)]。"""
        from ginkgo.libs import GLOG

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", autospec=True) as MockProducer, \
                GLOG.with_trace_id("tid-deploy-6787"):
            mock_producer = MockProducer.return_value
            ok = service._dispatch_deploy_command("port-new-123")

        assert ok is True
        mock_producer.send.assert_called_once()
        kwargs = mock_producer.send.call_args.kwargs
        assert kwargs["headers"] == [("trace_id", b"tid-deploy-6787")]

    @pytest.mark.unit
    def test_no_trace_id_no_header(self, service):
        """无 trace_id 上下文时 headers=None（向后兼容）。"""
        from ginkgo.libs.core.logger import _trace_id_ctx

        token = _trace_id_ctx.set(None)
        try:
            with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", autospec=True) as MockProducer:
                mock_producer = MockProducer.return_value
                ok = service._dispatch_deploy_command("port-new-123")
        finally:
            _trace_id_ctx.reset(token)

        assert ok is True
        kwargs = mock_producer.send.call_args.kwargs
        assert kwargs.get("headers") is None
