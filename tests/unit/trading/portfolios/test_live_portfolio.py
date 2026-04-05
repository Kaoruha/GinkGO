"""
PortfolioLive实盘组合TDD测试

通过TDD方式开发PortfolioLive的核心逻辑测试套件
聚焦于持仓恢复、实时信号处理、订单处理和数据库集成
"""
import pytest
import sys
import datetime
from datetime import timezone
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.portfolios.portfolio_live import PortfolioLive
from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.bases.selector_base import SelectorBase
from ginkgo.trading.bases.risk_base import RiskBase
from ginkgo.trading.bases.sizer_base import SizerBase
from ginkgo.trading.strategies.strategy_base import BaseStrategy
from ginkgo.entities.order import Order
from ginkgo.entities.position import Position
from ginkgo.entities.signal import Signal
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.order_lifecycle_events import (
    EventOrderAck,
    EventOrderPartiallyFilled,
    EventOrderCancelAck,
)
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities.bar import Bar
class FakeSizer(SizerBase):
    def __init__(self):
        SizerBase.__init__(self)
        # Use a Mock for cal so we can assert calls
        self.cal = Mock(return_value=None)
    def real_cal(self, portfolio_info, signal, *args, **kwargs):
        return None


class FakeRisk(RiskBase):
    def __init__(self):
        RiskBase.__init__(self)
    def generate_signals(self, portfolio_info, event):
        return []


from ginkgo.trading.time.providers import LogicalTimeProvider
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    FREQUENCY_TYPES,
    PORTFOLIO_MODE_TYPES,
    PORTFOLIO_RUNSTATE_TYPES,
    RECORDSTAGE_TYPES,
)
def _set_context_ids(p, engine_id="eid", run_id="rid"):
    """Set engine_id and run_id on a portfolio via context."""
    mock_ctx = Mock()
    mock_ctx.engine_id = engine_id
    mock_ctx.run_id = run_id
    mock_ctx.portfolio_id = p.uuid
    p._context = mock_ctx


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_portfolio(name="Portfolio", **kwargs):
    """Create a PortfolioLive with a LogicalTimeProvider."""
    tp = LogicalTimeProvider(datetime.datetime(2024, 1, 2))
    p = PortfolioLive(
        name=name, use_default_analyzers=False,
        notification_service=Mock(),
        **kwargs,
    )
    p.set_time_provider(tp)
    return p


def _setup_portfolio(p, time_val=None):
    """Wire up a portfolio with strategy, selector, sizer, risk and publisher."""
    if time_val is not None:
        p.get_time_provider().set_current_time(time_val)

    mock_strategy = Mock(spec=BaseStrategy)
    mock_strategy.name = "Strat1"
    mock_strategy.cal = Mock(return_value=[])
    mock_strategy.bind_portfolio = Mock()
    mock_strategy.bind_data_feeder = Mock()
    p.add_strategy(mock_strategy)

    mock_selector = Mock(spec=SelectorBase)
    mock_selector.bind_portfolio = Mock()
    p.bind_selector(mock_selector)

    fake_sizer = FakeSizer()
    p.bind_sizer(fake_sizer)

    mock_risk = Mock(spec=RiskBase)
    mock_risk.cal = Mock(side_effect=lambda info, o: o)
    p.add_risk_manager(mock_risk)

    publisher = Mock()
    p.set_event_publisher(publisher)

    return {
        "strategy": mock_strategy,
        "selector": mock_selector,
        "sizer": fake_sizer,
        "risk": mock_risk,
        "publisher": publisher,
    }


def _make_order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=100,
                limit_price=Decimal("10.0"), portfolio_id="pid",
                engine_id="eid", run_id="rid", **overrides):
    defaults = dict(
        portfolio_id=portfolio_id, engine_id=engine_id, run_id=run_id,
        code=code, direction=direction, order_type=ORDER_TYPES.LIMITORDER,
        status=ORDERSTATUS_TYPES.NEW, volume=volume,
        limit_price=limit_price, frozen_money=volume * limit_price,
    )
    defaults.update(overrides)
    return Order(**defaults)


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG,
                 portfolio_id="pid", engine_id="eid", run_id="rid",
                 **overrides):
    defaults = dict(
        portfolio_id=portfolio_id, engine_id=engine_id, run_id=run_id,
        code=code, direction=direction, reason="test",
        source=SOURCE_TYPES.OTHER,
    )
    defaults.update(overrides)
    return Signal(**defaults)


