"""Tests for SliceDataManager.get_backtest_data -- #6174 / ADR-016 task_id 边界。

回测记录主查询键为 task_id（≡ 回测 uuid）。get_backtest_data 不得用 engine_id
当 task_id 喂 get_by_task_id，也不得以 engine_id 作为 signal/order 的查询条件。
crud mock 按 task_id 键敏感：实现若用错键（空 engine_id / engine_id 列）即返回空，
断言失败——从而把 #6174 的"空 engine_id 查不到数据"固化成回归守卫。
"""
import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

try:
    from ginkgo.trading.analysis.evaluation.slice_data_manager import SliceDataManager
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="SliceDataManager not available")
@pytest.mark.tdd
class TestGetBacktestDataTaskId:
    """ADR-016: get_backtest_data 按 task_id 查回测记录。"""

    @staticmethod
    def _mock_services_keyed_on(expected_task_id):
        """crud mock：仅当查询键 == expected_task_id 时返回数据，否则空（捕获键错配）。"""
        analyzer_df = pd.DataFrame([
            {"timestamp": "2025-01-%02d" % i, "name": "sharpe_ratio", "value": 1.0 + i * 0.1}
            for i in range(1, 13)
        ])
        signal_df = pd.DataFrame([
            {"timestamp": "2025-01-%02d" % i, "code": "000001"} for i in range(1, 6)
        ])
        order_df = pd.DataFrame([
            {"timestamp": "2025-01-%02d" % i, "volume": 100} for i in range(1, 4)
        ])

        # 形参名必须叫 task_id，以接住 impl 的 task_id= 关键字实参
        def _analyzer(task_id=None, **kw):
            return analyzer_df if task_id == expected_task_id else pd.DataFrame()

        def _find(df):
            def _impl(filters=None, **kw):
                return df if (filters and filters.get("task_id") == expected_task_id) else pd.DataFrame()
            return _impl

        mock = MagicMock()
        mock.data.cruds.analyzer_record.return_value.get_by_task_id.side_effect = _analyzer
        mock.data.cruds.signal.return_value.find.side_effect = _find(signal_df)
        mock.data.cruds.order_record.return_value.find.side_effect = _find(order_df)
        return mock

    def test_get_backtest_data_returns_records_by_task_id(self):
        """task_id=T 有记录 → 返回非空 analyzer/signal/order。"""
        T = "8b7b8cd8d69444db9a59e01862e601d6"
        P = "bcc34af44a074a95a9e56345d33b6d93"
        mgr = SliceDataManager()
        with patch("ginkgo.services", new=self._mock_services_keyed_on(T)):
            result = mgr.get_backtest_data(portfolio_id=P, task_id=T)

        assert len(result["analyzer_data"]) == 12
        assert len(result["signal_data"]) == 5
        assert len(result["order_data"]) == 3

    def test_get_backtest_data_empty_when_no_records_under_task_id(self):
        """task_id 查不到记录 → 三类全空。"""
        T = "nonexistent_task_id"
        P = "some_portfolio"
        mgr = SliceDataManager()
        # mock 仅对 TASK_X 返回数据；传 T 永远空
        mock = MagicMock()
        mock.data.cruds.analyzer_record.return_value.get_by_task_id.return_value = pd.DataFrame()
        mock.data.cruds.signal.return_value.find.return_value = pd.DataFrame()
        mock.data.cruds.order_record.return_value.find.return_value = pd.DataFrame()
        with patch("ginkgo.services", new=mock):
            result = mgr.get_backtest_data(portfolio_id=P, task_id=T)

        assert result["analyzer_data"].empty
        assert result["signal_data"].empty
        assert result["order_data"].empty
