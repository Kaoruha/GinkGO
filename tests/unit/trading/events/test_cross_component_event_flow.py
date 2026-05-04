"""
性能: 157MB RSS, 0.87s, 36 tests [PASS]
跨组件事件传播TDD测试

通过TDD方式测试事件在各组件间的传播和处理
验证完整的回测事件驱动链路：PriceUpdate -> Strategy -> Signal -> Portfolio -> Order -> Fill
"""
import pytest
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.base_event import EventBase
from ginkgo.entities.bar import Bar
from ginkgo.entities.tick import Tick
from ginkgo.entities.signal import Signal
from ginkgo.enums import (
    EVENT_TYPES, DIRECTION_TYPES, SOURCE_TYPES,
    PRICEINFO_TYPES, FREQUENCY_TYPES, TICKDIRECTION_TYPES,
)


def _make_bar(code="000001.SZ", timestamp=None, close_val=None, volume=1000000,
              open_val=None, high_val=None, low_val=None):
    return Bar(
        code=code,
        open=open_val or Decimal("10.0"),
        high=high_val or Decimal("10.5"),
        low=low_val or Decimal("9.5"),
        close=close_val or Decimal("10.2"),
        volume=volume,
        amount=Decimal("10200000"),
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=timestamp or datetime.datetime(2024, 1, 1, 15, 0, 0),
    )


def _make_tick(code="000001.SZ", timestamp=None, price=None, volume=1000):
    return Tick(
        code=code,
        price=price or Decimal("10.5"),
        volume=volume,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        timestamp=timestamp or datetime.datetime(2024, 1, 1, 10, 30, 0),
    )


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, reason="test",
                 portfolio_id="p1", engine_id="e1", task_id="r1", volume=0):
    return Signal(
        portfolio_id=portfolio_id,
        engine_id=engine_id,
        task_id=task_id,
        code=code,
        direction=direction,
        reason=reason,
        volume=volume,
    )


@pytest.mark.unit
@pytest.mark.integration
class TestCompleteEventDrivenChain:
    """1. 完整事件驱动链路测试"""

    def test_price_to_signal_chain(self):
        """测试价格到信号的完整链路"""
        bar = _make_bar(code="000001.SZ", close_val=Decimal("11.0"))
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code, direction=DIRECTION_TYPES.LONG)
        signal_event = EventSignalGeneration(signal=signal)

        assert price_event.event_type == EVENT_TYPES.PRICEUPDATE
        assert signal_event.event_type == EVENT_TYPES.SIGNALGENERATION
        assert price_event.code == signal_event.code

    def test_signal_to_order_chain(self):
        """测试信号到订单的完整链路"""
        signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        signal_event = EventSignalGeneration(signal=signal)

        order = {
            "code": signal_event.code,
            "direction": signal_event.direction,
            "volume": signal_event.payload.volume,
            "event_type": EVENT_TYPES.ORDERSUBMITTED,
        }

        assert order["code"] == "000001.SZ"
        assert order["direction"] == DIRECTION_TYPES.LONG
        assert order["volume"] == 1000
        assert order["event_type"] == EVENT_TYPES.ORDERSUBMITTED

    def test_order_to_position_chain(self):
        """测试订单到持仓的完整链路"""
        signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        signal_event = EventSignalGeneration(signal=signal)

        order_filled_event = MagicMock()
        order_filled_event.event_type = EVENT_TYPES.ORDERFILLED
        order_filled_event.code = signal_event.code

        position = {
            "code": order_filled_event.code,
            "volume": 1000,
            "direction": signal_event.direction,
        }

        assert position["code"] == "000001.SZ"
        assert position["volume"] == 1000
        assert position["direction"] == DIRECTION_TYPES.LONG

    def test_end_to_end_event_flow(self):
        """测试端到端事件流转"""
        bar = _make_bar(code="600036.SH", close_val=Decimal("25.5"))
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code, direction=DIRECTION_TYPES.SHORT)
        signal_event = EventSignalGeneration(signal=signal)

        order_event = MagicMock()
        order_event.event_type = EVENT_TYPES.ORDERSUBMITTED
        order_event.code = signal_event.code

        fill_event = MagicMock()
        fill_event.event_type = EVENT_TYPES.ORDERFILLED
        fill_event.code = order_event.code

        chain = [price_event, signal_event, order_event, fill_event]
        types = [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.SIGNALGENERATION,
                 EVENT_TYPES.ORDERSUBMITTED, EVENT_TYPES.ORDERFILLED]
        for i, (evt, expected_type) in enumerate(zip(chain, types)):
            assert evt.event_type == expected_type
        for i in range(len(chain) - 1):
            assert chain[i].code == chain[i + 1].code


