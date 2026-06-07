"""Tests for evaluation/ directory GLOG uppercase -- PR review Issue 1"""
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from ginkgo.trading.analysis.evaluation.slice_data_manager import SliceDataManager
from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector
from ginkgo.trading.analysis.evaluation.slice_period_optimizer import SlicePeriodOptimizer


@pytest.mark.tdd
class TestSliceDataManagerGLOG:
    """GLOG calls in SliceDataManager must use uppercase methods."""

    def test_get_backtest_data_no_glog_crash(self):
        """get_backtest_data calls GLOG — must not raise AttributeError."""
        mgr = SliceDataManager()
        mock_services = MagicMock()
        mock_crud = MagicMock()
        mock_crud.get_by_task_id.return_value = pd.DataFrame()
        mock_crud.find.return_value = pd.DataFrame()
        mock_services.data.cruds.analyzer_record.return_value = mock_crud
        mock_services.data.cruds.signal.return_value = mock_crud
        mock_services.data.cruds.order_record.return_value = mock_crud

        with patch("ginkgo.services", mock_services):
            result = mgr.get_backtest_data(portfolio_id="test", engine_id="test")
        # Should return dict with DataFrames, NOT crash on GLOG
        assert isinstance(result, dict)

    def test_slice_data_by_period_no_glog_crash(self):
        """slice_data_by_period calls GLOG.info — must not crash."""
        mgr = SliceDataManager()
        data = {
            "analyzer_data": pd.DataFrame({"timestamp": [], "name": [], "value": []}),
            "signal_data": pd.DataFrame(),
            "order_data": pd.DataFrame(),
        }
        result = mgr.slice_data_by_period(data, period_days=30)
        # Should return empty list, NOT crash on GLOG
        assert isinstance(result, list)


@pytest.mark.tdd
class TestLiveDeviationDetectorGLOG:
    """GLOG calls in LiveDeviationDetector must use uppercase methods."""

    def test_accumulate_live_data_no_glog_crash(self):
        """accumulate_live_data calls GLOG — must not crash."""
        detector = LiveDeviationDetector(
            baseline_stats={"sharpe": {"mean": 1.0, "std": 0.2}},
            slice_period_days=30,
        )
        result = detector.accumulate_live_data(
            analyzer_records=[],
            signal_records=[],
            order_records=[],
        )
        # Should return False (empty data), NOT crash on GLOG
        assert isinstance(result, bool)


@pytest.mark.tdd
class TestSlicePeriodOptimizerGLOG:
    """GLOG calls in SlicePeriodOptimizer must use uppercase methods."""

    def test_find_optimal_slice_period_no_glog_crash(self):
        """find_optimal_slice_period calls GLOG — must not crash with AttributeError."""
        optimizer = SlicePeriodOptimizer()
        empty = pd.DataFrame({"timestamp": pd.Series(dtype="datetime64[ns]"), "name": pd.Series(dtype=str), "value": pd.Series(dtype=float)})
        # Empty data raises ValueError (no valid period found), NOT AttributeError from GLOG
        with pytest.raises(ValueError, match="切片周期"):
            optimizer.find_optimal_slice_period(
                analyzer_data=empty,
                signal_data=pd.DataFrame(),
                order_data=pd.DataFrame(),
            )
