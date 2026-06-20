"""#5403: analyzers 端点返回空数组。

根因: list_analyzer_groups 调 find_by_portfolio(portfolio_id, task_id),
而 find_by_portfolio 无条件按 portfolio_id 过滤。_resolve_task_id 取得的
portfolio_id 可能是 ""(空), 导致 filter {"portfolio_id": ""} 匹配不到任何
analyzer 记录, 返回空。

按 ADR-012(task_id 是主查询键), 改走 task_id 主键路径:
list_analyzer_groups → analyzer_service.get_by_task_id(task_id, portfolio_id),
portfolio_id 仅在非空时作为可选过滤。CRUD 的 get_by_task_id 已满足此语义。
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


class TestListAnalyzerGroupsTaskIdPath:
    """#5403: list_analyzer_groups 按 task_id 主键查询, portfolio_id 空时仍返回记录。"""

    @pytest.mark.unit
    def test_uses_task_id_primary_query_when_portfolio_id_empty(self):
        svc = BacktestTaskService(MagicMock())

        records = [
            SimpleNamespace(name="Sharpe", value=-4.85),
            SimpleNamespace(name="MaxDrawdown", value=0.12),
        ]
        analyzer_svc = MagicMock()
        analyzer_svc.get_by_task_id.return_value = ServiceResult(
            success=True, data=records)

        container = MagicMock()
        container.analyzer_service.return_value = analyzer_svc

        # 模拟 _resolve_task_id 返回 portfolio_id="" (复现 bug 场景)
        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "", None)), \
             patch("ginkgo.data.containers.container", container):
            out = svc.list_analyzer_groups("any-uuid")

        assert out.is_success()
        groups = out.data
        # 两个分析器名 → 两个分组, 不再为空
        assert len(groups) == 2, f"expected 2 analyzer groups, got {len(groups)}"
        names = {g.name for g in groups}
        assert names == {"Sharpe", "MaxDrawdown"}

        # 走 task_id 主键路径
        analyzer_svc.get_by_task_id.assert_called_once()
        called_kwargs = analyzer_svc.get_by_task_id.call_args.kwargs
        assert called_kwargs.get("task_id") == "task-1"
        # 不再调用强制 portfolio_id 的 find_by_portfolio
        analyzer_svc.find_by_portfolio.assert_not_called()
