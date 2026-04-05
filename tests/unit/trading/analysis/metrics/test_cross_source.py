"""
跨数据源指标 TDD测试

SignalOrderConversion 和 SignalIC 的测试套件，
使用 mock 数据覆盖正常场景和边界条件。
"""
import pytest
import sys
import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime, timedelta, date

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.analysis.metrics.cross_source import (
    SignalOrderConversion,
    SignalIC,
)


# ============================================================
# 测试数据构建
# ============================================================

def _make_signals(
    codes: list[str],
    directions: list[int],
    base_date: date = date(2024, 1, 2),
    days: int = 10,
) -> pd.DataFrame:
    """构建信号 DataFrame，每天每个 code 出现一次"""
    rows = []
    for day_idx in range(days):
        d = base_date + timedelta(days=day_idx)
        for code, direction in zip(codes, directions):
            rows.append({
                "code": code,
                "direction": direction,
                "timestamp": datetime(d.year, d.month, d.day),
            })
    return pd.DataFrame(rows)


def _make_orders(
    codes: list[str],
    base_date: date = date(2024, 1, 2),
    days: int = 10,
) -> pd.DataFrame:
    """构建订单 DataFrame，每天每个 code 出现一次"""
    rows = []
    for day_idx in range(days):
        d = base_date + timedelta(days=day_idx)
        for code in codes:
            rows.append({
                "code": code,
                "timestamp": datetime(d.year, d.month, d.day),
            })
    return pd.DataFrame(rows)


def _make_nav(
    base_date: date = date(2024, 1, 2),
    days: int = 11,
    start_value: float = 1.0,
    daily_returns: list[float] | None = None,
) -> pd.DataFrame:
    """构建净值 DataFrame"""
    if daily_returns is None:
        rng = np.random.default_rng(42)
        daily_returns = rng.normal(0.001, 0.02, days - 1).tolist()

    rows = []
    value = start_value
    for day_idx in range(days):
        d = base_date + timedelta(days=day_idx)
        rows.append({
            "value": value,
            "timestamp": datetime(d.year, d.month, d.day),
        })
        if day_idx < len(daily_returns):
            value *= (1 + daily_returns[day_idx])
    return pd.DataFrame(rows)


# ============================================================
# SignalOrderConversion 测试
# ============================================================

@pytest.mark.unit
class TestSignalOrderConversion:
    """信号订单转化率指标测试"""

    def test_full_conversion(self):
        """所有信号标的都有订单 → 转化率 1.0"""
        metric = SignalOrderConversion()
        df_signal = _make_signals(["A", "B"], [1, -1])
        df_order = _make_orders(["A", "B"])
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == 1.0

    def test_partial_conversion(self):
        """部分信号标的有订单"""
        metric = SignalOrderConversion()
        df_signal = _make_signals(["A", "B", "C"], [1, -1, 1])
        df_order = _make_orders(["A", "C"])
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == pytest.approx(2 / 3)

    def test_zero_conversion(self):
        """信号标的都没有订单 → 转化率 0.0"""
        metric = SignalOrderConversion()
        df_signal = _make_signals(["A", "B"], [1, -1])
        df_order = _make_orders(["X", "Y"])
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == 0.0

    def test_no_signals(self):
        """无信号 → 转化率 0.0"""
        metric = SignalOrderConversion()
        df_signal = pd.DataFrame(columns=["code", "direction", "timestamp"])
        df_order = _make_orders(["A"])
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == 0.0

    def test_no_orders(self):
        """有信号但无订单 → 转化率 0.0"""
        metric = SignalOrderConversion()
        df_signal = _make_signals(["A"], [1])
        df_order = pd.DataFrame(columns=["code", "timestamp"])
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == 0.0

    def test_duplicate_codes_handled(self):
        """同一标的多次信号和订单不影响转化率计算"""
        metric = SignalOrderConversion()
        df_signal = _make_signals(["A", "B"], [1, -1], days=20)
        df_order = _make_orders(["A"], days=20)
        result = metric.compute({"signal": df_signal, "order": df_order})
        assert result == pytest.approx(0.5)

    def test_protocol_compliance(self):
        """满足 Metric Protocol"""
        from ginkgo.trading.analysis.metrics.base import Metric
        m = SignalOrderConversion()
        assert isinstance(m, Metric)
        assert m.name == "signal_order_conversion"
        assert "signal" in m.requires
        assert "order" in m.requires


# ============================================================
# SignalIC 测试
# ============================================================

