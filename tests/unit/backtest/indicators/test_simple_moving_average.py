"""
Test cases for Simple Moving Average (SMA) indicator.
Tests cover basic calculation, edge cases, matrix operations, and performance.
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage


@pytest.mark.unit
@pytest.mark.indicator
class TestSimpleMovingAverageCalculation:
    """Test basic SMA calculation functionality."""

    def test_sma_basic_calculation(self, sample_prices_5):
        """Test basic SMA calculation with standard data."""
        result = SimpleMovingAverage.cal(5, sample_prices_5)
        expected = sum(sample_prices_5) / 5
        assert pytest.approx(result, rel=1e-6) == expected

    @pytest.mark.parametrize("period,expected_slice", [
        (3, slice(0, 3)),
        (5, slice(0, 5)),
        (10, slice(0, 10)),
    ])
    def test_sma_different_periods(self, sample_prices_5, sample_prices_10, period, expected_slice):
        """Test SMA calculation with different periods."""
        prices = sample_prices_10 if period == 10 else sample_prices_5
        relevant_prices = prices[expected_slice]
        result = SimpleMovingAverage.cal(period, relevant_prices)
        expected = sum(relevant_prices) / period
        assert pytest.approx(result, rel=1e-6) == expected

    def test_sma_single_price(self):
        """Test SMA with single price (period=1)."""
        result = SimpleMovingAverage.cal(1, [105.0])
        assert pytest.approx(result, rel=1e-6) == 105.0

    def test_sma_increasing_trend(self, sample_prices_5):
        """Test SMA with increasing trend."""
        result = SimpleMovingAverage.cal(5, sample_prices_5)
        # For increasing prices, SMA should be between min and max
        assert result > min(sample_prices_5)
        assert result < max(sample_prices_5)

    def test_sma_constant_prices(self, constant_prices):
        """Test SMA with constant prices."""
        result = SimpleMovingAverage.cal(5, constant_prices)
        assert pytest.approx(result, rel=1e-6) == 100.0


@pytest.mark.unit
@pytest.mark.indicator
class TestSimpleMovingAverageEdgeCases:
    """Test SMA behavior with edge cases and invalid inputs."""

    def test_sma_insufficient_data(self, sample_prices_5):
        """Test SMA with insufficient data points."""
        result = SimpleMovingAverage.cal(5, sample_prices_5[:3])
        assert pd.isna(result)

    def test_sma_excess_data(self, sample_prices_5):
        """Test SMA with too many data points."""
        result = SimpleMovingAverage.cal(3, sample_prices_5)
        assert pd.isna(result)

    def test_sma_with_nan(self, prices_with_nan):
        """Test SMA with NaN values in data."""
        result = SimpleMovingAverage.cal(5, prices_with_nan)
        assert pd.isna(result)

    def test_sma_zero_period(self, sample_prices_5):
        """Test SMA with zero period."""
        result = SimpleMovingAverage.cal(0, sample_prices_5)
        assert pd.isna(result)

    def test_sma_negative_period(self, sample_prices_5):
        """Test SMA with negative period."""
        result = SimpleMovingAverage.cal(-5, sample_prices_5)
        assert pd.isna(result)

    def test_sma_with_zero_prices(self, prices_with_zero):
        """Test SMA with zero prices."""
        result = SimpleMovingAverage.cal(5, prices_with_zero)
        expected = sum(prices_with_zero) / 5
        assert pytest.approx(result, rel=1e-6) == expected

    def test_sma_with_negative_prices(self, prices_with_negative):
        """Test SMA with negative prices (edge case)."""
        result = SimpleMovingAverage.cal(5, prices_with_negative)
        expected = sum(prices_with_negative) / 5
        assert pytest.approx(result, rel=1e-6) == expected

    def test_sma_extreme_small_prices(self, extreme_small_prices):
        """Test SMA with extremely small price values."""
        result = SimpleMovingAverage.cal(5, extreme_small_prices)
        assert not pd.isna(result)
        assert result > 0

    def test_sma_extreme_large_prices(self, extreme_large_prices):
        """Test SMA with extremely large price values."""
        result = SimpleMovingAverage.cal(5, extreme_large_prices)
        assert not pd.isna(result)
        assert result > 1e6


@pytest.mark.unit
@pytest.mark.indicator
class TestSimpleMovingAverageMatrix:
    """Test SMA matrix operations for multi-asset calculations."""

    def test_sma_matrix_wide_format(self, price_matrix_wide):
        """Test SMA calculation with wide format matrix."""
        period = 5
        result = SimpleMovingAverage.cal_matrix(period, price_matrix_wide)

        # Check result dimensions
        assert result.shape == price_matrix_wide.shape

        # First 4 rows should be NaN (insufficient data)
        assert pd.isna(result.iloc[0, 0])
        assert pd.isna(result.iloc[3, 0])

        # 5th row should have valid value
        expected_stock1 = sum(range(100, 105)) / 5
        assert pytest.approx(result.iloc[4, 0], rel=1e-6) == expected_stock1

    def test_sma_matrix_empty_data(self):
        """Test SMA with empty matrix."""
        empty_matrix = pd.DataFrame()
        result = SimpleMovingAverage.cal_matrix(5, empty_matrix)
        assert result.empty

    def test_sma_matrix_insufficient_data(self):
        """Test SMA matrix with insufficient data per column."""
        small_matrix = pd.DataFrame({
            'stock1': [100, 101, 102],
            'stock2': [200, 201, 202]
        })

        result = SimpleMovingAverage.cal_matrix(5, small_matrix)

        # All values should be NaN due to insufficient data
        assert pd.isna(result.iloc[0, 0])
        assert pd.isna(result.iloc[1, 0])
        assert pd.isna(result.iloc[2, 0])

    def test_sma_matrix_multiple_periods(self, price_matrix_wide):
        """Test SMA matrix with different periods."""
        for period in [3, 5, 7]:
            result = SimpleMovingAverage.cal_matrix(period, price_matrix_wide)
            assert result.shape == price_matrix_wide.shape
            # First (period-1) rows should be NaN
            for i in range(period - 1):
                assert pd.isna(result.iloc[i, 0])


@pytest.mark.slow
@pytest.mark.indicator
class TestSimpleMovingAveragePerformance:
    """Test SMA calculation performance."""

    def test_sma_calculation_speed(self, large_price_series):
        """Test SMA calculation performance with large dataset."""
        import time

        period = 20
        iterations = 100

        start_time = time.time()
        for _ in range(iterations):
            result = SimpleMovingAverage.cal(period, large_price_series[-period:])
        end_time = time.time()

        # 100 calculations should complete in 1 second
        assert end_time - start_time < 1.0
        assert not pd.isna(result)

    def test_sma_matrix_performance(self, price_matrix_wide):
        """Test SMA matrix calculation performance."""
        import time

        start_time = time.time()
        for _ in range(50):
            result = SimpleMovingAverage.cal_matrix(5, price_matrix_wide)
        end_time = time.time()

        # 50 matrix calculations should complete in 0.5 seconds
        assert end_time - start_time < 0.5
        assert not result.empty


@pytest.mark.unit
@pytest.mark.indicator
class TestSimpleMovingAverageFinancialAccuracy:
    """Test SMA financial calculation accuracy and precision."""

    @pytest.mark.parametrize("prices,period,expected", [
        ([100.0, 101.0, 102.0, 103.0, 104.0], 5, 102.0),
        ([10.5, 10.6, 10.7, 10.8, 10.9], 5, 10.7),
        ([1000.0, 1001.0, 1002.0, 1003.0, 1004.0], 5, 1002.0),
    ])
    def test_sma_financial_precision(self, prices, period, expected):
        """Test SMA maintains financial precision."""
        result = SimpleMovingAverage.cal(period, prices)
        assert pytest.approx(result, rel=1e-6) == expected

    def test_sma_decimal_places_consistency(self, sample_prices_5):
        """Test SMA calculation maintains decimal consistency."""
        result = SimpleMovingAverage.cal(5, sample_prices_5)
        # Should have reasonable decimal precision
        assert isinstance(result, (float, np.floating))
        assert not pd.isna(result)


@pytest.mark.unit
@pytest.mark.indicator
class TestSimpleMovingAverageBoundaryValues:
    """Test SMA behavior at boundary conditions."""

    @pytest.mark.parametrize("period", [1, 2, 3, 5, 10, 20, 50, 100])
    def test_sma_various_periods(self, period):
        """Test SMA works with various common periods."""
        prices = [100.0 + i for i in range(period)]
        result = SimpleMovingAverage.cal(period, prices)
        expected = sum(prices) / period
        assert pytest.approx(result, rel=1e-6) == expected

    def test_sma_minimum_period(self):
        """Test SMA with minimum valid period (1)."""
        result = SimpleMovingAverage.cal(1, [105.0])
        assert pytest.approx(result, rel=1e-6) == 105.0

    def test_sma_large_period(self):
        """Test SMA with large period."""
        period = 100
        prices = [100.0 + i for i in range(period)]
        result = SimpleMovingAverage.cal(period, prices)
        expected = sum(prices) / period
        assert pytest.approx(result, rel=1e-6) == expected