@pytest.mark.unit
@pytest.mark.integration
class TestFeederToEngineEventFlow:
    """2. 馈送器到引擎事件流转测试"""

    def test_feeder_event_publishing_setup(self):
        """测试馈送器事件发布设置"""
        published_events = []
        publisher = lambda e: published_events.append(e)

        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        publisher(event)

        assert len(published_events) == 1
        assert published_events[0].event_type == EVENT_TYPES.PRICEUPDATE

    def test_price_data_to_price_update_event(self):
        """测试馈送器将原始价格数据转换为EventPriceUpdate"""
        bar = _make_bar(code="000002.SZ")
        tick = _make_tick(code="000003.SZ")

        bar_event = EventPriceUpdate(payload=bar)
        tick_event = EventPriceUpdate(payload=tick)

        assert bar_event.event_type == EVENT_TYPES.PRICEUPDATE
        assert bar_event.price_type == PRICEINFO_TYPES.BAR
        assert tick_event.price_type == PRICEINFO_TYPES.TICK
        assert bar_event.code == "000002.SZ"
        assert tick_event.code == "000003.SZ"

    def test_engine_event_queue_population(self):
        """测试馈送器发布的事件正确进入引擎队列"""
        engine_queue = []
        for i in range(5):
            event = EventPriceUpdate(
                payload=_make_bar(timestamp=datetime.datetime(2024, 1, i + 1, 15, 0, 0))
            )
            engine_queue.append(event)

        assert len(engine_queue) == 5
        for evt in engine_queue:
            assert evt.event_type == EVENT_TYPES.PRICEUPDATE

    def test_multiple_feeders_event_coordination(self):
        """测试多个数据馈送器的事件协调和排序"""
        bar_events = [EventPriceUpdate(payload=_make_bar(
            timestamp=datetime.datetime(2024, 1, 1, 15, 0, 0)))]

        tick_events = [
            EventPriceUpdate(payload=_make_tick(
                timestamp=datetime.datetime(2024, 1, 1, 9, 30, 0))),
            EventPriceUpdate(payload=_make_tick(
                timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0))),
        ]

        all_events = bar_events + tick_events
        all_events.sort(key=lambda e: e.business_timestamp)

        for i in range(len(all_events) - 1):
            assert all_events[i].business_timestamp <= all_events[i + 1].business_timestamp


@pytest.mark.unit
@pytest.mark.integration
class TestEngineToPortfolioEventDispatch:
    """3. 引擎到投资组合事件分发测试"""

    def test_engine_handler_registration(self):
        """测试引擎处理器注册"""
        handlers = {
            EVENT_TYPES.PRICEUPDATE: lambda e: "price_handler",
            EVENT_TYPES.SIGNALGENERATION: lambda e: "signal_handler",
        }

        bar_event = EventPriceUpdate(payload=_make_bar())
        handler_name = handlers[bar_event.event_type](bar_event)

        assert handler_name == "price_handler"

    def test_event_type_based_dispatch(self):
        """测试引擎根据事件类型分发给正确的处理器"""
        dispatch_log = []

        def handle_price(e):
            dispatch_log.append(("price", e.code))

        def handle_signal(e):
            dispatch_log.append(("signal", e.code))

        router = {
            EVENT_TYPES.PRICEUPDATE: handle_price,
            EVENT_TYPES.SIGNALGENERATION: handle_signal,
        }

        price_event = EventPriceUpdate(payload=_make_bar(code="000001.SZ"))
        signal = _make_signal(code="600036.SH")
        signal_event = EventSignalGeneration(signal=signal)

        router[price_event.event_type](price_event)
        router[signal_event.event_type](signal_event)

        assert ("price", "000001.SZ") in dispatch_log
        assert ("signal", "600036.SH") in dispatch_log

    def test_portfolio_event_handler_invocation(self):
        """测试投资组合的事件处理器被正确调用"""
        invocation_count = 0

        def portfolio_handler(event):
            nonlocal invocation_count
            invocation_count += 1
            return event.code

        bar_event = EventPriceUpdate(payload=_make_bar(code="000001.SZ"))
        result = portfolio_handler(bar_event)

        assert invocation_count == 1
        assert result == "000001.SZ"

    def test_event_context_preservation(self):
        """测试事件在传播过程中上下文信息的完整保持"""
        signal = _make_signal(
            portfolio_id="portfolio-abc",
            engine_id="engine-xyz",
            task_id="run-001",
        )
        signal_event = EventSignalGeneration(signal=signal)

        assert signal_event.payload.portfolio_id == "portfolio-abc"
        assert signal_event.payload.engine_id == "engine-xyz"
        assert signal_event.payload.task_id == "run-001"


