"""result_service.get_positions_df 单元测试。

#5341: record position 读错表。回测持仓经 create_position_record 写
MPositionRecord（流水表），但 record_cli 读 PositionCRUD（MPosition 当前态表）。
result_service 新增 get_positions_df 查 PositionRecordCRUD，对齐
position_service 出口签名（portfolio/engine/task 三过滤 + DataFrame）。
"""
import os

os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pandas as pd
import pytest
from unittest.mock import patch, MagicMock

from ginkgo.data.services.result_service import ResultService


@pytest.fixture
def service():
    # ResultService.__init__ 要求 analyzer_crud（Container 注入）；单测用 MagicMock
    return ResultService(analyzer_crud=MagicMock())


@pytest.fixture
def mock_record_crud():
    crud = MagicMock()
    model_list = MagicMock()
    model_list.to_dataframe.return_value = pd.DataFrame([{
        "uuid": "pr1",
        "portfolio_id": "p1",
        "engine_id": "e1",
        "task_id": "t1",
        "code": "000001.SZ",
        "volume": 100,
        "cost": 10.5,
        "price": 10.8,
        "fee": 5.0,
    }])
    crud.find.return_value = model_list
    return crud


@pytest.mark.unit
class TestResultServiceGetPositionsDf:
    """get_positions_df 必须查 PositionRecordCRUD（MPositionRecord 流水表）——
    回测只写该表，读 PositionCRUD（MPosition 当前态）永远空（#5341 根因）。"""

    def test_filters_by_portfolio_engine_task(self, service, mock_record_crud):
        """portfolio/engine/task 三过滤透传到 PositionRecordCRUD.find"""
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD",
            return_value=mock_record_crud,
        ):
            service.get_positions_df(
                portfolio_id="p1", engine_id="e1", task_id="t1"
            )
        mock_record_crud.find.assert_called_once()
        _, kwargs = mock_record_crud.find.call_args
        assert kwargs["filters"] == {
            "is_del": False,
            "portfolio_id": "p1",
            "engine_id": "e1",
            "task_id": "t1",
        }

    def test_returns_dataframe_with_records(self, service, mock_record_crud):
        """to_dataframe() 结果透传到 ServiceResult.data（pandas.DataFrame）"""
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD",
            return_value=mock_record_crud,
        ):
            result = service.get_positions_df(
                portfolio_id="p1", engine_id="e1", task_id="t1"
            )
        assert result.is_success()
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == 1
        # MPositionRecord 流水字段（非 MPosition 当前态）
        assert result.data.iloc[0]["code"] == "000001.SZ"
        assert result.data.iloc[0]["volume"] == 100
        assert result.data.iloc[0]["cost"] == 10.5

    def test_empty_returns_empty_dataframe(self, service, mock_record_crud):
        """find 返回空时 data 是空 DataFrame（非 None/非 list），CLI 下游 len() 安全"""
        mock_record_crud.find.return_value = None
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD",
            return_value=mock_record_crud,
        ):
            result = service.get_positions_df(
                portfolio_id="p1", engine_id="e1", task_id="t1"
            )
        assert result.is_success()
        assert isinstance(result.data, pd.DataFrame)
        assert len(result.data) == 0

    def test_omits_unset_filters(self, service, mock_record_crud):
        """未传的过滤维度不进 filters（避免 None 污染）"""
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD",
            return_value=mock_record_crud,
        ):
            service.get_positions_df(portfolio_id="p1")
        _, kwargs = mock_record_crud.find.call_args
        assert kwargs["filters"] == {"is_del": False, "portfolio_id": "p1"}
