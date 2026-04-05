import pytest
from unittest.mock import MagicMock, patch
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ginkgo.trading.analysis.engine import AnalysisEngine
from ginkgo.trading.analysis.reports.single import SingleReport
from ginkgo.trading.analysis.reports.comparison import ComparisonReport
from ginkgo.trading.analysis.reports.segment import SegmentReport
from ginkgo.trading.analysis.reports.rolling import RollingReport
from ginkgo.trading.analysis.metrics.analyzer_metrics import RollingMean, RollingStd, CV, IC


# ============================================================
# Helpers
# ============================================================

def _make_mock_analyzer_service(records_by_name):
    """Create mock AnalyzerService that returns fake records grouped by name."""
    service = MagicMock()
    result = MagicMock()
    result.is_success.return_value = True

    records = []
    for name, values in records_by_name.items():
        for i, val in enumerate(values):
            obj = MagicMock()
            obj.name = name
            obj.__dict__ = {
                "name": name,
                "timestamp": f"2024-01-{(i % 28) + 1:02d} 00:00:00",
                "value": val,
            }
            records.append(obj)

    result.data = records
    service.get_by_run_id.return_value = result
    return service


def _make_mock_result_service():
    """Create mock ResultService with empty signal/order/position."""
    service = MagicMock()
    for method in ["get_signals", "get_orders", "get_positions"]:
        result = MagicMock()
        result.is_success.return_value = True
        result.data = {"data": []}
        getattr(service, method).return_value = result
    return service


def _make_engine(analyzer_data):
    """Create AnalysisEngine with mocked services."""
    analyzer_service = _make_mock_analyzer_service(analyzer_data)
    result_service = _make_mock_result_service()
    return AnalysisEngine(result_service, analyzer_service), analyzer_service


# ============================================================
# _load_analyzer_records
# ============================================================

class TestLoadAnalyzerRecords:
    def test_groups_records_by_name(self):
        engine, analyzer_service = _make_engine({
            "net_value": [1.0, 1.1, 1.2],
            "sharpe": [0.5, 0.6, 0.7],
        })
        result = engine._load_analyzer_records("test-run")
        assert set(result.keys()) == {"net_value", "sharpe"}
        assert len(result["net_value"]) == 3
        assert len(result["sharpe"]) == 3

    def test_returns_empty_dict_on_service_failure(self):
        engine, analyzer_service = _make_engine({})
        analyzer_service.get_by_run_id.return_value.is_success.return_value = False
        result = engine._load_analyzer_records("test-run")
        assert result == {}

    def test_returns_empty_dict_on_no_data(self):
        engine, analyzer_service = _make_engine({})
        analyzer_service.get_by_run_id.return_value.data = None
        result = engine._load_analyzer_records("test-run")
        assert result == {}

    def test_skips_records_without_name(self):
        # Records without 'name' attribute should be skipped
        service = MagicMock()
        result = MagicMock()
        result.is_success.return_value = True
        obj = MagicMock()
        del obj.name
        obj.__dict__ = {"timestamp": "2024-01-01", "value": 1.0}
        result.data = [obj]
        service.get_by_run_id.return_value = result

        result_service = _make_mock_result_service()
        engine = AnalysisEngine(result_service, service)
        loaded = engine._load_analyzer_records("test-run")
        assert loaded == {}

    def test_dataframes_have_timestamp_and_value_columns(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1]})
        result = engine._load_analyzer_records("test-run")
        df = result["net_value"]
        assert list(df.columns) == ["timestamp", "value"]
        assert df["value"].dtype == float


# ============================================================
# _auto_register_metrics
# ============================================================

