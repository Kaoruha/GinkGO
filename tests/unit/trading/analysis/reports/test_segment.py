# SegmentReport 测试用例
#
# 测试范围:
#   - 构造与基础属性
#   - 频率参数 (M/Q/Y)
#   - to_dict() 按分段输出指标
#   - to_dataframe() 以分段为 index
#   - to_rich() Rich Table 分段行
#   - 时间戳列分组逻辑


import pytest

import pandas as pd

from ginkgo.trading.analysis.reports.segment import SegmentReport
from ginkgo.trading.analysis.metrics.base import MetricRegistry, DataProvider
from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown


# ============================================================
# 辅助函数
# ============================================================

def _make_net_value_with_timestamp(days: int = 90) -> pd.DataFrame:
    """创建带有 timestamp 列的 net_value DataFrame

    生成 90 天的净值数据，跨 3 个月，用于分段测试。
    """
    dates = pd.date_range(start="2024-01-01", periods=days, freq="D")
    import numpy as np
    np.random.seed(42)
    values = 100 * (1 + np.random.randn(days).cumsum() * 0.01)
    return pd.DataFrame({"timestamp": dates, "value": values})


# ============================================================
# 1. 构造与基础属性
# ============================================================

class TestSegmentConstruction:
    """SegmentReport 构造测试"""

    def test_segment_stores_run_id(self):
        """run_id 应被正确存储"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp)
        assert sr.run_id == "seg_test"

    def test_segment_default_freq_monthly(self):
        """默认频率应为月度 ('M')"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp)
        assert sr.freq == "M"

    def test_segment_custom_freq(self):
        """应支持自定义频率 Q/Y"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="Q")
        assert sr.freq == "Q"


# ============================================================
# 2. 频率映射
# ============================================================

class TestSegmentFrequency:
    """分段频率测试"""

    def test_monthly_segment_count(self):
        """月度分段应产生约 3 个分段 (90天跨3月)"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        d = sr.to_dict()
        # 2024-01, 2024-02, 2024-03 共 3 个月
        assert len(d) == 3

    def test_quarterly_segment_count(self):
        """季度分段应产生 1 个分段 (90天约1个季度)"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="Q")
        d = sr.to_dict()
        assert len(d) == 1


# ============================================================
# 3. to_dict() 输出
# ============================================================

class TestSegmentToDict:
    """to_dict() 分段输出测试"""

    def test_to_dict_keys_are_segment_labels(self):
        """to_dict 的 key 应为分段标签"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        d = sr.to_dict()
        # 分段标签格式如 "2024-01"
        for key in d:
            assert isinstance(key, str)

    def test_to_dict_each_segment_has_summary(self):
        """每个分段应包含 summary 指标"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        d = sr.to_dict()
        for segment_label, metrics in d.items():
            assert "annualized_return" in metrics


# ============================================================
# 4. to_dataframe() 输出
# ============================================================

class TestSegmentToDataFrame:
    """to_dataframe() DataFrame 输出测试"""

    def test_to_dataframe_returns_dataframe(self):
        """to_dataframe 应返回 DataFrame"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        df = sr.to_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_index_is_segments(self):
        """DataFrame 的 index 应为分段标签"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        df = sr.to_dataframe()
        # index 应包含分段标签
        assert len(df) == 3


# ============================================================
# 5. to_rich() 输出
# ============================================================

class TestSegmentToRich:
    """to_rich() Rich Table 输出测试"""

    def test_to_rich_returns_table(self):
        """to_rich 应返回 rich.table.Table 实例"""
        from rich.table import Table

        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(90))
        sr = SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
        table = sr.to_rich()
        assert isinstance(table, Table)


# ============================================================
# 6. 无 timestamp 列的处理
# ============================================================

class TestSegmentNoTimestamp:
    """无 timestamp 列时的处理"""

    def test_no_timestamp_raises_error(self):
        """net_value 没有 timestamp 列时应抛出 ValueError"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105, 110]}))
        with pytest.raises(ValueError, match="timestamp"):
            SegmentReport(run_id="seg_test", registry=reg, data=dp, freq="M")
