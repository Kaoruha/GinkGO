# SegmentReport 测试用例
#
# 测试范围:
#   - 构造与基础属性 (空数据/无效频率/分析器过滤/缺失处理)
#   - 分段计算 (月/季/年分段数量与统计结构)
#   - to_dict() 按分段输出指标
#   - to_dataframe() 以分段为 index
#   - to_rich() Rich Table 输出


import pytest

import pandas as pd
import numpy as np

from rich.table import Table

from ginkgo.trading.analysis.metrics.base import DataProvider
from ginkgo.trading.analysis.reports.segment import SegmentReport


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
        with pytest.raises(ValueError, match="无任何可用"):
            SegmentReport(run_id="test", data=DataProvider())

    def test_invalid_freq_raises(self):
        dp = _make_dp(("net_value", _make_df([1.0, 2.0, 3.0])))
        with pytest.raises(ValueError, match="不支持的频率"):
            SegmentReport(run_id="test", data=dp, freq="W")

    def test_accepts_analyzers_filter(self):
        dp = _make_dp(
            ("net_value", _make_df(list(range(90)))),
            ("sharpe", _make_df([0.5] * 90)),
        )
        report = SegmentReport(run_id="test", data=dp, freq="M", analyzers=["net_value"])
        d = report.to_dict()
        for segment_metrics in d.values():
            assert "net_value" in segment_metrics
            assert "sharpe" not in segment_metrics

    def test_analyzers_none_processes_all(self):
        dp = _make_dp(
            ("net_value", _make_df(list(range(90)))),
            ("sharpe", _make_df([0.5] * 90)),
        )
        report = SegmentReport(run_id="test", data=dp, freq="M", analyzers=None)
        d = report.to_dict()
        for segment_metrics in d.values():
            assert "net_value" in segment_metrics
            assert "sharpe" in segment_metrics

    def test_missing_analyzer_skipped(self):
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M", analyzers=["nonexistent"])
        assert report.to_dict() == {}

    def test_no_timestamp_skipped(self):
        dp = DataProvider()
        dp.add("bad", pd.DataFrame({"value": [1.0, 2.0, 3.0]}))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        assert report.to_dict() == {}


# ============================================================
# Segment computation
# ============================================================

class TestSegmentComputation:
    def test_monthly_segment_count(self):
        """90 days from 2024-01-01 -> 3 monthly segments (Jan, Feb, Mar)."""
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        d = report.to_dict()
        assert len(d) == 3

    def test_quarterly_segment_count(self):
        """90 days -> 1 quarterly segment."""
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="Q")
        d = report.to_dict()
        assert len(d) == 1

    def test_yearly_segment_count(self):
        """400 days -> 2 yearly segments (2024, 2025)."""
        dp = _make_dp(("net_value", _make_df(list(range(400)))))
        report = SegmentReport(run_id="test", data=dp, freq="Y")
        d = report.to_dict()
        assert len(d) == 2

    def test_segment_stats_structure(self):
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        d = report.to_dict()
        first_key = list(d.keys())[0]
        stats = d[first_key]["net_value"]
        assert set(stats.keys()) == {"mean", "std", "min", "max", "final"}
        assert isinstance(stats["mean"], float)


# ============================================================
# to_dataframe
# ============================================================

class TestToDataFrame:
    def test_index_is_segment(self):
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        df = report.to_dataframe()
        assert df.index.name == "segment"
        assert not df.empty

    def test_columns_are_analyzer_stat(self):
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        df = report.to_dataframe()
        assert "net_value.mean" in df.columns
        assert "net_value.std" in df.columns
        assert "net_value.final" in df.columns


# ============================================================
# to_rich
# ============================================================

class TestToRich:
    def test_returns_rich_table(self):
        dp = _make_dp(("net_value", _make_df(list(range(90)))))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        table = report.to_rich()
        assert isinstance(table, Table)

    def test_empty_data_returns_table_with_message(self):
        dp = _make_dp(("net_value", _make_df([1.0])))
        report = SegmentReport(run_id="test", data=dp, freq="M")
        table = report.to_rich()
        assert isinstance(table, Table)