class TestAutoRegisterMetrics:
    def test_registers_rolling_metrics_for_each_analyzer(self):
        engine, _ = _make_engine({"net_value": [1.0], "sharpe": [0.5]})
        engine._auto_register_metrics(["net_value", "sharpe"])

        # Should have RollingMean, RollingStd, CV for each analyzer = 6 total
        metrics = engine._registry.list_metrics()
        assert "rolling_mean.net_value" in metrics
        assert "rolling_std.net_value" in metrics
        assert "cv.net_value" in metrics
        assert "rolling_mean.sharpe" in metrics
        assert "rolling_std.sharpe" in metrics
        assert "cv.sharpe" in metrics

    def test_registers_ic_for_non_net_value_analyzers(self):
        engine, _ = _make_engine({"net_value": [1.0], "sharpe": [0.5]})
        engine._auto_register_metrics(["net_value", "sharpe"])

        metrics = engine._registry.list_metrics()
        assert "ic.sharpe" in metrics
        # net_value should NOT have IC
        assert "ic.net_value" not in metrics

    def test_creates_fresh_registry(self):
        engine, _ = _make_engine({"net_value": [1.0]})
        engine._auto_register_metrics(["net_value"])
        assert len(engine._registry.list_metrics()) == 3  # rm, rs, cv

        # Second call should reset
        engine._auto_register_metrics(["net_value", "sharpe"])
        assert len(engine._registry.list_metrics()) == 7  # rm*2 + rs*2 + cv*2 + ic*1


# ============================================================
# _load_data
# ============================================================

class TestLoadData:
    def test_raises_on_empty_analyzer_records(self):
        engine, analyzer_service = _make_engine({})
        analyzer_service.get_by_run_id.return_value.is_success.return_value = False
        with pytest.raises(ValueError, match="分析器记录"):
            engine._load_data("test-run")

    def test_returns_data_provider_with_analyzers(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2]})
        dp = engine._load_data("test-run")
        assert "net_value" in dp.available

    def test_includes_optional_signal_order_position(self):
        # When signal/order/position return data, they should be in DataProvider
        result_service = MagicMock()
        for method in ["get_signals", "get_orders", "get_positions"]:
            result = MagicMock()
            result.is_success.return_value = True
            # Return mock records with some data
            obj = MagicMock()
            obj.__dict__ = {"code": "000001.SZ"}
            result.data = {"data": [obj]}
            getattr(result_service, method).return_value = result

        analyzer_service = _make_mock_analyzer_service({"net_value": [1.0]})
        engine = AnalysisEngine(result_service, analyzer_service)
        dp = engine._load_data("test-run")
        assert "signal" in dp.available
        assert "order" in dp.available
        assert "position" in dp.available

    def test_skips_optional_data_on_failure(self):
        result_service = MagicMock()
        result_service.get_signals.side_effect = Exception("DB error")
        result_service.get_orders.return_value = MagicMock(is_success=False, data=None)
        result_service.get_positions.return_value = MagicMock(is_success=True, data={"data": []})

        analyzer_service = _make_mock_analyzer_service({"net_value": [1.0]})
        engine = AnalysisEngine(result_service, analyzer_service)
        dp = engine._load_data("test-run")
        assert "net_value" in dp.available
        # Optional data should be skipped, not crash


# ============================================================
# analyze
# ============================================================

class TestAnalyze:
    def test_returns_single_report(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2]})
        report = engine.analyze("test-run")
        assert isinstance(report, SingleReport)

    def test_report_has_analyzer_summary(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2]})
        report = engine.analyze("test-run")
        assert "net_value" in report.analyzer_summary
        assert "final" in report.analyzer_summary["net_value"]
        assert "mean" in report.analyzer_summary["net_value"]


# ============================================================
# compare
# ============================================================

class TestCompare:
    def test_returns_comparison_report(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2]})
        report = engine.compare(run_ids=["run1", "run2"])
        assert isinstance(report, ComparisonReport)


# ============================================================
# time_segments
# ============================================================

class TestTimeSegments:
    def test_returns_segment_report(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2]})
        report = engine.time_segments("test-run")
        assert isinstance(report, SegmentReport)

    def test_passes_analyzers_parameter(self):
        engine, _ = _make_engine({"net_value": [1.0, 1.1, 1.2], "sharpe": [0.5, 0.6]})
        report = engine.time_segments("test-run", analyzers=["net_value"])
        assert isinstance(report, SegmentReport)


# ============================================================
# rolling
# ============================================================

class TestRolling:
    def test_returns_rolling_report(self):
        engine, _ = _make_engine({"net_value": list(range(100))})
        report = engine.rolling("test-run")
        assert isinstance(report, RollingReport)

    def test_passes_window_and_step(self):
        engine, _ = _make_engine({"net_value": list(range(100))})
        report = engine.rolling("test-run", window=30, step=5)
        assert isinstance(report, RollingReport)
        assert report.window == 30
        assert report.step == 5
