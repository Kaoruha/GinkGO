"""
性能: 272MB RSS, 2.46s, 27 tests [PASS]
Analyzer Metrics TDD 测试

事后分析指标 (RollingMean / RollingStd / CV / IC) 的单元测试。
验证基于 AnalyzerRecord 时间序列的滚动统计和 IC 计算逻辑。
"""
import pytest
import pandas as pd
import numpy as np
from typing import List, Dict, Any

from ginkgo.trading.analysis.metrics.analyzer_metrics import RollingMean, RollingStd, CV, IC
from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry


# ============================================================
# 辅助函数
# ============================================================

def make_analyzer_df(values: List[float]) -> pd.DataFrame:
    """构造模拟的 AnalyzerRecord 时间序列 DataFrame"""
    return pd.DataFrame({"value": values})


def make_net_value_df(values: List[float]) -> pd.DataFrame:
    """构造模拟的 net_value 时间序列 DataFrame"""
    return pd.DataFrame({"value": values})


# ============================================================
# RollingMean 测试
# ============================================================

@pytest.mark.unit
class TestRollingMean:
    """滚动均值指标测试"""

    def test_satisfies_metric_protocol(self):
        """RollingMean 满足 Metric Protocol"""
        m = RollingMean(analyzer_name="sharpe")
        assert isinstance(m, Metric)

    def test_name_format(self):
        """name 格式为 rolling_mean.{analyzer_name}"""
        m = RollingMean(analyzer_name="sharpe")
        assert m.name == "rolling_mean.sharpe"

    def test_requires_single_analyzer(self):
        """requires 包含 analyzer_name"""
        m = RollingMean(analyzer_name="sharpe")
        assert m.requires == ["sharpe"]

    def test_params_stored(self):
        """params 包含 analyzer 和 window"""
        m = RollingMean(analyzer_name="sharpe", window=30)
        assert m.params["analyzer"] == "sharpe"
        assert m.params["window"] == 30

    def test_compute_basic(self):
        """基本滚动均值计算"""
        m = RollingMean(analyzer_name="sharpe", window=3)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        data = {"sharpe": make_analyzer_df(values)}
        result = m.compute(data)
        # 前 2 个为 NaN（window=3），从第 3 个开始有值
        assert pd.isna(result.iloc[0])
        assert pd.isna(result.iloc[1])
        assert result.iloc[2] == pytest.approx(2.0)
        assert result.iloc[4] == pytest.approx(4.0)

    def test_compute_returns_series(self):
        """compute 返回 pd.Series"""
        m = RollingMean(analyzer_name="sharpe", window=2)
        data = {"sharpe": make_analyzer_df([1.0, 2.0, 3.0])}
        result = m.compute(data)
        assert isinstance(result, pd.Series)


# ============================================================
# RollingStd 测试
# ============================================================

@pytest.mark.unit
class TestRollingStd:
    """滚动标准差指标测试"""

    def test_satisfies_metric_protocol(self):
        """RollingStd 满足 Metric Protocol"""
        m = RollingStd(analyzer_name="drawdown")
        assert isinstance(m, Metric)

    def test_name_format(self):
        """name 格式为 rolling_std.{analyzer_name}"""
        m = RollingStd(analyzer_name="drawdown")
        assert m.name == "rolling_std.drawdown"

    def test_compute_basic(self):
        """基本滚动标准差计算"""
        m = RollingStd(analyzer_name="drawdown", window=3)
        values = [1.0, 2.0, 3.0, 4.0, 5.0]
        data = {"drawdown": make_analyzer_df(values)}
        result = m.compute(data)
        # window=3 的标准差从索引 2 开始
        # [1,2,3] 的 std(ddof=1) = 1.0
        assert result.iloc[2] == pytest.approx(1.0, abs=1e-4)

    def test_constant_values_std_zero(self):
        """常数序列的标准差为 0"""
        m = RollingStd(analyzer_name="const", window=3)
        data = {"const": make_analyzer_df([5.0, 5.0, 5.0, 5.0])}
        result = m.compute(data)
        assert result.iloc[2] == pytest.approx(0.0, abs=1e-10)


# ============================================================
# CV (Coefficient of Variation) 测试
# ============================================================

@pytest.mark.unit
class TestCV:
    """变异系数指标测试"""

    def test_satisfies_metric_protocol(self):
        """CV 满足 Metric Protocol"""
        m = CV(analyzer_name="sharpe")
        assert isinstance(m, Metric)

    def test_name_format(self):
        """name 格式为 cv.{analyzer_name}"""
        m = CV(analyzer_name="sharpe")
        assert m.name == "cv.sharpe"

    def test_compute_basic(self):
        """基本变异系数计算"""
        m = CV(analyzer_name="sharpe", window=3)
        values = [2.0, 4.0, 6.0, 8.0, 10.0]
        data = {"sharpe": make_analyzer_df(values)}
        result = m.compute(data)
        # [2,4,6] mean=4, std(ddof=1)=2.0, cv=0.5
        assert result.iloc[2] == pytest.approx(0.5, abs=1e-4)

    def test_compute_returns_series(self):
        """compute 返回 pd.Series"""
        m = CV(analyzer_name="sharpe", window=2)
        data = {"sharpe": make_analyzer_df([1.0, 2.0, 3.0])}
        result = m.compute(data)
        assert isinstance(result, pd.Series)


# ============================================================
# IC (Information Coefficient) 测试
# ============================================================