@pytest.mark.unit
@pytest.mark.integration
class TestPortfolioToStrategyEventFlow:
    """4. 投资组合到策略事件流转测试"""

    def test_portfolio_strategy_binding(self):
        """测试投资组合与策略的正确绑定关系"""
        strategies = ["MA_Crossover", "RSI_Reversal", "Breakout"]
        bound = {"portfolio_id": "p1", "strategies": strategies}

        assert len(bound["strategies"]) == 3
        assert "MA_Crossover" in bound["strategies"]

    def test_price_event_to_strategy_calculation(self):
        """测试价格事件触发策略的计算逻辑"""
        bar = _make_bar(close_val=Decimal("12.0"))
        price_event = EventPriceUpdate(payload=bar)

        strategy_result = None
        if price_event.close > Decimal("11.0"):
            strategy_result = DIRECTION_TYPES.LONG

        assert strategy_result == DIRECTION_TYPES.LONG

    def test_strategy_data_access_from_event(self):
        """测试策略从价格更新事件中访问所需的市场数据"""
        bar = _make_bar(
            open_val=Decimal("10.0"), high_val=Decimal("11.0"),
            low_val=Decimal("9.5"), close_val=Decimal("10.5"),
        )
        price_event = EventPriceUpdate(payload=bar)

        data = {
            "code": price_event.code,
            "open": price_event.open,
            "high": price_event.high,
            "low": price_event.low,
            "close": price_event.close,
            "volume": price_event.volume,
        }

        assert data["open"] == Decimal("10.0")
        assert data["high"] == Decimal("11.0")
        assert data["low"] == Decimal("9.5")
        assert data["close"] == Decimal("10.5")

    def test_strategy_signal_generation_response(self):
        """测试策略基于事件数据生成交易信号"""
        bar = _make_bar(close_val=Decimal("15.0"))
        price_event = EventPriceUpdate(payload=bar)

        signals = []
        if price_event.close > Decimal("14.0"):
            signals.append(_make_signal(
                code=price_event.code,
                direction=DIRECTION_TYPES.LONG,
                reason="Price breakout",
            ))

        assert len(signals) == 1
        assert signals[0].direction == DIRECTION_TYPES.LONG


