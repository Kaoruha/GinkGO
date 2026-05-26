"""Smoke test for ResultService -- #3823"""
import pytest
from unittest.mock import MagicMock, patch

try:
    from ginkgo.data.services.result_service import ResultService
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="ginkgo.data.services.result_service not importable")
class TestResultServiceSmoke:
    """冒烟测试：验证可实例化和公开方法可调用"""

    def _make_svc(self):
        mock_crud = MagicMock()
        return ResultService(analyzer_crud=mock_crud), mock_crud

    def test_instantiation(self):
        svc, _ = self._make_svc()
        assert svc is not None

    def test_get_run_summary_callable(self):
        svc, mock_crud = self._make_svc()
        mock_record = MagicMock(
            portfolio_id="p1", engine_id="e1", name="nav",
            timestamp="2025-01-01",
        )
        mock_crud.get_by_task_id.return_value = [mock_record]
        result = svc.get_run_summary(task_id="t1")
        assert result is not None

    def test_list_runs_callable(self):
        svc, mock_crud = self._make_svc()
        mock_crud.find.return_value = []
        result = svc.list_runs()
        assert result is not None

    def test_get_signals_callable(self):
        svc, mock_crud = self._make_svc()
        with patch("ginkgo.data.crud.signal_crud.SignalCRUD") as MockSignalCRUD:
            mock_signal_crud = MagicMock()
            mock_signal_crud.find.return_value = []
            mock_signal_crud.count.return_value = 0
            MockSignalCRUD.return_value = mock_signal_crud
            result = svc.get_signals(task_id="t1")
            assert result is not None

    def test_get_orders_callable(self):
        svc, mock_crud = self._make_svc()
        with patch("ginkgo.data.crud.order_record_crud.OrderRecordCRUD") as MockOrderCRUD:
            mock_order_crud = MagicMock()
            mock_order_crud.find.return_value = []
            mock_order_crud.count.return_value = 0
            MockOrderCRUD.return_value = mock_order_crud
            result = svc.get_orders(task_id="t1")
            assert result is not None
