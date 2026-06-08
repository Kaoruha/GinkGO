"""Smoke tests for livecore.scheduler sub-components -- #3870

#3856 check_commands() TDD tests
"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.livecore.scheduler.load_balancer import LoadBalancer
    HAS_LB = True
except ImportError:
    HAS_LB = False

try:
    from ginkgo.livecore.scheduler.command_handler import CommandHandler
    HAS_CMD = True
except ImportError:
    HAS_CMD = False

try:
    from ginkgo.livecore.scheduler.heartbeat import HeartbeatChecker
    HAS_HB = True
except ImportError:
    HAS_HB = False

try:
    from ginkgo.livecore.scheduler.plan_manager import PlanManager
    HAS_PM = True
except ImportError:
    HAS_PM = False

try:
    from ginkgo.livecore.scheduler.publisher import SchedulePublisher
    HAS_PUB = True
except ImportError:
    HAS_PUB = False


@pytest.mark.skipif(not HAS_LB, reason="LoadBalancer not available")
class TestLoadBalancer:
    def test_instantiation(self):
        lb = LoadBalancer()
        assert lb is not None

    def test_instantiation_custom(self):
        lb = LoadBalancer(max_portfolios_per_node=10)
        assert lb is not None

    def test_assign_portfolios_empty(self):
        lb = LoadBalancer()
        plan = lb.assign_portfolios([], {}, [])
        assert isinstance(plan, dict)

    def test_assign_portfolios_basic(self):
        lb = LoadBalancer()
        nodes = [{"node_id": "node1", "metrics": {"portfolio_count": 0}}]
        plan = lb.assign_portfolios(nodes, {}, ["portfolio_A"])
        assert isinstance(plan, dict)
        assert "portfolio_A" in plan

    def test_get_plan_changes(self):
        old = {"p1": "n1", "p2": "n1"}
        new = {"p1": "n1", "p2": "n2", "p3": "n2"}
        changes = LoadBalancer.get_plan_changes(old, new)
        assert isinstance(changes, dict)


def _make_handler(**overrides):
    """Helper: 创建 CommandHandler 实例 (#3856)"""
    defaults = dict(
        scheduler_ref=MagicMock(),
        schedule_loop_callback=MagicMock(),
        get_healthy_nodes_callback=MagicMock(),
        get_current_plan_callback=MagicMock(return_value={}),
        get_all_portfolios_callback=MagicMock(return_value=[]),
        assign_portfolios_callback=MagicMock(),
        publish_update_callback=MagicMock(),
        send_command_callback=MagicMock(),
    )
    defaults.update(overrides)
    return CommandHandler(**defaults)


@pytest.mark.skipif(not HAS_CMD, reason="CommandHandler not available")
class TestCommandHandler:
    def test_instantiation(self):
        handler = _make_handler()
        assert handler is not None

    def test_process_unknown_command(self):
        handler = _make_handler()
        # Should not crash on unknown command
        handler.process_command({"type": "unknown_command", "params": {}})

    # --- #3856 check_commands() tests ---

    def test_check_commands_none_consumer_returns_immediately(self):
        """check_commands(None) 应立即返回，不抛异常"""
        handler = _make_handler()
        handler.check_commands(None)  # 不应抛异常

    def test_check_commands_empty_poll_does_not_process(self):
        """poll 返回空消息时不触发 process_command"""
        handler = _make_handler()
        mock_consumer = MagicMock()
        mock_consumer.consumer.poll.return_value = {}

        with patch.object(handler, 'process_command') as mock_process:
            handler.check_commands(mock_consumer)
            mock_process.assert_not_called()
            mock_consumer.consumer.poll.assert_called_once()

    def test_check_commands_dispatches_message_to_process_command(self):
        """收到消息时提取 value 并调用 process_command"""
        handler = _make_handler()
        mock_consumer = MagicMock()

        # Kafka poll 返回格式: {TopicPartition: [ConsumerRecord, ...]}
        mock_tp = MagicMock()
        mock_tp.topic = "scheduler.commands"
        mock_tp.partition = 0

        mock_record = MagicMock()
        mock_record.value = {"command": "pause", "timestamp": "2026-01-01", "params": {}}

        mock_consumer.consumer.poll.return_value = {mock_tp: [mock_record]}

        with patch.object(handler, 'process_command') as mock_process:
            handler.check_commands(mock_consumer)
            mock_process.assert_called_once_with({"command": "pause", "timestamp": "2026-01-01", "params": {}})

    def test_check_commands_handles_multiple_messages(self):
        """单次 poll 多条消息全部处理"""
        handler = _make_handler()
        mock_consumer = MagicMock()

        mock_tp = MagicMock()
        records = []
        for cmd in ["pause", "resume", "status"]:
            rec = MagicMock()
            rec.value = {"command": cmd, "params": {}}
            records.append(rec)

        mock_consumer.consumer.poll.return_value = {mock_tp: records}

        with patch.object(handler, 'process_command') as mock_process:
            handler.check_commands(mock_consumer)
            assert mock_process.call_count == 3

    def test_check_commands_poll_exception_does_not_raise(self):
        """poll 异常时应捕获并记录日志，不向调用方抛异常"""
        handler = _make_handler()
        mock_consumer = MagicMock()
        mock_consumer.consumer.poll.side_effect = Exception("Kafka error")

        # 不应抛异常
        handler.check_commands(mock_consumer)


@pytest.mark.skipif(not HAS_HB, reason="HeartbeatChecker not available")
class TestHeartbeatChecker:
    def test_instantiation(self):
        mock_redis = MagicMock()
        checker = HeartbeatChecker(mock_redis)
        assert checker is not None

    def test_get_healthy_nodes_empty(self):
        mock_redis = MagicMock()
        mock_redis.keys.return_value = []
        checker = HeartbeatChecker(mock_redis)
        nodes = checker.get_healthy_nodes()
        assert isinstance(nodes, list)


@pytest.mark.skipif(not HAS_PM, reason="PlanManager not available")
class TestPlanManager:
    def test_instantiation(self):
        mock_redis = MagicMock()
        pm = PlanManager(mock_redis)
        assert pm is not None

    def test_get_current_schedule_plan(self):
        mock_redis = MagicMock()
        mock_redis.hgetall.return_value = {}
        pm = PlanManager(mock_redis)
        plan = pm.get_current_schedule_plan()
        assert isinstance(plan, dict)

    def test_detect_orphaned_portfolios(self):
        mock_redis = MagicMock()
        pm = PlanManager(mock_redis)
        result = pm.detect_orphaned_portfolios([], {})
        assert isinstance(result, list)


@pytest.mark.skipif(not HAS_PUB, reason="SchedulePublisher not available")
class TestSchedulePublisher:
    def test_instantiation(self):
        mock_redis = MagicMock()
        mock_kafka = MagicMock()
        pub = SchedulePublisher(mock_redis, mock_kafka)
        assert pub is not None
