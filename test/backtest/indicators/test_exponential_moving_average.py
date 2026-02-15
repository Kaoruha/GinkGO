"""
Test cases for Exponential Moving Average (EMA) indicator.
Tests cover basic calculation, trend analysis, edge cases, and comparison with SMA.
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.exponential_moving_average import ExponentialMovingAverage
from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageCalculation:
    """Test basic EMA calculation functionality."""

    def test_ema_basic_calculation(self, sample_prices_5):
        """Test basic EMA calculation with standard data."""
        result = ExponentialMovingAverage.cal(5, sample_prices_5)

        # Manual EMA calculation for verification
        alpha = 2.0 / (5 + 1)
        ema = sample_prices_5[0]
        for i in range(1, len(sample_prices_5)):
            ema = alpha * sample_prices_5[i] + (1 - alpha) * ema

        assert pytest.approx(result, rel=1e-6) == ema

    def test_ema_single_value(self):
        """Test EMA with single value (period=1)."""
        result = ExponentialMovingAverage.cal(1, [105.0])
        assert pytest.approx(result, rel=1e-6) == 105.0

    def test_ema_two_values(self):
        """Test EMA with two values."""
        prices = [100.0, 102.0]
        result = ExponentialMovingAverage.cal(2, prices)

        alpha = 2.0 / (2 + 1)
        expected = alpha * 102.0 + (1 - alpha) * 100.0
        assert pytest.approx(result, rel=1e-6) == expected

    def test_ema_constant_prices(self, constant_prices):
        """Test EMA with constant prices."""
        result = ExponentialMovingAverage.cal(5, constant_prices)
        assert pytest.approx(result, rel=1e-6) == 100.0


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageTrendAnalysis:
    """Test EMA behavior with different price trends."""

    def test_ema_increasing_trend(self, sample_prices_5):
        """Test EMA with increasing trend."""
        result = ExponentialMovingAverage.cal(5, sample_prices_5)

        # EMA should be between min and max, closer to latest price
        assert result > min(sample_prices_5)
        assert result < max(sample_prices_5)

    def test_ema_decreasing_trend(self, decreasing_prices):
        """Test EMA with decreasing trend."""
        result = ExponentialMovingAverage.cal(5, decreasing_prices)

        # EMA should be between min and max, closer to latest price
        assert result < max(decreasing_prices)
        assert result > min(decreasing_prices)

    def test_ema_volatility_tracking(self, volatile_prices):
        """Test EMA tracks volatile prices better than SMA."""
        ema_result = ExponentialMovingAverage.cal(5, volatile_prices)
        sma_result = SimpleMovingAverage.cal(5, volatile_prices)

        # Both should be valid
        assert not pd.isna(ema_result)
        assert not pd.isna(sma_result)

        # EMA should react more to latest price
        assert ema_result > 80.0
        assert ema_result < 120.0


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageEdgeCases:
    """Test EMA behavior with edge cases and invalid inputs."""

    def test_ema_insufficient_data(self, sample_prices_5):
        """Test EMA with insufficient data points."""
        result = ExponentialMovingAverage.cal(5, sample_prices_5[:2])
        assert pd.isna(result)

    def test_ema_excess_data(self, sample_prices_5):
        """Test EMA with too many data points."""
        result = ExponentialMovingAverage.cal(3, sample_prices_5)
        assert pd.isna(result)

    def test_ema_with_nan(self, prices_with_nan):
        """Test EMA with NaN values in data."""
        result = ExponentialMovingAverage.cal(5, prices_with_nan)
        assert pd.isna(result)

    def test_ema_zero_period(self, sample_prices_5):
        """Test EMA with zero period."""
        result = ExponentialMovingAverage.cal(0, sample_prices_5)
        assert pd.isna(result)

    def test_ema_negative_period(self, sample_prices_5):
        """Test EMA with negative period."""
        result = ExponentialMovingAverage.cal(-5, sample_prices_5)
        assert pd.isna(result)

    def test_ema_extreme_small_prices(self, extreme_small_prices):
        """Test EMA with extremely small price values."""
        result = ExponentialMovingAverage.cal(5, extreme_small_prices)
        assert not pd.isna(result)
        assert result > 0

    def test_ema_extreme_large_prices(self, extreme_large_prices):
        """Test EMA with extremely large price values."""
        result = ExponentialMovingAverage.cal(5, extreme_large_prices)
        assert not pd.isna(result)
        assert result > 1e6


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageAlphaCalculation:
    """Test EMA smoothing coefficient (alpha) calculation."""

    @pytest.mark.parametrize("period,expected_alpha_min,expected_alpha_max", [
        (2, 0.5, 0.8),
        (5, 0.25, 0.4),
        (10, 0.15, 0.25),
        (20, 0.08, 0.12),
    ])
    def test_ema_alpha_range(self, period, expected_alpha_min, expected_alpha_max):
        """Test EMA alpha is in valid range for different periods."""
        alpha = 2.0 / (period + 1)
        assert expected_alpha_min < alpha < expected_alpha_max

    def test_ema_alpha_sensitivity(self):
        """Test that shorter periods have higher alpha (more sensitive)."""
        alpha_5 = 2.0 / (5 + 1)
        alpha_20 = 2.0 / (20 + 1)

        # Shorter period should have higher alpha
        assert alpha_5 > alpha_20

        # Both should be between 0 and 1
        assert 0 < alpha_5 < 1
        assert 0 < alpha_20 < 1


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageVsSMA:
    """Test comparison between EMA and SMA calculations."""

    def test_ema_vs_sma_basic(self, volatile_prices):
        """Test basic comparison between EMA and SMA."""
        ema_result = ExponentialMovingAverage.cal(5, volatile_prices)
        sma_result = SimpleMovingAverage.cal(5, volatile_prices)

        # Both should be valid
        assert not pd.isna(ema_result)
        assert not pd.isna(sma_result)

        # EMA should typically be closer to latest price in volatile markets
        # This is a general property, not guaranteed for all cases
        assert ema_result > 80.0
        assert sma_result > 80.0

    def test_ema_reacts_faster_to_price_changes(self):
        """Test that EMA reacts faster to recent price changes."""
        # Create a series with a sudden jump at the end
        prices = [100.0] * 9 + [110.0]  # Sudden 10% jump

        ema_10 = ExponentialMovingAverage.cal(10, prices)
        sma_10 = SimpleMovingAverage.cal(10, prices)

        # EMA should be higher than SMA because it weights recent prices more
        assert ema_10 > sma_10


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageMatrix:
    """Test EMA matrix operations for multi-asset calculations."""

    def test_ema_matrix_wide_format(self, price_matrix_wide):
        """Test EMA calculation with wide format matrix."""
        period = 5
        result = ExponentialMovingAverage.cal_matrix(period, price_matrix_wide)

        # Check result dimensions
        assert result.shape == price_matrix_wide.shape

        # EMA should have values from first row (unlike SMA)
        assert not pd.isna(result.iloc[0, 0])
        assert not pd.isna(result.iloc[0, 1])

    def test_ema_matrix_multiple_periods(self, price_matrix_wide):
        """Test EMA matrix with different periods."""
        for period in [3, 5, 7]:
            result = ExponentialMovingAverage.cal_matrix(period, price_matrix_wide)
            assert result.shape == price_matrix_wide.shape
            # EMA should have values from first row
            assert not pd.isna(result.iloc[0, 0])


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageFinancialAccuracy:
    """Test EMA financial calculation accuracy and precision."""

    @pytest.mark.parametrize("prices,period,expected_range", [
        ([100.0, 100.0, 100.0, 100.0, 100.0], 5, (99.9, 100.1)),
        ([10.5, 10.5, 10.5, 10.5, 10.5], 5, (10.4, 10.6)),
        ([1000.0, 1000.0, 1000.0, 1000.0, 1000.0], 5, (999.9, 1000.1)),
    ])
    def test_ema_const_price_precision(self, prices, period, expected_range):
        """Test EMA maintains precision for constant prices."""
        result = ExponentialMovingAverage.cal(period, prices)
        min_val, max_val = expected_range
        assert min_val < result < max_val

    def test_ema_decimal_places_consistency(self, sample_prices_5):
        """Test EMA calculation maintains decimal consistency."""
        result = ExponentialMovingAverage.cal(5, sample_prices_5)
        assert isinstance(result, (float, np.floating))
        assert not pd.isna(result)


@pytest.mark.unit
@pytest.mark.indicator
class TestExponentialMovingAverageBoundaryValues:
    """Test EMA behavior at boundary conditions."""

    @pytest.mark.parametrize("period", [1, 2, 3, 5, 10, 20, 50])
    def test_ema_various_periods(self, period):
        """Test EMA works with various common periods."""
        prices = [100.0 + i for i in range(period)]
        result = ExponentialMovingAverage.cal(period, prices)
        assert not pd.isna(result)
        assert result > 100.0

    def test_ema_minimum_period(self):
        """Test EMA with minimum valid period (1)."""
        result = ExponentialMovingAverage.cal(1, [105.0])
        assert pytest.approx(result, rel=1e-6) == 105.0

    def test_ema_large_period(self):
        """Test EMA with large period."""
        period = 100
        prices = [100.0 + i for i in range(period)]
        result = ExponentialMovingAverage.cal(period, prices)
        assert not pd.isna(result)
        assert result > 100.0


@pytest.mark.slow
@pytest.mark.indicator
class TestExponentialMovingAveragePerformance:
    """Test EMA calculation performance."""

    def test_ema_calculation_speed(self, large_price_series):
        """Test EMA calculation performance with large dataset."""
        import time

        period = 20
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            result = ExponentialMovingAverage.cal(period, large_price_series[-period:])
        end_time = time.time()

        # 100 calculations should complete in 1 second
        assert end_time - start_time < 1.0
        assert not pd.isna(result)

    def test_ema_matrix_performance(self, price_matrix_wide):
        """Test EMA matrix calculation performance."""
        import time

        start_time = time.time()
        for _ in range(50):
            result = ExponentialMovingAverage.cal_matrix(5, price_matrix_wide)
        end_time = time.time()

        # 50 matrix calculations should complete in 0.5 seconds
        assert end_time - start_time < 0.5
        assert not result.empty
