"""
Event Payload测试 - Refactored

使用pytest最佳实践重构的EventPayload测试套件
验证payload与value属性的完全一致性
"""
import pytest
import datetime

from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.enums import FREQUENCY_TYPES, TICKDIRECTION_TYPES, SOURCE_TYPES


@pytest.fixture
def sample_bar():
    """标准Bar测试数据"""
    return Bar(
        code="000001.SZ",
        open=Decimal('10.0'),
        high=Decimal('10.5'),
        low=Decimal('9.5'),
        close=Decimal('10.2'),
        volume=1000000,
        amount=Decimal('10200000'),
        frequency=FREQUENCY_TYPES.DAY,
        timestamp=datetime.datetime(2024, 1, 1, 15, 0, 0)
    )


@pytest.fixture
def sample_tick():
    """标准Tick测试数据"""
    return Tick(
        code="000001.SZ",
        price=Decimal('10.5'),
        volume=1000,
        direction=TICKDIRECTION_TYPES.ACTIVEBUY,
        timestamp=datetime.datetime(2024, 1, 1, 9, 30, 25)
    )


@pytest.mark.unit
class TestEventBasePayload:
    """1. EventBase payload基础测试"""

    def test_payload_initial_state(self):
        """测试payload初始状态"""
        event = EventBase(name="TestEvent")

        assert event.value is None
        assert event.payload is None
        assert event.value is event.payload

    def test_payload_setter_consistency(self):
        """测试payload setter与value的一致性"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Hello World", "type": "test"}

        event.payload = test_data

        assert event.value is test_data
        assert event.payload is test_data
        assert event.value is event.payload

    def test_value_setter_consistency(self):
        """测试value setter与payload的一致性"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Hello World", "type": "test"}

        event.value = test_data

        assert event.value is test_data
        assert event.payload is test_data
        assert event.value is event.payload

    def test_set_payload_method(self):
        """测试set_payload便捷方法"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Set Payload Test"}

        result = event.set_payload(test_data)

        assert result is event
        assert event.value is test_data
        assert event.payload is test_data

    def test_set_value_method(self):
        """测试set_value方法"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Set Value Test"}

        result = event.set_value(test_data)

        assert result is event
        assert event.value is test_data
        assert event.payload is test_data

    @pytest.mark.parametrize("test_data", [
        "字符串",
        42,
        3.14,
        True,
        [1, 2, 3],
        {"key": "value"},
        None
    ])
    def test_payload_data_types(self, test_data):
        """测试payload支持各种数据类型"""
        event = EventBase(name="TestEvent")
        event.payload = test_data

        assert event.value is test_data
        assert event.payload is test_data
        assert event.value is event.payload


@pytest.mark.unit
class TestEventPriceUpdatePayload:
    """2. EventPriceUpdate payload测试"""

    def test_bar_payload_consistency(self, sample_bar):
        """测试Bar类型payload的一致性"""
        event = EventPriceUpdate(price_info=sample_bar)

        assert event.value is sample_bar
        assert event.payload is sample_bar
        assert event.value is event.payload

    def test_bar_payload_access(self, sample_bar):
        """测试通过payload访问Bar属性"""
        event = EventPriceUpdate(price_info=sample_bar)

        assert event.payload.code == "000001.SZ"
        assert float(event.payload.close) == 10.2
        assert event.payload.volume == 1000000

    def test_tick_payload_consistency(self, sample_tick):
        """测试Tick类型payload的一致性"""
        event = EventPriceUpdate(price_info=sample_tick)

        assert event.value is sample_tick
        assert event.payload is sample_tick
        assert event.value is event.payload

    def test_tick_payload_access(self, sample_tick):
        """测试通过payload访问Tick属性"""
        event = EventPriceUpdate(price_info=sample_tick)

        assert event.payload.code == "000001.SZ"
        assert event.payload.price == 10.5
        assert event.payload.volume == 1000

    def test_unset_payload_consistency(self):
        """测试未设置payload时的一致性"""
        event = EventPriceUpdate()  # 不设置price_info

        assert event.value is None
        assert event.payload is None
        assert event.value is event.payload

    def test_payload_after_price_change(self, sample_bar, sample_tick):
        """测试更换价格数据后的payload一致性"""
        event = EventPriceUpdate(price_info=sample_bar)

        assert event.payload is sample_bar
        assert float(event.payload.close) == 10.2

        # 更换为Tick数据
        event.set(sample_tick)

        assert event.value is sample_tick
        assert event.payload is sample_tick
        assert event.payload.price == 10.5


@pytest.mark.unit
class TestEventPayloadBusinessLogic:
    """3. Event payload业务逻辑测试"""

    def test_event_processor_with_payload(self, sample_bar):
        """测试事件处理器使用payload"""
        event = EventPriceUpdate(price_info=sample_bar)
        processed_data = []

        def price_processor(event):
            payload = event.payload
            if payload:
                processed_data.append({
                    'symbol': payload.code,
                    'close': float(payload.close),
                    'volume': payload.volume,
                    'timestamp': event.timestamp
                })

        price_processor(event)

        assert len(processed_data) == 1
        assert processed_data[0]['symbol'] == "000001.SZ"
        assert processed_data[0]['close'] == 10.2
        assert processed_data[0]['volume'] == 1000000

    def test_payload_vs_value_api_consistency(self, sample_tick):
        """测试payload与value API在业务逻辑中的一致性"""
        event = EventPriceUpdate(price_info=sample_tick)
        value_results = []
        payload_results = []

        def value_api_processor(event):
            value_results.append({
                'symbol': event.value.code,
                'price': float(event.value.price),
                'volume': event.value.volume
            })

        def payload_api_processor(event):
            payload_results.append({
                'symbol': event.payload.code,
                'price': float(event.payload.price),
                'volume': event.payload.volume
            })

        value_api_processor(event)
        payload_api_processor(event)

        assert value_results == payload_results

    def test_payload_in_event_chain(self):
        """测试payload在事件链中的传递"""
        price_event = EventPriceUpdate(price_info=Tick(
            code="CHAIN.SZ",
            price=Decimal('25.50'),
            volume=800,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        ))

        strategy_decisions = []

        def strategy_processor(event):
            payload = event.payload
            if payload and float(payload.price) > 25.0:
                strategy_decisions.append({
                    'symbol': payload.code,
                    'action': 'BUY',
                    'trigger_price': float(payload.price)
                })

        strategy_processor(price_event)

        assert len(strategy_decisions) == 1
        assert strategy_decisions[0]['symbol'] == "CHAIN.SZ"
        assert strategy_decisions[0]['trigger_price'] == 25.5