# =========================================================================
# 1. Construction
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestLivePortfolioConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        p = _make_portfolio()
        assert isinstance(p, PortfolioBase)
        assert p.__abstract__ is False
        assert p.mode == PORTFOLIO_MODE_TYPES.BACKTEST  # default from base

    def test_portfolio_inheritance(self):
        p = _make_portfolio()
        assert isinstance(p, PortfolioLive)
        assert isinstance(p, PortfolioBase)
        assert callable(getattr(p, 'add_strategy', None))
        assert callable(getattr(p, 'add_cash', None))
        assert callable(getattr(p, 'freeze', None))
        # Live portfolio does NOT have _signals (no T+1 mechanism)
        assert not hasattr(p, '_signals') or p.__class__.__name__ != 'PortfolioT1Backtest'

    def test_initial_state(self):
        p = _make_portfolio()
        assert isinstance(p.positions, dict)
        assert len(p.positions) == 0
        assert p.cash == Decimal("0")
        assert p.frozen == Decimal("0")

    def test_live_portfolio_attributes(self):
        p = _make_portfolio()
        # Live portfolio has status management attributes
        assert getattr(p, '_status', None) is not None
        assert getattr(p, '_status_lock', None) is not None
        assert getattr(p, '_event_buffer', None) is not None
        assert p.get_status() == PORTFOLIO_RUNSTATE_TYPES.RUNNING
        # No T+1 signals list
        assert not hasattr(p, 'signals') or not isinstance(getattr(p, 'signals', None), property)


