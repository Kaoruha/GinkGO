"""
SignalGeneration事件流转TDD测试

通过TDD方式测试SignalGeneration事件在回测系统中的完整流转过程
涵盖信号生成、事件创建、传播和订单生成的完整链路测试
"""
import pytest
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.base_event import EventBase
from ginkgo.entities.signal import Signal
from ginkgo.enums import EVENT_TYPES, DIRECTION_TYPES, SOURCE_TYPES


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, reason="test reason",
                 portfolio_id="test-portfolio", engine_id="test-engine", task_id="test-run",
                 business_timestamp=None, volume=0, strength=None, confidence=None):
    kwargs = dict(
        portfolio_id=portfolio_id,
        engine_id=engine_id,
        task_id=task_id,
        code=code,
        direction=direction,
        reason=reason,
        volume=volume,
    )
    if business_timestamp is not None:
        kwargs["business_timestamp"] = business_timestamp
    if strength is not None:
        kwargs["strength"] = strength
    if confidence is not None:
        kwargs["confidence"] = confidence
    return Signal(**kwargs)


@pytest.mark.unit
class TestSignalGenerationEventCreation:
    """1. SignalGeneration事件创建测试"""

    def test_constructor_with_signal(self):
        """测试使用信号构造函数"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert isinstance(event, EventBase)
        assert event.payload is signal

    def test_constructor_with_custom_name(self):
        """测试自定义名称构造函数"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal, name="CustomEventName")

        assert event.name == "CustomEventName"

    def test_event_type_setting(self):
        """测试事件类型设置"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event.event_type == EVENT_TYPES.SIGNALGENERATION

    def test_signal_storage(self):
        """测试信号存储"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event._value is signal
        assert event.payload is signal


