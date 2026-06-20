"""#5847: 分析器命名以指标名为准, 不接受类名。

GET /{uuid}/analyzer/{name} 对类名(如 SharpeAnalyzer)原静默返回空 data。
根因: get_analyzer_data 对无记录名返回 success(空 detail), 路由再包成
ok(data=[])——调用方无从区分"该指标本次无数据"与"名字写错了"。

决策(#5847): 指标名为准, 未知名(含类名)→404, message 列出可用指标名。
权威白名单取自该回测实际产出的指标名(list_analyzer_groups 的 group.name)。
"""
import asyncio
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.base_service import ServiceResult


def _groups_result(names):
    """模拟 list_analyzer_groups 的 ServiceResult, groups 带 .name。"""
    return ServiceResult(success=True, data=[SimpleNamespace(name=n) for n in names])


class TestAnalyzerNameAuthority:
    """#5847: 类名/未知名 → 404 且 message 列出可用指标名。"""

    @pytest.mark.unit
    def test_class_name_rejected_with_404_listing_available(self):
        from api.backtest import get_backtest_analyzer_data
        from core.exceptions import APIError

        task_service = MagicMock()
        task_service.list_analyzer_groups.return_value = _groups_result(
            ["sharpe_ratio", "max_drawdown"])

        with patch("api.backtest.get_backtest_task_service", return_value=task_service):
            with pytest.raises(APIError) as exc:
                asyncio.run(get_backtest_analyzer_data("uuid-1", "SharpeAnalyzer"))

        # 未知名 → 404
        assert exc.value.code == 404, "类名应被拒为 404, 不再静默返回空"
        assert exc.value.status_code == 404
        # message 列出可用指标名, 且点名被拒的名字
        assert "sharpe_ratio" in exc.value.message
        assert "SharpeAnalyzer" in exc.value.message
        # 白名单未命中即拒, 不应再下钻取数据
        task_service.get_analyzer_data.assert_not_called()

    @pytest.mark.unit
    def test_metric_name_returns_data(self):
        """#5847: 合法指标名穿过白名单, 正常返回时序数据(守卫不误伤)。"""
        from api.backtest import get_backtest_analyzer_data

        point = MagicMock()
        point.dict.return_value = {"time": "2025-01-01", "value": 1.5}
        detail = MagicMock()
        detail.data = [point]
        detail.stats = {"mean": 1.5}

        task_service = MagicMock()
        task_service.list_analyzer_groups.return_value = _groups_result(["sharpe_ratio"])
        task_service.get_analyzer_data.return_value = ServiceResult(
            success=True, data=detail)

        with patch("api.backtest.get_backtest_task_service", return_value=task_service):
            resp = asyncio.run(get_backtest_analyzer_data("uuid-1", "sharpe_ratio"))

        task_service.get_analyzer_data.assert_called_once_with("uuid-1", "sharpe_ratio")
        # ok() 把 {"data":..., "stats":...} 包进 resp["data"]
        assert resp["data"]["data"] == [{"time": "2025-01-01", "value": 1.5}]
        assert resp["data"]["stats"] == {"mean": 1.5}
