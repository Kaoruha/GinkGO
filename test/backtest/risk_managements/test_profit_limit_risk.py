"""
Test cases for ProfitLimitRisk risk management.
Tests cover profit calculation, signal generation, edge cases, and financial accuracy.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
import uuid

from ginkgo.trading.risk_management.profit_target_risk import ProfitTargetRisk as ProfitLimitRisk
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    EVENT_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES
)


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskInit:
    """Test ProfitLimitRisk initialization and configuration."""

    def test_init_default(self):
        """Test initialization with default values."""
        risk = ProfitLimitRisk(profit_limit=20.0)
        assert risk.profit_limit == 20.0
        assert "20.0" in risk.name

    def test_init_with_name(self):
        """Test initialization with custom name."""
        risk = ProfitLimitRisk(name="CustomProfitLimit", profit_limit=15.0)
        assert risk.name == "CustomProfitLimit"
        assert risk.profit_limit == 15.0

    @pytest.mark.parametrize("profit_limit", [5.0, 10.0, 15.0, 20.0, 25.0, 50.0])
    def test_init_various_limits(self, profit_limit):
        """Test initialization with various profit limits."""
        risk = ProfitLimitRisk(profit_limit=profit_limit)
        assert risk.profit_limit == profit_limit


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskOrderProcessing:
    """Test ProfitLimitRisk order processing (should pass through)."""

    def test_cal_order_passthrough(self, sample_portfolio_info, sample_order):
        """Test that orders pass through unchanged."""
        risk = ProfitLimitRisk(profit_limit=15.0)
        result = risk.cal(sample_portfolio_info, sample_order)

        assert result == sample_order

    @pytest.mark.parametrize("volume", [100, 500, 1000, 5000])
    def test_cal_various_order_volumes(self, sample_portfolio_info, volume):
        """Test order processing with various volumes."""
        risk = ProfitLimitRisk(profit_limit=15.0)
        order = Order()
        order.set(
            "000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=volume,
        )

        result = risk.cal(sample_portfolio_info, order)
        assert result.volume == volume


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskSignalGeneration:
    """Test ProfitLimitRisk signal generation logic."""

    def test_generate_signals_no_position(self, sample_portfolio_info, price_update_event_basic):
        """Test no signals when no positions exist."""
        risk = ProfitLimitRisk(profit_limit=15.0)
        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"] = {}

        signals = risk.generate_signals(portfolio_info, price_update_event_basic)
        assert len(signals) == 0

    def test_generate_signals_zero_volume_position(
        self, sample_portfolio_info, price_update_event_basic
    ):
        """Test no signals when position volume is zero."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        zero_position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=0,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = zero_position

        signals = risk.generate_signals(portfolio_info, price_update_event_basic)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskProfitCalculation:
    """Test profit ratio calculation accuracy."""

    @pytest.mark.parametrize("current_price,expected_profit", [
        (110.0, 10.0),   # 10% profit
        (120.0, 20.0),   # 20% profit
        (150.0, 50.0),   # 50% profit
        (200.0, 100.0),  # 100% profit
    ])
    def test_profit_ratio_calculation(self, current_price, expected_profit):
        """Test profit ratio calculation for various scenarios."""
        risk = ProfitLimitRisk(profit_limit=200.0)  # High limit to avoid triggering

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("100.0"),
            volume=100,
            price=Decimal("100.0"),
            uuid=uuid.uuid4().hex,
        )

        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal(str(current_price)),
            high=Decimal(str(current_price)),
            low=Decimal(str(current_price)),
            close=Decimal(str(current_price)),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = {
            "uuid": "test_portfolio_id",
            "engine_id": "test_engine_id",
            "now": datetime.now(),
            "cash": Decimal("100000"),
            "positions": {"000001.SZ": position},
        }

        # Should not trigger signal due to high limit
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskThresholds:
    """Test profit limit threshold behavior."""

    def test_profit_below_limit_no_signal(self, sample_portfolio_info):
        """Test no signal when profit is below threshold."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # 10% profit (below 15% threshold)
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("11.0"),
            high=Decimal("11.2"),
            low=Decimal("10.8"),
            close=Decimal("11.0"),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_profit_above_limit_generates_signal(self, sample_portfolio_info):
        """Test signal generation when profit exceeds threshold."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # 16% profit (exceeds 15% threshold)
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("11.5"),
            high=Decimal("11.8"),
            low=Decimal("11.4"),
            close=Decimal("11.6"),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, event)

        assert len(signals) == 1
        signal = signals[0]
        assert signal.code == "000001.SZ"
        assert signal.direction == DIRECTION_TYPES.SHORT
        assert signal.portfolio_id == "test_portfolio_id"
        assert signal.engine_id == "test_engine_id"
        assert signal.source == SOURCE_TYPES.STRATEGY
        assert "Profit Limit" in signal.reason
        assert "16.00%" in signal.reason

    def test_loss_no_signal(self, sample_portfolio_info):
        """Test no signal when position is losing."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # 10% loss
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("9.0"),
            high=Decimal("9.2"),
            low=Decimal("8.8"),
            close=Decimal("9.0"),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    @pytest.mark.parametrize("profit_limit,profit_percentage,should_signal", [
        (5.0, 6.0, True),    # Exceeds limit
        (10.0, 11.0, True),   # Exceeds limit
        (15.0, 14.0, False),  # Below limit
        (20.0, 19.0, False),  # Below limit
    ])
    def test_various_thresholds(self, profit_limit, profit_percentage, should_signal):
        """Test various profit limit thresholds."""
        risk = ProfitLimitRisk(profit_limit=profit_limit)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("100.0"),
            volume=1000,
            price=Decimal("100.0"),
            uuid=uuid.uuid4().hex,
        )

        current_price = 100.0 * (1 + profit_percentage / 100)
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal(str(current_price)),
            high=Decimal(str(current_price)),
            low=Decimal(str(current_price)),
            close=Decimal(str(current_price)),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = {
            "uuid": "test_portfolio_id",
            "engine_id": "test_engine_id",
            "now": datetime.now(),
            "cash": Decimal("100000"),
            "positions": {"000001.SZ": position},
        }

        signals = risk.generate_signals(portfolio_info, event)

        if should_signal:
            assert len(signals) == 1
            assert signals[0].direction == DIRECTION_TYPES.SHORT
        else:
            assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskEdgeCases:
    """Test ProfitLimitRisk edge cases and error handling."""

    def test_invalid_price_data(self, sample_portfolio_info):
        """Test behavior with invalid price data."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # Event without close price
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("11.0"),
            high=Decimal("12.0"),
            low=Decimal("10.5"),
            close=None,  # Invalid
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        with patch.object(risk, "log") as mock_log:
            signals = risk.generate_signals(portfolio_info, event)
            assert len(signals) == 0
            mock_log.assert_called_with(
                "WARN",
                "ProfitLimitRisk: Invalid price data for 000001.SZ"
            )

    def test_invalid_cost(self, sample_portfolio_info, price_update_event_basic):
        """Test behavior with invalid cost price."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("0.0"),  # Invalid
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        with patch.object(risk, "log") as mock_log:
            signals = risk.generate_signals(portfolio_info, price_update_event_basic)
            assert len(signals) == 0
            mock_log.assert_called_with(
                "WARN",
                "ProfitLimitRisk: Invalid price data for 000001.SZ"
            )

    def test_non_price_event(self, sample_portfolio_info):
        """Test behavior with non-price events."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        non_price_event = Mock()
        non_price_event.event_type = EVENT_TYPES.SIGNALGENERATION
        non_price_event.code = "000001.SZ"

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, non_price_event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskFinancialAccuracy:
    """Test financial calculation accuracy."""

    @pytest.mark.parametrize("cost,price,expected_profit_ratio", [
        (100.0, 110.0, 10.0),
        (100.0, 115.0, 15.0),
        (100.0, 120.0, 20.0),
        (50.0, 55.0, 10.0),
        (10.0, 11.5, 15.0),
    ])
    def test_profit_ratio_precision(self, cost, price, expected_profit_ratio):
        """Test profit ratio calculation precision."""
        risk = ProfitLimitRisk(profit_limit=expected_profit_ratio)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal(str(cost)),
            volume=1000,
            price=Decimal(str(cost)),
            uuid=uuid.uuid4().hex,
        )

        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal(str(price)),
            high=Decimal(str(price)),
            low=Decimal(str(price)),
            close=Decimal(str(price)),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = {
            "uuid": "test_portfolio_id",
            "engine_id": "test_engine_id",
            "now": datetime.now(),
            "cash": Decimal("100000"),
            "positions": {"000001.SZ": position},
        }

        # Should trigger signal exactly at threshold
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 1
        assert f"{expected_profit_ratio:.2f}%" in signals[0].reason

    def test_decimal_precision_calculation(self, sample_portfolio_info):
        """Test that decimal precision is maintained."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.55"),
            volume=1000,
            price=Decimal("10.55"),
            uuid=uuid.uuid4().hex,
        )

        # Calculate exact 15% profit
        current_price = 10.55 * 1.15  # Exactly 15% profit
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal(str(current_price)),
            high=Decimal(str(current_price)),
            low=Decimal(str(current_price)),
            close=Decimal(str(current_price)),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 1


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskMultiplePositions:
    """Test behavior with multiple positions."""

    def test_multiple_positions_mixed_signals(self, sample_portfolio_info):
        """Test signal generation with multiple positions."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        # Position 1: Profit below threshold
        position1 = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # Position 2: Profit above threshold
        position2 = Position(
            portfolio_id="test_portfolio_id",
            code="000002.SZ",
            cost=Decimal("20.0"),
            volume=500,
            price=Decimal("20.0"),
            uuid=uuid.uuid4().hex,
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"] = {
            "000001.SZ": position1,
            "000002.SZ": position2,
        }

        # Event for stock 1 (11.0 = 10% profit)
        event1 = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("11.0"),
            high=Decimal("11.0"),
            low=Decimal("11.0"),
            close=Decimal("11.0"),
            volume=10000,
            timestamp=datetime.now(),
        )

        # Only check stock 1
        signals = risk.generate_signals(portfolio_info, event1)
        assert len(signals) == 0  # Below threshold

        # Event for stock 2 (24.0 = 20% profit)
        event2 = EventPriceUpdate(
            code="000002.SZ",
            open=Decimal("24.0"),
            high=Decimal("24.0"),
            low=Decimal("24.0"),
            close=Decimal("24.0"),
            volume=10000,
            timestamp=datetime.now(),
        )

        signals = risk.generate_signals(portfolio_info, event2)
        assert len(signals) == 1  # Exceeds threshold
        assert signals[0].code == "000002.SZ"


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskBreakEven:
    """Test break-even scenarios."""

    def test_break_even_no_signal(self, sample_portfolio_info):
        """Test that break-even (no profit, no loss) doesn't trigger signal."""
        risk = ProfitLimitRisk(profit_limit=15.0)

        position = Position(
            portfolio_id="test_portfolio_id",
            code="000001.SZ",
            cost=Decimal("10.0"),
            volume=1000,
            price=Decimal("10.0"),
            uuid=uuid.uuid4().hex,
        )

        # Break-even: current price = cost
        event = EventPriceUpdate(
            code="000001.SZ",
            open=Decimal("10.0"),
            high=Decimal("10.0"),
            low=Decimal("10.0"),
            close=Decimal("10.0"),
            volume=10000,
            timestamp=datetime.now(),
        )

        portfolio_info = sample_portfolio_info.copy()
        portfolio_info["positions"]["000001.SZ"] = position

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0  # No profit = no signal
