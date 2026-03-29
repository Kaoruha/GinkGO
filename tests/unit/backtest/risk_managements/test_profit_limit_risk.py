"""
Test cases for ProfitTargetRisk risk management.
Tests cover profit calculation, signal generation, edge cases, and financial accuracy.

Note: ProfitTargetRisk uses a different API from LossLimitRisk:
- Constructor parameter is `profit_target` (decimal ratio, e.g. 0.15 for 15%), not `profit_limit`
- profit_target must be in range (0, 1]
- Positions in portfolio_info are accessed as dicts with 'profit_loss_ratio' key
"""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock, patch
import uuid

from ginkgo.trading.risk_management.profit_target_risk import ProfitTargetRisk
from ginkgo.entities.signal import Signal
from ginkgo.entities.order import Order
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


def _make_dict_position(profit_loss_ratio=0.0, volume=1000):
    """Helper to create a position dict as ProfitTargetRisk expects."""
    return {
        "profit_loss_ratio": profit_loss_ratio,
        "volume": volume,
    }


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


def _make_risk(profit_target=0.15):
    """Helper to create a ProfitTargetRisk."""
    return ProfitTargetRisk(profit_target=profit_target)


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskInit:
    """Test ProfitTargetRisk initialization and configuration."""

    def test_init_default(self):
        """Test initialization with default values."""
        risk = ProfitTargetRisk(profit_target=0.20)
        assert risk.profit_target == 0.20

    def test_init_with_name(self):
        """Test initialization verifies name is set."""
        risk = ProfitTargetRisk(profit_target=0.15)
        assert risk.name == "ProfitTargetRisk"

    @pytest.mark.parametrize("profit_target", [0.05, 0.10, 0.15, 0.20, 0.25, 0.50])
    def test_init_various_limits(self, profit_target):
        """Test initialization with various profit targets."""
        risk = ProfitTargetRisk(profit_target=profit_target)
        assert risk.profit_target == profit_target


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskOrderProcessing:
    """Test ProfitTargetRisk order processing."""

    def test_cal_order_passthrough(self, sample_portfolio_info, sample_order):
        """Test that LONG orders pass through unchanged."""
        risk = _make_risk()
        result = risk.cal(sample_portfolio_info, sample_order)
        assert result == sample_order

    @pytest.mark.parametrize("volume", [100, 500, 1000, 5000])
    def test_cal_various_order_volumes(self, sample_portfolio_info, volume):
        """Test order processing with various volumes."""
        risk = _make_risk()
        order = Order(
            portfolio_id="test_portfolio_id",
            engine_id="test_engine_id",
            run_id="test_run_id",
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
class TestProfitLimitRiskSignalGeneration:
    """Test ProfitTargetRisk signal generation logic."""

    def test_generate_signals_no_position(self):
        """Test no signals when no positions exist."""
        risk = _make_risk()
        portfolio_info = _make_portfolio_info(positions={})
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_generate_signals_zero_profit(self):
        """Test no signals when profit_loss_ratio is zero."""
        risk = _make_risk()

        position = _make_dict_position(profit_loss_ratio=0.0)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskProfitCalculation:
    """Test profit ratio threshold behavior."""

    @pytest.mark.parametrize("profit_ratio", [0.10, 0.20, 0.50])
    def test_profit_below_target(self, profit_ratio):
        """Test no signal when profit is below target."""
        risk = ProfitTargetRisk(profit_target=0.99)  # Very high target (max is 1.0)

        position = _make_dict_position(profit_loss_ratio=profit_ratio)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskThresholds:
    """Test profit limit threshold behavior."""

    def test_profit_below_limit_no_signal(self):
        """Test no signal when profit is below threshold."""
        risk = ProfitTargetRisk(profit_target=0.15)

        # 10% profit (below 15% threshold)
        position = _make_dict_position(profit_loss_ratio=0.10)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_profit_above_limit_generates_signal(self):
        """Test signal generation when profit exceeds threshold."""
        risk = ProfitTargetRisk(profit_target=0.15)

        # 16% profit (exceeds 15% threshold)
        position = _make_dict_position(profit_loss_ratio=0.16)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        with patch("ginkgo.trading.risk_management.profit_target_risk.Signal") as MockSignal:
            mock_signal = Mock()
            MockSignal.return_value = mock_signal

            signals = risk.generate_signals(portfolio_info, event)

            assert len(signals) == 1
            assert signals[0] == mock_signal

            MockSignal.assert_called_once()
            call_kwargs = MockSignal.call_args[1]
            assert call_kwargs["code"] == "000001.SZ"
            assert call_kwargs["direction"] == DIRECTION_TYPES.SHORT
            assert call_kwargs["portfolio_id"] == "test_portfolio_id"
            assert call_kwargs["engine_id"] == "profit_target_risk"
            assert "Profit target reached" in call_kwargs["reason"]
            assert "16.0%" in call_kwargs["reason"]

    def test_loss_no_signal(self):
        """Test no signal when position is losing."""
        risk = ProfitTargetRisk(profit_target=0.15)

        position = _make_dict_position(profit_loss_ratio=-0.10)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    @pytest.mark.parametrize("target,profit_ratio,should_signal", [
        (0.05, 0.06, True),    # Exceeds limit
        (0.10, 0.11, True),    # Exceeds limit
        (0.15, 0.14, False),   # Below limit
        (0.20, 0.19, False),   # Below limit
    ])
    def test_various_thresholds(self, target, profit_ratio, should_signal):
        """Test various profit target thresholds."""
        risk = ProfitTargetRisk(profit_target=target)

        position = _make_dict_position(profit_loss_ratio=profit_ratio)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        with patch("ginkgo.trading.risk_management.profit_target_risk.Signal") as MockSignal:
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
class TestProfitLimitRiskEdgeCases:
    """Test ProfitTargetRisk edge cases and error handling."""

    def test_non_price_event(self):
        """Test behavior with non-price events."""
        risk = _make_risk()

        # Mock event without 'code' attribute
        non_price_event = Mock(spec=[])  # No attributes

        position = _make_dict_position(profit_loss_ratio=0.20)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )

        signals = risk.generate_signals(portfolio_info, non_price_event)
        assert len(signals) == 0

    def test_event_code_not_in_positions(self):
        """Test behavior when event code is not in positions."""
        risk = _make_risk()

        position = _make_dict_position(profit_loss_ratio=0.20)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        # Event for a different stock
        event = _make_price_event(code="999999.SZ")

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0

    def test_init_invalid_negative_target(self):
        """Test that negative profit target raises ValueError."""
        with pytest.raises(ValueError, match="正数"):
            ProfitTargetRisk(profit_target=-0.1)

    def test_init_invalid_zero_target(self):
        """Test that zero profit target raises ValueError."""
        with pytest.raises(ValueError, match="正数"):
            ProfitTargetRisk(profit_target=0.0)

    def test_init_target_exceeds_one(self):
        """Test that profit target > 1.0 raises ValueError."""
        with pytest.raises(ValueError, match="100%"):
            ProfitTargetRisk(profit_target=1.5)


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskFinancialAccuracy:
    """Test financial calculation accuracy."""

    @pytest.mark.parametrize("profit_target,profit_ratio,should_trigger", [
        (0.10, 0.10, True),   # Exactly at threshold (source uses >=)
        (0.15, 0.15, True),   # Exactly at threshold
        (0.20, 0.20, True),   # Exactly at threshold
        (0.10, 0.099, False), # Just below
        (0.15, 0.149, False), # Just below
    ])
    def test_profit_ratio_precision(self, profit_target, profit_ratio, should_trigger):
        """Test profit ratio calculation and threshold comparison."""
        risk = ProfitTargetRisk(profit_target=profit_target)

        position = _make_dict_position(profit_loss_ratio=profit_ratio)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        with patch("ginkgo.trading.risk_management.profit_target_risk.Signal") as MockSignal:
            MockSignal.return_value = Mock()

            signals = risk.generate_signals(portfolio_info, event)

            if should_trigger:
                assert len(signals) == 1
                assert MockSignal.called
            else:
                assert len(signals) == 0
                assert not MockSignal.called

    def test_partial_take_profit_signal(self):
        """Test partial take profit signal generation."""
        risk = ProfitTargetRisk(
            profit_target=0.15,
            partial_take_profit=True,
            partial_ratio=0.5,
        )

        position = _make_dict_position(profit_loss_ratio=0.20)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        with patch("ginkgo.trading.risk_management.profit_target_risk.Signal") as MockSignal:
            mock_signal = Mock()
            MockSignal.return_value = mock_signal

            signals = risk.generate_signals(portfolio_info, event)

            assert len(signals) == 1
            # Verify partial take profit reason
            call_kwargs = MockSignal.call_args[1]
            assert "Partial profit target reached" in call_kwargs["reason"]
            # Verify volume_ratio is set
            assert mock_signal.volume_ratio == 0.5


