"""
Test cases for Relative Strength Index (RSI) indicator.
Tests cover calculation logic, boundary conditions, edge cases, and matrix operations.
"""

import pytest
import pandas as pd
import numpy as np

from ginkgo.trading.computation.technical.relative_strength_index import RelativeStrengthIndex


@pytest.mark.unit
@pytest.mark.indicator
class TestRSIBasicCalculation:
    """Test basic RSI calculation functionality."""

    def test_rsi_basic_calculation(self, sample_prices_rsi14):
        """Test basic RSI calculation with standard data."""
        result = RelativeStrengthIndex.cal(14, sample_prices_rsi14)

        # All changes are positive, RSI should be high
        assert result > 90
        assert result <= 100
        assert not pd.isna(result)

    def test_rsi_period_5(self, sample_prices_rsi5):
        """Test RSI with period 5."""
        result = RelativeStrengthIndex.cal(5, sample_prices_rsi5)

        # Should return valid value
        assert not pd.isna(result)
        assert 0 <= result <= 100

    def test_rsi_no_change(self):
        """Test RSI when prices don't change."""
        constant_prices = [100.0] * 15
        result = RelativeStrengthIndex.cal(14, constant_prices)

        # No change means RSI should be 50 (neutral)
        assert pytest.approx(result, abs=0.1) == 50.0

    def test_rsi_calculation_logic(self):
        """Test RSI calculation logic with known data."""
        prices = [100.0, 102.0, 101.0, 103.0, 102.0, 104.0]  # 5+1 data points
        result = RelativeStrengthIndex.cal(5, prices)

        # Manual calculation for verification
        price_diffs = [2.0, -1.0, 2.0, -1.0, 2.0]  # Price changes
        gains = [2.0, 0.0, 2.0, 0.0, 2.0]         # Gains only
        losses = [0.0, 1.0, 0.0, 1.0, 0.0]        # Losses only

        avg_gain = sum(gains) / 5    # 1.2
        avg_loss = sum(losses) / 5   # 0.4

        rs = avg_gain / avg_loss     # 3.0
        expected_rsi = 100 - (100 / (1 + rs))  # 75.0

        assert pytest.approx(result, abs=0.1) == expected_rsi


@pytest.mark.unit
@pytest.mark.indicator
class TestRSITrendAnalysis:
    """Test RSI behavior with different price trends."""

    def test_rsi_increasing_trend(self, sample_prices_rsi14):
        """Test RSI with increasing prices (strong uptrend)."""
        result = RelativeStrengthIndex.cal(14, sample_prices_rsi14)

        # Strong uptrend should give RSI near 100
        assert result > 90
        assert result <= 100

    def test_rsi_decreasing_trend(self):
        """Test RSI with decreasing prices (strong downtrend)."""
        decreasing_prices = [114.0] + [114.0 - i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, decreasing_prices)

        # Strong downtrend should give RSI near 0
        assert result < 10
        assert result >= 0

    def test_rsi_mixed_changes(self):
        """Test RSI with mixed gains and losses."""
        # Alternating up and down movements
        mixed_prices = [100.0]
        for i in range(14):
            if i % 2 == 0:
                mixed_prices.append(mixed_prices[-1] + 1)
            else:
                mixed_prices.append(mixed_prices[-1] - 0.5)

        result = RelativeStrengthIndex.cal(14, mixed_prices)

        # Should be in neutral zone (30-70)
        assert 30 < result < 70

    def test_rsi_extreme_gains(self):
        """Test RSI with extreme gains."""
        extreme_up_prices = [100.0] + [100.0 + i*10 for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, extreme_up_prices)

        # Should be very close to 100
        assert result > 95
        assert result <= 100

    def test_rsi_extreme_losses(self):
        """Test RSI with extreme losses."""
        extreme_down_prices = [200.0] + [200.0 - i*10 for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, extreme_down_prices)

        # Should be very close to 0
        assert result < 5
        assert result >= 0


@pytest.mark.unit
@pytest.mark.indicator
class TestRSIEdgeCases:
    """Test RSI behavior with edge cases and invalid inputs."""

    def test_rsi_insufficient_data(self):
        """Test RSI with insufficient data points (needs period+1)."""
        result = RelativeStrengthIndex.cal(14, [100.0, 101.0, 102.0])
        assert pd.isna(result)

    def test_rsi_excess_data(self, sample_prices_rsi14):
        """Test RSI with too many data points."""
        result = RelativeStrengthIndex.cal(5, sample_prices_rsi14)
        assert pd.isna(result)

    def test_rsi_with_nan(self):
        """Test RSI with NaN values in data."""
        prices_with_nan = [100.0] + [
            100.0 + i if i != 7 else float('nan') for i in range(1, 15)
        ]
        result = RelativeStrengthIndex.cal(14, prices_with_nan)
        assert pd.isna(result)

    def test_rsi_zero_period(self, sample_prices_rsi14):
        """Test RSI with zero period."""
        result = RelativeStrengthIndex.cal(0, sample_prices_rsi14)
        assert pd.isna(result)

    def test_rsi_negative_period(self, sample_prices_rsi14):
        """Test RSI with negative period."""
        result = RelativeStrengthIndex.cal(-14, sample_prices_rsi14)
        assert pd.isna(result)


