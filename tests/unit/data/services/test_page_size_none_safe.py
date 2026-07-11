"""page_size None-safety 回归（#6652 review E1）。

CLI ``--page-size 0`` → 下推 ``page_size=None`` 给 service。旧守卫
``page_size if page_size > 0 else None`` 对 ``None`` 求值 ``None > 0`` 触发 TypeError，
被 ``except Exception`` 吞成"查询失败" exit 1（help 文档承诺的"0=全部"即崩）。

本测试直击守卫：调**真实 service 方法**（只 mock CRUD 层，不 mock 整个 service——
后者绕过守卫，正是 CLI smoke 测不出该 TypeError 的根因，见 review E1），断言
``page_size=None`` 不再崩溃、CRUD.find 收到 ``page_size=None``。

Run: pytest tests/unit/data/services/test_page_size_none_safe.py -v -o "addopts="
"""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.data.services.signal_service import SignalService
from ginkgo.data.services.order_service import OrderService
from ginkgo.data.services.analyzer_service import AnalyzerService
from ginkgo.data.services.result_service import ResultService


def _model_list():
    """CRUD.find 返回的 ModelList mock（带 to_dataframe，空 df 即可）。"""
    ml = MagicMock()
    ml.to_dataframe.return_value = pd.DataFrame()
    return ml


# (构造器, df 方法名)：signal/order 走 crud_repo 注入，analyzer 走 analyzer_crud 注入
# （三者 __init__ 都赋给 self._crud_repo，df 方法经 self._crud_repo.find）。
_INJECTABLE = [
    (lambda m: SignalService(crud_repo=m), "get_signals_df"),
    (lambda m: OrderService(crud_repo=m), "get_orders_df"),
    (lambda m: AnalyzerService(analyzer_crud=m), "get_records_df"),
]


@pytest.mark.unit
class TestPageSizeNoneSafe:
    """page_size=None 不再触发 TypeError（#6652 review E1）。"""

    @pytest.mark.parametrize("ctor, method", _INJECTABLE)
    def test_df_method_tolerates_none_page_size(self, ctor, method):
        """self._crud_repo 注入型：None 守卫短路 → CRUD.find 收到 page_size=None，无 TypeError。"""
        mock_crud = MagicMock()
        mock_crud.find.return_value = _model_list()
        svc = ctor(mock_crud)

        result = getattr(svc, method)(page_size=None)

        assert result.success is True  # 未进 except（旧代码 TypeError → ServiceResult.error）
        _, kwargs = mock_crud.find.call_args
        assert kwargs["page_size"] is None

    def test_result_get_positions_df_tolerates_none_page_size(self):
        """result_service.get_positions_df 内部自建 PositionRecordCRUD（不走 self._crud_repo），
        record position 命令走此路径；patch 该 CRUD 验证同一守卫。"""
        svc = ResultService(analyzer_crud=MagicMock())
        # PositionRecordCRUD 在方法内 function-local import，patch 源模块（非 result_service 命名空间）
        with patch("ginkgo.data.crud.position_record_crud.PositionRecordCRUD") as MockCrud:
            MockCrud.return_value.find.return_value = _model_list()
            result = svc.get_positions_df(page_size=None)

        assert result.success is True
        _, kwargs = MockCrud.return_value.find.call_args
        assert kwargs["page_size"] is None
