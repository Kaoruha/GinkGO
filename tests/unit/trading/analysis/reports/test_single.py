# AnalysisReport + SingleReport 测试用例
#
# 测试范围:
#   - AnalysisReport 构造与指标分类
#   - to_dict() 平铺字典输出
#   - to_dataframe() DataFrame 输出
#   - to_rich() Rich Table 输出
#   - 缺失指标 N/A 处理
#   - 自定义分析器数据分类
#   - SingleReport 别名/元数据


import pytest

import pandas as pd

from ginkgo.trading.analysis.reports.base import AnalysisReport
from ginkgo.trading.analysis.reports.single import SingleReport
from ginkgo.trading.analysis.metrics.base import MetricRegistry, DataProvider
from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown
from ginkgo.trading.analysis.metrics.signal import SignalCount
from ginkgo.trading.analysis.metrics.order import FillRate
from ginkgo.trading.analysis.metrics.position import MaxPositions


# ============================================================
# Fake Metrics (用于测试 N/A 和自定义分类)
# ============================================================

class FakeMetric:
    """依赖不存在数据的指标，应该返回 N/A"""
    name = "fake"
    requires = ["nonexistent"]
    params = {}

    def compute(self, data):
        return 42.0


class FakeCrossSourceMetric:
    """跨数据源指标，应该归入 summary"""
    name = "fake_cross_source"
    requires = ["signal", "order"]
    params = {}

    def compute(self, data):
        return 0.5


# ============================================================
# 1. 构造与基础功能
# ============================================================

class TestReportConstruction:
    """报告构造与基础属性测试"""

    def test_report_stores_run_id(self):
        """run_id 应被正确存储"""
        reg = MetricRegistry()
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="my_run_001", registry=reg, data=dp)
        assert report.run_id == "my_run_001"

    def test_empty_registry_produces_empty_report(self):
        """空注册中心应生成空报告"""
        reg = MetricRegistry()
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert d["summary"] == {}
        assert d["signal_analysis"] == {}
        assert d["order_analysis"] == {}
        assert d["position_analysis"] == {}

    def test_net_value_required(self):
        """net_value 不存在时应抛出 ValueError"""
        reg = MetricRegistry()
        dp = DataProvider()
        with pytest.raises(ValueError, match="net_value"):
            AnalysisReport(run_id="test", registry=reg, data=dp)


# ============================================================
# 2. to_dict() 输出
# ============================================================

class TestReportToDict:
    """to_dict() 输出格式测试"""

    def test_report_to_dict_structure(self):
        """to_dict 应返回包含标准 section 的字典"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        reg.register(MaxDrawdown)
        dp = DataProvider(
            net_value=pd.DataFrame({"value": [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]})
        )
        report = AnalysisReport(run_id="test_run", registry=reg, data=dp)
        d = report.to_dict()
        assert "run_id" in d
        assert "summary" in d
        assert "signal_analysis" in d
        assert "order_analysis" in d
        assert "position_analysis" in d
        assert "custom_metrics" in d
        assert isinstance(d["summary"], dict)

    def test_portfolio_metrics_in_summary(self):
        """requires=['net_value'] 的指标应归入 summary"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "annualized_return" in d["summary"]

    def test_missing_metric_n_a(self):
        """数据不可用的指标应显示 N/A"""
        reg = MetricRegistry()
        reg.register(FakeMetric)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert d["metrics"]["fake"] == "N/A"

    def test_custom_analyzer_data(self):
        """未消耗的 DataProvider key 应归入 custom_metrics"""
        reg = MetricRegistry()
        dp = DataProvider(
            net_value=pd.DataFrame({"value": [100, 105]}),
            my_custom=pd.DataFrame({"value": [1, 2]}),
        )
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "my_custom" in d["custom_metrics"]

    def test_cross_source_metric_in_summary(self):
        """跨数据源指标应归入 summary"""
        reg = MetricRegistry()
        reg.register(FakeCrossSourceMetric)
        dp = DataProvider(
            signal=pd.DataFrame({"code": ["000001.SZ"]}),
            order=pd.DataFrame({"code": ["000001.SZ"]}),
            net_value=pd.DataFrame({"value": [100, 105]}),
        )
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "fake_cross_source" in d["summary"]


