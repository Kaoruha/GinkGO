# Upstream: trading.analysis 完整模块 (metrics, reports, engine)
# Downstream: None (集成测试)
# Role: 验证分析模块各组件的集成性 — 模块导出、端到端分析流程、自定义指标注册


"""
分析模块集成测试

验证分析模块的整体集成性：
1. 模块导出 — __init__.py 中的所有公开符号可正确导入
2. AnalysisEngine 构造 — 使用 mock services 正常初始化
3. 端到端 analyze → SingleReport → to_dict() → 结构验证
4. 端到端 compare → ComparisonReport → to_dict() 结构验证
5. register_metric 端到端 — 自定义指标注册后可被计算
"""

from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from typing import Dict, Any, List

import pytest
import pandas as pd

from ginkgo.trading.analysis.engine import AnalysisEngine
from ginkgo.trading.analysis.metrics.base import DataProvider, MetricRegistry


# ============================================================
# 测试辅助
# ============================================================

class _SimpleMetric:
    """简单测试指标，仅返回固定值"""
    name: str = "simple_test_metric"
    requires: List[str] = ["net_value"]
    params: Dict[str, Any] = {}

    def __init__(self):
        self.params = {}

    def compute(self, data: Dict[str, pd.DataFrame]) -> float:
        return 42.0


def _make_net_value_df(days: int = 100, start: datetime = None) -> pd.DataFrame:
    """构造 net_value DataFrame (timestamp, value 列)"""
    if start is None:
        start = datetime(2023, 1, 1)
    dates = [start + timedelta(days=i) for i in range(days)]
    values = [1.0 + 0.001 * i for i in range(days)]
    return pd.DataFrame({"timestamp": dates, "value": values})


def _make_service_result(data, is_success: bool = True):
    """构造 mock ServiceResult"""
    result = MagicMock()
    result.is_success.return_value = is_success
    result.data = data
    return result


def _make_mock_services(net_value_df: pd.DataFrame = None):
    """构造 mock result_service 和 analyzer_service

    Args:
        net_value_df: net_value 数据，默认自动生成

    Returns:
        (result_service, analyzer_service) tuple
    """
    if net_value_df is None:
        net_value_df = _make_net_value_df()

    analyzer_service = MagicMock()
    analyzer_service.get_by_run_id.return_value = _make_service_result(net_value_df)

    # signal/order/position 均返回空列表
    result_service = MagicMock()
    result_service.get_signals.return_value = _make_service_result({"data": []})
    result_service.get_orders.return_value = _make_service_result({"data": []})
    result_service.get_positions.return_value = _make_service_result({"data": []})

    return result_service, analyzer_service


# ============================================================
# 1. 模块导出验证
# ============================================================

class TestModuleExports:
    """验证 __init__.py 中的公开符号可正确导入"""

    def test_metrics_base_exports(self):
        """Metric, DataProvider, MetricRegistry 可从 __init__.py 导入"""
        from ginkgo.trading.analysis import Metric, DataProvider, MetricRegistry
        assert Metric is not None
        assert DataProvider is not None
        assert MetricRegistry is not None

    def test_reports_exports(self):
        """报告类可从 __init__.py 导入"""
        from ginkgo.trading.analysis import (
            AnalysisReport, SingleReport, ComparisonReport,
            SegmentReport, RollingReport,
        )
        assert AnalysisReport is not None
        assert SingleReport is not None
        assert ComparisonReport is not None
        assert SegmentReport is not None
        assert RollingReport is not None

    def test_engine_export(self):
        """AnalysisEngine 可从 __init__.py 导入"""
        from ginkgo.trading.analysis import AnalysisEngine
        assert AnalysisEngine is not None

    def test_existing_analyzer_exports_unchanged(self):
        """原有分析器导出不受影响"""
        from ginkgo.trading.analysis import (
            BaseAnalyzer,
            Profit, NetValue, MaxDrawdown, SharpeRatio,
            BacktestResultAggregator,
        )
        assert BaseAnalyzer is not None
        assert Profit is not None
        assert NetValue is not None
        assert MaxDrawdown is not None
        assert SharpeRatio is not None
        assert BacktestResultAggregator is not None

    def test___all___contains_new_symbols(self):
        """__all__ 包含新增的 symbols"""
        from ginkgo.trading import analysis
        expected_new = {
            "Metric", "DataProvider", "MetricRegistry",
            "AnalysisReport", "SingleReport", "ComparisonReport",
            "SegmentReport", "RollingReport",
            "AnalysisEngine",
        }
        assert expected_new.issubset(set(analysis.__all__))


# ============================================================
# 2. AnalysisEngine 构造
# ============================================================