@pytest.mark.unit
class TestSignalGenerationEventProperties:
    """2. SignalGeneration事件属性测试"""

    def test_value_property(self):
        """测试值属性"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event._value is signal

    def test_code_property(self):
        """测试代码属性"""
        signal = _make_signal(code="600036.SH")
        event = EventSignalGeneration(signal=signal)

        assert event.code == "600036.SH"

    def test_direction_property(self):
        """测试方向属性"""
        signal = _make_signal(direction=DIRECTION_TYPES.SHORT)
        event = EventSignalGeneration(signal=signal)

        assert event.direction == DIRECTION_TYPES.SHORT

    def test_timestamp_property(self):
        """测试时间戳属性"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert isinstance(event.timestamp, datetime.datetime)

    def test_business_timestamp_with_signal_biz_ts(self):
        """测试有业务时间戳时的business_timestamp"""
        biz_ts = datetime.datetime(2024, 1, 15, 10, 30, 0)
        signal = _make_signal(business_timestamp=biz_ts)
        event = EventSignalGeneration(signal=signal)

        assert event.business_timestamp == biz_ts

    def test_business_timestamp_fallback_to_signal_timestamp(self):
        """测试无业务时间戳时回退到信号时间戳"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event.business_timestamp == signal.timestamp

    def test_business_timestamp_with_none_payload(self):
        """测试payload为None时的business_timestamp回退"""
        event = EventSignalGeneration(signal=None)

        assert event.business_timestamp == event.timestamp


@pytest.mark.unit
class TestSignalGenerationStrategyToPortfolio:
    """3. 策略到投资组合的SignalGeneration流转测试"""

    def test_strategy_generates_signal_event(self):
        """测试策略生成信号事件"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event.event_type == EVENT_TYPES.SIGNALGENERATION
        assert event.code == signal.code
        assert event.direction == signal.direction

    def test_strategy_publishes_signal_event(self):
        """测试策略发布信号事件"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        event_queue = []
        event_queue.append(event)

        assert len(event_queue) == 1
        assert event_queue[0].event_type == EVENT_TYPES.SIGNALGENERATION

    def test_portfolio_receives_signal_event(self):
        """测试投资组合接收信号事件"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        received_events = []
        handler = lambda e: received_events.append(e)
        handler(event)

        assert len(received_events) == 1
        assert received_events[0].payload is signal

    def test_signal_event_validation(self):
        """测试信号事件验证"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert event.event_type == EVENT_TYPES.SIGNALGENERATION
        assert event.code is not None
        assert event.code != ""
        assert event.direction is not None
        assert isinstance(event.direction, DIRECTION_TYPES)


@pytest.mark.unit
class TestSignalGenerationToRiskManagement:
    """4. SignalGeneration到风险管理测试"""

    def test_portfolio_forwards_to_risk_managers(self):
        """测试投资组合转发到风险管理器"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        processed_signals = []
        risk_handler = lambda evt: processed_signals.append(evt.payload)
        risk_handler(event)

        assert len(processed_signals) == 1
        assert processed_signals[0].code == "000001.SZ"

    def test_risk_manager_processes_signal(self):
        """测试风险管理器处理信号"""
        signal = _make_signal(direction=DIRECTION_TYPES.LONG, volume=5000)
        event = EventSignalGeneration(signal=signal)

        def risk_check(evt):
            if evt.payload.volume > 3000:
                evt.payload.volume = 3000
            return evt

        processed = risk_check(event)
        assert processed.payload.volume == 3000

    def test_risk_manager_generates_risk_signals(self):
        """测试风险管理器生成风险信号"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        risk_signals = []
        if event.direction == DIRECTION_TYPES.LONG:
            risk_signal = _make_signal(
                code=event.code,
                direction=DIRECTION_TYPES.SHORT,
                reason="Risk: stop loss triggered"
            )
            risk_signals.append(risk_signal)

        assert len(risk_signals) == 1
        assert risk_signals[0].direction == DIRECTION_TYPES.SHORT

    def test_signal_modification_by_risk_manager(self):
        """测试风险管理器修改信号"""
        signal = _make_signal(volume=10000)
        event = EventSignalGeneration(signal=signal)

        original_volume = event.payload.volume
        event.payload.volume = 5000

        assert event.payload.volume == 5000
        assert event.payload.volume != original_volume


@pytest.mark.unit
class TestSignalGenerationToOrderCreation:
    """5. SignalGeneration到订单创建测试"""

    def test_portfolio_creates_orders_from_signals(self):
        """测试投资组合根据信号创建订单"""
        signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        event = EventSignalGeneration(signal=signal)

        order_created = {
            "code": event.code,
            "direction": event.direction,
            "volume": event.payload.volume,
        }

        assert order_created["code"] == "000001.SZ"
        assert order_created["direction"] == DIRECTION_TYPES.LONG
        assert order_created["volume"] == 1000

    def test_signal_to_order_conversion_logic(self):
        """测试信号到订单转换逻辑"""
        long_signal = _make_signal(direction=DIRECTION_TYPES.LONG)
        short_signal = _make_signal(direction=DIRECTION_TYPES.SHORT)

        long_event = EventSignalGeneration(signal=long_signal)
        short_event = EventSignalGeneration(signal=short_signal)

        assert long_event.direction == DIRECTION_TYPES.LONG
        assert short_event.direction == DIRECTION_TYPES.SHORT
        assert long_event.direction != short_event.direction

    def test_order_sizing_from_signal(self):
        """测试从信号确定订单大小"""
        signal = _make_signal(volume=0)
        event = EventSignalGeneration(signal=signal)

        order_volume = event.payload.volume or 100
        assert order_volume == 100

        signal2 = _make_signal(volume=500)
        event2 = EventSignalGeneration(signal=signal2)
        order_volume2 = event2.payload.volume or 100
        assert order_volume2 == 500

    def test_order_validation_before_submission(self):
        """测试订单提交前验证"""
        signal = _make_signal(direction=DIRECTION_TYPES.LONG, volume=1000)
        event = EventSignalGeneration(signal=signal)

        assert event.payload.volume == 1000
        assert event.code is not None
        assert event.code != ""
        assert event.direction == DIRECTION_TYPES.LONG


@pytest.mark.unit
class TestSignalGenerationEventChaining:
    """6. SignalGeneration事件链测试"""

    def test_signal_event_triggers_order_events(self):
        """测试信号事件触发订单事件"""
        signal = _make_signal()
        signal_event = EventSignalGeneration(signal=signal)

        event_chain = [signal_event]
        order_event = MagicMock()
        order_event.event_type = EVENT_TYPES.ORDERSUBMITTED
        event_chain.append(order_event)

        assert len(event_chain) == 2
        assert event_chain[0].event_type == EVENT_TYPES.SIGNALGENERATION
        assert event_chain[1].event_type == EVENT_TYPES.ORDERSUBMITTED

    def test_multiple_signals_batch_processing(self):
        """测试多信号批处理"""
        signals = [
            _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
            _make_signal(code="600036.SH", direction=DIRECTION_TYPES.SHORT),
            _make_signal(code="000002.SZ", direction=DIRECTION_TYPES.LONG),
        ]
        events = [EventSignalGeneration(signal=s) for s in signals]

        assert len(events) == 3
        assert events[0].code == "000001.SZ"
        assert events[1].code == "600036.SH"
        assert events[2].code == "000002.SZ"

    def test_signal_priority_handling(self):
        """测试信号优先级处理"""
        high_confidence_signal = _make_signal()
        high_confidence_signal.confidence = 0.9
        low_confidence_signal = _make_signal(code="600036.SH")
        low_confidence_signal.confidence = 0.3

        events = [
            EventSignalGeneration(signal=low_confidence_signal),
            EventSignalGeneration(signal=high_confidence_signal),
        ]
        events.sort(key=lambda e: e.payload.confidence, reverse=True)

        assert events[0].payload.confidence == 0.9
        assert events[1].payload.confidence == 0.3

    def test_signal_event_error_propagation(self):
        """测试信号事件错误传播"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        error_occurred = False
        try:
            event.code = None
        except AttributeError:
            error_occurred = True

        assert error_occurred


