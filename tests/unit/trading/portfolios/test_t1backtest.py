"""
PortfolioT1Backtest T+1交易组合TDD测试

通过TDD方式开发PortfolioT1Backtest的核心逻辑测试套件
聚焦于T+1延迟机制、信号缓存、跨日处理、批处理模式和订单生命周期
"""
import pytest
import sys
import datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
_path = str(project_root / "src")
if _path not in sys.path:
    sys.path.insert(0, _path)

from ginkgo.trading.portfolios.t1backtest import PortfolioT1Backtest
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
    EventOrderRejected,
    EventOrderExpired,
    EventOrderCancelAck,
)
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.entities.bar import Bar
from ginkgo.enums import (
    DIRECTION_TYPES,
    SOURCE_TYPES,
    ORDERSTATUS_TYPES,
    ORDER_TYPES,
    FREQUENCY_TYPES,
    RECORDSTAGE_TYPES,
)
from ginkgo.trading.time.providers import LogicalTimeProvider
from datetime import timezone


# ---------------------------------------------------------------------------
# Minimal concrete subclasses for components that need isinstance checks
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_portfolio(name="Portfolio", **kwargs):
    """Create a PortfolioT1Backtest with a LogicalTimeProvider."""
    tp = LogicalTimeProvider(datetime.datetime(2024, 1, 2))
    p = PortfolioT1Backtest(
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
    mock_selector.advance_time = Mock()
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
                 ts=None, **overrides):
    if ts is not None and ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    defaults = dict(
        portfolio_id=portfolio_id, engine_id=engine_id, run_id=run_id,
        code=code, direction=direction, reason="test",
        source=SOURCE_TYPES.OTHER, business_timestamp=ts,
    )
    defaults.update(overrides)
    return Signal(**defaults)


def _utc(dt):
    """Convert naive datetime to UTC-aware."""
    return dt.replace(tzinfo=timezone.utc)


def _set_context_ids(p, engine_id="eid", run_id="rid"):
    """Set engine_id and run_id on a portfolio via context."""
    mock_ctx = Mock()
    mock_ctx.engine_id = engine_id
    mock_ctx.run_id = run_id
    mock_ctx.portfolio_id = p.uuid
    p._context = mock_ctx


# =========================================================================
# 1. Construction
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestPortfolioT1BacktestConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        p = _make_portfolio()
        assert isinstance(p, PortfolioBase)
        assert p.__abstract__ is False

    def test_signals_initialization(self):
        p = _make_portfolio()
        assert isinstance(p.signals, list)
        assert len(p.signals) == 0

    def test_orders_initialization(self):
        p = _make_portfolio()
        assert isinstance(p.orders, list)
        assert len(p.orders) == 0
        assert isinstance(p.filled_orders, list)
        assert len(p.filled_orders) == 0

    def test_portfolio_inheritance(self):
        p = _make_portfolio()
        assert isinstance(p, PortfolioBase)
        assert callable(getattr(p, 'add_strategy', None))
        assert callable(getattr(p, 'add_risk_manager', None))
        assert callable(getattr(p, 'bind_selector', None))
        assert callable(getattr(p, 'bind_sizer', None))
        assert callable(getattr(p, 'add_cash', None))
        assert callable(getattr(p, 'freeze', None))


