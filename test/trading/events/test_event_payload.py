"""
Event payload属性测试

测试EventBase和EventPriceUpdate的payload属性功能，
验证payload与value属性的完全一致性。
"""
import pytest
import sys
import datetime
from pathlib import Path

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.enums import FREQUENCY_TYPES, TICKDIRECTION_TYPES, EVENT_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestEventBasePayload:
    """1. EventBase payload属性基础测试"""

    def test_payload_initial_state(self):
        """测试payload初始状态"""
        event = EventBase(name="TestEvent")

        # 验证初始状态
        assert event.value is None, "初始value应为None"
        assert event.payload is None, "初始payload应为None"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_payload_setter_consistency(self):
        """测试payload setter与value的一致性"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Hello World", "type": "test"}

        # 通过payload设置数据
        event.payload = test_data

        # 验证一致性
        assert event.value is test_data, "value应等于设置的数据"
        assert event.payload is test_data, "payload应等于设置的数据"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_value_setter_consistency(self):
        """测试value setter与payload的一致性"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Hello World", "type": "test"}

        # 通过value设置数据
        event.value = test_data

        # 验证一致性
        assert event.value is test_data, "value应等于设置的数据"
        assert event.payload is test_data, "payload应等于设置的数据"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_set_payload_method(self):
        """测试set_payload便捷方法"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Set Payload Test"}

        # 使用set_payload方法
        result = event.set_payload(test_data)

        # 验证返回值和数据一致性
        assert result is event, "set_payload应返回self"
        assert event.value is test_data, "value应等于设置的数据"
        assert event.payload is test_data, "payload应等于设置的数据"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_set_value_method_consistency(self):
        """测试set_value方法与payload的一致性"""
        event = EventBase(name="TestEvent")
        test_data = {"message": "Set Value Test"}

        # 使用set_value方法
        result = event.set_value(test_data)

        # 验证返回值和数据一致性
        assert result is event, "set_value应返回self"
        assert event.value is test_data, "value应等于设置的数据"
        assert event.payload is test_data, "payload应等于设置的数据"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_payload_data_types(self):
        """测试payload支持各种数据类型"""
        event = EventBase(name="TestEvent")

        # 测试各种数据类型
        test_cases = [
            ("字符串", "Hello World"),
            ("整数", 42),
            ("浮点数", 3.14),
            ("布尔值", True),
            ("列表", [1, 2, 3]),
            ("字典", {"key": "value"}),
            ("None", None)
        ]

        for name, test_data in test_cases:
            event.payload = test_data
            assert event.value is test_data, f"{name}: value应等于设置的数据"
            assert event.payload is test_data, f"{name}: payload应等于设置的数据"
            assert event.value is event.payload, f"{name}: value和payload应为同一对象"


@pytest.mark.unit
class TestEventPriceUpdatePayload:
    """2. EventPriceUpdate payload属性测试"""

    def test_bar_payload_consistency(self):
        """测试Bar类型payload的一致性"""
        bar = Bar(
            code="000001.SZ",
            open=10.0, high=10.5, low=9.5, close=10.2,
            volume=1000, amount=10200,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event = EventPriceUpdate(price_info=bar)

        # 验证payload与value的一致性
        assert event.value is bar, "value应等于bar对象"
        assert event.payload is bar, "payload应等于bar对象"
        assert event.value is event.payload, "value和payload应为同一对象"

        # 验证通过payload访问bar属性
        assert event.payload.code == "000001.SZ", "通过payload访问code"
        assert float(event.payload.close) == 10.2, "通过payload访问close"
        assert event.payload.volume == 1000, "通过payload访问volume"

    def test_tick_payload_consistency(self):
        """测试Tick类型payload的一致性"""
        tick = Tick(
            code="000001.SZ",
            price=10.5,
            volume=500,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event = EventPriceUpdate(price_info=tick)

        # 验证payload与value的一致性
        assert event.value is tick, "value应等于tick对象"
        assert event.payload is tick, "payload应等于tick对象"
        assert event.value is event.payload, "value和payload应为同一对象"

        # 验证通过payload访问tick属性
        assert event.payload.code == "000001.SZ", "通过payload访问code"
        assert event.payload.price == 10.5, "通过payload访问price"
        assert event.payload.volume == 500, "通过payload访问volume"

    def test_unset_payload_consistency(self):
        """测试未设置payload时的一致性"""
        event = EventPriceUpdate()  # 不设置price_info

        # 验证payload与value的一致性
        assert event.value is None, "未设置时value应为None"
        assert event.payload is None, "未设置时payload应为None"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_payload_after_price_change(self):
        """测试更换价格数据后的payload一致性"""
        # 初始Bar数据
        bar1 = Bar(
            code="000001.SZ",
            open=10.0, high=10.5, low=9.5, close=10.2,
            volume=1000, amount=10200,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event = EventPriceUpdate(price_info=bar1)

        # 验证初始状态
        assert event.payload is bar1, "初始payload应为bar1"
        assert float(event.payload.close) == 10.2, "初始close价格应为10.2"

        # 更换为Tick数据
        tick = Tick(
            code="000001.SZ",
            price=11.0,
            volume=600,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event.set(tick)

        # 验证更换后的一致性
        assert event.value is tick, "更换后value应为tick"
        assert event.payload is tick, "更换后payload应为tick"
        assert event.value is event.payload, "更换后value和payload应为同一对象"
        assert event.payload.price == 11.0, "更换后price应为11.0"


@pytest.mark.unit
class TestEventPayloadBusinessLogic:
    """3. Event payload业务逻辑测试"""

    def test_event_processor_with_payload(self):
        """测试事件处理器使用payload"""
        # 创建Bar事件
        bar = Bar(
            code="TEST.SZ",
            open=100.0, high=105.0, low=95.0, close=102.0,
            volume=10000, amount=1020000,
            frequency=FREQUENCY_TYPES.DAY,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event = EventPriceUpdate(price_info=bar)

        # 模拟事件处理器逻辑
        processed_data = []

        def price_processor(event):
            # 使用payload访问价格数据
            payload = event.payload
            if payload:
                processed_data.append({
                    'symbol': payload.code,
                    'close': payload.close,
                    'volume': payload.volume,
                    'timestamp': event.timestamp
                })

        price_processor(event)

        # 验证处理器正确访问了payload
        assert len(processed_data) == 1, "应处理一个事件"
        assert processed_data[0]['symbol'] == "TEST.SZ", "股票代码应正确"
        assert processed_data[0]['close'] == 102.0, "收盘价应正确"
        assert processed_data[0]['volume'] == 10000, "成交量应正确"

    def test_payload_vs_value_api_consistency(self):
        """测试payload与value API在业务逻辑中的一致性"""
        # 创建Tick事件
        tick = Tick(
            code="API_TEST.SZ",
            price=50.25,
            volume=1500,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        )

        event = EventPriceUpdate(price_info=tick)

        # 模拟两种API使用方式
        value_results = []
        payload_results = []

        def value_api_processor(event):
            value_results.append({
                'symbol': event.value.code,
                'price': event.value.price,
                'volume': event.value.volume
            })

        def payload_api_processor(event):
            payload_results.append({
                'symbol': event.payload.code,
                'price': event.payload.price,
                'volume': event.payload.volume
            })

        value_api_processor(event)
        payload_api_processor(event)

        # 验证两种API结果完全一致
        assert value_results == payload_results, "value和payload API应产生相同结果"
        assert value_results[0]['symbol'] == "API_TEST.SZ", "股票代码应正确"
        assert value_results[0]['price'] == 50.25, "价格应正确"
        assert value_results[0]['volume'] == 1500, "成交量应正确"

    def test_payload_in_event_chain(self):
        """测试payload在事件链中的传递"""
        # 模拟事件链：PriceUpdate -> Strategy -> Signal
        price_event = EventPriceUpdate(price_info=Tick(
            code="CHAIN.SZ",
            price=25.50,
            volume=800,
            direction=TICKDIRECTION_TYPES.ACTIVESELL,
            timestamp=datetime.datetime.now(datetime.timezone.utc)
        ))

        # 策略处理阶段
        strategy_decisions = []

        def strategy_processor(event):
            payload = event.payload
            if payload and payload.price > 25.0:
                strategy_decisions.append({
                    'symbol': payload.code,
                    'action': 'BUY',
                    'trigger_price': payload.price,
                    'source': 'payload_analysis'
                })

        strategy_processor(price_event)

        # 验证策略正确使用了payload
        assert len(strategy_decisions) == 1, "应产生一个策略决策"
        assert strategy_decisions[0]['symbol'] == "CHAIN.SZ", "股票代码应正确"
        assert strategy_decisions[0]['trigger_price'] == 25.50, "触发价格应正确"
        assert strategy_decisions[0]['source'] == 'payload_analysis', "应标记为payload分析"


@pytest.mark.unit
class TestEventPayloadEdgeCases:
    """4. Event payload边界情况测试"""

    def test_payload_with_none_value(self):
        """测试payload设置为None的情况"""
        event = EventBase(name="TestEvent")

        # 设置初始数据
        event.payload = {"initial": "data"}
        assert event.value is not None, "初始数据应存在"

        # 设置为None
        event.payload = None
        assert event.value is None, "设置None后value应为None"
        assert event.payload is None, "设置None后payload应为None"
        assert event.value is event.payload, "value和payload应为同一对象"

    def test_payload_overwrite_multiple_times(self):
        """测试多次覆写payload"""
        event = EventBase(name="TestEvent")
        data_sequence = [
            {"step": 1, "data": "first"},
            {"step": 2, "data": "second"},
            {"step": 3, "data": "third"},
            None,
            "final_string"
        ]

        for i, data in enumerate(data_sequence):
            event.payload = data

            # 验证每次设置后的一致性
            assert event.value is data, f"第{i+1}次设置后value应正确"
            assert event.payload is data, f"第{i+1}次设置后payload应正确"
            assert event.value is event.payload, f"第{i+1}次设置后value和payload应为同一对象"

    def test_payload_memory_reference(self):
        """测试payload的内存引用一致性"""
        event = EventBase(name="TestEvent")

        # 创建可变对象
        original_data = {"counter": 0, "items": []}
        event.payload = original_data

        # 通过不同引用修改数据
        event.value["counter"] = 1
        event.payload["items"].append("item1")

        # 验证内存引用一致性
        assert original_data["counter"] == 1, "通过value修改应影响原数据"
        assert len(original_data["items"]) == 1, "通过payload修改应影响原数据"
        assert event.value["counter"] == event.payload["counter"], "value和payload应看到相同数据"
        assert event.value["items"] is event.payload["items"], "value和payload的嵌套对象应为同一引用"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])