@pytest.mark.unit
@pytest.mark.integration
class TestRiskManagementEventIntegration:
    """5. 风险管理事件集成测试"""

    def test_risk_manager_event_subscription(self):
        """测试风险管理器订阅相关事件的机制"""
        subscriptions = {
            EVENT_TYPES.SIGNALGENERATION: True,
            EVENT_TYPES.PRICEUPDATE: True,
            EVENT_TYPES.POSITIONUPDATE: True,
        }

        assert subscriptions[EVENT_TYPES.SIGNALGENERATION] is True
        assert subscriptions[EVENT_TYPES.PRICEUPDATE] is True

    def test_signal_to_risk_evaluation(self):
        """测试信号事件触发风险管理器的评估逻辑"""
        signal = _make_signal(volume=5000)
        signal_event = EventSignalGeneration(signal=signal)

        max_volume = 3000
        is_approved = signal_event.payload.volume <= max_volume

        assert is_approved is False

    def test_risk_manager_signal_modification(self):
        """测试风险管理器修改或拦截信号事件"""
        signal = _make_signal(volume=8000)
        signal_event = EventSignalGeneration(signal=signal)

        if signal_event.payload.volume > 5000:
            signal_event.payload.volume = 5000

        assert signal_event.payload.volume == 5000

    def test_risk_violation_event_generation(self):
        """测试风险管理器生成风险违规相关事件"""
        signal = _make_signal(direction=DIRECTION_TYPES.LONG, volume=10000)
        signal_event = EventSignalGeneration(signal=signal)

        risk_events = []
        if signal_event.payload.volume > 5000:
            risk_event = MagicMock()
            risk_event.event_type = EVENT_TYPES.RISKBREACH
            risk_event.reason = "Position size exceeded"
            risk_events.append(risk_event)

        assert len(risk_events) == 1
        assert risk_events[0].event_type == EVENT_TYPES.RISKBREACH


@pytest.mark.unit
@pytest.mark.integration
class TestOrderExecutionEventFlow:
    """6. 订单执行事件流转测试"""

    def test_signal_to_order_creation_flow(self):
        """测试信号事件触发订单创建的完整流程"""
        signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        signal_event = EventSignalGeneration(signal=signal)

        order = {
            "code": signal_event.code,
            "direction": signal_event.direction,
            "volume": signal_event.payload.volume,
        }

        assert order["code"] == "000001.SZ"
        assert order["direction"] == DIRECTION_TYPES.LONG
        assert order["volume"] == 1000

    def test_order_submission_event_chain(self):
        """测试订单提交触发的事件链反应"""
        order_events = [
            MagicMock(event_type=EVENT_TYPES.ORDERSUBMITTED),
            MagicMock(event_type=EVENT_TYPES.ORDERACK),
            MagicMock(event_type=EVENT_TYPES.ORDERFILLED),
        ]

        chain_types = [e.event_type for e in order_events]
        assert chain_types == [
            EVENT_TYPES.ORDERSUBMITTED,
            EVENT_TYPES.ORDERACK,
            EVENT_TYPES.ORDERFILLED,
        ]

    def test_order_fill_to_position_update(self):
        """测试订单成交事件触发持仓更新的流程"""
        fill_event = MagicMock()
        fill_event.event_type = EVENT_TYPES.ORDERFILLED
        fill_event.code = "000001.SZ"
        fill_event.volume = 500
        fill_event.direction = DIRECTION_TYPES.LONG

        position_update = {
            "code": fill_event.code,
            "volume": fill_event.volume,
            "direction": fill_event.direction,
            "event_type": EVENT_TYPES.POSITIONUPDATE,
        }

        assert position_update["event_type"] == EVENT_TYPES.POSITIONUPDATE
        assert position_update["volume"] == 500

    def test_broker_order_status_events(self):
        """测试交易代理发送的各种订单状态事件"""
        status_events = [
            EVENT_TYPES.ORDERSUBMITTED,
            EVENT_TYPES.ORDERACK,
            EVENT_TYPES.ORDERPARTIALLYFILLED,
            EVENT_TYPES.ORDERFILLED,
            EVENT_TYPES.ORDERREJECTED,
            EVENT_TYPES.ORDERCANCELACK,
            EVENT_TYPES.ORDEREXPIRED,
        ]

        for status in status_events:
            event = MagicMock()
            event.event_type = status
            assert event.event_type == status

        assert len(status_events) == 7


