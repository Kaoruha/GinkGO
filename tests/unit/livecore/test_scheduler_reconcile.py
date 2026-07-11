"""Tests for Scheduler._schedule_loop reconcile -- #4863"""
import pytest
from unittest.mock import MagicMock, patch


def _make_scheduler_with_mocks():
    """构造 Scheduler（patch 掉 GinkgoConsumer 网络依赖），替换 4 个子模块为 mock。"""
    with patch("ginkgo.data.drivers.ginkgo_kafka.GinkgoConsumer", MagicMock):
        from ginkgo.livecore.scheduler.scheduler import Scheduler
        sched = Scheduler(redis_client=MagicMock(), kafka_producer=MagicMock())
    sched._heartbeat_checker = MagicMock()
    sched._plan_manager = MagicMock()
    sched._load_balancer = MagicMock()
    sched._publisher = MagicMock()
    return sched


def _stub_no_changes(sched, current_plan, healthy_nodes):
    """让 plan_manager/load_balancer 不引入任何 plan 变化（隔离 reconcile 行为）。"""
    sched._heartbeat_checker.get_healthy_nodes.return_value = healthy_nodes
    sched._plan_manager.get_current_schedule_plan.return_value = dict(current_plan)
    sched._plan_manager.discover_new_portfolios.return_value = []
    sched._plan_manager.detect_deleted_portfolios.return_value = []
    sched._plan_manager.detect_orphaned_portfolios.return_value = []
    # assign 原样返回 plan → 不触发 publish_schedule_update
    sched._load_balancer.assign_portfolios.return_value = dict(current_plan)
    sched._load_balancer.get_plan_changes.return_value = {}


@pytest.mark.tdd
class TestScheduleLoopReconcilesUndelivered:
    """#4863: _schedule_loop 检测到「plan 已分配但健康节点漏加载」的 portfolio 时，
    通过 _send_schedule_command 重发加载命令（复用 migrate 接收端 →
    _receive_portfolio → load_portfolio 幂等），且不修改 plan（重发≠重新分配）。
    """

    def test_undelivered_triggers_send_schedule_command(self):
        sched = _make_scheduler_with_mocks()
        plan = {"pid-1": "nodeX"}
        healthy = [
            {"node_id": "nodeX", "metrics": {"portfolio_count": 0, "loaded_portfolio_ids": []}}
        ]
        _stub_no_changes(sched, plan, healthy)
        # detect_undelivered 报告 1 个漏加载
        sched._plan_manager.detect_undelivered_portfolios.return_value = [
            {"portfolio_id": "pid-1", "node_id": "nodeX"}
        ]

        sched._schedule_loop()

        # 重发了加载命令，to_node=原分配节点，from_node=None（非真实迁移）
        sched._publisher.send_schedule_command.assert_called()
        sent = [c.args[0] for c in sched._publisher.send_schedule_command.call_args_list]
        assert any(
            c["portfolio_id"] == "pid-1" and c["to_node"] == "nodeX" and c["from_node"] is None
            for c in sent
        ), f"expected resend for pid-1→nodeX, sent={sent}"
        # plan 未变 → 不发布计划更新
        sched._publisher.publish_schedule_update.assert_not_called()

    def test_no_undelivered_no_resend(self):
        sched = _make_scheduler_with_mocks()
        _stub_no_changes(sched, {}, [])
        sched._plan_manager.detect_undelivered_portfolios.return_value = []

        sched._schedule_loop()

        sched._publisher.send_schedule_command.assert_not_called()

    def test_reconcile_does_not_mutate_plan(self):
        """重发不改 plan：plan 仍含原分配，不触发 assign 重新分配。"""
        sched = _make_scheduler_with_mocks()
        plan = {"pid-1": "nodeX", "pid-2": "nodeX"}
        healthy = [
            {"node_id": "nodeX", "metrics": {"portfolio_count": 1, "loaded_portfolio_ids": ["pid-1"]}}
        ]
        _stub_no_changes(sched, plan, healthy)
        sched._plan_manager.detect_undelivered_portfolios.return_value = [
            {"portfolio_id": "pid-2", "node_id": "nodeX"}
        ]

        sched._schedule_loop()

        # assign 收到的 orphaned 不应含 pid-2（它是漏加载，不是孤儿）
        assign_kwargs = sched._load_balancer.assign_portfolios.call_args.kwargs
        assert "pid-2" not in (assign_kwargs.get("orphaned_portfolios") or [])