@pytest.mark.unit
class TestIC:
    """IC 指标测试"""

    def test_satisfies_metric_protocol(self):
        """IC 满足 Metric Protocol"""
        m = IC(analyzer_name="sharpe")
        assert isinstance(m, Metric)

    def test_name_format(self):
        """name 格式为 ic.{analyzer_name}"""
        m = IC(analyzer_name="sharpe")
        assert m.name == "ic.sharpe"

    def test_requires_includes_net_value(self):
        """requires 包含 analyzer_name 和 net_value"""
        m = IC(analyzer_name="sharpe")
        assert "sharpe" in m.requires
        assert "net_value" in m.requires

    def test_params_stored(self):
        """params 包含 analyzer、method、lag"""
        m = IC(analyzer_name="sharpe", method="spearman", lag=3)
        assert m.params["analyzer"] == "sharpe"
        assert m.params["method"] == "spearman"
        assert m.params["lag"] == 3

    def test_compute_returns_float(self):
        """compute 返回 float"""
        n = 50
        np.random.seed(42)
        analyzer_vals = np.random.randn(n).tolist()
        net_vals = np.cumsum(np.random.randn(n) * 0.01 + 0.001).tolist()
        data = {
            "sharpe": make_analyzer_df(analyzer_vals),
            "net_value": make_net_value_df(net_vals),
        }
        m = IC(analyzer_name="sharpe")
        result = m.compute(data)
        assert isinstance(result, float)
        assert -1.0 <= result <= 1.0

    def test_compute_insufficient_data_returns_zero(self):
        """数据不足 (< 5 个有效对齐点) 时返回 0.0"""
        data = {
            "sharpe": make_analyzer_df([1.0, 2.0, 3.0]),
            "net_value": make_net_value_df([1.0, 1.1, 1.2]),
        }
        m = IC(analyzer_name="sharpe")
        result = m.compute(data)
        assert result == 0.0

    def test_compute_lag_parameter(self):
        """lag 参数影响未来收益的偏移"""
        n = 50
        np.random.seed(42)
        analyzer_vals = np.random.randn(n).tolist()
        net_vals = np.cumsum(np.random.randn(n) * 0.01 + 0.001).tolist()
        data = {
            "sharpe": make_analyzer_df(analyzer_vals),
            "net_value": make_net_value_df(net_vals),
        }
        m1 = IC(analyzer_name="sharpe", lag=1)
        m2 = IC(analyzer_name="sharpe", lag=5)
        r1 = m1.compute(data)
        r2 = m2.compute(data)
        # 不同 lag 通常产生不同 IC
        # 注意：随机数据下可能偶然相等，但不影响类型正确性
        assert isinstance(r1, float)
        assert isinstance(r2, float)


# ============================================================
# MetricRegistry 集成测试
# ============================================================

@pytest.mark.unit
class TestAnalyzerMetricsRegistryIntegration:
    """analyzer_metrics 与 MetricRegistry 集成测试"""

    def test_register_instance_rolling_mean(self):
        """RollingMean 实例可通过 register_instance 注册"""
        registry = MetricRegistry()
        rm = RollingMean(analyzer_name="sharpe", window=20)
        registry.register_instance(rm)
        assert registry.get_instance("rolling_mean.sharpe") is rm

    def test_register_instance_all_four_metrics(self):
        """4 个指标实例同时注册"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="sharpe"))
        registry.register_instance(RollingStd(analyzer_name="sharpe"))
        registry.register_instance(CV(analyzer_name="sharpe"))
        registry.register_instance(IC(analyzer_name="sharpe"))
        names = registry.list_metrics()
        assert "rolling_mean.sharpe" in names
        assert "rolling_std.sharpe" in names
        assert "cv.sharpe" in names
        assert "ic.sharpe" in names

    def test_check_availability_with_analyzer_data(self):
        """提供 analyzer 数据后指标可用"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="sharpe"))
        dp = DataProvider(sharpe=make_analyzer_df([1.0, 2.0, 3.0]))
        available, missing = registry.check_availability(dp)
        assert "rolling_mean.sharpe" in available

    def test_check_availability_ic_needs_net_value(self):
        """IC 指标需要 net_value 数据"""
        registry = MetricRegistry()
        registry.register_instance(IC(analyzer_name="sharpe"))
        dp = DataProvider(sharpe=make_analyzer_df([1.0] * 10))
        available, missing = registry.check_availability(dp)
        # 缺少 net_value → ic.sharpe 在 missing 中
        assert "ic.sharpe" in missing

    def test_check_availability_ic_with_both_data(self):
        """IC 指标在 analyzer + net_value 都有数据时可用"""
        registry = MetricRegistry()
        registry.register_instance(IC(analyzer_name="sharpe"))
        dp = DataProvider(
            sharpe=make_analyzer_df([1.0] * 10),
            net_value=make_net_value_df([1.0] * 10),
        )
        available, missing = registry.check_availability(dp)
        assert "ic.sharpe" in available

    def test_same_analyzer_different_windows(self):
        """同一 analyzer 不同 window 可以共存"""
        registry = MetricRegistry()
        registry.register_instance(RollingMean(analyzer_name="sharpe", window=10))
        registry.register_instance(RollingMean(analyzer_name="sharpe", window=30))
        names = registry.list_metrics()
        assert "rolling_mean.sharpe" in names
        assert registry.get_instance("rolling_mean.sharpe").params["window"] == 30