@pytest.mark.unit
class TestSignalIC:
    """信号IC指标测试"""

    def test_positive_ic_signal_predicts_return(self):
        """信号方向与次日收益正相关 → IC > 0"""
        metric = SignalIC()
        base = date(2024, 1, 2)

        # 构造信号：前半段做多(全部LONG)，后半段做空(全部SHORT)
        signal_rows = []
        for day_idx in range(10):
            d = base + timedelta(days=day_idx)
            direction = 1 if day_idx < 5 else -1
            signal_rows.append({
                "code": "A",
                "direction": direction,
                "timestamp": datetime(d.year, d.month, d.day),
            })
        df_signal = pd.DataFrame(signal_rows)

        # 构造净值：前半段涨，后半段跌 → 信号与收益正相关
        returns = [0.02, 0.02, 0.02, 0.02, 0.01, -0.01, -0.02, -0.02, -0.02, -0.02]
        df_nav = _make_nav(base_date=base, days=11, daily_returns=returns)

        data = {"signal": df_signal, "net_value": df_nav}
        result = metric.compute(data)
        assert isinstance(result, float)
        assert result > 0

    def test_negative_ic_signal_adversely_predicts(self):
        """信号方向与次日收益负相关 → IC < 0"""
        metric = SignalIC()
        base = date(2024, 1, 2)

        # 前半段做多，后半段做空
        signal_rows = []
        for day_idx in range(10):
            d = base + timedelta(days=day_idx)
            direction = 1 if day_idx < 5 else -1
            signal_rows.append({
                "code": "A",
                "direction": direction,
                "timestamp": datetime(d.year, d.month, d.day),
            })
        df_signal = pd.DataFrame(signal_rows)

        # 净值：前半段跌，后半段涨 → 负相关
        returns = [-0.02, -0.02, -0.02, -0.02, -0.01, 0.01, 0.02, 0.02, 0.02, 0.02]
        df_nav = _make_nav(base_date=base, days=11, daily_returns=returns)

        result = metric.compute({"signal": df_signal, "net_value": df_nav})
        assert result < 0

    def test_insufficient_data_returns_zero(self):
        """数据点不足 (< 2) → 返回 0.0"""
        metric = SignalIC()
        base = date(2024, 1, 2)

        # 只有一天信号
        df_signal = pd.DataFrame([{
            "code": "A",
            "direction": 1,
            "timestamp": datetime(base.year, base.month, base.day),
        }])
        df_nav = _make_nav(base_date=base, days=3)

        result = metric.compute({"signal": df_signal, "net_value": df_nav})
        assert result == 0.0

    def test_no_signals_returns_zero(self):
        """无信号 → 返回 0.0"""
        metric = SignalIC()
        df_signal = pd.DataFrame(columns=["code", "direction", "timestamp"])
        df_nav = _make_nav(days=11)

        result = metric.compute({"signal": df_signal, "net_value": df_nav})
        assert result == 0.0

    def test_multiple_codes_per_day(self):
        """每天多个标的的信号被正确聚合，方向变化时 IC 有意义"""
        metric = SignalIC()
        base = date(2024, 1, 2)

        signal_rows = []
        for day_idx in range(10):
            d = base + timedelta(days=day_idx)
            # 前5天偏多(3L+1S=0.5)，后5天偏空(1L+3S=-0.5)
            if day_idx < 5:
                long_count, short_count = 3, 1
            else:
                long_count, short_count = 1, 3
            for _ in range(long_count):
                signal_rows.append({
                    "code": f"LONG_{day_idx}_{_}",
                    "direction": 1,
                    "timestamp": datetime(d.year, d.month, d.day),
                })
            for _ in range(short_count):
                signal_rows.append({
                    "code": f"SHORT_{day_idx}_{_}",
                    "direction": -1,
                    "timestamp": datetime(d.year, d.month, d.day),
                })
        df_signal = pd.DataFrame(signal_rows)

        # 净值：前涨后跌，与信号方向一致 → 正相关
        returns = [0.02, 0.02, 0.02, 0.02, 0.01, -0.01, -0.02, -0.02, -0.02, -0.02]
        df_nav = _make_nav(base_date=base, days=11, daily_returns=returns)

        result = metric.compute({"signal": df_signal, "net_value": df_nav})
        assert isinstance(result, float)
        assert not pd.isna(result)
        assert result > 0

    def test_ic_range(self):
        """IC 值在 [-1, 1] 范围内"""
        metric = SignalIC()
        rng = np.random.default_rng(123)
        returns = rng.normal(0, 0.02, 10).tolist()

        # 方向有变化的信号（避免常量输入导致 NaN）
        signal_rows = []
        base = date(2024, 1, 2)
        for day_idx in range(10):
            d = base + timedelta(days=day_idx)
            direction = 1 if rng.random() > 0.5 else -1
            signal_rows.append({
                "code": "A",
                "direction": direction,
                "timestamp": datetime(d.year, d.month, d.day),
            })
        df_signal = pd.DataFrame(signal_rows)
        df_nav = _make_nav(days=11, daily_returns=returns)

        result = metric.compute({"signal": df_signal, "net_value": df_nav})
        assert isinstance(result, float)
        assert not pd.isna(result)
        assert -1 <= result <= 1

    def test_protocol_compliance(self):
        """满足 Metric Protocol"""
        from ginkgo.trading.analysis.metrics.base import Metric
        m = SignalIC()
        assert isinstance(m, Metric)
        assert m.name == "signal_ic"
        assert "signal" in m.requires
        assert "net_value" in m.requires
