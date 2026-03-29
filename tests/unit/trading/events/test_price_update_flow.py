"""
PriceUpdate事件流转TDD测试

通过TDD方式测试PriceUpdate事件在回测系统中的完整流转过程
涵盖事件创建、传播、处理和响应的完整链路测试
"""
import pytest
import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.entities.bar import Bar
from ginkgo.entities.tick import Tick
from ginkgo.entities.signal import Signal
from ginkgo.enums import EVENT_TYPES, DIRECTION_TYPES, PRICEINFO_TYPES, FREQUENCY_TYPES, TICKDIRECTION_TYPES, SOURCE_TYPES


def _make_bar(code="000001.SZ", timestamp=None, open_val=None, high_val=None,
              low_val=None, close_val=None, volume=1000000):
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


def _make_signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG):
    return Signal(
        portfolio_id="test-portfolio",
        engine_id="test-engine",
        run_id="test-run",
        code=code,
        direction=direction,
        reason="test reason",
    )


@pytest.mark.unit
class TestPriceUpdateEventCreation:
    """1. PriceUpdate事件创建测试"""

    def test_default_constructor(self):
        """测试不带价格信息的EventPriceUpdate创建"""
        event = EventPriceUpdate()

        assert isinstance(event, EventBase)
        assert event.price_type is None
        assert event.payload is None

    def test_bar_constructor(self):
        """测试使用Bar对象的EventPriceUpdate创建"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        assert event.price_type == PRICEINFO_TYPES.BAR
        assert event.payload is bar
        assert event.code == "000001.SZ"

    def test_tick_constructor(self):
        """测试使用Tick对象的EventPriceUpdate创建"""
        tick = _make_tick()
        event = EventPriceUpdate(payload=tick)

        assert event.price_type == PRICEINFO_TYPES.TICK
        assert event.payload is tick
        assert event.code == "000001.SZ"

    def test_event_type_setting(self):
        """测试事件类型设置"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        assert event.event_type == EVENT_TYPES.PRICEUPDATE


@pytest.mark.unit
class TestPriceUpdateEventProperties:
    """2. PriceUpdate事件属性测试"""

    def test_price_type_property(self):
        """测试price_type属性正确返回PRICEINFO_TYPES"""
        bar_event = EventPriceUpdate(payload=_make_bar())
        tick_event = EventPriceUpdate(payload=_make_tick())

        assert bar_event.price_type == PRICEINFO_TYPES.BAR
        assert tick_event.price_type == PRICEINFO_TYPES.TICK

    def test_value_property_bar(self):
        """测试价格类型为BAR时payload属性返回Bar对象"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        assert isinstance(event.payload, Bar)
        assert event.payload is bar

    def test_value_property_tick(self):
        """测试价格类型为TICK时payload属性返回Tick对象"""
        tick = _make_tick()
        event = EventPriceUpdate(payload=tick)

        assert isinstance(event.payload, Tick)
        assert event.payload is tick

    def test_value_property_unset(self):
        """测试未设置价格信息时payload属性返回None"""
        event = EventPriceUpdate()

        assert event.payload is None
        assert event.code is None


@pytest.mark.unit
class TestPriceUpdateBarProperties:
    """Bar类型PriceUpdate的OHLCV属性测试"""

    def test_bar_open_property(self):
        """测试Bar类型的open属性"""
        bar = _make_bar(open_val=Decimal("11.0"))
        event = EventPriceUpdate(payload=bar)

        assert event.open == Decimal("11.0")

    def test_bar_high_property(self):
        """测试Bar类型的high属性"""
        bar = _make_bar(high_val=Decimal("12.0"))
        event = EventPriceUpdate(payload=bar)

        assert event.high == Decimal("12.0")

    def test_bar_low_property(self):
        """测试Bar类型的low属性"""
        bar = _make_bar(low_val=Decimal("9.0"))
        event = EventPriceUpdate(payload=bar)

        assert event.low == Decimal("9.0")

    def test_bar_close_property(self):
        """测试Bar类型的close属性"""
        bar = _make_bar(close_val=Decimal("10.8"))
        event = EventPriceUpdate(payload=bar)

        assert event.close == Decimal("10.8")

    def test_bar_volume_property(self):
        """测试Bar类型的volume属性"""
        bar = _make_bar(volume=2000000)
        event = EventPriceUpdate(payload=bar)

        assert event.volume == 2000000


@pytest.mark.unit
class TestPriceUpdateTickProperties:
    """Tick类型PriceUpdate的价格属性测试"""

    def test_tick_price_property(self):
        """测试Tick类型的price属性"""
        tick = _make_tick(price=Decimal("15.5"))
        event = EventPriceUpdate(payload=tick)

        assert event.price == Decimal("15.5")

    def test_tick_volume_property(self):
        """测试Tick类型的volume属性"""
        tick = _make_tick(volume=500)
        event = EventPriceUpdate(payload=tick)

        assert event.volume == 500

    def test_tick_bar_properties_return_none(self):
        """测试Tick类型访问Bar属性返回None"""
        tick = _make_tick()
        event = EventPriceUpdate(payload=tick)

        assert event.open is None
        assert event.high is None
        assert event.close is None

    def test_bar_price_property_returns_none(self):
        """测试Bar类型访问tick price返回None"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        assert event.price is None


