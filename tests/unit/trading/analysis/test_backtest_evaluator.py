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
            result = evaluator.evaluate_backtest_stability(portfolio_id="test", task_id="test")

        # Should return a failed result, NOT raise AttributeError
        assert result["status"] == "failed"


@pytest.mark.skipif(not HAS_MODULE, reason="BacktestEvaluator not available")
@pytest.mark.tdd
class TestEvaluateBacktestStabilityTaskId:
    """ADR-016: evaluate_backtest_stability 形参 task_id，透传给 get_backtest_data。

    #6174 的核心混用点之一：调用方曾传 task.engine_id（可能空）→ 查不到记录。
    形参改为 task_id 后，由调用方负责提供 task_id（= 回测 uuid），下游按 task_id 查。
    """

    def test_threads_task_id_to_data_manager(self):
        """evaluate_backtest_stability(task_id=T) → get_backtest_data(task_id=T)。"""
        import pandas as pd
        from unittest.mock import patch, MagicMock

        evaluator = BacktestEvaluator()
        T = "8b7b8cd8d69444db9a59e01862e601d6"
        P = "bcc34af44a074a95a9e56345d33b6d93"

        empty_data = {
            "analyzer_data": pd.DataFrame(columns=["timestamp", "name", "value"]),
            "signal_data": pd.DataFrame(),
            "order_data": pd.DataFrame(),
        }
        mock_dm = MagicMock()
        mock_dm.get_backtest_data.return_value = empty_data
        evaluator.data_manager = mock_dm

        with patch.object(evaluator, "data_manager", mock_dm):
            evaluator.evaluate_backtest_stability(portfolio_id=P, task_id=T)

        # 断言：透传 task_id（非 engine_id）
        kwargs = mock_dm.get_backtest_data.call_args.kwargs
        assert "task_id" in kwargs, "应按 task_id 透传（ADR-016）"
        assert kwargs["task_id"] == T
        assert "engine_id" not in kwargs, "不应残留 engine_id 形参"