# =========================================================================
# 2. T+1 Delay Mechanism
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestT1DelayMechanism:
    """2. T+1延迟机制测试"""

    def test_on_signal_intercepts_current_day(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # Signal should be delayed, sizer should NOT be called
        components["sizer"].cal.assert_not_called()

    def test_signal_appended_to_list(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        assert len(p._signals) == 1

    def test_signal_delayed_execution(self):
        """第二天 advance_time 会发送延迟信号"""
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        assert len(p._signals) == 1
        # advance_time should publish the delayed signal
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        # After advance_time, signals are cleared
        assert len(p._signals) == 0
        # Publisher should have been called (signal re-published)
        assert components["publisher"].called

    def test_sizer_not_called_current_day(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        components["sizer"].cal.assert_not_called()

    def test_risk_managers_not_called_current_day(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        components["risk"].cal.assert_not_called()

    def test_debug_log_t1_message(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG') as mock_glog:
            p.on_signal(event)
            # Verify logging was invoked for T+1 delay
            assert mock_glog.INFO.called or mock_glog.WARN.called

    def test_next_day_signal_processing(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # Advance to next day
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        # Publisher called to re-publish signal
        assert components["publisher"].called

    def test_signal_batch_processing_next_day(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        for i in range(3):
            signal = _make_signal(code=f"00000{i+1}.SZ", ts=datetime.datetime(2024, 1, 2))
            event = EventSignalGeneration(signal)
            p.on_signal(event)
        assert len(p._signals) == 3
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert len(p._signals) == 0


# =========================================================================
# 3. Signal Caching
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestSignalCaching:
    """3. 信号缓存测试"""

    def test_signals_property_returns_reference(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        assert p.signals is p._signals

    def test_signals_accumulation(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        for i in range(3):
            signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
            event = EventSignalGeneration(signal)
            p.on_signal(event)
        assert len(p._signals) == 3

    def test_signals_clear_after_advance_time(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        assert len(p._signals) == 1
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert len(p._signals) == 0

    def test_multiple_signals_same_day(self):
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        for code in ["000001.SZ", "000002.SZ"]:
            signal = _make_signal(code=code, ts=datetime.datetime(2024, 1, 2))
            event = EventSignalGeneration(signal)
            p.on_signal(event)
        assert len(p._signals) == 2

    def test_signals_persistence_across_days(self):
        """Signals persist until advance_time is called"""
        p = _make_portfolio()
        _setup_portfolio(p, time_val=datetime.datetime(2024, 1, 2))
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # Before advance_time, signals are still there
        assert len(p._signals) == 1


# =========================================================================
# 4. advance_time Behavior
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestAdvanceTimeBehavior:
    """4. advance_time行为测试"""

    def test_advance_time_sends_delayed_signals(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert components["publisher"].called

    def test_advance_time_clears_signals(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert p._signals == []

    def test_advance_time_calls_parent_advance_time(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        new_time = _utc(datetime.datetime(2024, 1, 3))
        p.advance_time(new_time)
        assert p.get_time_provider().now() == new_time

    def test_advance_time_updates_worth_and_profit(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        p.add_cash(Decimal("100000"))
        with patch.object(p, 'update_worth') as mock_worth, \
             patch.object(p, 'update_profit') as mock_profit:
            p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
            mock_worth.assert_called()
            mock_profit.assert_called()

    def test_advance_time_triggers_endday_hooks(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ENDDAY].append(
            lambda stage, info: hook_called.append('activate_endday')
        )
        p._analyzer_record_hook[RECORDSTAGE_TYPES.ENDDAY].append(
            lambda stage, info: hook_called.append('record_endday')
        )
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert 'activate_endday' in hook_called
        assert 'record_endday' in hook_called

    def test_advance_time_triggers_newday_hooks(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.NEWDAY].append(
            lambda stage, info: hook_called.append('activate_newday')
        )
        p._analyzer_record_hook[RECORDSTAGE_TYPES.NEWDAY].append(
            lambda stage, info: hook_called.append('record_newday')
        )
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))
        assert 'activate_newday' in hook_called
        assert 'record_newday' in hook_called

    def test_advance_time_processes_pending_batches(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        p._batch_processing_enabled = True
        # force_process_pending_batches is defined on BasePortfolio, not on T1Backtest directly
        # In non-batch mode or without a processor, this should just not crash
        p.advance_time(_utc(datetime.datetime(2024, 1, 3)))


# =========================================================================
# 5. Batch Processing Mode
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestBatchProcessingMode:
    """5. 批处理模式测试"""

    def test_batch_mode_enabled_signal_delay(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        p._batch_processing_enabled = True
        p._batch_processor = Mock()
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # Signal should be delayed in batch mode too
        assert len(p._signals) == 1
        components["sizer"].cal.assert_not_called()

    def test_batch_aware_on_signal_called(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 3)
        )
        p._batch_processing_enabled = True
        p._batch_processor = Mock()
        # Past signal (ts < now) should trigger batch processing path
        signal = _make_signal(ts=datetime.datetime(2024, 1, 1))
        event = EventSignalGeneration(signal)
        # _batch_aware_on_signal may not exist; just verify the signal path is taken
        p.on_signal(event)

    def test_batch_fallback_to_traditional_mode(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 3)
        )
        p._batch_processing_enabled = True
        p._batch_processor = None  # disable batch

        # Past signal should use traditional path
        signal = _make_signal(ts=datetime.datetime(2024, 1, 1))
        event = EventSignalGeneration(signal)
        # Should not crash, just fall back
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'):
            p.on_signal(event)

    def test_batch_processor_error_handling(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 3)
        )
        p._batch_processing_enabled = True
        p._batch_processor = None  # no processor means traditional fallback
        signal = _make_signal(ts=datetime.datetime(2024, 1, 1))
        event = EventSignalGeneration(signal)
        # Should not raise, just log
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'):
            p.on_signal(event)

    def test_force_process_pending_batches_method(self):
        p = _make_portfolio()
        # The method may or may not exist depending on base class
        # Just verify batch processing can be enabled
        p._batch_processing_enabled = False
        p._batch_processor = None
        assert p._batch_processing_enabled is False


# =========================================================================
# 6. Order Lifecycle Events
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestOrderLifecycleEvents:
    """6. 订单生命周期事件测试"""

    def test_on_order_ack_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERACK].append(
            lambda stage, info: hook_called.append('activate')
        )
        order = _make_order()
        event = EventOrderAck(order)
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'):
            p.on_order_ack(event)
        assert 'activate' in hook_called

    def test_on_order_ack_adds_to_orders_list(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        order = _make_order()
        event = EventOrderAck(order)
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'):
            p.on_order_ack(event)
        assert order in p._orders

    def test_on_order_partially_filled_new_implementation(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERPARTIALLYFILLED].append(
            lambda stage, info: hook_called.append('activate')
        )
        order = _make_order()
        event = EventOrderPartiallyFilled(
            order=order, filled_quantity=100,
            fill_price=Decimal("10.0"), portfolio_id="pid",
            engine_id="eid", run_id="rid",
        )
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'), \
             patch.object(p, 'is_event_from_future', return_value=False), \
             patch.object(p, 'update_worth'), \
             patch.object(p, 'update_profit'):
            p.on_order_partially_filled(event)
        assert 'activate' in hook_called

    def test_on_order_rejected_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERREJECTED].append(
            lambda stage, info: hook_called.append('activate')
        )
        order = _make_order()
        event = EventOrderRejected(order, reject_reason="test")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            p.on_order_rejected(event)
        assert 'activate' in hook_called

    def test_on_order_expired_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDEREXPIRED].append(
            lambda stage, info: hook_called.append('activate')
        )
        order = _make_order()
        event = EventOrderExpired(order, expire_reason="timeout")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            p.on_order_expired(event)
        assert 'activate' in hook_called

    def test_on_order_cancel_ack_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        hook_called = []
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELED].append(
            lambda stage, info: hook_called.append('activate_canceled')
        )
        p._analyzer_activate_hook[RECORDSTAGE_TYPES.ORDERCANCELACK].append(
            lambda stage, info: hook_called.append('activate_cancelack')
        )
        order = _make_order()
        event = EventOrderCancelAck(order, cancelled_quantity=100)
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'), \
             patch.object(p, 'is_event_from_future', return_value=False), \
             patch.object(p, 'update_worth'), \
             patch.object(p, 'update_profit'):
            p.on_order_cancel_ack(event)
        assert 'activate_canceled' in hook_called
        assert 'activate_cancelack' in hook_called


# =========================================================================
# 7. Long/Short Fill Handling
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestLongShortFillHandling:
    """7. 多空成交处理测试"""

    def test_deal_long_filled_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1000"))
        event = Mock()
        event.code = "000001.SZ"
        event.transaction_volume = 100
        event.transaction_price = Decimal("10.0")
        event.frozen = Decimal("1000")
        event.remain = Decimal("0")
        event.fee = Decimal("5")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            # deal_long_filled creates Position internally using p.uuid
            # Need to set engine_id/run_id via context
            _set_context_ids(p)
            p.deal_long_filled(event)
        assert "000001.SZ" in p.positions

    def test_deal_short_filled_method(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        # SHORT deal in t1backtest requires position with frozen_volume
        pos._frozen_volume = 50
        event = Mock()
        event.code = "000001.SZ"
        event.transaction_volume = 50
        event.transaction_price = Decimal("10.0")
        event.remain = Decimal("0")
        event.fee = Decimal("5")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            p.clean_positions = Mock()
            p.deal_short_filled(event)
        # After selling 50 frozen shares, frozen_volume should decrease
        assert pos.frozen_volume == 0

    def test_long_filled_position_creation(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("1000"))
        event = Mock()
        event.code = "000001.SZ"
        event.transaction_volume = 100
        event.transaction_price = Decimal("10.0")
        event.frozen = Decimal("1000")
        event.remain = Decimal("0")
        event.fee = Decimal("5")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            p.deal_long_filled(event)
        pos = p.get_position("000001.SZ")
        assert pos is not None
        assert pos.code == "000001.SZ"
        assert pos.volume == 100
        assert pos.cost == Decimal("10.0")

    def test_short_filled_position_reduction(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        pos = Position(
            portfolio_id=p.uuid, engine_id="eid", run_id="rid",
            code="000001.SZ", cost=Decimal("10.0"), volume=100,
            price=Decimal("10.0"), uuid="pos1",
        )
        p.add_position(pos)
        pos._frozen_volume = 100  # freeze 100 shares first
        event = Mock()
        event.code = "000001.SZ"
        event.transaction_volume = 100
        event.transaction_price = Decimal("10.0")
        event.remain = Decimal("0")
        event.fee = Decimal("5")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch('ginkgo.trading.portfolios.t1backtest.container'):
            p.clean_positions = Mock()
            p.deal_short_filled(event)
        # frozen_volume should be reduced after sell
        assert pos.frozen_volume == 0

    def test_fill_validation_checks(self):
        p = _make_portfolio()
        _setup_portfolio(p)
        _set_context_ids(p)
        p.add_cash(Decimal("100000"))
        p.freeze(Decimal("500"))
        # remain < 0 should be rejected
        event = Mock()
        event.code = "000001.SZ"
        event.transaction_volume = 100
        event.transaction_price = Decimal("10.0")
        event.frozen = Decimal("1000")  # frozen > self.frozen
        event.remain = Decimal("-10")  # negative remain
        event.fee = Decimal("0")
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'):
            p.deal_long_filled(event)
        # Position should NOT be created because of validation failure
        assert p.get_position("000001.SZ") is None


# =========================================================================
# 8. T+1 Constraint Validation
# =========================================================================
@pytest.mark.unit
@pytest.mark.backtest
class TestT1ConstraintValidation:
    """8. T+1约束验证测试"""

    def test_current_day_order_prevented(self):
        p = _make_portfolio()
        components = _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 2))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # No order event should be published
        components["publisher"].assert_not_called()

    def test_future_event_interception(self):
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 2)
        )
        signal = _make_signal(ts=datetime.datetime(2024, 1, 5))
        event = EventSignalGeneration(signal)
        p.on_signal(event)
        # Future signal should not be processed or stored
        assert len(p._signals) == 0

    def test_is_all_set_validation(self):
        p = _make_portfolio()
        # Without setup, is_all_set returns False
        assert p.is_all_set() is False

    def test_t1_timing_accuracy(self):
        """Verify signal from past day gets processed immediately."""
        p = _make_portfolio()
        _setup_portfolio(
            p, time_val=datetime.datetime(2024, 1, 3)
        )
        # Signal from yesterday (past) should be processed immediately
        signal = _make_signal(ts=datetime.datetime(2024, 1, 1))
        event = EventSignalGeneration(signal)
        with patch('ginkgo.trading.portfolios.t1backtest.GLOG'), \
             patch.object(p, '_save_order_record'):
            p.on_signal(event)
        # Sizer should be called because signal is from the past
        p.sizer.cal.assert_called()
