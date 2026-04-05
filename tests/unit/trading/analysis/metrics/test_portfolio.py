"""
组合层级指标单元测试

覆盖8个指标：年化收益率、最大回撤、夏普比率、索提诺比率、
波动率、卡尔玛比率、滚动夏普比率和滚动波动率。
"""

import math

import pandas as pd
import pytest

from ginkgo.trading.analysis.metrics.base import DataProvider
from ginkgo.trading.analysis.metrics.portfolio import (
    AnnualizedReturn,
    CalmarRatio,
    MaxDrawdown,
    RollingSharpe,
    RollingVolatility,
    SharpeRatio,
    SortinoRatio,
    Volatility,
)


# ============================================================
# Test fixtures
# ============================================================

NAV = [100, 102, 101, 103, 105, 104, 106, 108, 107, 110]


def _make_dp(nav: list = NAV) -> DataProvider:
    """构造包含 net_value 的 DataProvider"""
    df = pd.DataFrame({"value": nav})
    return DataProvider(net_value=df)


def _make_data(nav: list = NAV) -> dict:
    """构造 Metric.compute 所需的 data 字典"""
    df = pd.DataFrame({"value": nav})
    return {"net_value": df}


# ============================================================
# AnnualizedReturn
# ============================================================

class TestAnnualizedReturn:
    """年化收益率指标测试"""

    def test_returns_float(self):
        m = AnnualizedReturn()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_value_range(self):
        """NAV 从100涨到110 (9个交易日)，年化收益应为正"""
        m = AnnualizedReturn()
        result = m.compute(_make_data())
        assert result > 0

    def test_exact_value(self):
        """(110/100) ** (252/9) - 1，约等于 248.7"""
        m = AnnualizedReturn()
        result = m.compute(_make_data())
        expected = (110 / 100) ** (252 / 9) - 1
        assert abs(result - expected) < 1e-10


# ============================================================
# MaxDrawdown
# ============================================================

class TestMaxDrawdown:
    """最大回撤指标测试"""

    def test_returns_float(self):
        m = MaxDrawdown()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_negative_value(self):
        m = MaxDrawdown()
        result = m.compute(_make_data())
        assert result < 0

    def test_max_drawdown_value(self):
        """NAV: 100,102,101,103,105,104,106,108,107,110
        最大回撤发生在 102→101: (101-102)/102 ≈ -0.009804
        """
        m = MaxDrawdown()
        result = m.compute(_make_data())
        expected = (101 - 102) / 102
        assert abs(result - expected) < 1e-10


# ============================================================
# SharpeRatio
# ============================================================

class TestSharpeRatio:
    """夏普比率指标测试"""

    def test_returns_float(self):
        m = SharpeRatio()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_positive_sharpe(self):
        """NAV 整体上涨，夏普比率应为正"""
        m = SharpeRatio()
        result = m.compute(_make_data())
        assert result > 0

    def test_custom_risk_free_rate(self):
        m1 = SharpeRatio(risk_free_rate=0.03)
        m2 = SharpeRatio(risk_free_rate=0.05)
        r1 = m1.compute(_make_data())
        r2 = m2.compute(_make_data())
        assert r1 > r2  # 更高的无风险利率 → 更低的夏普


# ============================================================
# SortinoRatio
# ============================================================

class TestSortinoRatio:
    """索提诺比率指标测试"""

    def test_returns_float(self):
        m = SortinoRatio()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_positive_sortino(self):
        """NAV 整体上涨，索提诺比率应为正"""
        m = SortinoRatio()
        result = m.compute(_make_data())
        assert result > 0

    def test_sortino_greater_than_sharpe(self):
        """下行波动率 <= 全部波动率，所以 Sortino >= Sharpe"""
        m_sharpe = SharpeRatio(risk_free_rate=0.03)
        m_sortino = SortinoRatio(risk_free_rate=0.03)
        sharpe = m_sharpe.compute(_make_data())
        sortino = m_sortino.compute(_make_data())
        assert sortino >= sharpe


# ============================================================
# Volatility
# ============================================================