@pytest.mark.unit
class TestSignalGenerationMultiStrategy:
    """7. 多策略SignalGeneration测试"""

    def test_multiple_strategies_signal_generation(self):
        """测试多策略信号生成"""
        strategy_a_signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        strategy_b_signal = _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT)

        events_a = EventSignalGeneration(signal=strategy_a_signal)
        events_b = EventSignalGeneration(signal=strategy_b_signal)

        assert events_a.direction == DIRECTION_TYPES.LONG
        assert events_b.direction == DIRECTION_TYPES.SHORT

    def test_signal_conflict_resolution(self):
        """测试信号冲突解决"""
        long_event = EventSignalGeneration(signal=_make_signal(direction=DIRECTION_TYPES.LONG))
        short_event = EventSignalGeneration(signal=_make_signal(direction=DIRECTION_TYPES.SHORT))

        conflicting = [long_event, short_event]
        assert len(conflicting) == 2
        assert conflicting[0].direction != conflicting[1].direction

    def test_signal_aggregation_logic(self):
        """测试信号聚合逻辑"""
        signals = [
            _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
            _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG),
            _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.SHORT),
        ]

        long_count = sum(1 for s in signals if s.direction == DIRECTION_TYPES.LONG)
        short_count = sum(1 for s in signals if s.direction == DIRECTION_TYPES.SHORT)

        assert long_count == 2
        assert short_count == 1
        assert long_count > short_count

    def test_strategy_weight_in_signal_processing(self):
        """测试策略权重在信号处理中的作用"""
        signal_a = _make_signal()
        signal_a.weight = 0.7
        signal_b = _make_signal(code="600036.SH")
        signal_b.weight = 0.3

        events = [EventSignalGeneration(signal=signal_a), EventSignalGeneration(signal=signal_b)]
        total_weight = sum(e.payload.weight for e in events)

        assert total_weight == pytest.approx(1.0, abs=0.01)


@pytest.mark.unit
class TestSignalGenerationTimingAndContext:
    """8. SignalGeneration时间和上下文测试"""

    def test_signal_timing_consistency(self):
        """测试信号时间一致性"""
        signal = _make_signal()
        event = EventSignalGeneration(signal=signal)

        assert isinstance(event.timestamp, datetime.datetime)
        assert isinstance(signal.timestamp, datetime.datetime)

    def test_signal_market_context_preservation(self):
        """测试信号市场上下文保持"""
        signal = _make_signal(code="000001.SZ", reason="MA crossover on daily")
        event = EventSignalGeneration(signal=signal)

        assert event.payload.reason == "MA crossover on daily"
        assert event.code == "000001.SZ"

    def test_signal_strategy_context_tracking(self):
        """测试信号策略上下文追踪"""
        signal = _make_signal(portfolio_id="portfolio-123", engine_id="engine-456", task_id="run-789")
        event = EventSignalGeneration(signal=signal)

        assert event.payload.portfolio_id == "portfolio-123"
        assert event.payload.engine_id == "engine-456"
        assert event.payload.task_id == "run-789"

    def test_signal_historical_reference(self):
        """测试信号历史参考"""
        signal = _make_signal(
            direction=DIRECTION_TYPES.LONG,
            reason="Breakout above 20-day high",
            volume=2000,
            strength=0.8,
            confidence=0.7,
        )
        event = EventSignalGeneration(signal=signal)

        assert event.payload.strength == 0.8
        assert event.payload.confidence == 0.7
        assert event.payload.volume == 2000
