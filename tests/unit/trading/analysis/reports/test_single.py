# AnalysisReport + SingleReport 测试用例
#
# 测试范围:
#   - AnalysisReport 构造与校验
#   - analyzer_summary 自动统计摘要
#   - summary 向后兼容别名
#   - MetricRegistry 指标计算 (stability + IC)
#   - signal / order / position 计数分析
#   - time_series 原始数据保留
#   - to_dict() / to_dataframe() / to_rich() 输出适配
#   - SingleReport 别名/元数据


import pytest

import pandas as pd
import numpy as np
from datetime import datetime, timedelta

from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry
from ginkgo.trading.analysis.metrics.analyzer_metrics import RollingMean, RollingStd, CV, IC
from ginkgo.trading.analysis.reports.base import AnalysisReport
from ginkgo.trading.analysis.reports.single import SingleReport


# ============================================================
# Helpers
# ============================================================

def _make_df(values, start="2024-01-01"):
    """Create a DataFrame with timestamp and value columns."""
    dates = pd.date_range(start, periods=len(values), freq="D")
    return pd.DataFrame({"timestamp": dates, "value": values})


def _make_report(*data_pairs, registry=None):
    """Create AnalysisReport with given data.

    data_pairs: tuples of (name, df_or_None)
    """
    dp = DataProvider()
    for name, df in data_pairs:
        if df is not None:
            dp.add(name, df)
    if registry is None:
        registry = MetricRegistry()
    return AnalysisReport(run_id="test-run", registry=registry, data=dp)


# ============================================================
# 1. Validation
# ============================================================

class TestValidation:
    """构造校验测试"""

    def test_empty_data_provider_raises(self):
        """无任何可用数据时应抛出 ValueError"""
        dp = DataProvider()
        with pytest.raises(ValueError, match="无任何可用数据"):
            AnalysisReport(run_id="test", registry=MetricRegistry(), data=dp)

    def test_no_value_column_skipped_gracefully(self):
        """不含 'value' 列的 DataFrame 在 analyzer_summary 中被跳过"""
        df = pd.DataFrame({
            "timestamp": pd.date_range("2024-01-01", periods=5),
            "other": [1, 2, 3, 4, 5],
        })
        report = _make_report(("test", df))
        assert "test" not in report.analyzer_summary


# ============================================================
# 2. analyzer_summary
# ============================================================

class TestAnalyzerSummary:
    """analyzer_summary 自动统计摘要测试"""

    def test_single_analyzer_stats(self):
        """单个含 value 列的 DataFrame 应产生完整的统计量"""
        df = _make_df([1.0, 2.0, 3.0, 4.0, 5.0])
        report = _make_report(("net_value", df))

        assert "net_value" in report.analyzer_summary
        stats = report.analyzer_summary["net_value"]
        assert stats["final"] == 5.0
        assert stats["mean"] == 3.0
        assert "std" in stats
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0

    def test_multiple_analyzers(self):
        """多个含 value 列的 DataFrame 应各自产生统计量"""
        report = _make_report(
            ("net_value", _make_df([1.0, 2.0, 3.0])),
            ("sharpe", _make_df([0.5, 0.6, 0.7])),
        )
        assert "net_value" in report.analyzer_summary
        assert "sharpe" in report.analyzer_summary

    def test_nan_values_handled(self):
        """NaN 值应被 dropna 后正确计算统计量"""
        df = _make_df([1.0, float("nan"), 3.0, float("nan"), 5.0])
        report = _make_report(("net_value", df))
        stats = report.analyzer_summary["net_value"]
        # dropna -> [1.0, 3.0, 5.0]
        assert stats["final"] == 5.0
        assert stats["mean"] == pytest.approx(3.0)

    def test_all_nan_no_entry(self):
        """全部为 NaN 的 DataFrame 不应产生 analyzer_summary 条目"""
        df = _make_df([float("nan"), float("nan")])
        report = _make_report(("empty_analyzer", df))
        assert "empty_analyzer" not in report.analyzer_summary


# ============================================================
# 3. Backward compatibility
# ============================================================

class TestBackwardCompatibility:
    """向后兼容性测试"""

    def test_summary_is_alias(self):
        """summary 应是 analyzer_summary 的别名"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        assert report.summary is report.analyzer_summary


# ============================================================
# 4. Metric computation (stability + IC)
# ============================================================

class TestMetricComputation:
    """指标计算测试 (stability_analysis + ic_analysis)"""

    def test_stability_metrics_computed(self):
        """stability 指标应正确计算并归入 stability_analysis"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="net_value", window=2))

        report = _make_report(
            ("net_value", _make_df([1.0, 2.0, 3.0, 4.0])),
            registry=registry,
        )
        assert "rolling_mean.net_value" in report.stability_analysis

    def test_ic_metrics_computed(self):
        """IC 指标应正确计算并归入 ic_analysis"""
        registry = MetricRegistry()
        registry.register_instance(IC(analyzer_name="sharpe", method="spearman", lag=1))

        report = _make_report(
            ("net_value", _make_df([1.0, 1.1, 1.2, 1.3, 1.4])),
            ("sharpe", _make_df([0.5, 0.6, 0.7, 0.8, 0.9])),
            registry=registry,
        )
        assert "ic.sharpe" in report.ic_analysis

    def test_failed_metric_goes_to_warning(self):
        """依赖不存在的数据的指标应被跳过"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="nonexistent", window=2))

        report = _make_report(
            ("net_value", _make_df([1.0, 2.0])),
            registry=registry,
        )
        assert "rolling_mean.nonexistent" not in report.stability_analysis

    def test_unavailable_metrics_tracked(self):
        """不可用指标应被记录在 _na_metrics 中"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="missing_data", window=2))

        report = _make_report(
            ("net_value", _make_df([1.0, 2.0])),
            registry=registry,
        )
        assert "rolling_mean.missing_data" in report._na_metrics


