import pytest
import pandas as pd
import numpy as np
from rich.table import Table

from ginkgo.trading.analysis.metrics.base import DataProvider
from ginkgo.trading.analysis.reports.rolling import RollingReport


# ============================================================
# Helpers
# ============================================================

def _make_df(values, start="2024-01-01"):
    dates = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"timestamp": dates, "value": values})


def _make_dp(*data_pairs):
    dp = DataProvider()
    for name, df in data_pairs:
        dp.add(name, df)
    return dp


# ============================================================
# Construction
# ============================================================

class TestConstruction:
    def test_empty_data_raises(self):
        with pytest.raises(ValueError, match="无任何可用数据"):
            RollingReport(run_id="test", data=DataProvider())

    def test_data_shorter_than_window(self):
        dp = _make_dp(("net_value", _make_df(list(range(10)))))
        report = RollingReport(run_id="test", data=dp, window=60)
        assert report.to_dict() == {}

    def test_accepts_analyzers_filter(self):
        dp = _make_dp(
            ("net_value", _make_df(list(range(120)))),
            ("sharpe", _make_df([0.5] * 120)),
        )
        report = RollingReport(run_id="test", data=dp, window=60, analyzers=["net_value"])
        d = report.to_dict()
        for date_metrics in d.values():
            assert "net_value" in date_metrics
            assert "sharpe" not in date_metrics

    def test_analyzers_none_processes_all(self):
        dp = _make_dp(
            ("net_value", _make_df(list(range(120)))),
            ("sharpe", _make_df([0.5] * 120)),
        )
        report = RollingReport(run_id="test", data=dp, window=60, analyzers=None)
        d = report.to_dict()
        for date_metrics in d.values():
            assert "net_value" in date_metrics
            assert "sharpe" in date_metrics

    def test_missing_analyzer_skipped(self):
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60, analyzers=["nonexistent"])
        assert report.to_dict() == {}

    def test_no_timestamp_skipped(self):
        dp = DataProvider()
        dp.add("bad", pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
        report = RollingReport(run_id="test", data=dp, window=2)
        assert report.to_dict() == {}


# ============================================================
# Window computation
# ============================================================

class TestWindowComputation:
    def test_sliding_window_count(self):
        """120 data points, window=60, step=1 -> 61 windows."""
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60, step=1)
        d = report.to_dict()
        assert len(d) == 61

    def test_tumbling_window_count(self):
        """120 data points, window=60, step=60 -> 2 windows."""
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60, step=60)
        d = report.to_dict()
        assert len(d) == 2

    def test_window_stats_structure(self):
        dp = _make_dp(("net_value", _make_df(list(range(100)))))
        report = RollingReport(run_id="test", data=dp, window=10)
        d = report.to_dict()
        first_key = list(d.keys())[0]
        stats = d[first_key]["net_value"]
        assert set(stats.keys()) == {"mean", "std", "min", "max", "final"}
        assert isinstance(stats["mean"], float)

    def test_window_values_correct(self):
        """First window of [0,1,...,9] should have final=9, min=0, max=9."""
        dp = _make_dp(("net_value", _make_df(list(range(100)))))
        report = RollingReport(run_id="test", data=dp, window=10, step=1)
        d = report.to_dict()
        first_key = list(d.keys())[0]
        stats = d[first_key]["net_value"]
        assert stats["min"] == 0.0
        assert stats["max"] == 9.0
        assert stats["final"] == 9.0


# ============================================================
# to_dataframe
# ============================================================

class TestToDataFrame:
    def test_index_is_window_start(self):
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60)
        df = report.to_dataframe()
        assert df.index.name == "window_start"
        assert not df.empty

    def test_columns_are_analyzer_stat(self):
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60)
        df = report.to_dataframe()
        assert "net_value.mean" in df.columns
        assert "net_value.std" in df.columns
        assert "net_value.final" in df.columns


# ============================================================
# to_rich
# ============================================================

class TestToRich:
    def test_returns_rich_table(self):
        dp = _make_dp(("net_value", _make_df(list(range(120)))))
        report = RollingReport(run_id="test", data=dp, window=60)
        table = report.to_rich()
        assert isinstance(table, Table)

    def test_empty_data_returns_table_with_message(self):
        dp = _make_dp(("net_value", _make_df(list(range(10)))))
        report = RollingReport(run_id="test", data=dp, window=60)
        table = report.to_rich()
        assert isinstance(table, Table)
