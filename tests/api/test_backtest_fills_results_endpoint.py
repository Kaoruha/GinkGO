"""#5676: 新增 GET /{uuid}/fills 与 GET /{uuid}/results 端点。

/fills    → task_service.list_fills(uuid)（已成交订单填充）
/results  → task_service.get_results(uuid)（运行结果摘要）

修两子端点 404。直调路由函数, mock task_service（仿 #5842 order-records 端点测试）。
"""
import asyncio
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult


def _mock_item(order_id, status):
    m = MagicMock()
    m.dict.return_value = {"order_id": order_id, "status": status}
    return m


class TestFillsEndpoint:
    """#5676: /{uuid}/fills 端点返回已成交订单。"""

    @pytest.mark.unit
    def test_fills_calls_list_fills_and_returns_filled(self):
        from api.backtest import get_backtest_fills

        fills = [_mock_item("ord-A", 4), _mock_item("ord-B", 4)]
        sr = ServiceResult(success=True, data=fills)
        sr.set_metadata("total", 2)

        task_service = MagicMock()
        task_service.list_fills.return_value = sr

        with patch("api.backtest.get_backtest_task_service", return_value=task_service):
            resp = asyncio.run(get_backtest_fills("any-uuid"))

        # 路由调用 list_fills（非 list_orders）
        task_service.list_fills.assert_called_once_with("any-uuid")
        assert len(resp["data"]) == 2
        assert resp["meta"]["total"] == 2


class TestResultsEndpoint:
    """#5676: /{uuid}/results 端点返回运行结果摘要(dict, 非 list)。"""

    @pytest.mark.unit
    def test_results_calls_get_results_and_returns_summary(self):
        from api.backtest import get_backtest_results

        summary = {
            "task_id": "task-1", "engine_id": "eng-1",
            "portfolio_count": 1, "total_records": 10,
        }
        sr = ServiceResult(success=True, data=summary)

        task_service = MagicMock()
        task_service.get_results.return_value = sr

        with patch("api.backtest.get_backtest_task_service", return_value=task_service):
            resp = asyncio.run(get_backtest_results("any-uuid"))

        # 路由调用 get_results（透传 uuid）
        task_service.get_results.assert_called_once_with("any-uuid")
        # results 是摘要 dict, 用 ok() 包装 → data 直接是 summary（无 meta 分页）
        assert resp["data"] == summary
        assert "meta" not in resp, "results 是单个摘要, 不应带分页 meta"
