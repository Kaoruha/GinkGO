"""
Verify that refactored test imports work correctly.
"""

import sys
sys.path.insert(0, '.')
sys.path.insert(0, 'src')

def test_imports():
    """Test that all imports work correctly."""
    print("Testing imports...")
    print("=" * 60)

    # Test indicator imports
    print("\n1. Testing indicator imports...")
    try:
        from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage
        from ginkgo.trading.computation.technical.exponential_moving_average import ExponentialMovingAverage
        from ginkgo.trading.computation.technical.relative_strength_index import RelativeStrengthIndex
        print("   ✅ All indicator imports successful")
    except Exception as e:
        print(f"   ❌ Indicator imports failed: {e}")
        return False

    # Test risk management imports
    print("\n2. Testing risk management imports...")
    try:
        from ginkgo.trading.risk_management.loss_limit_risk import LossLimitRisk
        from ginkgo.trading.risk_management.profit_target_risk import ProfitTargetRisk
        print("   ✅ All risk management imports successful")
    except Exception as e:
        print(f"   ❌ Risk management imports failed: {e}")
        return False

    # Test entity imports
    print("\n3. Testing entity imports...")
    try:
        from ginkgo.trading.entities.position import Position
        from ginkgo.trading.entities.order import Order
        from ginkgo.trading.entities.signal import Signal
        print("   ✅ All entity imports successful")
    except Exception as e:
        print(f"   ❌ Entity imports failed: {e}")
        return False

    # Test event imports
    print("\n4. Testing event imports...")
    try:
        from ginkgo.trading.events import EventPriceUpdate
        print("   ✅ Event imports successful")
    except Exception as e:
        print(f"   ❌ Event imports failed: {e}")
        return False

    # Test enum imports
    print("\n5. Testing enum imports...")
    try:
        from ginkgo.enums import (
            DIRECTION_TYPES, SOURCE_TYPES, EVENT_TYPES,
            ORDER_TYPES, ORDERSTATUS_TYPES
        )
        print("   ✅ All enum imports successful")
    except Exception as e:
        print(f"   ❌ Enum imports failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All imports verified successfully! ✅")
    return True

def test_basic_functionality():
    """Test basic functionality of refactored tests."""
    print("\n\nTesting basic functionality...")
    print("=" * 60)

    # Test SMA calculation
    print("\n1. Testing SMA calculation...")
    try:
        from ginkgo.trading.computation.technical.simple_moving_average import SimpleMovingAverage
        prices = [100.0, 101.0, 102.0, 103.0, 104.0]
        result = SimpleMovingAverage.cal(5, prices)
        expected = sum(prices) / 5
        assert abs(result - expected) < 0.0001, f"Expected {expected}, got {result}"
        print(f"   ✅ SMA calculation: {result} (expected {expected})")
    except Exception as e:
        print(f"   ❌ SMA calculation failed: {e}")
        return False

    # Test LossLimitRisk
    print("\n2. Testing LossLimitRisk initialization...")
    try:
        from ginkgo.trading.risk_management.loss_limit_risk import LossLimitRisk
        risk = LossLimitRisk(loss_limit=15.0)
        assert risk.loss_limit == 15.0
        print(f"   ✅ LossLimitRisk initialized with limit: {risk.loss_limit}%")
    except Exception as e:
        print(f"   ❌ LossLimitRisk initialization failed: {e}")
        return False

    print("\n" + "=" * 60)
    print("All functionality tests passed! ✅")
    return True

if __name__ == "__main__":
    success = test_imports() and test_basic_functionality()
    sys.exit(0 if success else 1)
