"""
性能: 159MB RSS, 0.87s, 15 tests [PASS]
"""

#!/usr/bin/env python3
"""
Test cases for Average True Range (ATR)
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.average_true_range import AverageTrueRange


@pytest.fixture
def atr_data():
    """ATR test data: (high_prices, low_prices, close_prices, simple variants)"""
    high_prices = [105.0] + [105.0 + i for i in range(1, 15)]
    low_prices = [95.0] + [95.0 + i for i in range(1, 15)]
    close_prices = [100.0] + [100.0 + i for i in range(1, 15)]
    simple_high = [102.0, 103.0, 104.0, 105.0, 106.0, 107.0]
    simple_low = [98.0, 99.0, 100.0, 101.0, 102.0, 103.0]
    simple_close = [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]
    return {
        "high": high_prices,
        "low": low_prices,
        "close": close_prices,
        "simple_high": simple_high,
        "simple_low": simple_low,
        "simple_close": simple_close,
    }


def test_atr_basic_calculation(atr_data):
    """测试基本ATR计算"""
    result = AverageTrueRange.cal(
        14, atr_data["high"], atr_data["low"], atr_data["close"]
    )
    assert result > 0
    assert not pd.isna(result)


def test_atr_simple_case(atr_data):
    """测试简单情况的ATR计算"""
    result = AverageTrueRange.cal(
        5,
        atr_data["simple_high"],
        atr_data["simple_low"],
        atr_data["simple_close"],
    )
    assert result == pytest.approx(4.0, abs=1e-6)


def test_atr_with_gaps():
    """测试有跳空的ATR计算"""
    high_with_gap = [102.0, 110.0, 111.0, 112.0, 113.0, 114.0]
    low_with_gap = [98.0, 108.0, 109.0, 110.0, 111.0, 112.0]
    close_with_gap = [100.0, 109.0, 110.0, 111.0, 112.0, 113.0]

    result = AverageTrueRange.cal(5, high_with_gap, low_with_gap, close_with_gap)
    assert result > 3.0
    assert not pd.isna(result)


def test_atr_no_volatility():
    """测试无波动的情况"""
    constant_high = [100.0] * 6
    constant_low = [100.0] * 6
    constant_close = [100.0] * 6

    result = AverageTrueRange.cal(5, constant_high, constant_low, constant_close)
    assert result == pytest.approx(0.0, abs=1e-6)


def test_atr_wrong_length(atr_data):
    """测试错误数据长度"""
    # 数据不足
    result = AverageTrueRange.cal(
        14,
        atr_data["simple_high"],
        atr_data["simple_low"],
        atr_data["simple_close"],
    )
    assert pd.isna(result)

    # 数据过多
    result = AverageTrueRange.cal(
        3, atr_data["high"], atr_data["low"], atr_data["close"]
    )
    assert pd.isna(result)


def test_atr_mismatched_lengths(atr_data):
    """测试数据长度不匹配"""
    high_short = [105.0, 106.0, 107.0]
    result = AverageTrueRange.cal(14, high_short, atr_data["low"], atr_data["close"])
    assert pd.isna(result)


def test_atr_with_nan(atr_data):
    """测试包含NaN的数据"""
    high_with_nan = atr_data["high"].copy()
    high_with_nan[5] = float("nan")

    result = AverageTrueRange.cal(
        14, high_with_nan, atr_data["low"], atr_data["close"]
    )
    assert pd.isna(result)


def test_atr_zero_period(atr_data):
    """测试周期为0"""
    result = AverageTrueRange.cal(0, atr_data["high"], atr_data["low"], atr_data["close"])
    assert pd.isna(result)


def test_atr_negative_period(atr_data):
    """测试负周期"""
    result = AverageTrueRange.cal(-5, atr_data["high"], atr_data["low"], atr_data["close"])
    assert pd.isna(result)


def test_atr_true_range_components():
    """测试真实范围的三个组成部分"""

    # 情况1：当日高低差最大
    high_case1 = [100.0, 110.0]
    low_case1 = [100.0, 100.0]
    close_case1 = [100.0, 105.0]

    result1 = AverageTrueRange.cal(1, high_case1, low_case1, close_case1)
    assert result1 == pytest.approx(10.0, abs=1e-6)

    # 情况2：当日高价与前收差最大
    high_case2 = [100.0, 115.0]
    low_case2 = [100.0, 110.0]
    close_case2 = [100.0, 112.0]

    result2 = AverageTrueRange.cal(1, high_case2, low_case2, close_case2)
    assert result2 == pytest.approx(15.0, abs=1e-6)

    # 情况3：当日低价与前收差最大
    high_case3 = [100.0, 95.0]
    low_case3 = [100.0, 90.0]
    close_case3 = [100.0, 92.0]

    result3 = AverageTrueRange.cal(1, high_case3, low_case3, close_case3)
    assert result3 == pytest.approx(10.0, abs=1e-6)


def test_atr_increasing_volatility():
    """测试递增波动率"""
    high_increasing = [100.0]
    low_increasing = [100.0]
    close_increasing = [100.0]

    for i in range(1, 15):
        volatility = i
        high_increasing.append(100.0 + volatility)
        low_increasing.append(100.0 - volatility)
        close_increasing.append(100.0)

    result = AverageTrueRange.cal(14, high_increasing, low_increasing, close_increasing)
    assert result > 10.0
    assert result <= 15.0


def test_atr_matrix_calculation():
    """测试ATR矩阵计算"""
    data = []
    stocks = ["STOCK_A", "STOCK_B"]
    dates = pd.date_range("2023-01-01", periods=20)

    for stock in stocks:
        for i, date in enumerate(dates):
            data.append(
                {
                    "code": stock,
                    "timestamp": date,
                    "high": 100.0 + i + 2,
                    "low": 100.0 + i - 2,
                    "close": 100.0 + i,
                    "volume": 1000,
                }
            )

    long_format_data = pd.DataFrame(data)
    result = AverageTrueRange.cal_matrix(5, long_format_data)

    assert "atr" in result.columns

    valid_atr = result["atr"].dropna()
    for atr_val in valid_atr:
        assert atr_val > 0


def test_atr_edge_cases():
    """测试边界情况"""
    # 极小数值
    small_high = [0.001, 0.002, 0.003, 0.004, 0.005, 0.006]
    small_low = [0.0005, 0.0015, 0.0025, 0.0035, 0.0045, 0.0055]
    small_close = [0.0008, 0.0018, 0.0028, 0.0038, 0.0048, 0.0058]

    result = AverageTrueRange.cal(5, small_high, small_low, small_close)
    assert result > 0
    assert not pd.isna(result)

    # 极大数值
    large_high = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6, 1.5e6]
    large_low = [0.9e6, 1.0e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
    large_close = [0.95e6, 1.05e6, 1.15e6, 1.25e6, 1.35e6, 1.45e6]

    result = AverageTrueRange.cal(5, large_high, large_low, large_close)
    assert result > 0
    assert not pd.isna(result)


def test_atr_realistic_data():
    """测试真实市场数据模拟"""
    np.random.seed(42)

    high_realistic = [100.0]
    low_realistic = [100.0]
    close_realistic = [100.0]

    for i in range(14):
        daily_range = np.random.uniform(1.0, 5.0)
        prev_close = close_realistic[-1]
        gap = np.random.normal(0, 0.5)
        open_price = prev_close + gap
        high_price = open_price + np.random.uniform(0, daily_range)
        low_price = open_price - np.random.uniform(0, daily_range)
        close_price = np.random.uniform(low_price, high_price)

        high_realistic.append(high_price)
        low_realistic.append(low_price)
        close_realistic.append(close_price)

    result = AverageTrueRange.cal(14, high_realistic, low_realistic, close_realistic)
    assert result > 0.5
    assert result < 10.0


def test_atr_performance():
    """测试ATR计算性能"""
    import time

    large_high = [100.0 + i + 2 for i in range(500)]
    large_low = [100.0 + i - 2 for i in range(500)]
    large_close = [100.0 + i for i in range(500)]

    start_time = time.time()
    for _ in range(50):
        result = AverageTrueRange.cal(
            14, large_high[-15:], large_low[-15:], large_close[-15:]
        )
    end_time = time.time()

    assert end_time - start_time < 0.5
    assert not pd.isna(result)