class TestVolatility:
    """年化波动率指标测试"""

    def test_returns_float(self):
        m = Volatility()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_positive_volatility(self):
        m = Volatility()
        result = m.compute(_make_data())
        assert result > 0

    def test_manual_calculation(self):
        """手动验证: std(daily_returns) * sqrt(252)"""
        nav = pd.Series(NAV)
        returns = nav.pct_change().dropna()
        expected = returns.std() * math.sqrt(252)
        m = Volatility()
        result = m.compute(_make_data())
        assert abs(result - expected) < 1e-10


# ============================================================
# CalmarRatio
# ============================================================

class TestCalmarRatio:
    """卡尔玛比率指标测试"""

    def test_returns_float(self):
        m = CalmarRatio()
        result = m.compute(_make_data())
        assert isinstance(result, float)

    def test_positive_calmar(self):
        """NAV 整体上涨且回撤存在，卡尔玛比率应为正"""
        m = CalmarRatio()
        result = m.compute(_make_data())
        assert result > 0

    def test_zero_drawdown(self):
        """单调上涨时 max_drawdown=0，应返回 0.0"""
        monotonic_data = _make_data([100, 101, 102, 103, 104])
        m = CalmarRatio()
        result = m.compute(monotonic_data)
        assert result == 0.0


# ============================================================
# RollingSharpe
# ============================================================

class TestRollingSharpe:
    """滚动夏普比率指标测试"""

    def test_returns_series(self):
        m = RollingSharpe(window=5)
        result = m.compute(_make_data())
        assert isinstance(result, pd.Series)

    def test_length(self):
        """9个日收益率，window=5，结果长度应为9"""
        m = RollingSharpe(window=5)
        result = m.compute(_make_data())
        assert len(result) == 9

    def test_nan_at_head(self):
        """滚动窗口前期应为 NaN"""
        m = RollingSharpe(window=5)
        result = m.compute(_make_data())
        assert pd.isna(result.iloc[3])  # index 0-3 (前4个) 都是 NaN


# ============================================================
# RollingVolatility
# ============================================================

class TestRollingVolatility:
    """滚动波动率指标测试"""

    def test_returns_series(self):
        m = RollingVolatility(window=5)
        result = m.compute(_make_data())
        assert isinstance(result, pd.Series)

    def test_length(self):
        m = RollingVolatility(window=5)
        result = m.compute(_make_data())
        assert len(result) == 9

    def test_nan_at_head(self):
        m = RollingVolatility(window=5)
        result = m.compute(_make_data())
        assert pd.isna(result.iloc[3])

    def test_positive_values(self):
        """窗口完全填充后，波动率应为正"""
        m = RollingVolatility(window=5)
        result = m.compute(_make_data())
        assert result.iloc[4] > 0


# ============================================================
# Metric Protocol conformance
# ============================================================

class TestMetricProtocolConformance:
    """验证所有指标结构匹配 Metric Protocol"""

    @pytest.fixture(params=[
        AnnualizedReturn,
        MaxDrawdown,
        SharpeRatio,
        SortinoRatio,
        Volatility,
        CalmarRatio,
        lambda: RollingSharpe(window=10),
        lambda: RollingVolatility(window=10),
    ])
    def metric_instance(self, request):
        cls_or_factory = request.param
        if callable(cls_or_factory) and isinstance(cls_or_factory, type):
            return cls_or_factory()
        return cls_or_factory()

    def test_has_name(self, metric_instance):
        assert hasattr(metric_instance, "name")
        assert isinstance(metric_instance.name, str)

    def test_has_requires(self, metric_instance):
        assert hasattr(metric_instance, "requires")
        assert isinstance(metric_instance.requires, list)
        assert "net_value" in metric_instance.requires

    def test_has_params(self, metric_instance):
        assert hasattr(metric_instance, "params")
        assert isinstance(metric_instance.params, dict)

    def test_has_compute(self, metric_instance):
        assert hasattr(metric_instance, "compute")
        assert callable(metric_instance.compute)

    def test_compute_accepts_data_dict(self, metric_instance):
        dp = _make_dp()
        result = metric_instance.compute({"net_value": dp.get("net_value")})
        assert result is not None