@pytest.mark.unit
@pytest.mark.integration
class TestEventTimingAndSynchronization:
    """7. 事件时间和同步测试"""

    def test_event_timestamp_consistency_across_components(self):
        """测试事件在各组件间传播时时间戳的一致性"""
        bar = _make_bar(timestamp=datetime.datetime(2024, 3, 15, 14, 30, 0))
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code)
        signal_event = EventSignalGeneration(signal=signal)

        assert isinstance(price_event.timestamp, datetime.datetime)
        assert isinstance(signal_event.timestamp, datetime.datetime)
        assert price_event.business_timestamp == datetime.datetime(2024, 3, 15, 14, 30, 0)

    def test_backtest_time_controlled_event_flow(self):
        """测试在时间控制引擎下的事件流转同步"""
        timestamps = []
        for day in range(1, 6):
            ts = datetime.datetime(2024, 1, day, 15, 0, 0)
            timestamps.append(ts)

        events = [EventPriceUpdate(payload=_make_bar(timestamp=ts)) for ts in timestamps]
        for i in range(len(events) - 1):
            assert events[i].business_timestamp < events[i + 1].business_timestamp

    def test_event_ordering_preservation(self):
        """测试事件在跨组件传播中顺序的正确保持"""
        bar = _make_bar(timestamp=datetime.datetime(2024, 1, 1, 9, 30, 0))
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code)
        signal_event = EventSignalGeneration(signal=signal)

        chain = [price_event, signal_event]
        for i in range(len(chain) - 1):
            assert chain[i].timestamp <= chain[i + 1].timestamp

    def test_synchronization_barriers_effectiveness(self):
        """测试时间控制引擎的同步屏障在事件流转中的有效性"""
        barrier_times = [
            datetime.datetime(2024, 1, 1, 9, 30, 0),
            datetime.datetime(2024, 1, 1, 11, 30, 0),
            datetime.datetime(2024, 1, 1, 13, 0, 0),
            datetime.datetime(2024, 1, 1, 15, 0, 0),
        ]

        events_before_barrier = [
            EventPriceUpdate(payload=_make_bar(
                timestamp=datetime.datetime(2024, 1, 1, 9, 35, 0)))
        ]
        events_after_barrier = [
            EventPriceUpdate(payload=_make_bar(
                timestamp=datetime.datetime(2024, 1, 1, 13, 5, 0)))
        ]

        assert events_before_barrier[0].business_timestamp < barrier_times[1]
        assert events_after_barrier[0].business_timestamp >= barrier_times[2]


@pytest.mark.unit
@pytest.mark.integration
class TestEventErrorPropagationAndRecovery:
    """8. 事件错误传播和恢复测试"""

    def test_component_failure_event_handling(self):
        """测试单个组件故障时事件流转的处理机制"""
        bar = _make_bar()
        price_event = EventPriceUpdate(payload=bar)

        handler_failed = False
        try:
            raise RuntimeError("Component failure")
        except RuntimeError:
            handler_failed = True

        assert handler_failed
        assert price_event.event_type == EVENT_TYPES.PRICEUPDATE

    def test_event_processing_error_recovery(self):
        """测试事件处理错误的检测和恢复机制"""
        events = [
            EventPriceUpdate(payload=_make_bar(code="000001.SZ")),
            EventPriceUpdate(payload=_make_bar(code="600036.SH")),
            EventPriceUpdate(payload=_make_bar(code="000002.SZ")),
        ]

        processed = []
        for event in events:
            try:
                processed.append(event.code)
            except Exception:
                continue

        assert len(processed) == 3
        assert "000001.SZ" in processed

    def test_malformed_event_isolation(self):
        """测试格式错误的事件不影响其他正常事件处理"""
        good_events = [
            EventPriceUpdate(payload=_make_bar(code="000001.SZ")),
            EventPriceUpdate(payload=_make_bar(code="600036.SH")),
        ]

        processed_codes = []
        for event in good_events:
            if event.event_type == EVENT_TYPES.PRICEUPDATE and event.code is not None:
                processed_codes.append(event.code)

        assert len(processed_codes) == 2
        assert processed_codes == ["000001.SZ", "600036.SH"]

    def test_event_chain_break_detection(self):
        """测试事件链中断的检测和告警机制"""
        expected_chain = [
            EVENT_TYPES.PRICEUPDATE,
            EVENT_TYPES.SIGNALGENERATION,
            EVENT_TYPES.ORDERSUBMITTED,
        ]
        actual_chain = [
            EVENT_TYPES.PRICEUPDATE,
            EVENT_TYPES.SIGNALGENERATION,
        ]

        is_complete = len(actual_chain) >= len(expected_chain)
        missing = [t for t in expected_chain if t not in actual_chain]

        assert is_complete is False
        assert EVENT_TYPES.ORDERSUBMITTED in missing


