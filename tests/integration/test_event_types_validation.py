"""
事件类型验证测试 - 简洁版

验证Ginkgo回测引擎中核心事件类型的基本功能，确保事件系统正常工作。
"""

import pytest
import datetime
from decimal import Decimal

from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.signal_generation import EventSignalGeneration
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.events.order_lifecycle_events import EventOrderAck
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES, DIRECTION_TYPES
from ginkgo.libs import datetime_normalize


@pytest.mark.integration
class TestEventPriceUpdate:
    """测试EventPriceUpdate事件"""

    def test_basic_creation_and_properties(self):
        """测试EventPriceUpdate基本创建和属性访问"""
        # 创建测试Bar数据
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30),
            open=Decimal("10.00"),
            high=Decimal("10.20"),
            low=Decimal("9.80"),
            close=Decimal("10.10"),
            volume=1000000
        )

        # 创建价格事件
        event = EventPriceUpdate(
            price_info=bar,
            source=SOURCE_TYPES.BACKTESTFEEDER
        )

        # 验证基本属性
        assert event.code == "000001.SZ"
        assert event.price_type.value == "bar"
        assert event.value == bar
        assert event.open == Decimal("10.00")
        assert event.close == Decimal("10.10")
        assert event.volume == 1000000
        assert event.event_type == EVENT_TYPES.PRICEUPDATE
        assert event.source == SOURCE_TYPES.BACKTESTFEEDER

    def test_bar_vs_tick_data(self):
        """测试Bar和Tick数据处理"""
        # 测试Bar数据
        bar = Bar(code="000001.SZ", close=Decimal("10.00"))
        event_bar = EventPriceUpdate(price_info=bar)
        assert event_bar.price_type.value == "bar"
        assert event_bar.close == Decimal("10.00")

        # 测试Tick数据（需要导入Tick类）
        # 这里简化为验证price_type设置机制
        assert hasattr(event_bar, 'price_type')


@pytest.mark.integration
class TestEventSignalGeneration:
    """测试EventSignalGeneration事件"""

    def test_signal_wrapping_and_access(self):
        """测试Signal包装和访问"""
        # 创建测试Signal
        signal = Signal(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            reason="测试买入信号",
            timestamp=datetime.datetime(2023, 1, 1, 9, 30)
        )

        # 创建信号事件
        event = EventSignalGeneration(signal)

        # 验证信号包装
        assert event.value == signal
        assert event.code == "000001.SZ"
        assert event.direction == DIRECTION_TYPES.LONG
        assert event.event_type == EVENT_TYPES.SIGNALGENERATION
        assert event.business_timestamp == signal.timestamp

    def test_source_setting(self):
        """测试来源标记设置"""
        signal = Signal(code="000001.SZ", direction=DIRECTION_TYPES.LONG)
        event = EventSignalGeneration(signal)

        # 测试默认来源
        assert event.source == SOURCE_TYPES.SIM

        # 测试来源设置
        event.set_source(SOURCE_TYPES.STRATEGY)
        assert event.source == SOURCE_TYPES.STRATEGY


@pytest.mark.integration
class TestEventTimeAdvance:
    """测试EventTimeAdvance事件"""

    def test_time_advance_creation(self):
        """测试时间推进事件创建"""
        target_time = datetime.datetime(2023, 1, 2, 9, 30)

        # 创建时间推进事件
        event = EventTimeAdvance(
            target_time=target_time,
            phase_id="test_phase"
        )

        # 验证时间推进属性
        assert event.target_time == target_time
        assert event.target_datetime == target_time
        assert event.phase_id == "test_phase"
        assert event.event_type == EVENT_TYPES.TIME_ADVANCE
        assert event.name == "EventTimeAdvance"

    def test_timestamp_handling(self):
        """测试时间戳处理"""
        target_time = datetime.datetime(2023, 1, 2, 9, 30)
        event = EventTimeAdvance(target_time=target_time)

        # 验证时间戳设置
        assert event.timestamp == target_time
        assert event.business_timestamp == target_time


@pytest.mark.integration
class TestEventOrderAck:
    """测试EventOrderAck事件"""

    def test_order_ack_creation_and_properties(self):
        """测试订单确认事件创建和属性"""
        # 创建测试Order
        order = Order(
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            volume=1000,
            limit_price=Decimal("10.50")
        )

        # 创建订单确认事件
        event = EventOrderAck(
            order=order,
            broker_order_id="BROKER_12345",
            ack_message="订单已接收"
        )

        # 验证订单确认属性
        assert event.order == order
        assert event.broker_order_id == "BROKER_12345"
        assert event.ack_message == "订单已接收"
        assert event.code == "000001.SZ"
        assert event.order_id == order.uuid
        assert event.event_type == EVENT_TYPES.ORDERACK

    def test_order_access_methods(self):
        """测试订单访问方法"""
        order = Order(code="000001.SZ", direction=DIRECTION_TYPES.LONG, volume=1000)
        event = EventOrderAck(order=order, broker_order_id="TEST")

        # 测试各种访问方法
        assert event.code == "000001.SZ"
        assert event.order_id == order.uuid
        assert isinstance(event.order_id, str)


@pytest.mark.integration
class TestEventTypeEnums:
    """测试事件类型枚举"""

    def test_critical_event_types_exist(self):
        """验证关键事件类型存在"""
        # 验证核心事件类型定义
        critical_events = [
            'PRICEUPDATE',
            'SIGNALGENERATION',
            'TIME_ADVANCE',
            'ORDERACK',
            'ORDERSUBMITTED',
            'ORDERPARTIALLYFILLED',
            'NEXTPHASE'
        ]

        for event_name in critical_events:
            assert hasattr(EVENT_TYPES, event_name), f"事件类型{event_name}应该被定义"
            event_type = getattr(EVENT_TYPES, event_name)
            assert event_type.value > 0, f"事件类型{event_name}应该有有效值"

    def test_source_types_exist(self):
        """验证来源类型存在"""
        critical_sources = [
            'SIM', 'BACKTESTFEEDER', 'STRATEGY', 'BROKERMATCHMAKING'
        ]

        for source_name in critical_sources:
            assert hasattr(SOURCE_TYPES, source_name), f"来源类型{source_name}应该被定义"
            source_type = getattr(SOURCE_TYPES, source_name)
            assert source_type.value > 0, f"来源类型{source_name}应该有有效值"

    def test_direction_types_exist(self):
        """验证方向类型存在"""
        critical_directions = ['LONG', 'SHORT', 'CLOSE']

        for direction_name in critical_directions:
            assert hasattr(DIRECTION_TYPES, direction_name), f"方向类型{direction_name}应该被定义"
            direction_type = getattr(DIRECTION_TYPES, direction_name)
            assert direction_type.value in [0, 1, 2], f"方向类型{direction_name}应该有有效值"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])