"""
Simple test runner to verify refactored tests without pytest configuration issues.
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

from test.backtest.indicators.test_simple_moving_average import TestSimpleMovingAverageCalculation
from test.backtest.indicators.test_exponential_moving_average import TestExponentialMovingAverageCalculation
from test.backtest.indicators.test_relative_strength_index import TestRSIBasicCalculation
from test.backtest.risk_managements.test_loss_limit_risk import TestLossLimitRiskInit
from test.backtest.risk_managements.test_profit_limit_risk import TestProfitLimitRiskInit

def run_tests():
    """Run a subset of refactored tests to verify functionality."""
    print("Running refactored tests...")
    print("=" * 60)

    # Test SMA
    print("\n1. Testing Simple Moving Average...")
    sma_test = TestSimpleMovingAverageCalculation()
    try:
        sma_test.test_sma_basic_calculation([100.0, 101.0, 102.0, 103.0, 104.0])
        print("   ✅ SMA basic calculation test passed")
    except Exception as e:
        print(f"   ❌ SMA test failed: {e}")

    # Test EMA
    print("\n2. Testing Exponential Moving Average...")
    ema_test = TestExponentialMovingAverageCalculation()
    try:
        ema_test.test_ema_basic_calculation([100.0, 101.0, 102.0, 103.0, 104.0])
        print("   ✅ EMA basic calculation test passed")
    except Exception as e:
        print(f"   ❌ EMA test failed: {e}")

    # Test RSI
    print("\n3. Testing Relative Strength Index...")
    rsi_test = TestRSIBasicCalculation()
    try:
        rsi_test.test_rsi_basic_calculation([100.0] + [100.0 + i for i in range(1, 15)])
        print("   ✅ RSI basic calculation test passed")
    except Exception as e:
        print(f"   ❌ RSI test failed: {e}")

    # Test LossLimitRisk
    print("\n4. Testing Loss Limit Risk...")
    loss_risk_test = TestLossLimitRiskInit()
    try:
        loss_risk_test.test_init_default()
        print("   ✅ LossLimitRisk init test passed")
    except Exception as e:
        print(f"   ❌ LossLimitRisk test failed: {e}")

    # Test ProfitLimitRisk
    print("\n5. Testing Profit Limit Risk...")
    profit_risk_test = TestProfitLimitRiskInit()
    try:
        profit_risk_test.test_init_default()
        print("   ✅ ProfitLimitRisk init test passed")
    except Exception as e:
        print(f"   ❌ ProfitLimitRisk test failed: {e}")

    print("\n" + "=" * 60)
    print("Refactored tests verification complete!")

if __name__ == "__main__":
    run_tests()