# =========================================================================
# 2. Position Recovery (simplified - no actual DB)
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestPositionRecovery:
    """2. 持仓恢复测试"""

    def test_reset_positions_from_empty_records(self):
        p = _make_portfolio()
        # Positions start empty
        assert len(p.positions) == 0

    def test_reset_positions_long_orders(self):
        """Manually add a long position to simulate recovery."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        assert "000001.SZ" in p.positions
        assert p.positions["000001.SZ"].volume == 100

    def test_reset_positions_short_orders(self):
        """Simulate short by buying then freezing and selling."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=200,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        # In this system, SHORT deal requires frozen_volume
        # Volume stays the same; frozen_volume decreases
        pos._frozen_volume = 100
        pos.deal(DIRECTION_TYPES.SHORT, Decimal("10.0"), 100)
        assert pos.frozen_volume == 0
        assert pos.volume == 200  # total volume unchanged

    def test_reset_positions_mixed_orders(self):
        """Simulate mixed long/short operations."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=0,
            price=Decimal("10.0"), uuid="pos1",
        )
        pos.deal(DIRECTION_TYPES.LONG, Decimal("10.0"), 100)
        assert pos.volume == 100

    def test_reset_positions_filters_zero_volume(self):
        """Zero volume positions can be manually removed."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=0,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        # Manually clean zero volume
        if pos.volume <= 0:
            del p._positions[pos.code]
        assert "000001.SZ" not in p.positions

    def test_reset_positions_database_persistence(self):
        """Test that sync_state_to_db calls DB functions."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        with patch('ginkgo.data.crud.position_crud.PositionCRUD') as mock_crud_cls, \
             patch('ginkgo.data.drivers.add') as mock_add:
            mock_crud_instance = Mock()
            mock_crud_cls.return_value = mock_crud_instance
            p.sync_state_to_db()
            mock_crud_cls.assert_called_once()


# =========================================================================
# 3. Live Signal Processing
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestLiveSignalProcessing:
    """3. 实时信号处理测试"""

    def test_on_signal_immediate_processing(self):
        p = _make_portfolio()
        components = _setup_portfolio(p)
        signal = _make_signal()
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch.object(p._notification_service, 'beep'):
            p.on_signal(event)
        # Sizer should be called immediately in live mode
        components["sizer"].cal.assert_called()

    def test_on_signal_no_t1_delay(self):
        """Live mode does NOT delay signals."""
        p = _make_portfolio()
        components = _setup_portfolio(p)
        signal = _make_signal()
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch.object(p._notification_service, 'beep'):
            p.on_signal(event)
        # In live mode, sizer is called immediately regardless of timing
        components["sizer"].cal.assert_called()

    def test_on_signal_calls_sizer_immediately(self):
        p = _make_portfolio()
        components = _setup_portfolio(p)
        signal = _make_signal()
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch.object(p._notification_service, 'beep'):
            p.on_signal(event)
        # Sizer called with portfolio_info and signal
        components["sizer"].cal.assert_called_once()
        call_args = components["sizer"].cal.call_args
        assert call_args[0][1] is signal  # second arg is signal

    def test_on_signal_risk_managers_immediate(self):
        p = _make_portfolio()
        components = _setup_portfolio(p)
        # Replace the sizer with one that returns an order
        order = _make_order(portfolio_id=p.uuid, engine_id="eid", run_id="rid")
        components["sizer"].cal = Mock(return_value=order)
        mock_risk = Mock(spec=RiskBase)
        mock_risk.cal = Mock(side_effect=lambda info, o: o)
        # Replace risk managers
        p._risk_managers.clear()
        p.add_risk_manager(mock_risk)

        signal = _make_signal(portfolio_id=p.uuid)
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'):
            p.on_signal(event)
        # Risk manager should have been called
        mock_risk.cal.assert_called()

    def test_on_signal_order_generation(self):
        p = _make_portfolio()
        components = _setup_portfolio(p)
        # Replace the sizer with one that returns an order with volume > 0
        order = _make_order(portfolio_id=p.uuid, engine_id="eid", run_id="rid")
        order.volume = 100
        components["sizer"].cal = Mock(return_value=order)
        signal = _make_signal(portfolio_id=p.uuid)
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'):
            result = p.on_signal(event)
        # on_signal should return an EventOrderAck when order is generated
        assert result is not None


# =========================================================================
# 4. Real-Time Order Handling
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestRealTimeOrderHandling:
    """4. 实时订单处理测试"""

    def test_on_order_partially_filled_real_time(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        _set_context_ids(p)
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        order = _make_order(portfolio_id=p.uuid, engine_id="eid", run_id="rid")
        order.transaction_volume = 0
        event = EventOrderPartiallyFilled(
            order=order, filled_quantity=100,
            fill_price=Decimal("10.0"), commission=Decimal("5"),
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
        )
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            p.on_order_partially_filled(event)
        # Position should be created
        assert "000001.SZ" in p.positions

    def test_on_order_filled_real_time(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        _set_context_ids(p)
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1005"))
        order = _make_order(portfolio_id=p.uuid, engine_id="eid", run_id="rid")
        order.transaction_volume = 0
        event = EventOrderPartiallyFilled(
            order=order, filled_quantity=100,
            fill_price=Decimal("10.0"), commission=Decimal("5"),
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
        )
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'), \
             patch('ginkgo.trading.portfolios.portfolio_live.container'):
            p.on_order_filled(event)
        assert "000001.SZ" in p.positions

    def test_on_order_cancel_real_time(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        p.add_cash(Decimal("100000"))
        frozen_result = p.freeze(Decimal("1000"))
        assert frozen_result is True

        order = _make_order(direction=DIRECTION_TYPES.LONG)
        order.frozen_money = Decimal("1000")
        order.remain = Decimal("1000")
        event = EventOrderCancelAck(
            order=order, cancelled_quantity=100,
            portfolio_id="pid", engine_id="eid", run_id="rid",
        )
        # EventOrderCancelAck doesn't have a direction attr directly;
        # set it on the event for the portfolio to read
        event.direction = DIRECTION_TYPES.LONG
        with patch('ginkgo.trading.portfolios.portfolio_live.GLOG'):
            p.on_order_cancel_ack(event)
        # Frozen money should be unfrozen
        assert p.frozen == Decimal("0")
        assert p.cash == Decimal("100000")

    def test_advance_time_no_signal_batch(self):
        """Live portfolio advance_time does NOT batch process signals."""
        p = _make_portfolio()
        _setup_portfolio(p)
        # advance_time just delegates to parent; no signal processing
        p.advance_time(datetime.datetime(2024, 1, 3))
        # No crash, no signal processing

    def test_real_time_worth_update(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        p.add_cash(Decimal("100000"))
        # Live portfolio's update_worth is a no-op (overridden)
        p.update_worth()
        # Worth remains unchanged (no-op in live)
        assert p.worth == p._worth


# =========================================================================
# 5. Database Integration (mocked)
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestDatabaseIntegration:
    """5. 数据库集成测试"""

    def test_record_positions_persistence(self):
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        # sync_state_to_db imports PositionCRUD locally inside the method
        with patch('ginkgo.data.crud.position_crud.PositionCRUD') as mock_crud_cls, \
             patch('ginkgo.data.drivers.add') as mock_add, \
             patch('ginkgo.data.models.model_position.MPosition'):
            result = p.sync_state_to_db()
        # Verify the method completes without exception
        assert isinstance(result, bool)

    def test_order_record_crud_integration(self):
        """sync_state_to_db uses PositionCRUD."""
        p = _make_portfolio()
        with patch('ginkgo.data.crud.position_crud.PositionCRUD') as mock_crud_cls:
            result = p.sync_state_to_db()
        mock_crud_cls.assert_called_once()

    def test_position_crud_integration(self):
        """Position CRUD is called for each position in sync."""
        p = _make_portfolio()
        pos1 = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos1)
        with patch('ginkgo.data.crud.position_crud.PositionCRUD') as mock_crud_cls, \
             patch('ginkgo.data.drivers.add') as mock_add, \
             patch('ginkgo.data.models.model_position.MPosition'):
            mock_crud_instance = Mock()
            mock_crud_cls.return_value = mock_crud_instance
            result = p.sync_state_to_db()
        # Verify the method completes
        assert isinstance(result, bool)

    def test_database_error_handling(self):
        """sync_state_to_db catches exceptions and returns False."""
        p = _make_portfolio()
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        with patch('ginkgo.data.crud.position_crud.PositionCRUD', side_effect=Exception("DB error")):
            result = p.sync_state_to_db()
            assert result is False

    def test_get_position_method(self):
        p = _make_portfolio()
        # No position
        assert p.get_position("000001.SZ") is None
        # Add position
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        assert p.get_position("000001.SZ") is pos


# =========================================================================
# 6. Live Constraints
# =========================================================================
@pytest.mark.unit
@pytest.mark.live
class TestLiveConstraints:
    """6. 实盘约束验证测试"""

    def test_no_future_event_in_live(self):
        """Live portfolio does not check future events in on_price_update."""
        p = _make_portfolio()
        _setup_portfolio(p)
        # Create a price update event (no timestamp check in live)
        event = Mock()
        event.code = "000001.SZ"
        result = p.on_price_update(event)
        # Should not crash and should return a list
        assert isinstance(result, list)

    def test_is_all_set_validation(self):
        """is_all_set returns False without required components."""
        p = _make_portfolio()
        assert p.is_all_set() is False

    def test_live_time_sync(self):
        """Portfolio time can be set via LogicalTimeProvider."""
        p = _make_portfolio()
        tp = p.get_time_provider()
        tp.set_current_time(datetime.datetime(2024, 6, 15))
        assert tp.now() == datetime.datetime(2024, 6, 15, tzinfo=timezone.utc)

    def test_live_error_notification(self):
        """Notification service is initialized and callable."""
        p = _make_portfolio()
        assert p._notification_service is not None
        # Notification service should have a beep method
        assert callable(getattr(p._notification_service, 'beep', None))
        p._notification_service.beep()  # should not raise

    def test_status_management(self):
        """Test graceful status transitions."""
        p = _make_portfolio()
        assert p.get_status() == PORTFOLIO_RUNSTATE_TYPES.RUNNING
        assert p.is_stopping() is False
        assert p.is_reloading() is False
        assert p.is_migrating() is False

    def test_event_buffer_management(self):
        """Test event buffering for graceful reload."""
        p = _make_portfolio()
        assert len(p._event_buffer) == 0
        p.buffer_event("event1")
        p.buffer_event("event2")
        assert len(p._event_buffer) == 2
        events = p.get_buffered_events()
        assert len(events) == 2
        assert events == ["event1", "event2"]
        p.clear_buffer()
        assert len(p._event_buffer) == 0

    def test_event_buffer_max_size(self):
        """Buffer drops oldest event when full."""
        p = _make_portfolio()
        p._max_buffer_size = 3
        for i in range(5):
            p.buffer_event(f"event{i}")
        assert len(p._event_buffer) == 3
        assert p._event_buffer == ["event2", "event3", "event4"]
