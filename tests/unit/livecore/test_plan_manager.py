"""Tests for PlanManager -- #4661"""
import pytest
from unittest.mock import MagicMock, patch

from ginkgo.data.services.base_service import ServiceResult


@pytest.fixture()
def mock_services():
    """Create a mock services module."""
    svc = MagicMock()
    with patch("ginkgo.services", svc):
        yield svc


@pytest.mark.tdd
class TestGetAllPortfolios:
    """#4661: _get_all_portfolios must query PAPER + LIVE modes explicitly.

    The old code called portfolio_service.get(is_live=True), but `is_live`
    is a @property on MPortfolio (mode >= PAPER), not a queryable DB field.
    It falls into **kwargs and is silently dropped by kwargs.get('filters', {}),
    returning ALL portfolios including BACKTEST ones.

    Fix: query PAPER mode and LIVE mode separately, then merge.
    """

    def test_queries_paper_and_live_modes(self, mock_services):
        """Must call portfolio_service.get() once for PAPER and once for LIVE."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        paper_portfolio = MagicMock()
        paper_portfolio.mode = 1  # PAPER

        live_portfolio = MagicMock()
        live_portfolio.mode = 2  # LIVE

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.side_effect = [
            ServiceResult.success([paper_portfolio]),
            ServiceResult.success([live_portfolio]),
        ]
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        # Must have called get() twice — once for PAPER, once for LIVE
        assert mock_pf_svc.get.call_count == 2
        calls = mock_pf_svc.get.call_args_list

        from ginkgo.enums import PORTFOLIO_MODE_TYPES
        modes_called = []
        for call in calls:
            mode_arg = call.kwargs.get("mode")
            if mode_arg is not None:
                modes_called.append(mode_arg)

        # Both PAPER and LIVE modes must be queried
        assert PORTFOLIO_MODE_TYPES.PAPER in modes_called, \
            f"PAPER mode not queried. Modes called: {modes_called}"
        assert PORTFOLIO_MODE_TYPES.LIVE in modes_called, \
            f"LIVE mode not queried. Modes called: {modes_called}"

        # Result must contain both portfolios
        assert len(result) == 2

    def test_does_not_query_backtest_mode(self, mock_services):
        """Must NOT return BACKTEST portfolios."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.side_effect = [
            ServiceResult.success([]),  # PAPER: none
            ServiceResult.success([]),  # LIVE: none
        ]
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        assert result == []
        # Should not call with is_live=True (which is silently dropped)
        for call in mock_pf_svc.get.call_args_list:
            assert "is_live" not in call.kwargs, \
                "is_live should not be used — it's a @property, not a DB field"

    def test_returns_empty_on_service_error(self, mock_services):
        """Must return empty list when service fails."""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        mock_pf_svc = MagicMock()
        mock_pf_svc.get.return_value = ServiceResult.error("DB error")
        mock_services.data.portfolio_service.return_value = mock_pf_svc

        result = PlanManager._get_all_portfolios()

        assert result == []


@pytest.mark.tdd
class TestDetectUndeliveredPortfolios:
    """#4863: detect_undelivered_portfolios 找出 plan 已分配给健康节点、
    但节点未实际加载的 portfolio。

    detect_orphaned_portfolios 只处理「节点下线」（plan 中 node_id 不在
    healthy_nodes），漏掉了「健康节点漏加载」——Kafka schedule.updates 丢失、
    节点启动晚于消息、load_portfolio 失败等，都会让 plan 写了 pid→X 但
    节点 X 的 self.portfolios 不含 pid，且无 reconcile 机制 → plan/status
    永久漂移（scheduler plan 显示 5、execution status 显示 0）。

    输入契约：healthy_nodes[i] = {
        "node_id": str,
        "metrics": {"portfolio_count": int, "loaded_portfolio_ids": [str, ...]}
    }
    返回：[{"portfolio_id": str, "node_id": str}, ...] 供 scheduler 重发加载命令。
    """

    def test_plan_assigned_but_node_not_loaded_returns_undelivered(self):
        """plan 把 pid 分给健康节点 X，X 上报 loaded_portfolio_ids=[] → 返回该 pid。"""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        redis_client = MagicMock()
        pm = PlanManager(redis_client)

        healthy_nodes = [
            {"node_id": "nodeX", "metrics": {"portfolio_count": 0, "loaded_portfolio_ids": []}}
        ]
        current_plan = {"pid-1": "nodeX"}

        result = pm.detect_undelivered_portfolios(healthy_nodes, current_plan)

        assert result == [{"portfolio_id": "pid-1", "node_id": "nodeX"}]

    def test_node_already_loaded_returns_empty(self):
        """plan 把 pid 分给 X，X 已加载该 pid → 空列表（幂等重发不必要）。"""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        redis_client = MagicMock()
        pm = PlanManager(redis_client)

        healthy_nodes = [
            {"node_id": "nodeX", "metrics": {"portfolio_count": 1, "loaded_portfolio_ids": ["pid-1"]}}
        ]
        current_plan = {"pid-1": "nodeX"}

        result = pm.detect_undelivered_portfolios(healthy_nodes, current_plan)

        assert result == []

    def test_old_node_missing_loaded_field_skipped(self):
        """老节点未上报 loaded_portfolio_ids（字段缺失）→ 跳过，不误报其 plan 为漏加载。"""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        redis_client = MagicMock()
        pm = PlanManager(redis_client)

        healthy_nodes = [
            # 老节点：只有 portfolio_count，无 loaded_portfolio_ids
            {"node_id": "node-old", "metrics": {"portfolio_count": 1}}
        ]
        current_plan = {"pid-1": "node-old"}

        result = pm.detect_undelivered_portfolios(healthy_nodes, current_plan)

        assert result == []

    def test_node_not_healthy_left_to_orphaned(self):
        """pid 分给的节点不在 healthy_nodes（已下线）→ 不归 undelivered（detect_orphaned 负责）。"""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        redis_client = MagicMock()
        pm = PlanManager(redis_client)

        # nodeX 下线了，healthy 列表里是另一个节点
        healthy_nodes = [
            {"node_id": "nodeY", "metrics": {"portfolio_count": 0, "loaded_portfolio_ids": []}}
        ]
        current_plan = {"pid-1": "nodeX"}

        result = pm.detect_undelivered_portfolios(healthy_nodes, current_plan)

        assert result == []

    def test_mixed_loaded_and_undelivered(self):
        """X 加载了 pid-1 漏了 pid-2，Y 健康无 plan → 只报 pid-2。"""
        from ginkgo.livecore.scheduler.plan_manager import PlanManager

        redis_client = MagicMock()
        pm = PlanManager(redis_client)

        healthy_nodes = [
            {"node_id": "nodeX", "metrics": {"portfolio_count": 1, "loaded_portfolio_ids": ["pid-1"]}},
            {"node_id": "nodeY", "metrics": {"portfolio_count": 0, "loaded_portfolio_ids": []}},
        ]
        current_plan = {"pid-1": "nodeX", "pid-2": "nodeX"}

        result = pm.detect_undelivered_portfolios(healthy_nodes, current_plan)

        assert result == [{"portfolio_id": "pid-2", "node_id": "nodeX"}]