@pytest.mark.unit
class TestEventPayloadEdgeCases:
    """4. Event payload边界情况测试"""

    def test_payload_with_none_value(self):
        """测试payload设置为None"""
        event = EventBase(name="TestEvent")

        event.payload = {"initial": "data"}
        assert event.value is not None

        event.payload = None
        assert event.value is None
        assert event.payload is None

    @pytest.mark.parametrize("data_sequence", [
        [{"step": 1, "data": "first"}],
        {"step": 2, "data": "second"},
        {"step": 3, "data": "third"},
        None,
        "final_string"
    ])
    def test_payload_overwrite_multiple_times(self, data_sequence):
        """测试多次覆写payload"""
        event = EventBase(name="TestEvent")

        for i, data in enumerate(data_sequence):
            event.payload = data

            assert event.value is data
            assert event.payload is data
            assert event.value is event.payload

    def test_payload_memory_reference(self):
        """测试payload的内存引用一致性"""
        event = EventBase(name="TestEvent")
        original_data = {"counter": 0, "items": []}

        event.payload = original_data

        # 通过不同引用修改数据
        event.value["counter"] = 1
        event.payload["items"].append("item1")

        # 验证内存引用一致性
        assert original_data["counter"] == 1
        assert len(original_data["items"]) == 1
        assert event.value["counter"] == event.payload["counter"]
        assert event.value["items"] is event.payload["items"]


@pytest.mark.unit
class TestEventPayloadTypes:
    """5. 各种payload类型测试"""

    @pytest.mark.parametrize("payload_value", [
        "string",
        123,
        45.67,
        True,
        False,
        [1, 2, 3],
        {"key": "value"},
        None,
        "",
        0
    ])
    def test_various_payload_types(self, payload_value):
        """测试各种payload类型"""
        event = EventBase(name="TestEvent")
        event.payload = payload_value

        assert event.value == payload_value
        assert event.payload == payload_value
        assert event.value is event.payload

    def test_complex_nested_payload(self):
        """测试复杂嵌套payload"""
        complex_data = {
            "level1": {
                "level2": {
                    "level3": [1, 2, 3]
                },
                "data": "nested"
            }
        }

        event = EventBase(name="TestEvent")
        event.payload = complex_data

        assert event.payload["level1"]["level2"]["level3"] == [1, 2, 3]
        assert event.value is event.payload


@pytest.mark.financial
class TestEventPayloadBusinessScenarios:
    """6. 业务场景测试"""

    def test_price_update_with_bar(self, sample_bar):
        """测试Bar价格更新场景"""
        event = EventPriceUpdate(price_info=sample_bar)

        # 验证业务逻辑可以正常访问
        if event.payload:
            price_change = float(event.payload.close) - float(event.payload.open)
            assert price_change == 0.2

    def test_price_update_with_tick(self, sample_tick):
        """测试Tick价格更新场景"""
        event = EventPriceUpdate(price_info=sample_tick)

        # 验证业务逻辑可以正常访问
        if event.payload:
            assert event.payload.code == "000001.SZ"
            assert event.payload.price == 10.5

    def test_multiple_price_updates(self, sample_bar, sample_tick):
        """测试多次价格更新"""
        event = EventPriceUpdate(price_info=sample_bar)
        assert event.payload is sample_bar

        # 更新为Tick
        event.set(sample_tick)
        assert event.payload is sample_tick
        assert event.payload.price == 10.5


@pytest.mark.integration
class TestEventPayloadPersistence:
    """7. Payload持久化测试"""

    def test_payload_serialization(self, sample_bar, ginkgo_config):
        """测试payload序列化"""
        event = EventPriceUpdate(price_info=sample_bar)
        model = event.to_model()

        assert model is not None
        assert hasattr(model, 'payload')

    def test_payload_deserialization(self, sample_bar, ginkgo_config):
        """测试payload反序列化"""
        event1 = EventPriceUpdate(price_info=sample_bar)
        model = event1.to_model()

        # 验证可以重建
        event2 = EventBase.from_model(model)
        assert event2.uuid == event1.uuid


@pytest.mark.unit
class TestEventPayloadPerformance:
    """8. Payload性能测试"""

    def test_large_payload_handling(self):
        """测试大payload处理"""
        large_data = {"items": list(range(10000))}

        event = EventBase(name="TestEvent")
        event.payload = large_data

        assert len(event.payload["items"]) == 10000
        assert event.payload is large_data

    def test_frequent_payload_updates(self):
        """测试频繁payload更新"""
        event = EventBase(name="TestEvent")

        for i in range(100):
            event.payload = {"counter": i}

        assert event.payload["counter"] == 99