@pytest.mark.unit
@pytest.mark.risk
class TestProfitLimitRiskMultiplePositions:
    """Test behavior with multiple positions."""

    def test_multiple_positions_mixed_signals(self):
        """Test signal generation with multiple positions."""
        risk = ProfitTargetRisk(profit_target=0.15)

        position1 = _make_dict_position(profit_loss_ratio=0.10)  # Below
        position2 = _make_dict_position(profit_loss_ratio=0.20, volume=500)  # Above

        portfolio_info = _make_portfolio_info(
            positions={
                "000001.SZ": position1,
                "000002.SZ": position2,
            }
        )

        # Event for stock 1 (below threshold)
        event1 = _make_price_event(code="000001.SZ")
        signals = risk.generate_signals(portfolio_info, event1)
        assert len(signals) == 0  # Below threshold

        # Event for stock 2 (above threshold)
        event2 = _make_price_event(code="000002.SZ")

        with patch("ginkgo.trading.risk_management.profit_target_risk.Signal") as MockSignal:
            mock_signal = Mock()
            MockSignal.return_value = mock_signal

            signals = risk.generate_signals(portfolio_info, event2)
            assert len(signals) == 1  # Exceeds threshold
            call_kwargs = MockSignal.call_args[1]
            assert call_kwargs["code"] == "000002.SZ"


@pytest.mark.unit
@pytest.mark.risk
@pytest.mark.financial
class TestProfitLimitRiskBreakEven:
    """Test break-even scenarios."""

    def test_break_even_no_signal(self):
        """Test that break-even (no profit, no loss) doesn't trigger signal."""
        risk = ProfitTargetRisk(profit_target=0.15)

        position = _make_dict_position(profit_loss_ratio=0.0)
        portfolio_info = _make_portfolio_info(
            positions={"000001.SZ": position}
        )
        event = _make_price_event()

        signals = risk.generate_signals(portfolio_info, event)
        assert len(signals) == 0  # No profit = no signal
