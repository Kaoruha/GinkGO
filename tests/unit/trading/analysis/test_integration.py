"""
性能: 272MB RSS, 2.59s, 11 tests [PASS]
"""

# Upstream: trading.analysis 完整模块 (metrics, reports)
# Downstream: None (集成测试)
# Role: 验证分析模块各组件的集成性 — 模块导出、端到端分析流程、比较报告

"""
分析模块集成测试

验证分析模块的整体集成性：
1. 模块导出 — __init__.py 中的所有公开符号可正确导入
2. 端到端 analyze → AnalysisReport → to_dict() → 结构验证
3. 端到端 compare → ComparisonReport → to_dict() 结构验证
4. RollingReport / SegmentReport 端到端验证
"""

import pytest
import pandas as pd
from datetime import datetime

from ginkgo.trading.analysis import (
    Metric, DataProvider, MetricRegistry,
    AnalysisReport, SingleReport, ComparisonReport,
    SegmentReport, RollingReport,
)
from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator
from ginkgo.trading.analysis.metrics.analyzer_metrics import RollingMean, RollingStd, CV, IC


# ============================================================
# Helpers
# ============================================================

def _make_df(values, start="2024-01-01"):
    dates = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"timestamp": dates, "value": values})


# ============================================================
# Module Exports (keep)
# ============================================================

class TestModuleExports:
    def test_metrics_base_exports(self):
        from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry
        assert callable(DataProvider)
        assert callable(MetricRegistry)

    def test_reports_exports(self):
        assert issubclass(SingleReport, AnalysisReport)
        assert callable(ComparisonReport)
        assert callable(SegmentReport)
        assert callable(RollingReport)

    def test_existing_analyzer_exports_unchanged(self):
        assert callable(BacktestResultAggregator)

    def test_new_metric_classes_exported(self):
        assert callable(RollingMean)
        assert callable(RollingStd)
        assert callable(CV)
        assert callable(IC)


# ============================================================
# End-to-End Analyze
# ============================================================

class TestEndToEndAnalyze:
    def test_analyze_with_single_analyzer(self):
        dp = DataProvider()
        dp.add("net_value", _make_df([1.0, 1.1, 1.2, 1.3, 1.4]))

        report = AnalysisReport(task_id="e2e-run", registry=MetricRegistry(), data=dp)

        assert report.task_id == "e2e-run"
        assert "net_value" in report.analyzer_summary
        assert report.analyzer_summary["net_value"]["final"] == 1.4

    def test_analyze_report_to_dict_structure(self):
        dp = DataProvider()
        dp.add("net_value", _make_df([1.0, 1.1, 1.2]))

        report = AnalysisReport(task_id="e2e-run", registry=MetricRegistry(), data=dp)
        d = report.to_dict()

        assert d["task_id"] == "e2e-run"
        assert "analyzer_summary" in d
        assert "stability_analysis" in d
        assert "ic_analysis" in d
        assert "time_series" in d

    def test_analyze_with_multiple_analyzers(self):
        dp = DataProvider()
        dp.add("net_value", _make_df([1.0, 1.1, 1.2, 1.3, 1.4, 1.5]))
        dp.add("sharpe", _make_df([0.5, 0.6, 0.7, 0.8, 0.9, 1.0]))

        report = AnalysisReport(task_id="e2e-run", registry=MetricRegistry(), data=dp)

        assert "net_value" in report.analyzer_summary
        assert "sharpe" in report.analyzer_summary


# ============================================================
# End-to-End Compare
# ============================================================

class TestEndToEndCompare:
    def test_compare_two_runs(self):
        dp1 = DataProvider()
        dp1.add("net_value", _make_df([1.0, 1.1, 1.2]))
        r1 = AnalysisReport(task_id="run-a", registry=MetricRegistry(), data=dp1)

        dp2 = DataProvider()
        dp2.add("net_value", _make_df([1.0, 0.9, 0.8]))
        r2 = AnalysisReport(task_id="run-b", registry=MetricRegistry(), data=dp2)

        comparison = ComparisonReport([r1, r2])
        d = comparison.to_dict()

        assert "run-a" in d
        assert "run-b" in d
        assert "analyzer_summary" in d["run-a"]

    def test_compare_to_dataframe(self):
        dp1 = DataProvider()
        dp1.add("net_value", _make_df([1.0, 1.1, 1.2]))
        r1 = AnalysisReport(task_id="run-a", registry=MetricRegistry(), data=dp1)

        dp2 = DataProvider()
        dp2.add("net_value", _make_df([1.0, 0.9, 0.8]))
        r2 = AnalysisReport(task_id="run-b", registry=MetricRegistry(), data=dp2)

        comparison = ComparisonReport([r1, r2])
        df = comparison.to_dataframe()
        assert not df.empty


# ============================================================
# End-to-End Rolling & Segment
# ============================================================

class TestEndToEndRolling:
    def test_rolling_report_e2e(self):
        dp = DataProvider()
        dp.add("net_value", _make_df(list(range(120))))

        report = RollingReport(task_id="e2e-run", data=dp, window=60, step=1)
        d = report.to_dict()

        assert len(d) > 0
        first_date = list(d.keys())[0]
        assert "net_value" in d[first_date]
        assert "mean" in d[first_date]["net_value"]


class TestEndToEndSegment:
    def test_segment_report_e2e(self):
        dp = DataProvider()
        dp.add("net_value", _make_df(list(range(90))))

        report = SegmentReport(task_id="e2e-run", data=dp, freq="M")
        d = report.to_dict()

        assert len(d) == 3  # Jan, Feb, Mar
        for segment, metrics in d.items():
            assert "net_value" in metrics
            assert "mean" in metrics["net_value"]
