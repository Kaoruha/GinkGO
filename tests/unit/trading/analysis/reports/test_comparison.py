# ComparisonReport 测试用例
#
# 测试范围:
#   - 构造与基础属性
#   - to_dict() 多 run 并排对比
#   - to_dataframe() 以 run_id 为列、指标名为 index
#   - to_rich() Rich Table 多列输出
#   - 空报告列表处理
#   - 单个报告处理


import pytest

import pandas as pd

from ginkgo.trading.analysis.reports.base import AnalysisReport
from ginkgo.trading.analysis.reports.comparison import ComparisonReport
from ginkgo.trading.analysis.metrics.base import MetricRegistry, DataProvider
from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown


# ============================================================
# 辅助函数
# ============================================================

def _make_report(run_id: str, values: list) -> AnalysisReport:
    """创建一个带有 AnnualizedReturn 指标的 AnalysisReport"""
    reg = MetricRegistry()
    reg.register(AnnualizedReturn)
    reg.register(MaxDrawdown)
    dp = DataProvider(net_value=pd.DataFrame({"value": values}))
    return AnalysisReport(run_id=run_id, registry=reg, data=dp)


# ============================================================
# 1. 构造与基础属性
# ============================================================

class TestComparisonConstruction:
    """ComparisonReport 构造测试"""

    def test_comparison_stores_reports(self):
        """应正确存储传入的报告列表"""
        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        cr = ComparisonReport(reports=[r1, r2])
        assert len(cr.reports) == 2

    def test_comparison_empty_reports(self):
        """空报告列表应创建空的 ComparisonReport"""
        cr = ComparisonReport(reports=[])
        assert len(cr.reports) == 0
        d = cr.to_dict()
        assert d == {}

    def test_comparison_single_report(self):
        """单个报告也应正常工作"""
        r1 = _make_report("run_a", [100, 105])
        cr = ComparisonReport(reports=[r1])
        d = cr.to_dict()
        assert "run_a" in d


# ============================================================
# 2. to_dict() 输出
# ============================================================

class TestComparisonToDict:
    """to_dict() 多 run 并排对比测试"""

    def test_to_dict_has_run_ids_as_keys(self):
        """to_dict 应以 run_id 为 key"""
        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        cr = ComparisonReport(reports=[r1, r2])
        d = cr.to_dict()
        assert "run_a" in d
        assert "run_b" in d

    def test_to_dict_contains_summary_metrics(self):
        """每个 run 的 value 应包含 summary 指标"""
        r1 = _make_report("run_a", [100, 105])
        cr = ComparisonReport(reports=[r1])
        d = cr.to_dict()
        assert "summary" in d["run_a"]
        assert "annualized_return" in d["run_a"]["summary"]

    def test_to_dict_three_runs(self):
        """三个 run 应正确输出"""
        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        r3 = _make_report("run_c", [100, 95])
        cr = ComparisonReport(reports=[r1, r2, r3])
        d = cr.to_dict()
        assert len(d) == 3


# ============================================================
# 3. to_dataframe() 输出
# ============================================================

class TestComparisonToDataFrame:
    """to_dataframe() DataFrame 输出测试"""

    def test_to_dataframe_returns_dataframe(self):
        """to_dataframe 应返回 DataFrame"""
        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        cr = ComparisonReport(reports=[r1, r2])
        df = cr.to_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_columns_are_run_ids(self):
        """DataFrame 的列应为 run_id"""
        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        cr = ComparisonReport(reports=[r1, r2])
        df = cr.to_dataframe()
        assert "run_a" in df.columns
        assert "run_b" in df.columns

    def test_to_dataframe_empty_reports(self):
        """空报告列表应返回空 DataFrame"""
        cr = ComparisonReport(reports=[])
        df = cr.to_dataframe()
        assert isinstance(df, pd.DataFrame)
        assert df.empty


# ============================================================
# 4. to_rich() 输出
# ============================================================

class TestComparisonToRich:
    """to_rich() Rich Table 输出测试"""

    def test_to_rich_returns_table(self):
        """to_rich 应返回 rich.table.Table 实例"""
        from rich.table import Table

        r1 = _make_report("run_a", [100, 105])
        r2 = _make_report("run_b", [100, 110])
        cr = ComparisonReport(reports=[r1, r2])
        table = cr.to_rich()
        assert isinstance(table, Table)

    def test_to_rich_empty_reports(self):
        """空报告列表应仍返回 Table"""
        from rich.table import Table

        cr = ComparisonReport(reports=[])
        table = cr.to_rich()
        assert isinstance(table, Table)
