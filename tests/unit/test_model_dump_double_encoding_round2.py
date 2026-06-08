"""Tests for model_dump_json() double encoding — PR review round 2.

3 additional sites found in execution_cli.py (2) and node.py (1).
Same double-encoding root cause: GinkgoProducer.value_serializer calls
json.dumps() on whatever it receives, so passing a str (from model_dump_json)
results in double-encoded JSON.

Strategy:
- node.py: OrderSubmissionDTO is imported inside a closure, can't mock it.
  Instead: (a) verify DTO.model_dump() returns dict (contract test),
  (b) verify source code uses model_dump() not model_dump_json() (static).
- execution_cli.py: mock GinkgoProducer only, let real ScheduleUpdateDTO flow.
"""
import inspect
import re
import pytest
from unittest.mock import MagicMock, patch


# ============================================================================
# node.py — 实盘订单提交 (production-critical, highest priority)
# ============================================================================


@pytest.mark.tdd
class TestExecutionNodeOrderSubmission:
    """ExecutionNode must send dict to order_producer, not JSON string."""

    def test_order_submission_dto_model_dump_returns_dict(self):
        """OrderSubmissionDTO.model_dump() must return dict for Kafka serializer."""
        from ginkgo.interfaces.dtos import OrderSubmissionDTO

        dto = OrderSubmissionDTO(
            order_id="order-123",
            portfolio_id="pf-001",
            code="000001.SZ",
            direction="LONG",
            volume=100,
            price="10.5",
            timestamp="2026-01-01T10:00:00",
        )
        result = dto.model_dump()
        assert isinstance(result, dict), (
            f"OrderSubmissionDTO.model_dump() returned {type(result).__name__}, expected dict. "
            "Kafka value_serializer calls json.dumps() — passing a dict is correct."
        )

    def test_node_source_uses_model_dump_not_json(self):
        """#4667: node.py order submission must use model_dump() not model_dump_json().

        OrderSubmissionDTO is imported inside listener_thread closure,
        so runtime mocking is infeasible. Static source verification instead.
        """
        import ginkgo.workers.execution_node.node as mod

        source = inspect.getsource(mod)
        # Find the ORDERS_SUBMISSION send line
        pattern = r"order_producer\.send\(.*model_dump"
        matches = re.findall(pattern, source)
        assert len(matches) >= 1, (
            "Expected order_producer.send(...model_dump()) in node.py — not found"
        )
        # Verify NO model_dump_json near ORDERS_SUBMISSION
        bad_pattern = r"ORDERS_SUBMISSION.*model_dump_json"
        bad_matches = re.findall(bad_pattern, source)
        assert len(bad_matches) == 0, (
            f"Found model_dump_json() near ORDERS_SUBMISSION in node.py: {bad_matches}. "
            "This causes double encoding — use model_dump() instead."
        )


# ============================================================================
# execution_cli.py — NODE_PAUSE / NODE_RESUME commands
# ============================================================================


@pytest.mark.tdd
class TestExecutionCliDoubleEncoding:
    """execution_cli pause/resume must send dict to producer, not JSON string."""

    def test_node_pause_sends_dict_not_str(self):
        """execution_cli pause: model_dump_json() causes double encoding."""
        from typer.testing import CliRunner
        from ginkgo.client.execution_cli import app

        runner = CliRunner()
        mock_producer = MagicMock()

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer):
            runner.invoke(app, ["pause", "--node-id", "node-1"])

        assert mock_producer.send.called, "producer.send() was never called"
        value = mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )

    def test_node_resume_sends_dict_not_str(self):
        """execution_cli resume: model_dump_json() causes double encoding."""
        from typer.testing import CliRunner
        from ginkgo.client.execution_cli import app

        runner = CliRunner()
        mock_producer = MagicMock()

        with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoProducer", return_value=mock_producer):
            runner.invoke(app, ["resume", "--node-id", "node-1"])

        assert mock_producer.send.called, "producer.send() was never called"
        value = mock_producer.send.call_args[0][1]
        assert isinstance(value, dict), (
            f"Expected dict (model_dump), got {type(value).__name__}. "
            "Use model_dump() not model_dump_json() to avoid double encoding."
        )
