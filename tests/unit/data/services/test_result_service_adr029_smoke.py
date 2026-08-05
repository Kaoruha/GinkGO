"""ResultService ADR-029 读路径 + 记录委托 smoke。

- ``get_analyzer_values_df``（L156：get_by_task_id → models_to_dataframe 出口）
- ``create_order_record``（L662-663：懒 import container 委托 OrderService）
被 containers import 链触达但 smoke 不调方法体 → diff coverage gate 红。本 smoke
补覆盖信号：get 路径 mock crud，委托路径 patch container。
"""
from unittest.mock import patch, MagicMock

import pandas as pd

from ginkgo.data.services.result_service import ResultService
from ginkgo.data.services.base_service import ServiceResult


class _FakeAnalyzerCrud:
    """get_by_task_id 返 truthy 列表，触发 models_to_dataframe 分支（L156）。"""

    def get_by_task_id(self, task_id=None, portfolio_id=None, analyzer_name=None, page_size=None):
        return [MagicMock()]


def test_get_analyzer_values_df_returns_dataframe():
    """get_by_task_id 返列表 → models_to_dataframe（L156）。patch models_to_dataframe
    返 DataFrame 以隔离 ORM 模型构造，专注覆盖 L156 出口分支。"""
    svc = ResultService(analyzer_crud=_FakeAnalyzerCrud())
    with patch(
        "ginkgo.data.services.result_service.models_to_dataframe",
        return_value=pd.DataFrame(),
    ):
        res = svc.get_analyzer_values_df(task_id="t")
    assert res.success
    assert isinstance(res.data, pd.DataFrame)


def test_create_order_record_delegates_to_container():
    """懒 import container → order_service().create_order_record(**kwargs)（L662-663）。"""
    fake_order_svc = MagicMock()
    fake_order_svc.create_order_record.return_value = ServiceResult.success()
    with patch("ginkgo.data.containers.container") as mock_container:
        mock_container.order_service.return_value = fake_order_svc
        svc = ResultService(analyzer_crud=_FakeAnalyzerCrud())
        res = svc.create_order_record(code="000001", portfolio_id="p")
    assert res.success
    fake_order_svc.create_order_record.assert_called_once_with(code="000001", portfolio_id="p")
