"""
性能: 158MB RSS, 0.89s, 16 tests [PASS]
"""

#!/usr/bin/env python3
"""
Test cases for Bollinger Bands
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.bollinger_bands import BollingerBands


@pytest.fixture
def bb_data():
    """Bollinger Bands test data"""
    return {
        "prices_5": [100.0, 101.0, 102.0, 103.0, 104.0],
        "prices_20": [100.0 + i * 0.5 for i in range(20)],
        "volatile": [100.0, 105.0, 95.0, 110.0, 90.0],
    }


def test_bollinger_bands_basic_calculation(bb_data):
    """测试基本布林带计算"""
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, bb_data["prices_5"])

    expected_middle = sum(bb_data["prices_5"]) / 5
    assert middle == pytest.approx(expected_middle, abs=1e-6)
    assert upper > middle
    assert lower < middle
    assert 0.0 <= position <= 1.0
    assert not any(pd.isna(val) for val in [upper, middle, lower, position])


def test_bollinger_bands_return_type(bb_data):
    """测试返回值类型"""
    result = BollingerBands.cal(5, 2.0, bb_data["prices_5"])
    assert isinstance(result, tuple)
    assert len(result) == 4
    for val in result:
        assert isinstance(val, (int, float))


def test_bollinger_bands_no_volatility():
    """测试无波动的情况"""
    constant_prices = [100.0] * 5
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, constant_prices)

    assert upper == pytest.approx(middle, abs=1e-6)
    assert lower == pytest.approx(middle, abs=1e-6)
    assert middle == pytest.approx(100.0, abs=1e-6)
    assert position == pytest.approx(0.5, abs=1e-6)


def test_bollinger_bands_high_volatility(bb_data):
    """测试高波动情况"""
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, bb_data["volatile"])

    band_width = upper - lower
    assert band_width > 10.0
    assert 0.0 <= position <= 1.0


def test_bollinger_bands_different_std_multipliers(bb_data):
    """测试不同标准差倍数"""
    upper_1, middle_1, lower_1, pos_1 = BollingerBands.cal(5, 1.0, bb_data["prices_5"])
    upper_2, middle_2, lower_2, pos_2 = BollingerBands.cal(5, 2.0, bb_data["prices_5"])
    upper_3, middle_3, lower_3, pos_3 = BollingerBands.cal(5, 3.0, bb_data["prices_5"])

    assert middle_1 == pytest.approx(middle_2, abs=1e-6)
    assert middle_2 == pytest.approx(middle_3, abs=1e-6)

    assert (upper_3 - lower_3) > (upper_2 - lower_2)
    assert (upper_2 - lower_2) > (upper_1 - lower_1)

    assert upper_3 > upper_2
    assert upper_2 > upper_1
    assert lower_3 < lower_2
    assert lower_2 < lower_1


def test_bollinger_bands_position_calculation():
    """测试价格位置计算"""
    # 价格在下轨
    prices_at_lower = [95.0, 96.0, 97.0, 98.0, 95.0]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_at_lower)
    assert position < 0.3

    # 价格在上轨
    prices_at_upper = [100.0, 101.0, 102.0, 103.0, 105.0]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_at_upper)
    assert position > 0.7


def test_bollinger_bands_wrong_length():
    """测试错误数据长度"""
    # 数据不足
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, [100.0, 101.0, 102.0])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])

    # 数据过多
    upper, middle, lower, position = BollingerBands.cal(3, 2.0, [100.0, 101.0, 102.0, 103.0, 104.0])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])


def test_bollinger_bands_with_nan():
    """测试包含NaN的数据"""
    prices_with_nan = [100.0, float("nan"), 102.0, 103.0, 104.0]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_with_nan)
    assert all(pd.isna(val) for val in [upper, middle, lower, position])


def test_bollinger_bands_invalid_parameters(bb_data):
    """测试无效参数"""
    # 周期为0
    upper, middle, lower, position = BollingerBands.cal(0, 2.0, bb_data["prices_5"])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])

    # 负周期
    upper, middle, lower, position = BollingerBands.cal(-5, 2.0, bb_data["prices_5"])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])

    # 标准差倍数为0
    upper, middle, lower, position = BollingerBands.cal(5, 0.0, bb_data["prices_5"])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])

    # 负标准差倍数
    upper, middle, lower, position = BollingerBands.cal(5, -2.0, bb_data["prices_5"])
    assert all(pd.isna(val) for val in [upper, middle, lower, position])


def test_bollinger_bands_mathematical_properties(bb_data):
    """测试布林带的数学特性"""
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, bb_data["prices_5"])

    mean_price = sum(bb_data["prices_5"]) / 5
    variance = sum((p - mean_price) ** 2 for p in bb_data["prices_5"]) / 5
    std_dev = variance**0.5

    expected_upper = mean_price + 2.0 * std_dev
    expected_lower = mean_price - 2.0 * std_dev

    assert upper == pytest.approx(expected_upper, abs=1e-6)
    assert lower == pytest.approx(expected_lower, abs=1e-6)
    assert middle == pytest.approx(mean_price, abs=1e-6)


def test_bollinger_bands_position_edge_cases():
    """测试位置计算的边界情况"""
    # 价格恰好在上轨
    prices = [100.0, 100.0, 100.0, 100.0, 110.0]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices)
    assert position > 0.8

    # 价格恰好在下轨附近
    prices_low = [100.0, 100.0, 100.0, 100.0, 90.0]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, prices_low)
    assert position < 0.2


def test_bollinger_bands_vs_sma(bb_data):
    """测试布林带中轨与SMA的一致性"""
    from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage

    upper, middle, lower, position = BollingerBands.cal(5, 2.0, bb_data["prices_5"])
    sma_result = SimpleMovingAverage.cal(5, bb_data["prices_5"])
    assert middle == pytest.approx(sma_result, abs=1e-6)


def test_bollinger_bands_matrix_calculation():
    """测试布林带矩阵计算"""
    dates = pd.date_range("2023-01-01", periods=25)
    data = {
        "stock1": [100 + i * 0.5 + np.random.normal(0, 1) for i in range(25)],
        "stock2": [200 + i * 0.3 + np.random.normal(0, 0.5) for i in range(25)],
    }
    matrix = pd.DataFrame(data, index=dates)

    result = BollingerBands.cal_matrix(20, 2.0, matrix)

    assert result.shape == matrix.shape
    assert not result.empty


def test_bollinger_bands_extreme_values():
    """测试极值情况"""
    # 极小数值
    small_prices = [0.001, 0.002, 0.003, 0.004, 0.005]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, small_prices)
    assert not any(pd.isna(val) for val in [upper, middle, lower, position])
    assert upper > middle
    assert lower < middle

    # 极大数值
    large_prices = [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]
    upper, middle, lower, position = BollingerBands.cal(5, 2.0, large_prices)
    assert not any(pd.isna(val) for val in [upper, middle, lower, position])
    assert upper > middle
    assert lower < middle


def test_bollinger_bands_realistic_scenario():
    """测试真实场景"""
    np.random.seed(42)
    realistic_prices = []
    base_price = 100.0

    for i in range(20):
        trend = i * 0.2
        noise = np.random.normal(0, 1)
        price = base_price + trend + noise
        realistic_prices.append(price)

    upper, middle, lower, position = BollingerBands.cal(20, 2.0, realistic_prices)

    assert not any(pd.isna(val) for val in [upper, middle, lower, position])
    assert upper > middle
    assert lower < middle
    assert 0.0 <= position <= 1.0

    band_width = upper - lower
    assert band_width > 0
    assert band_width < 50


def test_bollinger_bands_performance():
    """测试性能"""
    import time

    large_prices = [100.0 + i * 0.1 + np.random.normal(0, 0.5) for i in range(1000)]

    start_time = time.time()
    for _ in range(100):
        result = BollingerBands.cal(20, 2.0, large_prices[-20:])
    end_time = time.time()

    assert end_time - start_time < 1.0
    assert not any(pd.isna(val) for val in result)
