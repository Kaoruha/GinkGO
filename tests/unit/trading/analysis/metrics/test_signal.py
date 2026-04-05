"""
Signal 层级指标 TDD 测试

覆盖 SignalCount / LongShortRatio / DailySignalFreq 三个指标的核心逻辑。
"""

import pytest
import sys
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.analysis.metrics.signal import SignalCount, LongShortRatio, DailySignalFreq
from ginkgo.trading.analysis.metrics.base import Metric, DataProvider, MetricRegistry


def _signal_df() -> pd.DataFrame:
    """标准测试信号数据: 3 LONG + 2 SHORT, 5 个交易日"""
    return pd.DataFrame({
        "code": ["000001", "000002", "000001", "000003", "000001"],
        "direction": [1, 1, -1, 1, -1],
        "timestamp": pd.date_range("2024-01-01", periods=5, freq="D"),
    })


# ============================================================
# SignalCount 测试
# ============================================================

@pytest.mark.unit
class TestSignalCount:
    """信号总数指标测试"""

    def test_returns_total_signal_count(self):
        """5条信号应返回5"""
        metric = SignalCount()
        result = metric.compute({"signal": _signal_df()})
        assert result == 5

    def test_empty_dataframe_returns_zero(self):
        """空DataFrame应返回0"""
        metric = SignalCount()
        df = pd.DataFrame(columns=["code", "direction", "timestamp"])
        result = metric.compute({"signal": df})
        assert result == 0

    def test_single_signal_returns_one(self):
        """单条信号应返回1"""
        metric = SignalCount()
        df = pd.DataFrame({
            "code": ["000001"],
            "direction": [1],
            "timestamp": [pd.Timestamp("2024-01-01")],
        })
        result = metric.compute({"signal": df})
        assert result == 1

    def test_satisfies_metric_protocol(self):
        """满足Metric协议"""
        assert isinstance(SignalCount(), Metric)

    def test_name_and_requires(self):
        """name和requires属性正确"""
        metric = SignalCount()
        assert metric.name == "signal_count"
        assert metric.requires == ["signal"]
        assert metric.params == {}


# ============================================================
# LongShortRatio 测试
# ============================================================

@pytest.mark.unit
class TestLongShortRatio:
    """多空比例指标测试"""

    def test_basic_ratio(self):
        """3 LONG / 2 SHORT = 1.5"""
        metric = LongShortRatio()
        result = metric.compute({"signal": _signal_df()})
        assert result == 1.5

    def test_no_short_signals_returns_zero(self):
        """无做空信号时返回0"""
        metric = LongShortRatio()
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "direction": [1, 1],
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="D"),
        })
        result = metric.compute({"signal": df})
        assert result == 0.0

    def test_no_long_signals(self):
        """无做多信号: 0 / 2 = 0.0"""
        metric = LongShortRatio()
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "direction": [-1, -1],
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="D"),
        })
        result = metric.compute({"signal": df})
        assert result == 0.0

    def test_equal_long_short_returns_one(self):
        """多空相等时返回1.0"""
        metric = LongShortRatio()
        df = pd.DataFrame({
            "code": ["000001", "000002"],
            "direction": [1, -1],
            "timestamp": pd.date_range("2024-01-01", periods=2, freq="D"),
        })
        result = metric.compute({"signal": df})
        assert result == 1.0

    def test_empty_dataframe_returns_zero(self):
        """空DataFrame无做空信号，返回0"""
        metric = LongShortRatio()
        df = pd.DataFrame(columns=["code", "direction", "timestamp"])
        result = metric.compute({"signal": df})
        assert result == 0.0

    def test_satisfies_metric_protocol(self):
        """满足Metric协议"""
        assert isinstance(LongShortRatio(), Metric)

    def test_name_and_requires(self):
        """name和requires属性正确"""
        metric = LongShortRatio()
        assert metric.name == "long_short_ratio"
        assert metric.requires == ["signal"]
        assert metric.params == {}


# ============================================================
# DailySignalFreq 测试
# ============================================================

@pytest.mark.unit
class TestDailySignalFreq:
    """日均信号频率指标测试"""

    def test_basic_frequency(self):
        """5条信号 / 5天 = 1.0"""
        metric = DailySignalFreq()
        result = metric.compute({"signal": _signal_df()})
        assert result == 1.0

    def test_multiple_signals_same_day(self):
        """同一天多条信号频率 > 1"""
        metric = DailySignalFreq()
        df = pd.DataFrame({
            "code": ["000001", "000002", "000003"],
            "direction": [1, -1, 1],
            "timestamp": [
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-01-01"),
                pd.Timestamp("2024-01-01"),
            ],
        })
        result = metric.compute({"signal": df})
        assert result == 3.0

    def test_single_signal_single_day(self):
        """单条信号单天 = 1.0"""
        metric = DailySignalFreq()
        df = pd.DataFrame({
            "code": ["000001"],
            "direction": [1],
            "timestamp": [pd.Timestamp("2024-01-01")],
        })
        result = metric.compute({"signal": df})
        assert result == 1.0

    def test_empty_dataframe_returns_zero(self):
        """空DataFrame返回0"""
        metric = DailySignalFreq()
        df = pd.DataFrame(columns=["code", "direction", "timestamp"])
        result = metric.compute({"signal": df})
        assert result == 0.0

    def test_satisfies_metric_protocol(self):
        """满足Metric协议"""
        assert isinstance(DailySignalFreq(), Metric)

    def test_name_and_requires(self):
        """name和requires属性正确"""
        metric = DailySignalFreq()
        assert metric.name == "daily_signal_freq"
        assert metric.requires == ["signal"]
        assert metric.params == {}


# ============================================================
# DataProvider + MetricRegistry 集成测试
# ============================================================

@pytest.mark.unit
class TestSignalMetricsIntegration:
    """Signal 指标与 DataProvider / MetricRegistry 的集成测试"""

    def test_registry_register_and_instantiate(self):
        """三个Signal指标均可注册和实例化"""
        registry = MetricRegistry()
        registry.register(SignalCount)
        registry.register(LongShortRatio)
        registry.register(DailySignalFreq)

        assert "signal_count" in registry.list_metrics()
        assert "long_short_ratio" in registry.list_metrics()
        assert "daily_signal_freq" in registry.list_metrics()

        sc = registry.instantiate("signal_count")
        assert isinstance(sc, SignalCount)

    def test_check_availability_with_signal_data(self):
        """提供signal数据时三个指标全部available"""
        registry = MetricRegistry()
        registry.register(SignalCount)
        registry.register(LongShortRatio)
        registry.register(DailySignalFreq)

        dp = DataProvider(signal=_signal_df())
        available, missing = registry.check_availability(dp)
        assert len(available) == 3
        assert len(missing) == 0

    def test_check_availability_without_signal_data(self):
        """不提供signal数据时三个指标全部missing"""
        registry = MetricRegistry()
        registry.register(SignalCount)
        registry.register(LongShortRatio)
        registry.register(DailySignalFreq)

        dp = DataProvider()
        available, missing = registry.check_availability(dp)
        assert len(available) == 0
        assert len(missing) == 3