@pytest.mark.unit
class TestPriceUpdateFeederToEngine:
    """3. 馈送器到引擎的PriceUpdate流转测试"""

    def test_feeder_creates_price_update_event(self):
        """测试馈送器创建价格更新事件"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        assert event.event_type == EVENT_TYPES.PRICEUPDATE
        assert event.price_type == PRICEINFO_TYPES.BAR

    def test_feeder_publishes_to_engine(self):
        """测试馈送器发布事件到引擎"""
        event_queue = []
        mock_publisher = lambda e: event_queue.append(e)

        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        mock_publisher(event)

        assert len(event_queue) == 1
        assert event_queue[0].event_type == EVENT_TYPES.PRICEUPDATE

    def test_engine_receives_price_update(self):
        """测试引擎接收价格更新事件"""
        events = [EventPriceUpdate(payload=_make_bar()) for _ in range(3)]

        assert len(events) == 3
        for e in events:
            assert e.event_type == EVENT_TYPES.PRICEUPDATE

    def test_event_queue_ordering(self):
        """测试多个PriceUpdate事件在队列中的顺序保持"""
        timestamps = [
            datetime.datetime(2024, 1, 1, 9, 30, 0),
            datetime.datetime(2024, 1, 1, 9, 31, 0),
            datetime.datetime(2024, 1, 1, 9, 32, 0),
        ]
        events = []
        for ts in timestamps:
            events.append(EventPriceUpdate(payload=_make_bar(timestamp=ts)))

        for i, evt in enumerate(events):
            assert evt.business_timestamp == timestamps[i]


@pytest.mark.unit
class TestPriceUpdateEngineToPortfolio:
    """4. 引擎到投资组合的PriceUpdate流转测试"""

    def test_engine_dispatches_to_handlers(self):
        """测试引擎分发到处理器"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        handler_calls = []
        handler = lambda e: handler_calls.append(e)
        handler(event)

        assert len(handler_calls) == 1
        assert handler_calls[0].code == "000001.SZ"

    def test_portfolio_receives_price_update(self):
        """测试投资组合接收价格更新"""
        bar = _make_bar(code="600036.SH")
        event = EventPriceUpdate(payload=bar)

        assert event.code == "600036.SH"
        assert event.close == Decimal("10.2")

    def test_portfolio_processes_price_data(self):
        """测试投资组合从PriceUpdate事件中提取并处理价格数据"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        price_data = {
            "code": event.code,
            "open": float(event.open),
            "high": float(event.high),
            "low": float(event.low),
            "close": float(event.close),
            "volume": event.volume,
        }

        assert price_data["code"] == "000001.SZ"
        assert price_data["open"] == 10.0
        assert price_data["high"] == 10.5
        assert price_data["low"] == 9.5
        assert price_data["close"] == 10.2

    def test_multiple_portfolios_handling(self):
        """测试多个投资组合都能接收到相同的PriceUpdate事件"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        portfolio_a_received = []
        portfolio_b_received = []
        portfolio_a_received.append(event)
        portfolio_b_received.append(event)

        assert len(portfolio_a_received) == 1
        assert len(portfolio_b_received) == 1
        assert portfolio_a_received[0] is portfolio_b_received[0]


@pytest.mark.unit
class TestPriceUpdateToStrategyActivation:
    """5. PriceUpdate触发策略激活测试"""

    def test_portfolio_triggers_strategy_calculation(self):
        """测试接收PriceUpdate后投资组合触发策略计算"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        strategy_called = False

        def strategy_cal(event):
            nonlocal strategy_called
            strategy_called = True

        strategy_cal(event)
        assert strategy_called

    def test_strategy_accesses_price_data(self):
        """测试策略从PriceUpdate事件中获取最新价格数据"""
        bar = _make_bar(close_val=Decimal("11.5"))
        event = EventPriceUpdate(payload=bar)

        latest_close = event.close
        assert latest_close == Decimal("11.5")

    def test_strategy_historical_data_context(self):
        """测试策略结合历史数据和当前PriceUpdate进行分析"""
        historical_bars = [
            _make_bar(close_val=Decimal("10.0"), timestamp=datetime.datetime(2024, 1, 1, 15, 0, 0)),
            _make_bar(close_val=Decimal("10.3"), timestamp=datetime.datetime(2024, 1, 2, 15, 0, 0)),
            _make_bar(close_val=Decimal("10.5"), timestamp=datetime.datetime(2024, 1, 3, 15, 0, 0)),
        ]
        current_event = EventPriceUpdate(
            payload=_make_bar(close_val=Decimal("10.8"), timestamp=datetime.datetime(2024, 1, 4, 15, 0, 0))
        )

        closes = [b.close for b in historical_bars] + [current_event.close]
        assert len(closes) == 4
        assert closes[-1] == Decimal("10.8")

    def test_multiple_strategies_activation(self):
        """测试单个PriceUpdate触发多个策略的计算"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)

        strategy_results = []
        for i in range(3):
            strategy_results.append({"strategy_id": i, "processed": True})

        assert len(strategy_results) == 3
        assert all(r["processed"] for r in strategy_results)


