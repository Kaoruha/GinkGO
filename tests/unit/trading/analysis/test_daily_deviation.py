import os
os.environ["GINKGO_SKIP_DEBUG_CHECK"] = "1"

import pandas as pd
import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


class TestExtractDailyCurves:
    def test_extracts_per_day_values_from_slices(self):
        from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
        evaluator = BacktestEvaluator()
        day_base = datetime(2026, 1, 1)
        slices = []
        for slice_idx in range(2):
            records = []
            for day_offset in range(3):
                day = day_base + timedelta(days=day_offset)
                records.append({"timestamp": day, "name": "net_value", "value": 1.0 + slice_idx * 0.1 + day_offset * 0.01})
                records.append({"timestamp": day, "name": "profit", "value": 0.0 + slice_idx * 0.05 + day_offset * 0.005})
            df = pd.DataFrame(records)
            slices.append({"analyzer_data": df, "signal_data": pd.DataFrame(), "order_data": pd.DataFrame()})
        result = evaluator._extract_daily_curves(slices)
        assert "net_value" in result
        assert len(result["net_value"]) == 3
        assert len(result["net_value"][1]) == 2
        assert result["net_value"][1][0] == pytest.approx(1.00)
        assert result["net_value"][1][1] == pytest.approx(1.10)

    def test_handles_empty_analyzer_data(self):
        from ginkgo.trading.analysis.evaluation.backtest_evaluator import BacktestEvaluator
        evaluator = BacktestEvaluator()
        slices = [{"analyzer_data": pd.DataFrame(), "signal_data": pd.DataFrame(), "order_data": pd.DataFrame()}]
        result = evaluator._extract_daily_curves(slices)
        assert result == {}


class TestCheckPointInTime:
    """check_point_in_time 单元测试"""

    def _make_detector(self, daily_curves=None):
        from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector

        baseline_stats = {
            "net_value": {"mean": 1.05, "std": 0.03, "values": [1.05, 1.08, 1.03]},
        }
        if daily_curves is None:
            daily_curves = {
                "net_value": {1: [1.00, 1.01, 0.99], 2: [1.02, 1.03, 1.00]},
            }

        detector = LiveDeviationDetector(
            baseline_stats=baseline_stats,
            slice_period_days=2,
        )
        detector._daily_curves = daily_curves
        return detector

    def test_normal_deviation(self):
        """正常范围内的值应返回 NORMAL"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"net_value": 1.00})
        assert result["status"] == "completed"
        assert result["overall_level"] == "NORMAL"

    def test_severe_deviation(self):
        """严重偏离应返回 SEVERE"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"net_value": 1.20})
        assert result["overall_level"] == "SEVERE"
        assert "net_value" in result["deviations"]

    def test_unknown_day_index_returns_no_data(self):
        """超出 daily_curves 范围的 day_index 应返回 no_data"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=99, current_metrics={"net_value": 1.00})
        assert result["status"] == "no_data"

    def test_unknown_metric_is_skipped(self):
        """baseline 中不存在的指标应被跳过，返回 no_data"""
        detector = self._make_detector()
        result = detector.check_point_in_time(day_index=1, current_metrics={"unknown_metric": 1.0})
        assert result["status"] == "no_data"

    def test_no_daily_curves_returns_no_data(self):
        """无 daily_curves 时应返回 no_data"""
        from ginkgo.trading.analysis.evaluation.live_deviation_detector import LiveDeviationDetector

        detector = LiveDeviationDetector(
            baseline_stats={"net_value": {"mean": 1.0, "std": 0.1, "values": [1.0]}},
            slice_period_days=30,
        )
        result = detector.check_point_in_time(day_index=1, current_metrics={"net_value": 1.0})
        assert result["status"] == "no_data"
