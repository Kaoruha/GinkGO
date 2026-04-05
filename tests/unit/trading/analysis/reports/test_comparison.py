# ComparisonReport 测试用例
#
# 测试范围:
#   - 构造与基础属性
#   - to_dict() 多 run 并排对比
#   - to_dataframe() 以 run_id 为列、指标名为 index
#   - to_rich() Rich Table 多列输出
#   - 空报告列表处理


import pytest

import pandas as pd
from rich.table import Table

from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.reports.base import AnalysisReport
from ginkgo.trading.analysis.reports.comparison import ComparisonReport


# ============================================================
# Helpers
# ============================================================

def _make_df(values, start="2024-01-01"):
    dates = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"timestamp": dates, "value": values})


def _make_report(run_id, *data_pairs):
    dp = DataProvider()
    for name, df in data_pairs:
        if df is not None:
            dp.add(name, df)
    return AnalysisReport(run_id=run_id, registry=MetricRegistry(), data=dp)


# ============================================================
# Construction
# ============================================================

class TestConstruction:
    def test_accepts_list_of_reports(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        r2 = _make_report("run-b", ("net_value", _make_df([1.1, 2.1, 3.1])))
        report = ComparisonReport([r1, r2])
        assert len(report.reports) == 2

    def test_empty_reports_list(self):
        report = ComparisonReport([])
        assert report.to_dict() == {}
        assert report.to_dataframe().empty


# ============================================================
# to_dict
# ============================================================

class TestToDict:
    def test_run_ids_as_keys(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        r2 = _make_report("run-b", ("net_value", _make_df([1.1, 2.1, 3.1])))
        report = ComparisonReport([r1, r2])
        d = report.to_dict()
        assert "run-a" in d
        assert "run-b" in d
        assert "run_id" not in d.get("run-a", {})
        assert "run_id" not in d.get("run-b", {})

    def test_contains_analyzer_summary(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        report = ComparisonReport([r1])
        d = report.to_dict()
        assert "analyzer_summary" in d["run-a"]


# ============================================================
# to_dataframe
# ============================================================

class TestToDataFrame:
    def test_non_empty_dataframe(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        r2 = _make_report("run-b", ("net_value", _make_df([1.1, 2.1, 3.1])))
        report = ComparisonReport([r1, r2])
        df = report.to_dataframe()
        assert not df.empty

    def test_has_run_id_columns(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        r2 = _make_report("run-b", ("net_value", _make_df([1.1, 2.1, 3.1])))
        report = ComparisonReport([r1, r2])
        df = report.to_dataframe()
        assert "run-a" in df.columns
        assert "run-b" in df.columns


# ============================================================
# to_rich
# ============================================================

class TestToRich:
    def test_returns_rich_table(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        report = ComparisonReport([r1])
        table = report.to_rich()
        assert isinstance(table, Table)

    def test_table_has_run_id_columns(self):
        r1 = _make_report("run-a", ("net_value", _make_df([1.0, 2.0, 3.0])))
        r2 = _make_report("run-b", ("net_value", _make_df([1.1, 2.1, 3.1])))
        report = ComparisonReport([r1, r2])
        table = report.to_rich()
        # Table should have Metric + run_id columns
        assert len(table.columns) == 3  # Metric, run-a, run-b