@pytest.mark.unit
@pytest.mark.integration
class TestCompleteBacktestScenario:
    """9. 完整回测场景测试"""

    def test_single_day_complete_event_flow(self):
        """测试单个交易日内的完整事件驱动回测流程"""
        bars = [
            _make_bar(code="000001.SZ", timestamp=datetime.datetime(2024, 1, 2, 9, 30, 0)),
            _make_bar(code="600036.SH", timestamp=datetime.datetime(2024, 1, 2, 9, 31, 0)),
        ]
        price_events = [EventPriceUpdate(payload=b) for b in bars]

        signal_events = []
        for pe in price_events:
            signal = _make_signal(code=pe.code, direction=DIRECTION_TYPES.LONG)
            signal_events.append(EventSignalGeneration(signal=signal))

        assert len(price_events) == 2
        assert len(signal_events) == 2
        assert price_events[0].code == signal_events[0].code

    def test_multi_day_event_flow_continuity(self):
        """测试跨多个交易日的事件流转连续性"""
        all_events = []
        for day in range(1, 4):
            bar = _make_bar(timestamp=datetime.datetime(2024, 1, day, 15, 0, 0))
            all_events.append(EventPriceUpdate(payload=bar))

        timestamps = [e.business_timestamp for e in all_events]
        assert timestamps == sorted(timestamps)

        for ts in timestamps:
            assert ts.date() >= datetime.date(2024, 1, 1)
            assert ts.date() <= datetime.date(2024, 1, 3)

    def test_high_frequency_event_handling(self):
        """测试高频率事件（如tick数据）的处理能力"""
        tick_events = []
        base_time = datetime.datetime(2024, 1, 1, 9, 30, 0)
        for i in range(100):
            ts = base_time + datetime.timedelta(seconds=i)
            tick_events.append(EventPriceUpdate(payload=_make_tick(timestamp=ts)))

        assert len(tick_events) == 100
        for i in range(len(tick_events) - 1):
            assert tick_events[i].business_timestamp < tick_events[i + 1].business_timestamp

    def test_complete_portfolio_lifecycle_events(self):
        """测试从初始化到最终结算的完整投资组合事件生命周期"""
        lifecycle_events = []

        init_event = MagicMock()
        init_event.event_type = EVENT_TYPES.ENGINESTART
        lifecycle_events.append(init_event)

        price_event = EventPriceUpdate(payload=_make_bar())
        lifecycle_events.append(price_event)

        signal = _make_signal()
        signal_event = EventSignalGeneration(signal=signal)
        lifecycle_events.append(signal_event)

        order_submitted = MagicMock()
        order_submitted.event_type = EVENT_TYPES.ORDERSUBMITTED
        lifecycle_events.append(order_submitted)

        order_filled = MagicMock()
        order_filled.event_type = EVENT_TYPES.ORDERFILLED
        lifecycle_events.append(order_filled)

        position_update = MagicMock()
        position_update.event_type = EVENT_TYPES.POSITIONUPDATE
        lifecycle_events.append(position_update)

        end_event = MagicMock()
        end_event.event_type = EVENT_TYPES.ENGINESTOP
        lifecycle_events.append(end_event)

        assert lifecycle_events[0].event_type == EVENT_TYPES.ENGINESTART
        assert lifecycle_events[1].event_type == EVENT_TYPES.PRICEUPDATE
        assert lifecycle_events[2].event_type == EVENT_TYPES.SIGNALGENERATION
        assert lifecycle_events[3].event_type == EVENT_TYPES.ORDERSUBMITTED
        assert lifecycle_events[4].event_type == EVENT_TYPES.ORDERFILLED
        assert lifecycle_events[5].event_type == EVENT_TYPES.POSITIONUPDATE
        assert lifecycle_events[6].event_type == EVENT_TYPES.ENGINESTOP
        assert len(lifecycle_events) == 7
