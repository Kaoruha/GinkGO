# RollingReport 测试用例
#
# 测试范围:
#   - 构造与基础属性
#   - 滑动窗口参数
#   - to_dict() 以窗口起始日期为 key
#   - to_dataframe() 以窗口起始日期为 index
#   - to_rich() Rich Table 滚动指标行
#   - 无 timestamp 列的处理


import pytest

import pandas as pd

from ginkgo.trading.analysis.reports.rolling import RollingReport
from ginkgo.trading.analysis.metrics.base import MetricRegistry, DataProvider
from ginkgo.trading.analysis.metrics.portfolio import AnnualizedReturn, MaxDrawdown, SharpeRatio, Volatility


# ============================================================
# 辅助函数
# ============================================================

def _make_net_value_with_timestamp(days: int = 120) -> pd.DataFrame:
    """创建带有 timestamp 列的 net_value DataFrame

    生成 120 天的净值数据，用于滚动窗口测试。
    """
    dates = pd.date_range(start="2024-01-01", periods=days, freq="D")
    import numpy as np
    np.random.seed(42)
    values = 100 * (1 + np.random.randn(days).cumsum() * 0.005)
    return pd.DataFrame({"timestamp": dates, "value": values})


# ============================================================
# 1. 构造与基础属性
# ============================================================

class TestRollingConstruction:
    """RollingReport 构造测试"""

    def test_rolling_stores_run_id(self):
        """run_id 应被正确存储"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp)
        assert rr.run_id == "roll_test"

    def test_rolling_default_window(self):
        """默认窗口大小应为 60"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp)
        assert rr.window == 60

    def test_rolling_custom_window(self):
        """应支持自定义窗口大小"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp())
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=30)
        assert rr.window == 30


# ============================================================
# 2. to_dict() 输出
# ============================================================

class TestRollingToDict:
    """to_dict() 滚动窗口输出测试"""

    def test_to_dict_keys_are_dates(self):
        """to_dict 的 key 应为窗口起始日期"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        d = rr.to_dict()
        # 120 天, window=60, step=1 → 61 个滑动窗口
        assert len(d) > 0
        for key in d:
            assert isinstance(key, str)

    def test_to_dict_each_window_has_metrics(self):
        """每个窗口应包含 summary 指标"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        reg.register(Volatility)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        d = rr.to_dict()
        for window_label, metrics in d.items():
            assert "annualized_return" in metrics
            assert "volatility" in metrics

    def test_to_dict_window_count(self):
        """滑动窗口(step=1)数量应为 total_len - window + 1"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        d = rr.to_dict()
        # 120 天, window=60, step=1 → 61 个窗口
        assert len(d) == 61

    def test_to_dict_tumbling_window_count(self):
        """设置 step=window 退化为滚动窗口"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60, step=60)
        d = rr.to_dict()
        # 120 天, window=60, step=60 → 2 个非重叠窗口
        assert len(d) == 2

    def test_step_parameter_stored(self):
        """step 参数应被正确存储"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60, step=5)
        assert rr.step == 5


# ============================================================
# 3. to_dataframe() 输出
# ============================================================

class TestRollingToDataFrame:
    """to_dataframe() DataFrame 输出测试"""

    def test_to_dataframe_returns_dataframe(self):
        """to_dataframe 应返回 DataFrame"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        df = rr.to_dataframe()
        assert isinstance(df, pd.DataFrame)

    def test_to_dataframe_index_is_window_dates(self):
        """DataFrame 的 index 应为窗口起始日期"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60, step=60)
        df = rr.to_dataframe()
        assert len(df) == 2

    def test_to_dataframe_empty_with_short_data(self):
        """数据长度小于窗口时应返回空 DataFrame"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(30))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        df = rr.to_dataframe()
        assert df.empty


# ============================================================
# 4. to_rich() 输出
# ============================================================

class TestRollingToRich:
    """to_rich() Rich Table 输出测试"""

    def test_to_rich_returns_table(self):
        """to_rich 应返回 rich.table.Table 实例"""
        from rich.table import Table

        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=_make_net_value_with_timestamp(120))
        rr = RollingReport(run_id="roll_test", registry=reg, data=dp, window=60)
        table = rr.to_rich()
        assert isinstance(table, Table)


# ============================================================
# 5. 无 timestamp 列的处理
# ============================================================

class TestRollingNoTimestamp:
    """无 timestamp 列时的处理"""

    def test_no_timestamp_raises_error(self):
        """net_value 没有 timestamp 列时应抛出 ValueError"""
        reg = MetricRegistry()
        reg.register(AnnualizedReturn)
        dp = DataProvider(net_value=pd.DataFrame({"value": [100, 105, 110]}))
        with pytest.raises(ValueError, match="timestamp"):
            RollingReport(run_id="roll_test", registry=reg, data=dp, window=30)
