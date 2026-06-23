"""#5676: task_service 层 fills/results 双端点数据源。

list_fills  → result_service.get_orders(task_id) 后过滤 status==FILLED（已成交订单子集）
get_results → result_service.get_run_summary(task_id)（运行结果摘要）

修 /backtests/{uuid}/fills 与 /backtests/{uuid}/results 返回 404（端点未实现）。
"""
import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult
from ginkgo.enums import ORDERSTATUS_TYPES


def _rec(order_id: str, status: int, day: int):
    return SimpleNamespace(
        uuid=f"u-{order_id}-{status}", order_id=order_id,
        portfolio_id="port-1", engine_id="eng-1", task_id="task-1",
        code="000001.SZ", direction=1, order_type=1, status=status,
        volume=100, limit_price=10.0, transaction_price=10.0,
        transaction_volume=100, fee=5.0,
        timestamp=datetime.datetime(2025, 6, day, 9, 30),
    )


class TestListFillsFiltersFilled:
    """#5676: list_fills 只返回 status==FILLED 的订单（成交填充）。"""

    @pytest.mark.unit
    def test_list_fills_returns_only_filled_orders(self):
        """去重订单含 FILLED + CANCELED → list_fills 仅返 FILLED。

        RED: list_fills 方法不存在。
        """
        svc = BacktestTaskService(MagicMock())

        # 去重订单: 2 个 FILLED + 1 个 CANCELED(status=2)
        deduped = [
            _rec("ord-A", ORDERSTATUS_TYPES.FILLED.value, 3),
            _rec("ord-B", ORDERSTATUS_TYPES.FILLED.value, 4),
            _rec("ord-C", 2, 2),  # CANCELED，非成交
        ]
        result_svc = MagicMock()
        result_svc.get_orders.return_value = ServiceResult(
            success=True, data={"data": deduped, "total": 3})

        container = MagicMock()
        container.result_service.return_value = result_svc

        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            fills = svc.list_fills("any-uuid")

        assert fills.is_success()
        # 仅 2 个 FILLED（CANCELED 被过滤）
        assert len(fills.data) == 2, "list_fills 应只返回 FILLED 订单"
        assert fills.metadata.get("total") == 2
        # 走 get_orders 源（与 list_orders 同源，非另查）
        result_svc.get_orders.assert_called_once()


class TestGetResultsSummary:
    """#5676: get_results 透传 result_service.get_run_summary 的运行摘要。"""

    @pytest.mark.unit
    def test_get_results_returns_run_summary(self):
        """get_results(uuid) → _resolve_task_id → result_service.get_run_summary(task_id)。

        RED: get_results 方法不存在。
        """
        svc = BacktestTaskService(MagicMock())

        summary = {
            "task_id": "task-1", "engine_id": "eng-1",
            "portfolio_count": 1, "portfolios": ["port-1"],
            "analyzer_count": 1, "analyzers": ["SharpeRatio"],
            "total_records": 10,
            "time_range": {"start": "2025-06-01", "end": "2025-06-30"},
        }
        result_svc = MagicMock()
        result_svc.get_run_summary.return_value = ServiceResult(
            success=True, data=summary)

        container = MagicMock()
        container.result_service.return_value = result_svc

        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            res = svc.get_results("any-uuid")

        assert res.is_success()
        assert res.data == summary
        # 透传 task_id（非 uuid）
        result_svc.get_run_summary.assert_called_once_with("task-1")

