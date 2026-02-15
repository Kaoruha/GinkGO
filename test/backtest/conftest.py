"""
Shared fixtures for backtest module tests.
Provides common test data and configurations for indicators, strategies, and risk management tests.
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import uuid

from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.enums import DIRECTION_TYPES, SOURCE_TYPES, ORDER_TYPES, ORDERSTATUS_TYPES


@pytest.fixture
def ginkgo_config():
    """Configure Ginkgo for testing - must enable debug mode for database operations."""
    from ginkgo.libs import GCONF
    GCONF.set_debug(True)
    yield GCONF
    GCONF.set_debug(False)


# ========== Price Data Fixtures ==========

@pytest.fixture
def sample_prices_5() -> List[float]:
    """Standard 5-period price series for testing."""
    return [100.0, 101.0, 102.0, 103.0, 104.0]


@pytest.fixture
def sample_prices_10() -> List[float]:
    """Standard 10-period price series for testing."""
    return [100.0, 101.0, 102.0, 103.0, 104.0, 105.0, 106.0, 107.0, 108.0, 109.0]


@pytest.fixture
def sample_prices_rsi14() -> List[float]:
    """15-period price series for RSI(14) testing (needs period+1 data points)."""
    return [100.0] + [100.0 + i for i in range(1, 15)]


@pytest.fixture
def sample_prices_rsi5() -> List[float]:
    """6-period price series for RSI(5) testing."""
    return [100.0, 101.0, 102.0, 103.0, 104.0, 105.0]


@pytest.fixture
def decreasing_prices() -> List[float]:
    """Decreasing price series for testing indicators."""
    return [104.0, 103.0, 102.0, 101.0, 100.0]


@pytest.fixture
def constant_prices() -> List[float]:
    """Constant price series for testing indicators."""
    return [100.0] * 5


@pytest.fixture
def volatile_prices() -> List[float]:
    """Volatile price series for testing indicator behavior."""
    return [100.0, 105.0, 95.0, 110.0, 90.0]


@pytest.fixture
def price_matrix_wide():
    """Wide format price matrix (dates x stocks) for testing."""
    dates = pd.date_range('2023-01-01', periods=10)
    data = {
        'stock1': [100 + i for i in range(10)],
        'stock2': [200 + i*2 for i in range(10)]
    }
    return pd.DataFrame(data, index=dates)


@pytest.fixture
def price_matrix_long():
    """Long format price matrix for testing."""
    data = []
    stocks = ['STOCK_A', 'STOCK_B']
    dates = pd.date_range('2023-01-01', periods=20)

    for stock in stocks:
        base_price = 100.0
        for date in dates:
            data.append({
                'code': stock,
                'timestamp': date,
                'close': base_price,
                'volume': 1000
            })
            base_price += 1

    return pd.DataFrame(data)


# ========== Trading Entity Fixtures ==========

@pytest.fixture
def sample_portfolio_info() -> Dict[str, Any]:
    """Standard portfolio information dictionary for testing."""
    return {
        "uuid": "test_portfolio_id",
        "engine_id": "test_engine_id",
        "now": datetime.now(),
        "cash": Decimal("100000"),
        "positions": {},
    }


@pytest.fixture
def sample_position() -> Position:
    """Standard position object for testing."""
    return Position(
        portfolio_id="test_portfolio_id",
        code="000001.SZ",
        cost=Decimal("10.0"),
        volume=1000,
        price=Decimal("10.0"),
        uuid=uuid.uuid4().hex,
    )


@pytest.fixture
def sample_position_profit() -> Position:
    """Profitable position for testing risk management."""
    return Position(
        portfolio_id="test_portfolio_id",
        code="000001.SZ",
        cost=Decimal("10.0"),
        volume=1000,
        price=Decimal("10.0"),
        uuid=uuid.uuid4().hex,
    )


@pytest.fixture
def sample_position_loss() -> Position:
    """Loss-making position for testing risk management."""
    return Position(
        portfolio_id="test_portfolio_id",
        code="000001.SZ",
        cost=Decimal("10.0"),
        volume=1000,
        price=Decimal("10.0"),
        uuid=uuid.uuid4().hex,
    )


@pytest.fixture
def sample_order() -> Order:
    """Standard order object for testing."""
    order = Order()
    order.set(
        "000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        order_type=ORDER_TYPES.MARKETORDER,
        status=ORDERSTATUS_TYPES.NEW,
        volume=100,
    )
    return order


@pytest.fixture
def sample_signal() -> Signal:
    """Standard signal object for testing."""
    return Signal(
        code="000001.SZ",
        direction=DIRECTION_TYPES.LONG,
        portfolio_id="test_portfolio_id",
        engine_id="test_engine_id",
        source=SOURCE_TYPES.STRATEGY,
    )


# ========== Event Fixtures ==========

@pytest.fixture
def price_update_event_basic() -> EventPriceUpdate:
    """Basic price update event for testing."""
    return EventPriceUpdate(
        code="000001.SZ",
        open=Decimal("10.0"),
        high=Decimal("10.5"),
        low=Decimal("9.8"),
        close=Decimal("10.2"),
        volume=10000,
        timestamp=datetime.now(),
    )


@pytest.fixture
def price_update_event_profit() -> EventPriceUpdate:
    """Price update event indicating profit (price above cost)."""
    return EventPriceUpdate(
        code="000001.SZ",
        open=Decimal("11.0"),
        high=Decimal("11.2"),
        low=Decimal("10.8"),
        close=Decimal("11.0"),  # 10% profit
        volume=10000,
        timestamp=datetime.now(),
    )


@pytest.fixture
def price_update_event_loss() -> EventPriceUpdate:
    """Price update event indicating loss (price below cost)."""
    return EventPriceUpdate(
        code="000001.SZ",
        open=Decimal("8.5"),
        high=Decimal("9.0"),
        low=Decimal("8.0"),
        close=Decimal("8.5"),  # 15% loss
        volume=10000,
        timestamp=datetime.now(),
    )


@pytest.fixture
def price_update_event_extreme_loss() -> EventPriceUpdate:
    """Price update event indicating extreme loss."""
    return EventPriceUpdate(
        code="000001.SZ",
        open=Decimal("8.5"),
        high=Decimal("8.6"),
        low=Decimal("8.2"),
        close=Decimal("8.4"),  # 16% loss
        volume=10000,
        timestamp=datetime.now(),
    )


# ========== Parameterized Test Data ==========

@pytest.fixture
def sma_periods():
    """Common SMA periods for parameterized testing."""
    return [3, 5, 10, 20, 50]


@pytest.fixture
def ema_periods():
    """Common EMA periods for parameterized testing."""
    return [3, 5, 10, 12, 20, 26]


@pytest.fixture
def rsi_periods():
    """Common RSI periods for parameterized testing."""
    return [5, 9, 14, 21]


@pytest.fixture
def loss_limit_ratios():
    """Common loss limit ratios for parameterized testing."""
    return [5.0, 10.0, 15.0, 20.0, 25.0]


@pytest.fixture
def profit_limit_ratios():
    """Common profit limit ratios for parameterized testing."""
    return [10.0, 15.0, 20.0, 25.0, 30.0]


# ========== Edge Case Fixtures ==========

@pytest.fixture
def prices_with_nan() -> List[float]:
    """Price series containing NaN values."""
    return [100.0, float('nan'), 102.0, 103.0, 104.0]


@pytest.fixture
def prices_with_zero() -> List[float]:
    """Price series containing zero values."""
    return [0.0, 101.0, 102.0, 103.0, 104.0]


@pytest.fixture
def prices_with_negative() -> List[float]:
    """Price series containing negative values (edge case)."""
    return [-100.0, 101.0, 102.0, 103.0, 104.0]


@pytest.fixture
def extreme_small_prices() -> List[float]:
    """Very small price values for testing precision."""
    return [0.001, 0.002, 0.003, 0.004, 0.005]


@pytest.fixture
def extreme_large_prices() -> List[float]:
    """Very large price values for testing overflow."""
    return [1e6, 1.1e6, 1.2e6, 1.3e6, 1.4e6]


# ========== Performance Test Fixtures ==========

@pytest.fixture
def large_price_series() -> List[float]:
    """Large price series for performance testing."""
    return [100.0 + i*0.1 for i in range(1000)]


@pytest.fixture
def large_dataset_for_rsi() -> List[float]:
    """Large dataset for RSI performance testing."""
    prices = [100.0]
    for i in range(499):  # 500 data points
        change = (-1) ** i * (i % 5)  # Alternating changes
        prices.append(prices[-1] + change)
    return prices


# ========== Risk Management Test Scenarios ==========

@pytest.fixture
def loss_ratio_test_cases():
    """Test cases for loss ratio calculation."""
    cost = 100.0
    return [
        (90.0, 10.0),   # 90 yuan, 10% loss
        (80.0, 20.0),   # 80 yuan, 20% loss
        (50.0, 50.0),   # 50 yuan, 50% loss
        (30.0, 70.0),   # 30 yuan, 70% loss
    ]


@pytest.fixture
def profit_ratio_test_cases():
    """Test cases for profit ratio calculation."""
    cost = 100.0
    return [
        (110.0, 10.0),  # 110 yuan, 10% profit
        (120.0, 20.0),  # 120 yuan, 20% profit
        (150.0, 50.0),  # 150 yuan, 50% profit
    ]


# ========== Pytest Markers ==========

def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line("markers", "integration: Integration tests (slower, may use database)")
    config.addinivalue_line("markers", "slow: Slow tests (performance testing)")
    config.addinivalue_line("markers", "financial: Financial calculation tests (requires precision)")
    config.addinivalue_line("markers", "indicator: Technical indicator tests")
    config.addinivalue_line("markers", "risk: Risk management tests")
