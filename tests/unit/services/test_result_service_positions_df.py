"""#5964: record position 读路径修复——读写同源 PositionRecordCRUD。

根因: record_cli.position 调 PositionService.get_positions_df（查状态表
PositionCRUD），但回测引擎 t1backtest 通过 result_service.create_position_record
写流水表 PositionRecordCRUD。读写表不匹配 → record position 读空。

修复: result_service 新增 get_positions_df（DataFrame 出口，查 PositionRecordCRUD，
task_id 可选支持 portfolio-only），record_cli.position 改调它（读写同源）。
"""
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from ginkgo.data.services.result_service import ResultService


class TestGetPositionsDf:
    """#5964: get_positions_df 查 PositionRecordCRUD（流水表），返回 DataFrame。"""

    @pytest.mark.unit
    def test_returns_dataframe_from_position_record_crud(self):
        """查 PositionRecordCRUD（非 PositionCRUD 状态表），to_dataframe 转换。"""
        svc = ResultService(MagicMock())
        crud = MagicMock()
        df = pd.DataFrame([{"code": "000001.SZ", "volume": 100, "cost": 1000.0}])
        model_list = MagicMock()
        model_list.to_dataframe.return_value = df
        crud.find.return_value = model_list

        with patch("ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=crud):
            result = svc.get_positions_df(portfolio_id="p1")

        assert result.is_success()
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == 1
        crud.find.assert_called_once()

    @pytest.mark.unit
    def test_portfolio_only_filters_passed_to_crud(self):
        """portfolio-only 查询（无 task_id）仍查流水表，filters 含 portfolio_id。"""
        svc = ResultService(MagicMock())
        crud = MagicMock()
        crud.find.return_value = MagicMock(to_dataframe=MagicMock(return_value=pd.DataFrame()))

        with patch("ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=crud):
            svc.get_positions_df(portfolio_id="p1", engine_id="e1", task_id="t1")

        _, kwargs = crud.find.call_args
        assert kwargs["filters"]["portfolio_id"] == "p1"
        assert kwargs["filters"]["engine_id"] == "e1"
        assert kwargs["filters"]["task_id"] == "t1"

    @pytest.mark.unit
    def test_empty_result_returns_empty_dataframe(self):
        """crud 返空（None）→ 空 DataFrame，不抛异常。"""
        svc = ResultService(MagicMock())
        crud = MagicMock()
        crud.find.return_value = None

        with patch("ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=crud):
            result = svc.get_positions_df(portfolio_id="p1")

        assert result.is_success()
        assert isinstance(result.data, pd.DataFrame)
        assert result.data.empty