@pytest.mark.unit
@pytest.mark.indicator
class TestRSIBoundaryValues:
    """Test RSI behavior at boundary conditions."""

    @pytest.mark.parametrize("period", [5, 9, 14, 21, 30])
    def test_rsi_various_periods(self, period):
        """Test RSI works with various common periods."""
        prices = [100.0 + i for i in range(period + 1)]
        result = RelativeStrengthIndex.cal(period, prices)
        assert not pd.isna(result)
        assert 0 <= result <= 100

    def test_rsi_always_between_0_and_100(self):
        """Test that RSI is always between 0 and 100."""
        test_cases = [
            [100.0] + [100.0 + i*0.1 for i in range(1, 15)],  # Small gains
            [100.0] + [100.0 - i*0.1 for i in range(1, 15)],  # Small losses
            [100.0] + [100.0 + (i%2)*2 - 1 for i in range(1, 15)],  # Zigzag
        ]

        for prices in test_cases:
            result = RelativeStrengthIndex.cal(14, prices)
            assert 0 <= result <= 100, f"RSI should be 0-100, got {result}"

    def test_rsi_zero_average_loss(self):
        """Test RSI when average loss is zero (all gains)."""
        only_gains = [100.0] + [100.0 + i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, only_gains)

        # Should return 100 or very close
        assert result > 95
        assert result <= 100

    def test_rsi_zero_average_gain(self):
        """Test RSI when average gain is zero (all losses)."""
        only_losses = [114.0] + [114.0 - i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, only_losses)

        # Should return 0 or very close
        assert result >= 0
        assert result < 5


@pytest.mark.unit
@pytest.mark.indicator
class TestRSIMatrix:
    """Test RSI matrix operations for multi-asset calculations."""

    def test_rsi_matrix_long_format(self, price_matrix_long):
        """Test RSI calculation with long format matrix."""
        period = 14
        result = RelativeStrengthIndex.cal_matrix(period, price_matrix_long)

        # Check result contains rsi column
        assert 'rsi' in result.columns

        # Check RSI values are valid
        valid_rsi = result['rsi'].dropna()
        assert len(valid_rsi) > 0

        for rsi_val in valid_rsi:
            assert 0 <= rsi_val <= 100

    def test_rsi_matrix_multiple_stocks(self, price_matrix_long):
        """Test RSI matrix calculation for multiple stocks."""
        period = 14
        result = RelativeStrengthIndex.cal_matrix(period, price_matrix_long)

        # Should have results for both stocks
        stocks = result['code'].unique()
        assert len(stocks) == 2
        assert 'STOCK_A' in stocks
        assert 'STOCK_B' in stocks


@pytest.mark.unit
@pytest.mark.indicator
class TestRSIFinancialAccuracy:
    """Test RSI financial calculation accuracy and precision."""

    @pytest.mark.parametrize("prices,period,expected_range", [
        # Known RSI values for verification
        ([100.0, 102.0, 104.0, 106.0, 108.0, 110.0], 5, (90, 100)),
        ([110.0, 108.0, 106.0, 104.0, 102.0, 100.0], 5, (0, 10)),
    ])
    def test_rsi_known_values(self, prices, period, expected_range):
        """Test RSI with known expected ranges."""
        result = RelativeStrengthIndex.cal(period, prices)
        min_val, max_val = expected_range
        assert min_val <= result <= max_val

    def test_rsi_decimal_precision(self, sample_prices_rsi14):
        """Test RSI maintains proper decimal precision."""
        result = RelativeStrengthIndex.cal(14, sample_prices_rsi14)
        assert isinstance(result, (float, np.floating))
        assert not pd.isna(result)


@pytest.mark.slow
@pytest.mark.indicator
class TestRSIPerformance:
    """Test RSI calculation performance."""

    def test_rsi_calculation_speed(self, large_dataset_for_rsi):
        """Test RSI calculation performance with large dataset."""
        import time

        period = 14
        iterations = 50

        start_time = time.time()
        for _ in range(iterations):
            result = RelativeStrengthIndex.cal(period, large_dataset_for_rsi[-(period+1):])
        end_time = time.time()

        # 50 calculations should complete in 0.5 seconds
        assert end_time - start_time < 0.5
        assert not pd.isna(result)

    def test_rsi_matrix_performance(self, price_matrix_long):
        """Test RSI matrix calculation performance."""
        import time

        period = 14
        iterations = 10

        start_time = time.time()
        for _ in range(iterations):
            result = RelativeStrengthIndex.cal_matrix(period, price_matrix_long)
        end_time = time.time()

        # 10 matrix calculations should complete in 1 second
        assert end_time - start_time < 1.0
        assert not result.empty


@pytest.mark.unit
@pytest.mark.indicator
class TestRSITradingSignals:
    """Test RSI interpretation for trading signals."""

    def test_rsi_overbought_condition(self):
        """Test RSI overbought condition (RSI > 70)."""
        # Strong uptrend should trigger overbought
        overbought_prices = [100.0] + [100.0 + i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, overbought_prices)
        assert result > 70  # Overbought threshold

    def test_rsi_oversold_condition(self):
        """Test RSI oversold condition (RSI < 30)."""
        # Strong downtrend should trigger oversold
        oversold_prices = [114.0] + [114.0 - i for i in range(1, 15)]
        result = RelativeStrengthIndex.cal(14, oversold_prices)
        assert result < 30  # Oversold threshold

    def test_rsi_neutral_zone(self):
        """Test RSI in neutral zone (30-70)."""
        # Sideways movement should keep RSI in neutral zone
        neutral_prices = [100.0]
        for i in range(14):
            change = 1.0 if i % 3 == 0 else (-0.5 if i % 3 == 1 else 0)
            neutral_prices.append(neutral_prices[-1] + change)

        result = RelativeStrengthIndex.cal(14, neutral_prices)
        assert 30 <= result <= 70  # Neutral zone
