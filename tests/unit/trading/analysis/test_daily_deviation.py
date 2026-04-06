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
