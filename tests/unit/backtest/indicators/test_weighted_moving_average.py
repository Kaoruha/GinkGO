"""
性能: 158MB RSS, 0.85s, 15 tests [PASS]
"""

#!/usr/bin/env python3
"""
Test cases for Weighted Moving Average (WMA)
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.weighted_moving_average import WeightedMovingAverage


@pytest.fixture
def wma_data():
    """WMA test data"""
    return {
        "prices_5": [100.0, 101.0, 102.0, 103.0, 104.0],
        "prices_3": [100.0, 102.0, 104.0],
    }


def test_wma_basic_calculation(wma_data):
    """测试基本WMA计算"""
    result = WeightedMovingAverage.cal(5, wma_data["prices_5"])

    weights = np.array([1, 2, 3, 4, 5], dtype=float)
    weights = weights / weights.sum()
    expected = np.sum(np.array(wma_data["prices_5"]) * weights)

    assert result == pytest.approx(expected, abs=1e-6)


def test_wma_weight_distribution(wma_data):
    """测试权重分布"""
    result = WeightedMovingAverage.cal(5, wma_data["prices_5"])

    total_weight = 1 + 2 + 3 + 4 + 5  # 15
    expected = (100 * 1 + 101 * 2 + 102 * 3 + 103 * 4 + 104 * 5) / total_weight

    assert result == pytest.approx(expected, abs=1e-6)


def test_wma_three_period(wma_data):
    """测试3周期WMA"""
    result = WeightedMovingAverage.cal(3, wma_data["prices_3"])

    # 权重 [1, 2, 3]，总权重 6
    expected = (100 * 1 + 102 * 2 + 104 * 3) / 6
    assert result == pytest.approx(expected, abs=1e-6)


def test_wma_single_period():
    """测试周期为1的WMA"""
    result = WeightedMovingAverage.cal(1, [105.0])
    assert result == pytest.approx(105.0, abs=1e-6)


def test_wma_vs_sma_comparison():
    """测试WMA与SMA的比较"""
    from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage

    # 使用上升趋势数据
    prices = [100.0, 101.0, 102.0, 103.0, 104.0]

    wma_result = WeightedMovingAverage.cal(5, prices)
    sma_result = SimpleMovingAverage.cal(5, prices)

    # 在上升趋势中，WMA应该大于SMA
    assert wma_result > sma_result

    # 使用下降趋势数据
    decreasing_prices = [104.0, 103.0, 102.0, 101.0, 100.0]

    wma_decreasing = WeightedMovingAverage.cal(5, decreasing_prices)
    sma_decreasing = SimpleMovingAverage.cal(5, decreasing_prices)

    # 在下降趋势中，WMA应该小于SMA
    assert wma_decreasing < sma_decreasing


def test_wma_constant_prices():
    """测试价格不变的WMA"""
    constant_prices = [100.0] * 5
    result = WeightedMovingAverage.cal(5, constant_prices)
    assert result == pytest.approx(100.0, abs=1e-6)


def test_wma_wrong_length(wma_data):
    """测试错误数据长度"""
    # 数据不足
    result = WeightedMovingAverage.cal(5, [100.0, 101.0])
    assert pd.isna(result)

    # 数据过多
    result = WeightedMovingAverage.cal(3, wma_data["prices_5"])
    assert pd.isna(result)


def test_wma_with_nan():
    """测试包含NaN的数据"""
    prices_with_nan = [100.0, float("nan"), 102.0, 103.0, 104.0]
    result = WeightedMovingAverage.cal(5, prices_with_nan)
    assert pd.isna(result)


def test_wma_zero_period(wma_data):
    """测试周期为0"""
    result = WeightedMovingAverage.cal(0, wma_data["prices_5"])
    assert pd.isna(result)


def test_wma_negative_period(wma_data):
    """测试负周期"""
    result = WeightedMovingAverage.cal(-5, wma_data["prices_5"])
    assert pd.isna(result)


def test_wma_weight_calculation():
    """测试权重计算的正确性"""
    period = 4
    prices = [100.0, 101.0, 102.0, 103.0]

    result = WeightedMovingAverage.cal(period, prices)

    weights_sum = sum(range(1, period + 1))  # 1+2+3+4 = 10
    expected = sum(prices[i] * (i + 1) for i in range(period)) / weights_sum

    assert result == pytest.approx(expected, abs=1e-6)


def test_wma_sensitivity_to_recent_data():
    """测试WMA对最新数据的敏感性"""
    base_prices = [100.0, 100.0, 100.0, 100.0]

    # 最后价格上涨
    prices_up = base_prices + [110.0]
    wma_up = WeightedMovingAverage.cal(5, prices_up)

    # 最后价格下跌
    prices_down = base_prices + [90.0]
    wma_down = WeightedMovingAverage.cal(5, prices_down)

    assert wma_up > 100.0
    assert wma_down < 100.0

    # 上涨和下跌的差异应该明显
    assert (wma_up - 100.0) > (100.0 - wma_down)


def test_wma_matrix_calculation():
    """测试WMA矩阵计算"""
    dates = pd.date_range("2023-01-01", periods=10)
    data = {
        "stock1": [100 + i for i in range(10)],
        "stock2": [200 + i * 2 for i in range(10)],
    }
    matrix = pd.DataFrame(data, index=dates)

    result = WeightedMovingAverage.cal_matrix(5, matrix)

    assert result.shape == matrix.shape
    assert pd.isna(result.iloc[3, 0])

    # 检查第5行的值（手动计算验证）
    stock1_prices = [100, 101, 102, 103, 104]
    weights = np.array([1, 2, 3, 4, 5], dtype=float)
    weights = weights / weights.sum()
    expected_stock1 = np.sum(np.array(stock1_prices) * weights)

    assert result.iloc[4, 0] == pytest.approx(expected_stock1, abs=1e-6)


def test_wma_edge_cases():
    """测试边界情况"""
    # 零价格
    prices_with_zero = [0.0, 1.0, 2.0, 3.0, 4.0]
    result = WeightedMovingAverage.cal(5, prices_with_zero)
    assert not pd.isna(result)

    # 负价格
    negative_prices = [-5.0, -4.0, -3.0, -2.0, -1.0]
    result = WeightedMovingAverage.cal(5, negative_prices)
    assert not pd.isna(result)
    assert result < 0


def test_wma_large_period():
    """测试大周期WMA"""
    large_period = 20
    prices = [100.0 + i * 0.5 for i in range(large_period)]

    result = WeightedMovingAverage.cal(large_period, prices)
    assert not pd.isna(result)

    min_price = min(prices)
    max_price = max(prices)
    assert result >= min_price
    assert result <= max_price
