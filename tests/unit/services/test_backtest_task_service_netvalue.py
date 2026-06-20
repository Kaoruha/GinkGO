"""#5848: get_netvalue 的 strategy 数组必须按时间正序（最早在前）。

根因: analyzer_record_crud.get_by_task_id 硬编码 desc_order=True，
get_netvalue 原序 append records，导致最新日期落在 strategy[0]，
前端按序绘制净值曲线时显示反向走势图。

修复在组装前 reverse records（不改共享 CRUD——backtest_result_aggregator
依赖 desc 顺序取最新累计值）。
"""
import datetime
from unittest.mock import MagicMock, patch

import pytest

from ginkgo.data.services.backtest_task_service import BacktestTaskService
from ginkgo.data.services.base_service import ServiceResult


def _rec(day: int, val: float):
    """模拟一条 analyzer record（含 business_timestamp + value）。"""
    r = MagicMock()
    ts = datetime.datetime(2025, 6, day)
    r.business_timestamp = ts
    r.timestamp = ts
    r.value = val
    return r


class TestGetNetvalueOrdering:
    """#5848: 净值 strategy 数组按时间正序排列。"""

    @pytest.mark.unit
    def test_strategy_oldest_first_newest_last(self):
        svc = BacktestTaskService(MagicMock())
        # 模拟 DB desc_order 返回：最新日期(6/30)在前，最早(6/2)在后
        records_desc = [_rec(30, 1.30), _rec(20, 1.20), _rec(2, 1.00)]

        result_svc = MagicMock()
        result_svc.get_analyzer_values.return_value = ServiceResult(
            success=True, data=records_desc
        )
        container = MagicMock()
        container.result_service.return_value = result_svc

        with patch.object(svc, "_resolve_task_id",
                          return_value=("task-1", "port-1", None)), \
             patch("ginkgo.data.containers.container", container):
            out = svc.get_netvalue("any-uuid")

        assert out.is_success()
        strategy = out.data.strategy
        assert len(strategy) == 3
        assert strategy[0].time.startswith("2025-06-02"), f"first={strategy[0].time}"
        assert strategy[-1].time.startswith("2025-06-30"), f"last={strategy[-1].time}"