# ============================================================
# 5. Signal / Order / Position
# ============================================================

class TestSignalOrderPosition:
    """signal / order / position 计数分析测试"""

    def test_signal_count_included(self):
        """signal 数据应产生 signal_count"""
        signal_df = pd.DataFrame({"code": ["000001.SZ"] * 5})
        report = _make_report(
            ("net_value", _make_df([1.0, 2.0])),
            ("signal", signal_df),
        )
        assert report.signal_analysis["signal_count"] == 5

    def test_empty_signal_no_entry(self):
        """空的 signal DataFrame 不应产生条目"""
        signal_df = pd.DataFrame()
        report = _make_report(
            ("net_value", _make_df([1.0, 2.0])),
            ("signal", signal_df),
        )
        assert report.signal_analysis == {}

    def test_order_and_position_counts(self):
        """order 和 position 数据应产生对应计数"""
        order_df = pd.DataFrame({"code": ["000001.SZ"] * 3})
        position_df = pd.DataFrame({"code": ["000001.SZ"] * 2})
        report = _make_report(
            ("net_value", _make_df([1.0, 2.0])),
            ("order", order_df),
            ("position", position_df),
        )
        assert report.order_analysis["order_count"] == 3
        assert report.position_analysis["position_count"] == 2


# ============================================================
# 6. time_series
# ============================================================

class TestTimeSeries:
    """原始时间序列数据保留测试"""

    def test_raw_time_series_available(self):
        """time_series 应包含所有 DataProvider 中的 DataFrame"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        assert "net_value" in report.time_series


# ============================================================
# 7. Output adapters
# ============================================================

class TestToDict:
    """to_dict() 输出格式测试"""

    def test_contains_all_sections(self):
        """to_dict 应返回包含所有标准 section 的字典"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        d = report.to_dict()
        assert d["run_id"] == "test-run"
        assert "analyzer_summary" in d
        assert "stability_analysis" in d
        assert "ic_analysis" in d
        assert "signal_analysis" in d
        assert "order_analysis" in d
        assert "position_analysis" in d
        assert "metrics" in d
        assert "time_series" in d

    def test_analyzer_summary_serialized(self):
        """analyzer_summary 中的统计量应为 float 类型"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        d = report.to_dict()
        assert isinstance(d["analyzer_summary"]["net_value"]["final"], float)
        assert isinstance(d["analyzer_summary"]["net_value"]["mean"], float)


class TestToDataFrame:
    """to_dataframe() DataFrame 输出测试"""

    def test_has_section_column(self):
        """DataFrame 应包含 section 和 value 列"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        df_out = report.to_dataframe()
        assert "section" in df_out.columns
        assert "value" in df_out.columns

    def test_analyzer_summary_rows(self):
        """analyzer_summary 应产生 5 行 (final, mean, std, min, max)"""
        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        df_out = report.to_dataframe()
        analyzer_rows = df_out[df_out["section"] == "analyzer_summary"]
        assert len(analyzer_rows) == 5  # final, mean, std, min, max


class TestToRich:
    """to_rich() Rich Table 输出测试"""

    def test_returns_rich_table(self):
        """to_rich 应返回 rich.table.Table 实例"""
        from rich.table import Table

        df = _make_df([1.0, 2.0, 3.0])
        report = _make_report(("net_value", df))
        table = report.to_rich()
        assert isinstance(table, Table)


# ============================================================
# 8. SingleReport
# ============================================================

class TestSingleReport:
    """SingleReport 测试"""

    def test_single_report_is_analysis_report(self):
        """SingleReport 应是 AnalysisReport 的子类"""
        report = SingleReport(
            run_id="test_single",
            registry=MetricRegistry(),
            data=DataProvider(net_value=pd.DataFrame({"value": [100, 105]})),
        )
        assert isinstance(report, AnalysisReport)

    def test_single_report_to_dict_has_report_type(self):
        """SingleReport 的 to_dict 应包含 report_type"""
        report = SingleReport(
            run_id="single_001",
            registry=MetricRegistry(),
            data=DataProvider(net_value=pd.DataFrame({"value": [100, 105]})),
        )
        d = report.to_dict()
        assert d["run_id"] == "single_001"
        assert d["report_type"] == "single"

    def test_single_report_to_rich_title(self):
        """SingleReport 的 to_rich 标题应标注 [Single]"""
        report = SingleReport(
            run_id="single_001",
            registry=MetricRegistry(),
            data=DataProvider(net_value=pd.DataFrame({"value": [100, 105]})),
        )
        table = report.to_rich()
        assert "[Single]" in table.title