class TestEngineConstruction:
    """验证 AnalysisEngine 使用 mock services 可正常初始化"""

    def test_engine_init_with_mocks(self):
        """使用 mock services 构造 AnalysisEngine"""
        result_service, analyzer_service = _make_mock_services()
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )
        assert engine is not None
        assert isinstance(engine._registry, MetricRegistry)

    def test_engine_has_builtin_metrics(self):
        """初始化后内置指标已注册"""
        result_service, analyzer_service = _make_mock_services()
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )
        # 至少包含核心内置指标
        registered = engine._registry.list_metrics()
        assert "annualized_return" in registered
        assert "max_drawdown" in registered
        assert "sharpe_ratio" in registered


# ============================================================
# 3. 端到端 analyze → SingleReport → to_dict()
# ============================================================

class TestEndToEndAnalyze:
    """端到端验证 analyze 流程"""

    def test_analyze_returns_single_report(self):
        """analyze() 返回 SingleReport 实例"""
        from ginkgo.trading.analysis.reports.single import SingleReport

        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        report = engine.analyze(run_id="test-run-001")
        assert isinstance(report, SingleReport)

    def test_analyze_report_to_dict_structure(self):
        """analyze() → to_dict() 返回正确结构"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        report = engine.analyze(run_id="test-run-001")
        d = report.to_dict()

        # 验证顶层结构
        assert "run_id" in d
        assert "summary" in d
        assert "signal_analysis" in d
        assert "order_analysis" in d
        assert "position_analysis" in d
        assert "metrics" in d
        assert "time_series" in d
        assert "report_type" in d  # SingleReport 特有字段
        assert d["report_type"] == "single"

    def test_analyze_report_has_summary_metrics(self):
        """analyze() 报告包含 summary 级指标"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        report = engine.analyze(run_id="test-run-001")
        summary = report.summary

        # summary 应包含 net_value 依赖的指标
        assert len(summary) > 0
        # 至少包含年化收益率
        assert "annualized_return" in summary

    def test_analyze_report_run_id_preserved(self):
        """run_id 正确保留"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        report = engine.analyze(run_id="my-unique-run-id")
        assert report.run_id == "my-unique-run-id"
        assert report.to_dict()["run_id"] == "my-unique-run-id"


# ============================================================
# 4. 端到端 compare → ComparisonReport
# ============================================================

class TestEndToEndCompare:
    """端到端验证 compare 流程"""

    def test_compare_returns_comparison_report(self):
        """compare() 返回 ComparisonReport 实例"""
        from ginkgo.trading.analysis.reports.comparison import ComparisonReport

        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        comp = engine.compare(run_ids=["run-001", "run-002"])
        assert isinstance(comp, ComparisonReport)

    def test_compare_report_to_dict_structure(self):
        """compare() → to_dict() 返回以 run_id 为 key 的字典"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        comp = engine.compare(run_ids=["run-001", "run-002"])
        d = comp.to_dict()

        # 两个 run_id 作为 key
        assert "run-001" in d
        assert "run-002" in d

        # 每个 run 包含 summary
        assert "summary" in d["run-001"]
        assert "summary" in d["run-002"]

    def test_compare_contains_multiple_reports(self):
        """ComparisonReport 包含多个子报告"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        comp = engine.compare(run_ids=["run-001", "run-002", "run-003"])
        assert len(comp.reports) == 3


# ============================================================
# 5. register_metric 端到端
# ============================================================

class TestRegisterMetricEndToEnd:
    """验证自定义指标注册的端到端流程"""

    def test_register_custom_metric(self):
        """register_metric 后指标出现在 registry 中"""
        result_service, analyzer_service = _make_mock_services()
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        engine.register_metric(_SimpleMetric)
        assert "simple_test_metric" in engine._registry.list_metrics()

    def test_custom_metric_computed_in_analyze(self):
        """自定义指标在 analyze 报告中被计算"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        engine.register_metric(_SimpleMetric)
        report = engine.analyze(run_id="test-custom")

        # _SimpleMetric requires=["net_value"] → 分类为 summary
        assert "simple_test_metric" in report.summary
        assert report.summary["simple_test_metric"] == 42.0

    def test_custom_metric_appears_in_to_dict(self):
        """自定义指标值出现在 to_dict 输出中"""
        nv_df = _make_net_value_df()
        result_service, analyzer_service = _make_mock_services(nv_df)
        engine = AnalysisEngine(
            result_service=result_service,
            analyzer_service=analyzer_service,
        )

        engine.register_metric(_SimpleMetric)
        report = engine.analyze(run_id="test-custom")
        d = report.to_dict()

        assert "simple_test_metric" in d["summary"]
        assert d["summary"]["simple_test_metric"] == 42.0