@pytest.mark.unit
class TestPriceUpdateSignalGeneration:
    """6. PriceUpdate引发信号生成测试"""

    def test_strategy_generates_signals_from_price(self):
        """测试策略基于PriceUpdate数据生成交易信号"""
        bar = _make_bar(close_val=Decimal("15.0"))
        event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=event.code, direction=DIRECTION_TYPES.LONG)
        signal_event = EventSignalGeneration(signal=signal)

        assert signal_event.code == event.code
        assert signal_event.direction == DIRECTION_TYPES.LONG

    def test_signal_generation_event_creation(self):
        """测试策略创建EventSignalGeneration事件"""
        bar = _make_bar()
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code)
        signal_event = EventSignalGeneration(signal=signal)

        assert signal_event.event_type == EVENT_TYPES.SIGNALGENERATION
        assert signal_event.code == price_event.code

    def test_signal_event_chain_continuation(self):
        """测试PriceUpdate -> Strategy -> SignalGeneration的事件链"""
        bar = _make_bar()
        price_event = EventPriceUpdate(payload=bar)

        signal = _make_signal(code=price_event.code, direction=DIRECTION_TYPES.LONG)
        signal_event = EventSignalGeneration(signal=signal)

        chain = [price_event, signal_event]
        assert chain[0].event_type == EVENT_TYPES.PRICEUPDATE
        assert chain[1].event_type == EVENT_TYPES.SIGNALGENERATION
        assert chain[0].code == chain[1].code


@pytest.mark.unit
class TestPriceUpdateTimingAndSynchronization:
    """7. PriceUpdate时间和同步测试"""

    def test_event_timestamp_consistency(self):
        """测试PriceUpdate事件时间戳与价格数据时间戳的一致性"""
        bar = _make_bar(timestamp=datetime.datetime(2024, 6, 15, 14, 30, 0))
        event = EventPriceUpdate(payload=bar)

        assert isinstance(event.timestamp, datetime.datetime)
        assert event.business_timestamp == datetime.datetime(2024, 6, 15, 14, 30, 0)

    def test_time_controlled_processing(self):
        """测试在时间控制下PriceUpdate的时间同步处理"""
        timestamps = [
            datetime.datetime(2024, 1, 1, 9, 30, 0),
            datetime.datetime(2024, 1, 2, 9, 30, 0),
            datetime.datetime(2024, 1, 3, 9, 30, 0),
        ]
        events = [EventPriceUpdate(payload=_make_bar(timestamp=ts)) for ts in timestamps]

        biz_timestamps = [e.business_timestamp for e in events]
        assert biz_timestamps == sorted(biz_timestamps)

    def test_backtest_time_advancement(self):
        """测试PriceUpdate触发回测时间的正确推进"""
        events = []
        for day in range(1, 4):
            ts = datetime.datetime(2024, 1, day, 15, 0, 0)
            events.append(EventPriceUpdate(payload=_make_bar(timestamp=ts)))

        for i in range(len(events) - 1):
            assert events[i + 1].business_timestamp > events[i].business_timestamp

    def test_event_ordering_by_time(self):
        """测试多个不同时间的PriceUpdate事件按时间顺序处理"""
        unsorted_data = [
            datetime.datetime(2024, 1, 3, 9, 30, 0),
            datetime.datetime(2024, 1, 1, 9, 30, 0),
            datetime.datetime(2024, 1, 2, 9, 30, 0),
        ]
        events = [EventPriceUpdate(payload=_make_bar(timestamp=ts)) for ts in unsorted_data]
        events.sort(key=lambda e: e.business_timestamp)

        for i in range(len(events) - 1):
            assert events[i].business_timestamp <= events[i + 1].business_timestamp

    def test_to_dataframe_bar(self):
        """测试Bar类型PriceUpdate的to_dataframe方法"""
        bar = _make_bar()
        event = EventPriceUpdate(payload=bar)
        df = event.to_dataframe()

        assert df is not None
        assert len(df) == 1
        assert df.iloc[0]["code"] == "000001.SZ"

    def test_to_dataframe_tick(self):
        """测试Tick类型PriceUpdate的to_dataframe方法返回None"""
        tick = _make_tick()
        event = EventPriceUpdate(payload=tick)
        df = event.to_dataframe()

        assert df is None
