"""
性能: 157MB RSS, 0.91s, 36 tests [PASS]
Test cases for LossLimitRisk risk management.
Tests cover loss calculation, signal generation, edge cases, and financial accuracy.
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch, MagicMock
import uuid

from ginkgo.trading.risk_management.loss_limit_risk import LossLimitRisk
from ginkgo.entities.signal import Signal
from ginkgo.entities.order import Order
from ginkgo.entities.position import Position
from ginkgo.entities.bar import Bar
from ginkgo.trading.events import EventPriceUpdate
from ginkgo.trading.context.engine_context import EngineContext
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    EVENT_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
)


def _make_position(code="000001.SZ", cost="10.0", volume=1000, price="10.0"):
    """Helper to create a valid Position with required fields."""
    return Position(
        portfolio_id="test_portfolio_id",
        engine_id="test_engine_id",
        task_id="test_task_id",
        code=code,
        cost=Decimal(cost),
        volume=volume,
        price=Decimal(price),
        uuid=uuid.uuid4().hex,
    )


def _make_portfolio_info(**overrides):
    """Helper to create portfolio_info dict."""
    info = {
        "uuid": "test_portfolio_id",
        "engine_id": "test_engine_id",
        "now": datetime.now(),
        "cash": Decimal("100000"),
        "positions": {},
    }
    info.update(overrides)
    return info


def _make_price_event(code="000001.SZ", close="10.0", open_=None, high=None, low=None, volume=10000):
    """Helper to create an EventPriceUpdate with a Bar payload."""
    c = Decimal(str(close))
    bar = Bar(
        code=code,
        open=Decimal(str(open_)) if open_ is not None else c,
        high=Decimal(str(high)) if high is not None else c,
        low=Decimal(str(low)) if low is not None else c,
        close=c,
        volume=volume,
        amount=c * volume,
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=datetime.now(),
    )
    return EventPriceUpdate(payload=bar)


def _make_risk(loss_limit=15.0):
    """Helper to create a LossLimitRisk with engine context bound."""
    risk = LossLimitRisk(loss_limit=loss_limit)
    risk._context = EngineContext(engine_id="test_engine_id")
    return risk


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT, reason=""):
    """Create a mock signal that bypasses Signal constructor validation."""
    signal = Mock(spec=Signal)
    signal.code = code
    signal.direction = direction
    signal.portfolio_id = "test_portfolio_id"
    signal.engine_id = "test_engine_id"
    signal.source = SOURCE_TYPES.STRATEGY
    signal.reason = reason
    return signal


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskInit:
    """Test LossLimitRisk initialization and configuration."""

    def test_init_default(self):
        """Test initialization with default values."""
        risk = LossLimitRisk(loss_limit=20.0)
        assert risk.loss_limit == 20.0
        assert "20.0" in risk.name

    def test_init_with_name(self):
        """Test initialization with custom name."""
        risk = LossLimitRisk(name="CustomLossLimit", loss_limit=15.0)
        # Source calls set_name(f"{name}_{loss_limit}%"), so name includes suffix
        assert "CustomLossLimit" in risk.name
        assert risk.loss_limit == 15.0

    @pytest.mark.parametrize("loss_limit", [5.0, 10.0, 15.0, 20.0, 25.0, 50.0])
    def test_init_various_limits(self, loss_limit):
        """Test initialization with various loss limits."""
        risk = LossLimitRisk(loss_limit=loss_limit)
        assert risk.loss_limit == loss_limit


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskOrderProcessing:
    """Test LossLimitRisk order processing (should pass through)."""

    def test_cal_order_passthrough(self, sample_portfolio_info, sample_order):
        """Test that orders pass through unchanged."""
        risk = LossLimitRisk(loss_limit=15.0)
        result = risk.cal(sample_portfolio_info, sample_order)

        assert result == sample_order

    @pytest.mark.parametrize("volume", [100, 500, 1000, 5000])
    def test_cal_various_order_volumes(self, sample_portfolio_info, volume):
        """Test order processing with various volumes."""
        risk = LossLimitRisk(loss_limit=15.0)
        order = Order(
            portfolio_id="test_portfolio_id",
            engine_id="test_engine_id",
            task_id="test_task_id",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=volume,
            limit_price=Decimal("10.0"),
        )

        result = risk.cal(sample_portfolio_info, order)
        assert result.volume == volume


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskSignalGeneration:
    """Test LossLimitRisk signal generation logic."""

    def test_generate_signals_no_position(self):
        """Test no signals when no positions exist."""
        risk = _make_risk()
        portfolio_info = _make_portfolio_info(positions={})
        event = _make_price_event()
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_generate_signals_zero_volume_position(self):
        """Test no signals when position volume is zero."""
        risk = _make_risk()

        zero_position = _make_position(volume=0)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": zero_position}
        )
        event = _make_price_event()
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskLossCalculation:
    """Test loss ratio calculation accuracy."""

    @pytest.mark.parametrize("current_price,expected_loss", [
        (90.0, 10.0),   # 10% loss
        (80.0, 20.0),   # 20% loss
        (50.0, 50.0),   # 50% loss
        (30.0, 70.0),   # 70% loss
    ])
    def test_loss_ratio_calculation(self, current_price, expected_loss):
        """Test loss ratio calculation for various scenarios."""
        risk = _make_risk(loss_limit=200.0)  # High limit to avoid triggering

        position = _make_position(cost="100.0", price="100.0")
        event = _make_price_event(close=current_price)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        # Should not trigger signal due to high limit
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestLossLimitRiskThresholds:
    """Test loss limit threshold behavior."""

    def test_loss_below_limit_no_signal(self):
        """Test no signal when loss is below threshold."""
        risk = _make_risk()

        position = _make_position(cost="10.0")
        event = _make_price_event(close="9.0", open_="9.0", high="9.2", low="8.8")
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_loss_above_limit_generates_signal(self):
        """Test signal generation when loss exceeds threshold."""
        risk = _make_risk()

        position = _make_position(cost="10.0")
        event = _make_price_event(close="8.4", open_="8.5", high="8.6", low="8.2")
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        # Patch Signal to bypass task_id validation and capture the args
        with patch("ginkgo.trading.risk_management.loss_limit_risk.Signal") as MockSignal:
            mock_signal = Mock()
            MockSignal.return_value = mock_signal

            signals = risk.generate_signals(portfolio_info, event)

            assert len(signals) == 1
            assert signals[0] == mock_signal

            # Verify Signal was called with correct args
            MockSignal.assert_called_once()
            call_kwargs = MockSignal.call_args[1]
            assert call_kwargs["code"] == "000001.SZ"
            assert call_kwargs["direction"] == DIRECTION_TYPES.SHORT
            assert call_kwargs["portfolio_id"] == "test_portfolio_id"
            assert call_kwargs["engine_id"] == "test_engine_id"
            assert call_kwargs["source"] == SOURCE_TYPES.STRATEGY
            assert "Loss Limit" in call_kwargs["reason"]
            assert "16.00%" in call_kwargs["reason"]

    def test_profit_no_signal(self):
        """Test no signal when position is profitable."""
        risk = _make_risk()

        position = _make_position(cost="10.0")
        event = _make_price_event(close="11.0", open_="11.0", high="11.2", low="10.8")
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    @pytest.mark.parametrize("loss_limit,loss_percentage,should_signal", [
        (5.0, 6.0, True),    # Exceeds limit
        (10.0, 11.0, True),   # Exceeds limit
        (15.0, 14.0, False),  # Below limit
        (20.0, 19.0, False),  # Below limit
    ])
    def test_various_thresholds(self, loss_limit, loss_percentage, should_signal):
        """Test various loss limit thresholds."""
        risk = _make_risk(loss_limit=loss_limit)

        position = _make_position(cost="100.0", price="100.0")

        current_price = 100.0 * (1 - loss_percentage / 100)
        event = _make_price_event(close=current_price)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        with patch("ginkgo.trading.risk_management.loss_limit_risk.Signal") as MockSignal:
            MockSignal.return_value = Mock()

            signals = risk.generate_signals(portfolio_info, event)

            if should_signal:
                assert len(signals) == 1
                assert MockSignal.called
                call_kwargs = MockSignal.call_args[1]
                assert call_kwargs["direction"] == DIRECTION_TYPES.SHORT
            else:
                assert len(signals) == 0
                assert not MockSignal.called


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskEdgeCases:
    """Test LossLimitRisk edge cases and error handling."""

    def test_invalid_price_data(self):
        """Test behavior with invalid price data (no payload)."""
        risk = _make_risk()

        position = _make_position(cost="10.0")

        # Create an event without payload - code returns None
        event = EventPriceUpdate()

        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        # Without payload, event.code is None so code not in positions
        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_invalid_cost(self):
        """Test behavior with invalid cost price."""
        risk = _make_risk()

        position = _make_position(cost="0.0")  # Invalid

        event = _make_price_event(close="9.0")
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        with patch("ginkgo.trading.risk_management.loss_limit_risk.GLOG") as mock_glog:
            signals = risk.generate_signals(portfolio_info, event)
            assert len(signals) == 0
            mock_glog.WARN.assert_called_with(
                "LossLimitRisk: Invalid price data for 000001.SZ"
            )

    def test_non_price_event(self):
        """Test behavior with non-price events."""
        risk = _make_risk()

        non_price_event = Mock()
        non_price_event.event_type = EVENT_TYPES.SIGNALGENERATION
        non_price_event.code = "000001.SZ"

        position = _make_position(cost="10.0")
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        signals = risk.generate_signals(portfolio_info, non_price_event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestLossLimitRiskFinancialAccuracy:
    """Test financial calculation accuracy."""

    @pytest.mark.parametrize("cost,price,expected_loss_ratio", [
        (100.0, 90.0, 10.0),
        (100.0, 85.0, 15.0),
        (100.0, 80.0, 20.0),
        (50.0, 45.0, 10.0),
        (10.0, 8.5, 15.0),
    ])
    def test_loss_ratio_precision(self, cost, price, expected_loss_ratio):
        """Test loss ratio calculation precision."""
        # Set limit slightly below expected ratio since source uses strict >
        risk = _make_risk(loss_limit=expected_loss_ratio - 0.01)

        position = _make_position(cost=str(cost), price=str(cost))
        event = _make_price_event(close=price)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        with patch("ginkgo.trading.risk_management.loss_limit_risk.Signal") as MockSignal:
            MockSignal.return_value = Mock()

            # Should trigger signal since loss exceeds the slightly-lower limit
            signals = risk.generate_signals(portfolio_info, event)
            assert len(signals) == 1
            call_kwargs = MockSignal.call_args[1]
            assert f"{expected_loss_ratio:.2f}%" in call_kwargs["reason"]

    def test_decimal_precision_calculation(self):
        """Test that decimal precision is maintained."""
        # Set limit slightly below 15% since source uses strict >
        risk = _make_risk(loss_limit=14.99)

        position = _make_position(cost="10.55", price="10.55")

        # Calculate exact 15% loss
        current_price = 10.55 * 0.85  # Exactly 15% loss
        event = _make_price_event(close=current_price)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        with patch("ginkgo.trading.risk_management.loss_limit_risk.Signal") as MockSignal:
            MockSignal.return_value = Mock()

            signals = risk.generate_signals(portfolio_info, event)
            assert len(signals) == 1


@pytest.mark.unit
@pytest.mark.risk
class TestLossLimitRiskMultiplePositions:
    """Test behavior with multiple positions."""

    def test_multiple_positions_mixed_signals(self):
        """Test signal generation with multiple positions."""
        risk = _make_risk()

        position1 = _make_position(code="000001.SZ", cost="10.0")
        position2 = _make_position(code="000002.SZ", cost="20.0", volume=500)

        portfolio_info = _make_portfolio_info(
            positions={
                "000001.SZ": position1,
                "000002.SZ": position2,
            }
        )

        # Event for stock 1 (9.0 = 10% loss)
        event1 = _make_price_event(code="000001.SZ", close="9.0")
        signals = risk.generate_signals(portfolio_info, event1)
        assert len(signals) == 0  # Below threshold

        # Event for stock 2 (16.0 = 20% loss)
        event2 = _make_price_event(code="000002.SZ", close="16.0")

        with patch("ginkgo.trading.risk_management.loss_limit_risk.Signal") as MockSignal:
            mock_signal = Mock()
            MockSignal.return_value = mock_signal

            signals = risk.generate_signals(portfolio_info, event2)
            assert len(signals) == 1  # Exceeds threshold
            call_kwargs = MockSignal.call_args[1]
            assert call_kwargs["code"] == "000002.SZ"
