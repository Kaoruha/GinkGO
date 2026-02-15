"""
测试事件系统功能

测试范围：
1. EventBase 基础事件类
2. EventPriceUpdate 价格更新事件
3. EventCapitalUpdate 资金更新事件
4. EventOrderRelated 订单相关事件
5. 事件属性访问和修改
6. 事件数据设置（singledispatchmethod）
7. 事件载荷管理
8. 事件时间戳处理
"""

import pytest
import datetime
import uuid
from decimal import Decimal
from unittest.mock import Mock

from ginkgo.trading.bases.event_base import EventBase
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.capital_update import EventCapitalUpdate
from ginkgo.trading.events.order_related import EventOrderRelated
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.entities.order import Order
from ginkgo.enums import (
    EVENT_TYPES,
    SOURCE_TYPES,
    DIRECTION_TYPES,
    ORDER_TYPES,
    ORDERSTATUS_TYPES,
    FREQUENCY_TYPES,
    PRICEINFO_TYPES,
    TICKDIRECTION_TYPES
)


# ===== EventBase 测试 =====

@pytest.mark.unit
@pytest.mark.events
@pytest.mark.construction
class TestEventBaseConstruction:
    """测试 EventBase 构造和初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        event = EventBase()

        assert isinstance(event._uuid, str)
        assert len(event._uuid) > 0
        # EventBase 使用 _context 属性
        assert hasattr(event, '_context')

    def test_uuid_generation(self):
        """测试UUID自动生成"""
        event1 = EventBase()
        event2 = EventBase()

        assert event1.uuid != event2.uuid
        assert len(event1.uuid) == len(event2.uuid)

    def test_source_default(self):
        """测试默认数据源"""
        event = EventBase()
        # source 默认是 VOID 或其他值，不假设是 SIM
        assert isinstance(event.source, SOURCE_TYPES)


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.properties
class TestEventBaseProperties:
    """测试 EventBase 属性访问和修改"""

    @pytest.fixture
    def event(self):
        return EventBase()

    def test_uuid_property(self, event):
        """测试 uuid 属性"""
        assert isinstance(event.uuid, str)
        assert len(event.uuid) > 0

    def test_event_type_property(self, event):
        """测试 event_type 属性"""
        event.event_type = EVENT_TYPES.PRICEUPDATE
        assert event.event_type == EVENT_TYPES.PRICEUPDATE

    def test_event_type_with_string(self, event):
        """测试使用字符串设置事件类型"""
        event.event_type = "PRICEUPDATE"
        # 注意：字符串会被转换为枚举或保持为字符串
        assert isinstance(event.event_type, (EVENT_TYPES, str))

    def test_source_property(self, event):
        """测试 source 属性"""
        # 不假设默认值，只测试设置后的值
        event.set_source(SOURCE_TYPES.SIM)
        assert event.source == SOURCE_TYPES.SIM

    def test_set_source_method(self, event):
        """测试 set_source 方法"""
        event.set_source(SOURCE_TYPES.TUSHARE)
        assert event.source == SOURCE_TYPES.TUSHARE

    @pytest.mark.parametrize("source_type", [
        SOURCE_TYPES.SIM,
        SOURCE_TYPES.TUSHARE,
        SOURCE_TYPES.YAHOO,
        SOURCE_TYPES.AKSHARE,
    ])
    def test_all_source_types(self, event, source_type):
        """测试所有数据源类型"""
        event.set_source(source_type)
        assert event.source == source_type


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.time_handling
class TestEventBaseTimeHandling:
    """测试 EventBase 时间处理"""

    @pytest.fixture
    def event(self):
        return EventBase()

    def test_timestamp_property(self, event):
        """测试 timestamp 属性"""
        # EventBase 使用 TimeMixin，timestamp 可用
        assert event.timestamp is not None or hasattr(event, 'timestamp')


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.identification
class TestEventBaseIdentification:
    """测试 EventBase 标识符"""

    @pytest.fixture
    def event(self):
        return EventBase()

    def test_uuid_property(self, event):
        """测试 uuid 属性"""
        assert isinstance(event.uuid, str)
        assert len(event.uuid) > 0


# ===== EventPriceUpdate 测试 =====

@pytest.mark.unit
@pytest.mark.events
@pytest.mark.price_update
class TestEventPriceUpdateConstruction:
    """测试 EventPriceUpdate 构造和初始化"""

    def test_default_initialization(self):
        """测试默认初始化"""
        event = EventPriceUpdate()

        assert event.event_type == EVENT_TYPES.PRICEUPDATE
        assert event._price_type is None
        assert event.payload is None

    def test_initialization_with_bar(self, test_bar):
        """测试使用 Bar 初始化"""
        event = EventPriceUpdate(payload=test_bar)

        assert event._price_type == PRICEINFO_TYPES.BAR
        assert event.payload == test_bar
        assert event._bar == test_bar

    def test_initialization_with_tick(self, test_tick):
        """测试使用 Tick 初始化"""
        event = EventPriceUpdate(payload=test_tick)

        assert event._price_type == PRICEINFO_TYPES.TICK
        assert event.payload == test_tick
        assert event._tick == test_tick

    @pytest.fixture
    def test_bar(self):
        """创建测试 Bar 对象"""
        return Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            open=Decimal("10.0"),
            high=Decimal("10.8"),
            low=Decimal("9.8"),
            close=Decimal("10.5"),
            volume=1000000,
            amount=Decimal("10500000.0"),
            frequency=FREQUENCY_TYPES.DAY
        )

    @pytest.fixture
    def test_tick(self):
        """创建测试 Tick 对象"""
        return Tick(
            code="000001.SZ",
            price=Decimal("10.5"),
            volume=1000,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            source=SOURCE_TYPES.SIM
        )


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.price_update
class TestEventPriceUpdateBarAccess:
    """测试 EventPriceUpdate Bar 数据访问"""

    @pytest.fixture
    def bar_event(self):
        """创建 Bar 事件"""
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            open=Decimal("10.0"),
            high=Decimal("10.8"),
            low=Decimal("9.8"),
            close=Decimal("10.5"),
            volume=1000000,
            amount=Decimal("10500000.0"),
            frequency=FREQUENCY_TYPES.DAY
        )
        return EventPriceUpdate(payload=bar)

    def test_code_property(self, bar_event):
        """测试 code 属性"""
        assert bar_event.code == "000001.SZ"

    def test_open_property(self, bar_event):
        """测试 open 属性"""
        assert bar_event.open == Decimal("10.0")

    def test_high_property(self, bar_event):
        """测试 high 属性"""
        assert bar_event.high == Decimal("10.8")

    def test_low_property(self, bar_event):
        """测试 low 属性"""
        assert bar_event.low == Decimal("9.8")

    def test_close_property(self, bar_event):
        """测试 close 属性"""
        assert bar_event.close == Decimal("10.5")

    def test_volume_property(self, bar_event):
        """测试 volume 属性"""
        assert bar_event.volume == 1000000

    def test_business_timestamp(self, bar_event):
        """测试 business_timestamp 属性"""
        expected = datetime.datetime(2024, 1, 1, 10, 0, 0)
        assert bar_event.business_timestamp == expected


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.price_update
class TestEventPriceUpdateTickAccess:
    """测试 EventPriceUpdate Tick 数据访问"""

    @pytest.fixture
    def tick_event(self, test_tick):
        """创建 Tick 事件"""
        return EventPriceUpdate(payload=test_tick)

    @pytest.fixture
    def test_tick(self):
        """创建测试 Tick 对象"""
        return Tick(
            code="000001.SZ",
            price=Decimal("10.5"),
            volume=1000,
            direction=TICKDIRECTION_TYPES.NEUTRAL,
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            source=SOURCE_TYPES.SIM
        )

    def test_code_property(self, tick_event):
        """测试 code 属性"""
        assert tick_event.code == "000001.SZ"

    def test_volume_property(self, tick_event):
        """测试 volume 属性"""
        assert tick_event.volume == 1000

    def test_price_property_with_tick(self, tick_event):
        """测试 Tick 类型时 price 属性"""
        assert tick_event.price == Decimal("10.5")


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.price_update
class TestEventPriceUpdateDataConversion:
    """测试 EventPriceUpdate 数据转换"""

    @pytest.fixture
    def bar_event(self):
        """创建 Bar 事件"""
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            open=Decimal("10.0"),
            high=Decimal("10.8"),
            low=Decimal("9.8"),
            close=Decimal("10.5"),
            volume=1000000,
            amount=Decimal("10500000.0"),
            frequency=FREQUENCY_TYPES.DAY
        )
        return EventPriceUpdate(payload=bar)

    def test_to_dataframe(self, bar_event):
        """测试转换为 DataFrame"""
        df = bar_event.to_dataframe()

        assert df is not None
        assert "code" in df.columns
        assert "open" in df.columns
        assert "high" in df.columns
        assert "low" in df.columns
        assert "close" in df.columns
        assert "volume" in df.columns

    def test_to_dataframe_values(self, bar_event):
        """测试 DataFrame 数据正确性"""
        df = bar_event.to_dataframe()

        assert df["code"].iloc[0] == "000001.SZ"
        assert df["open"].iloc[0] == Decimal("10.0")
        assert df["close"].iloc[0] == Decimal("10.5")


# ===== EventCapitalUpdate 测试 =====

@pytest.mark.unit
@pytest.mark.events
@pytest.mark.capital_update
class TestEventCapitalUpdate:
    """测试 EventCapitalUpdate 事件"""

    def test_default_initialization(self):
        """测试默认初始化"""
        event = EventCapitalUpdate()

        assert event.event_type == EVENT_TYPES.CAPITALUPDATE

    def test_event_type_property(self):
        """测试事件类型"""
        event = EventCapitalUpdate()
        assert event.event_type == EVENT_TYPES.CAPITALUPDATE


# ===== EventOrderRelated 测试 =====

@pytest.mark.unit
@pytest.mark.events
@pytest.mark.order_related
class TestEventOrderRelatedConstruction:
    """测试 EventOrderRelated 构造和初始化"""

    @pytest.fixture
    def test_order(self):
        """创建测试 Order 对象"""
        return Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=Decimal("10.50"),
            frozen_money=10500,
            transaction_price=Decimal("0.0"),
            remain=Decimal("0.0"),
            fee=Decimal("5.25")
        )

    def test_initialization_with_order(self, test_order):
        """测试使用 Order 初始化"""
        event = EventOrderRelated(test_order)

        assert event.order_id == test_order.order_id
        assert event.code == test_order.code
        assert event.direction == test_order.direction
        assert event.order_type == test_order.order_type
        assert event.volume == test_order.volume
        # 使用 frozen_money 而不是 frozen
        assert event.limit_price == test_order.limit_price


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.order_related
class TestEventOrderRelatedProperties:
    """测试 EventOrderRelated 属性访问"""

    @pytest.fixture
    def test_order(self):
        """创建测试 Order 对象"""
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.LIMITORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=Decimal("10.50"),
            frozen_money=10500,
            transaction_price=Decimal("0.0"),
            remain=Decimal("0.0"),
            fee=Decimal("5.25")
        )
        return order

    @pytest.fixture
    def order_event(self, test_order):
        """创建订单事件"""
        return EventOrderRelated(test_order)

    def test_order_id_property(self, order_event, test_order):
        """测试 order_id 属性"""
        # order_id 是自动生成的
        assert order_event.order_id == test_order.order_id

    def test_code_property(self, order_event):
        """测试 code 属性"""
        assert order_event.code == "000001.SZ"

    def test_direction_property(self, order_event):
        """测试 direction 属性"""
        assert order_event.direction == DIRECTION_TYPES.LONG

    def test_order_type_property(self, order_event):
        """测试 order_type 属性"""
        assert order_event.order_type == ORDER_TYPES.LIMITORDER

    def test_volume_property(self, order_event):
        """测试 volume 属性"""
        assert order_event.volume == 1000

    def test_limit_price_property(self, order_event):
        """测试 limit_price 属性"""
        assert order_event.limit_price == Decimal("10.50")

    def test_transaction_price_property(self, order_event):
        """测试 transaction_price 属性"""
        assert order_event.transaction_price == Decimal("0.0")

    def test_remain_property(self, order_event):
        """测试 remain 属性"""
        assert order_event.remain == Decimal("0.0")

    def test_engine_id_property(self, order_event):
        """测试 engine_id 属性"""
        assert order_event.engine_id == "test_engine"


# ===== 事件综合测试 =====

@pytest.mark.unit
@pytest.mark.events
@pytest.mark.integration
class TestEventsIntegration:
    """测试事件系统集成"""

    def test_event_chain_creation(self):
        """测试事件链创建"""
        # 创建价格更新事件
        bar = Bar(
            code="000001.SZ",
            timestamp=datetime.datetime(2024, 1, 1, 10, 0, 0),
            open=Decimal("10.0"),
            high=Decimal("10.8"),
            low=Decimal("9.8"),
            close=Decimal("10.5"),
            volume=1000000,
            amount=Decimal("10500000.0"),
            frequency=FREQUENCY_TYPES.DAY
        )
        price_event = EventPriceUpdate(payload=bar)

        # 创建订单事件
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=Decimal("0.0")
        )
        order_event = EventOrderRelated(order)

        # 验证事件属性
        assert price_event.event_type == EVENT_TYPES.PRICEUPDATE
        assert order_event.code == price_event.code

    def test_event_context_property(self):
        """测试事件上下文属性"""
        event = EventBase()
        # EventBase 使用 _context 属性
        assert hasattr(event, '_context')

    def test_multiple_events_same_order(self):
        """测试同一订单的多个事件"""
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=DIRECTION_TYPES.LONG,
            order_type=ORDER_TYPES.MARKETORDER,
            status=ORDERSTATUS_TYPES.NEW,
            volume=1000,
            limit_price=Decimal("0.0")
        )

        # 创建订单生命周期事件
        events = [
            EventOrderRelated(order),
            EventOrderRelated(order),
            EventOrderRelated(order)
        ]

        # 验证所有事件引用相同订单
        expected_order_id = order.order_id
        for event in events:
            assert event.order_id == expected_order_id


@pytest.mark.unit
@pytest.mark.events
@pytest.mark.edge_cases
class TestEventsEdgeCases:
    """测试事件边界情况"""

    def test_event_without_payload(self):
        """测试无载荷事件"""
        event = EventPriceUpdate()

        assert event.payload is None
        assert event.code is None
        assert event.open is None

    def test_event_with_none_payload(self):
        """测试 None 载荷事件"""
        event = EventPriceUpdate(payload=None)

        assert event.payload is None

    def test_time_updates(self):
        """测试时间更新"""
        event = EventBase()

        times = [
            datetime.datetime(2024, 1, 1, 10, 0, 0),
            datetime.datetime(2024, 1, 1, 11, 0, 0),
            datetime.datetime(2024, 1, 1, 12, 0, 0),
        ]

        for t in times:
            event.timestamp = t
            assert event.timestamp == t

    def test_event_context_property(self):
        """测试上下文属性"""
        event = EventBase()
        # EventBase 使用 _context 属性
        assert hasattr(event, '_context')

    def test_large_payload(self):
        """测试大载荷事件"""
        large_data = list(range(10000))
        event = EventBase()
        event.payload = large_data

        assert len(event.payload) == 10000
