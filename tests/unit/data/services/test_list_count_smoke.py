"""#5009 list 分页 count_X 出口 smoke（#6685 diff coverage gate 采集）。

count_signals/count_orders/count_records/count_positions 是本 PR 新增可执行行，
被 containers import 链触达（class 定义行 executed → 非 exempt）但 smoke 不调其
方法体 → 函数体内 crud.count 调用行 0 覆盖 → 门禁红。本文件用 mock 依赖（不连 DB）
补足该信号，纳入 smoke 子集供门禁测量。

get_positions_df(page=) 的 ClickHouse 分页行同理需补覆盖（PositionRecordCRUD
为方法内 inline 实例化，patch 类构造返回 mock）。
"""

import os
import sys
import pytest
from unittest.mock import patch, MagicMock

_path = os.path.join(os.path.dirname(__file__), "..", "..", "..")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.data.services.signal_service import SignalService
from ginkgo.data.services.order_service import OrderService
from ginkgo.data.services.analyzer_service import AnalyzerService
from ginkgo.data.services.result_service import ResultService


@pytest.fixture
def signal_service():
    with patch("ginkgo.libs.GLOG"):
        return SignalService(crud_repo=MagicMock())


@pytest.fixture
def order_service():
    with patch("ginkgo.libs.GLOG"):
        return OrderService(crud_repo=MagicMock())


@pytest.fixture
def analyzer_service():
    with patch("ginkgo.libs.GLOG"):
        return AnalyzerService(analyzer_crud=MagicMock())


@pytest.fixture
def result_service():
    with patch("ginkgo.libs.GLOG"):
        return ResultService(analyzer_crud=MagicMock())


class TestCountMethodsPassthrough:
    """count_X → crud.count(filters=)，供 CLI metadata.total 真实总数（#5009）。"""

    @pytest.mark.unit
    def test_signal_count_signals_calls_crud_count(self, signal_service):
        signal_service._crud_repo.count.return_value = 42
        result = signal_service.count_signals(engine_id="e1", portfolio_id="p1", task_id="t1")
        assert result.success is True
        assert result.data == {"count": 42}
        signal_service._crud_repo.count.assert_called_once()
        assert "engine_id" in signal_service._crud_repo.count.call_args[1]["filters"]

    @pytest.mark.unit
    def test_order_count_orders_calls_crud_count(self, order_service):
        order_service._crud_repo.count.return_value = 7
        result = order_service.count_orders(portfolio_id="p1", engine_id="e1", task_id="t1")
        assert result.success is True
        assert result.data == {"count": 7}
        order_service._crud_repo.count.assert_called_once()
        assert "portfolio_id" in order_service._crud_repo.count.call_args[1]["filters"]

    @pytest.mark.unit
    def test_analyzer_count_records_calls_crud_count(self, analyzer_service):
        analyzer_service._crud_repo.count.return_value = 3
        result = analyzer_service.count_records(portfolio_id="p1", engine_id="e1")
        assert result.success is True
        assert result.data == {"count": 3}
        analyzer_service._crud_repo.count.assert_called_once()
        assert "portfolio_id" in analyzer_service._crud_repo.count.call_args[1]["filters"]

    @pytest.mark.unit
    def test_result_count_positions_calls_position_record_count(self, result_service):
        """count_positions inline 实例化 PositionRecordCRUD → patch 类构造。"""
        mock_crud = MagicMock()
        mock_crud.count.return_value = 11
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=mock_crud
        ):
            result = result_service.count_positions(portfolio_id="p1", engine_id="e1", task_id="t1")
        assert result.success is True
        assert result.data == {"count": 11}
        mock_crud.count.assert_called_once()
        assert "is_del" in mock_crud.count.call_args[1]["filters"]

    @pytest.mark.unit
    def test_result_get_positions_df_passes_page_to_find(self, result_service):
        """get_positions_df(page=, page_size=) → PositionRecordCRUD.find(page=, page_size=, order_by=timestamp)。"""
        mock_crud = MagicMock()
        mock_crud.find.return_value = MagicMock()
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=mock_crud
        ):
            result = result_service.get_positions_df(portfolio_id="p1", page=2, page_size=10)
        assert result.success is True
        _, kwargs = mock_crud.find.call_args
        assert kwargs["page"] == 2
        assert kwargs["page_size"] == 10
        assert kwargs["order_by"] == "timestamp"
        assert kwargs["desc_order"] is True


class TestCountMethodsErrorPath:
    """count_X 的 except 分支：crud.count 抛异常 → ServiceResult.error（不传播异常）。"""

    @pytest.mark.unit
    def test_signal_count_signals_handles_crud_error(self, signal_service):
        signal_service._crud_repo.count.side_effect = RuntimeError("db down")
        result = signal_service.count_signals()
        assert result.success is False

    @pytest.mark.unit
    def test_order_count_orders_handles_crud_error(self, order_service):
        order_service._crud_repo.count.side_effect = RuntimeError("db down")
        result = order_service.count_orders()
        assert result.success is False

    @pytest.mark.unit
    def test_analyzer_count_records_handles_crud_error(self, analyzer_service):
        analyzer_service._crud_repo.count.side_effect = RuntimeError("db down")
        result = analyzer_service.count_records()
        assert result.success is False

    @pytest.mark.unit
    def test_result_count_positions_handles_crud_error(self, result_service):
        mock_crud = MagicMock()
        mock_crud.count.side_effect = RuntimeError("ch down")
        with patch(
            "ginkgo.data.crud.position_record_crud.PositionRecordCRUD", return_value=mock_crud
        ):
            result = result_service.count_positions()
        assert result.success is False