# ============================================================
# 3. 指标分类测试
# ============================================================

class TestMetricCategorization:
    """指标按 requires 自动分类测试"""

    def test_signal_metrics_in_signal_analysis(self):
        """requires=['signal'] 应归入 signal_analysis"""
        reg = MetricRegistry()
        reg.register(SignalCount)
        dp = DataProvider(
            net_value=pd.DataFrame({"value": [100, 105]}),
            signal=pd.DataFrame({"code": ["000001.SZ", "000002.SZ"]}),
        )
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "signal_count" in d["signal_analysis"]

    def test_order_metrics_in_order_analysis(self):
        """requires=['order'] 应归入 order_analysis"""
        reg = MetricRegistry()
        reg.register(FillRate)
        dp = DataProvider(
            net_value=pd.DataFrame({"value": [100, 105]}),
            order=pd.DataFrame({"code": ["000001.SZ"], "status": [1]}),
        )
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "fill_rate" in d["order_analysis"]

    def test_position_metrics_in_position_analysis(self):
        """requires=['position'] 应归入 position_analysis"""
        reg = MetricRegistry()
        reg.register(MaxPositions)
        dp = DataProvider(
            net_value=pd.DataFrame({"value": [100, 105]}),
            position=pd.DataFrame({"code": ["000001.SZ"], "volume": [100]}),
        )
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        d = report.to_dict()
        assert "max_positions" in d["position_analysis"]


# ============================================================
# 4. to_dataframe() 输出
# ============================================================

class TestReportToDataFrame:
    """to_dataframe() DataFrame 输出测试"""

    def test_report_to_dataframe_type(self):
        """to_dataframe 应返回 DataFrame"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        df = report.to_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_report_to_dataframe_has_index(self):
        """DataFrame 的 index 应包含指标名"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        reg.register(MaxDrawdown)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 102, 101, 103]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        df = report.to_dataframe()
        assert "annualized_return" in df.index


# ============================================================
# 5. to_rich() 输出
# ============================================================

class TestReportToRich:
    """to_rich() Rich Table 输出测试"""

    def test_report_to_rich_returns_table(self):
        """to_rich 应返回 rich.table.Table 实例"""
        from rich.table import Table

        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = AnalysisReport(run_id="test", registry=reg, data=dp)
        table = report.to_rich()
        assert isinstance(table, Table)


# ============================================================
# 6. SingleReport
# ============================================================

class TestSingleReport:
    """SingleReport 测试"""

    def test_single_report_is_analysis_report(self):
        """SingleReport 应是 AnalysisReport 的子类或别名"""
        report = SingleReport(
            run_id="test_single",
            registry=MetricRegistry(),
            data=DataProvider(net_value=pd.DataFrame({"value": [100, 105]})),
        )
        assert isinstance(report, AnalysisReport)

    def test_single_report_to_dict(self):
        """SingleReport 的 to_dict 应正常工作"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105]}))
        report = SingleReport(run_id="single_001", registry=reg, data=dp)
        d = report.to_dict()
        assert d["run_id"] == "single_001"
        assert "summary" in d


# ============================================================
# 7. time_series
# ============================================================

class TestTimeSeries:
    """原始时间序列数据保留测试"""

    def test_time_series_in_to_dict(self):
        """time_series 应包含 DataProvider 中所有 DataFrame"""
        nv = pd.DataFrame({"value": [100, 105]})
        dp = DataProvider(net_value=nv)
        report = AnalysisReport(run_id="test", registry=MetricRegistry(), data=dp)
        d = report.to_dict()
        assert "time_series" in d
        assert "net_value" in d["time_series"]
