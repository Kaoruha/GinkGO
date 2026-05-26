"""Smoke tests for livecore.scheduler sub-components -- #3870"""
import pytest
from unittest.mock import MagicMock

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


@pytest.mark.skipif(not HAS_CMD, reason="CommandHandler not available")
class TestCommandHandler:
    def test_instantiation(self):
        handler = CommandHandler(
            scheduler_ref=MagicMock(),
            schedule_loop_callback=MagicMock(),
            get_healthy_nodes_callback=MagicMock(),
            get_current_plan_callback=MagicMock(return_value={}),
            get_all_portfolios_callback=MagicMock(return_value=[]),
            assign_portfolios_callback=MagicMock(),
            publish_update_callback=MagicMock(),
            send_command_callback=MagicMock(),
        )
        assert handler is not None

    def test_process_unknown_command(self):
        handler = CommandHandler(
            scheduler_ref=MagicMock(),
            schedule_loop_callback=MagicMock(),
            get_healthy_nodes_callback=MagicMock(),
            get_current_plan_callback=MagicMock(return_value={}),
            get_all_portfolios_callback=MagicMock(return_value=[]),
            assign_portfolios_callback=MagicMock(),
            publish_update_callback=MagicMock(),
            send_command_callback=MagicMock(),
        )
        # Should not crash on unknown command
        handler.process_command({"type": "unknown_command", "params": {}})


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
