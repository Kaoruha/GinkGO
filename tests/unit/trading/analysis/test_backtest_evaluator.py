"""Tests for BacktestEvaluator -- #4666"""
import pytest

try:
    from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
    HAS_MODULE = True
except ImportError:
    HAS_MODULE = False


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestEvaluator not available")
class TestBacktestEvaluatorGLOG:
    """#4666: All GLOG calls must use uppercase methods (INFO/ERROR, not info/error).

    GinkgoLogger only exposes INFO(), ERROR(), etc. (uppercase).
    Lowercase calls raise AttributeError at runtime.
    """

    def test_create_live_monitor_does_not_crash_on_glog(self):
        """create_live_monitor calls GLOG twice -- must not raise AttributeError."""
        evaluator = BacktestEvaluator()
        baseline = {
            "baseline_stats": {"sharpe_ratio": {"mean": 1.5, "std": 0.2, "median": 1.4}},
            "slice_period_days": 30,
        }
        # Should not raise AttributeError from GLOG.info()
        monitor = evaluator.create_live_monitor(baseline)
        assert monitor is not None

    def test_evaluate_backtest_stability_invalid_data_no_glog_crash(self):
        """evaluate_backtest_stability must not crash on GLOG when data is invalid."""
        import pandas as pd
        from unittest.mock import patch

        evaluator = BacktestEvaluator()

        # Mock get_backtest_data to return empty data (triggers GLOG.error in validation)
        empty_data = {
            "analyzer_data": pd.DataFrame(columns=["timestamp", "name", "value"]),
            "signal_data": pd.DataFrame(),
            "order_data": pd.DataFrame(),
        }
        with patch.object(evaluator.data_manager, "get_backtest_data", return_value=empty_data):
            result = evaluator.evaluate_backtest_stability(portfolio_id="test", engine_id="test")

        # Should return a failed result, NOT raise AttributeError
        assert result["status"] == "failed"
