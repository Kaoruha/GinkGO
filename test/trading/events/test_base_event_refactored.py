"""
EventBase测试 - Refactored

使用pytest最佳实践重构的EventBase测试套件
包括fixtures共享、参数化测试和清晰的测试分组
"""
import pytest
import datetime
import uuid as uuid_module
from unittest.mock import Mock, patch

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES
from ginkgo.trading.time.interfaces import ITimeProvider


@pytest.fixture
def sample_time_provider():
    """Mock时间提供者"""
    provider = Mock(spec=ITimeProvider)
    provider.now.return_value = datetime.datetime(2024, 1, 1, 10, 30, 0)
    return provider


@pytest.fixture
def sample_event_data():
    """标准事件测试数据"""
    return {
        "name": "TestEvent",
        "event_type": EVENT_TYPES.PRICEUPDATE,
        "source": SOURCE_TYPES.SIM
    }


@pytest.mark.unit
class TestEventBaseConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self, sample_event_data):
        """测试默认构造"""
        event = EventBase(**sample_event_data)

        assert event.name == "TestEvent"
        assert event.event_type == EVENT_TYPES.PRICEUPDATE
        assert event.value is None

    def test_custom_name(self):
        """测试自定义名称"""
        event = EventBase(name="CustomEvent")
        assert event.name == "CustomEvent"

    def test_with_time_provider(self, sample_event_data, sample_time_provider):
        """测试使用时间提供者"""
        sample_event_data['time_provider'] = sample_time_provider
        event = EventBase(**sample_event_data)

        assert event.timestamp == sample_time_provider.now.return_value

    def test_custom_uuid(self, sample_event_data):
        """测试自定义UUID"""
        custom_uuid = "custom-event-uuid-123"
        sample_event_data['uuid'] = custom_uuid

        event = EventBase(**sample_event_data)
        assert event.uuid == custom_uuid

    def test_id_parameters(self, sample_event_data):
        """测试ID参数"""
        sample_event_data.update({
            'engine_id': 'test_engine',
            'portfolio_id': 'test_portfolio',
            'run_id': 'test_run'
        })
        event = EventBase(**sample_event_data)

        assert event.engine_id == 'test_engine'
        assert event.portfolio_id == 'test_portfolio'
        assert event.run_id == 'test_run'

    def test_base_class_inheritance(self, sample_event_data):
        """测试BacktestBase继承"""
        from ginkgo.trading.core.backtest_base import BacktestBase

        event = EventBase(**sample_event_data)
        assert isinstance(event, BacktestBase)


@pytest.mark.unit
class TestEventBaseProperties:
    """2. 属性访问测试"""

    def test_name_property(self, sample_event_data):
        """测试名称属性"""
        event = EventBase(**sample_event_data)
        assert event.name == "TestEvent"
        assert isinstance(event.name, str)

    def test_timestamp_property(self, sample_event_data, sample_time_provider):
        """测试时间戳属性"""
        sample_event_data['time_provider'] = sample_time_provider
        event = EventBase(**sample_event_data)

        assert event.timestamp == sample_time_provider.now.return_value
        assert isinstance(event.timestamp, datetime.datetime)

    def test_uuid_property(self, sample_event_data):
        """测试UUID属性"""
        event = EventBase(**sample_event_data)

        assert event.uuid is not None
        assert len(event.uuid) > 0
        assert isinstance(event.uuid, str)

    def test_uuid_uniqueness(self, sample_event_data):
        """测试UUID唯一性"""
        event1 = EventBase(**sample_event_data)
        event2 = EventBase(**sample_event_data)

        assert event1.uuid != event2.uuid

    def test_event_type_property(self, sample_event_data):
        """测试事件类型属性"""
        sample_event_data['event_type'] = EVENT_TYPES.SIGNALGENERATION
        event = EventBase(**sample_event_data)

        assert event.event_type == EVENT_TYPES.SIGNALGENERATION

    def test_source_property(self, sample_event_data):
        """测试来源属性"""
        sample_event_data['source'] = SOURCE_TYPES.REALTIME
        event = EventBase(**sample_event_data)

        assert event.source == SOURCE_TYPES.REALTIME


@pytest.mark.unit
class TestEventBaseTimeManagement:
    """3. 时间管理测试"""

    def test_time_provider_integration(self, sample_event_data, sample_time_provider):
        """测试时间提供者集成"""
        sample_event_data['time_provider'] = sample_time_provider
        event = EventBase(**sample_event_data)

        current_time = event.get_current_time()
        assert current_time == sample_time_provider.now.return_value

    def test_clock_now_fallback(self, sample_event_data):
        """测试无时间提供者时使用系统时间"""
        event = EventBase(**sample_event_data)

        current_time = event.get_current_time()
        assert isinstance(current_time, datetime.datetime)

        # 验证时间在合理范围内（1秒内）
        time_diff = (datetime.datetime.now() - current_time).total_seconds()
        assert time_diff < 1.0

    def test_timezone_awareness(self, sample_event_data, sample_time_provider):
        """测试时区意识"""
        # 设置带时区的时间
        aware_time = datetime.datetime(2024, 1, 1, 10, 30, 0,
                                    tzinfo=datetime.timezone.utc)
        sample_time_provider.now.return_value = aware_time
        sample_event_data['time_provider'] = sample_time_provider

        event = EventBase(**sample_event_data)
        assert event.timestamp == aware_time


@pytest.mark.unit
class TestEventBaseIdentification:
    """4. 标识符管理测试"""

    def test_uuid_generation(self, sample_event_data):
        """测试UUID自动生成"""
        event = EventBase(**sample_event_data)

        assert event.uuid is not None
        assert len(event.uuid) == 36  # 标准UUID格式

    def test_custom_uuid_setting(self, sample_event_data):
        """测试自定义UUID设置"""
        custom_uuid = "custom-event-uuid-456"
        sample_event_data['uuid'] = custom_uuid

        event = EventBase(**sample_event_data)
        assert event.uuid == custom_uuid

    def test_uuid_format_validation(self, sample_event_data):
        """测试UUID格式验证"""
        event = EventBase(**sample_event_data)

        # 验证UUID格式
        try:
            uuid_module.UUID(event.uuid)
            is_valid = True
        except ValueError:
            is_valid = False

        assert is_valid


@pytest.mark.unit
class TestEventBaseEnumIntegration:
    """5. 枚举集成测试"""

    @pytest.mark.parametrize("event_type", [
        EVENT_TYPES.PRICEUPDATE,
        EVENT_TYPES.SIGNALGENERATION,
        EVENT_TYPES.ORDERSUBMITTED,
        EVENT_TYPES.ORDERFILLED,
        EVENT_TYPES.ENGINESTOP
    ])
    def test_event_types_integration(self, sample_event_data, event_type):
        """测试EVENT_TYPES集成"""
        sample_event_data['event_type'] = event_type
        event = EventBase(**sample_event_data)
        assert event.event_type == event_type

    @pytest.mark.parametrize("source", [
        SOURCE_TYPES.SIM,
        SOURCE_TYPES.REALTIME,
        SOURCE_TYPES.BACKTEST,
        SOURCE_TYPES.DATABASE
    ])
    def test_source_types_integration(self, sample_event_data, source):
        """测试SOURCE_TYPES集成"""
        sample_event_data['source'] = source
        event = EventBase(**sample_event_data)
        assert event.source == source


@pytest.mark.unit
class TestEventBaseAbstractBehavior:
    """6. 抽象行为测试"""

    def test_abstract_metaclass(self, sample_event_data):
        """测试抽象元类"""
        # EventBase使用ABCMeta元类
        event = EventBase(**sample_event_data)
        assert hasattr(event, '__abstractmethods__')

    def test_direct_instantiation_possible(self, sample_event_data):
        """测试直接实例化"""
        # EventBase可以被直接实例化（不像纯抽象类）
        event = EventBase(**sample_event_data)
        assert event is not None


@pytest.mark.unit
class TestEventBasePayload:
    """7. Payload管理测试"""

    def test_payload_initial_state(self, sample_event_data):
        """测试payload初始状态"""
        event = EventBase(**sample_event_data)

        assert event.value is None
        assert event.payload is None

    def test_payload_setting(self, sample_event_data):
        """测试payload设置"""
        event = EventBase(**sample_event_data)
        test_data = {"message": "Hello", "value": 123}

        event.payload = test_data

        assert event.value is test_data
        assert event.payload is test_data

    def test_value_setting(self, sample_event_data):
        """测试value设置"""
        event = EventBase(**sample_event_data)
        test_data = {"message": "World", "value": 456}

        event.value = test_data

        assert event.value is test_data
        assert event.payload is test_data

    @pytest.mark.parametrize("test_data", [
        "string",
        42,
        3.14,
        True,
        [1, 2, 3],
        {"key": "value"},
        None
    ])
    def test_various_payload_types(self, sample_event_data, test_data):
        """测试各种payload数据类型"""
        event = EventBase(**sample_event_data)
        event.payload = test_data

        assert event.value == test_data
        assert event.payload == test_data


@pytest.mark.unit
class TestEventBaseMethods:
    """8. 事件方法测试"""

    def test_set_name(self, sample_event_data):
        """测试set_name方法"""
        event = EventBase(**sample_event_data)
        new_name = "UpdatedEvent"

        event.set_name(new_name)
        assert event.name == new_name

    def test_set_payload(self, sample_event_data):
        """测试set_payload方法"""
        event = EventBase(**sample_event_data)
        test_data = {"key": "value"}

        result = event.set_payload(test_data)

        assert result is event  # 返回self
        assert event.payload == test_data

    def test_set_value(self, sample_event_data):
        """测试set_value方法"""
        event = EventBase(**sample_event_data)
        test_data = {"key": "value"}

        result = event.set_value(test_data)

        assert result is event  # 返回self
        assert event.value == test_data


@pytest.mark.integration
class TestEventBaseDatabaseOperations:
    """9. 数据库操作测试"""

    def test_event_to_model(self, sample_event_data, ginkgo_config):
        """测试Event到Model的转换"""
        event = EventBase(**sample_event_data)
        model = event.to_model()

        assert model.uuid == event.uuid
        assert model.name == event.name

    def test_event_from_model(self, sample_event_data, ginkgo_config):
        """测试Model到Event的转换"""
        event1 = EventBase(**sample_event_data)
        model = event1.to_model()
        event2 = EventBase.from_model(model)

        assert event2.uuid == event1.uuid
        assert event2.name == event1.name


@pytest.mark.unit
class TestEventBaseEdgeCases:
    """10. 边界情况测试"""

    def test_empty_name(self):
        """测试空名称"""
        event = EventBase(name="")
        assert event.name == ""

    def test_none_payload(self, sample_event_data):
        """测试None payload"""
        event = EventBase(**sample_event_data)
        event.payload = None

        assert event.value is None
        assert event.payload is None

    @pytest.mark.parametrize("name", [
        "Event1",
        "Event2",
        "Event3",
        "SimpleEvent",
        "COMPLEX_EVENT_NAME"
    ])
    def test_various_names(self, name):
        """测试各种事件名称"""
        event = EventBase(name=name)
        assert event.name == name


@pytest.mark.unit
class TestEventBaseTimeProviders:
    """11. 时间提供者测试"""

    def test_mock_time_provider(self, sample_event_data, sample_time_provider):
        """测试Mock时间提供者"""
        sample_event_data['time_provider'] = sample_time_provider
        event = EventBase(**sample_event_data)

        assert event.timestamp == sample_time_provider.now.return_value

    def test_multiple_time_calls(self, sample_event_data, sample_time_provider):
        """测试多次时间调用"""
        sample_event_data['time_provider'] = sample_time_provider
        event = EventBase(**sample_event_data)

        # 多次调用应该返回相同时间
        time1 = event.get_current_time()
        time2 = event.get_current_time()

        assert time1 == time2


@pytest.mark.financial
class TestEventBaseBusinessScenarios:
    """12. 业务场景测试"""

    def test_price_update_event(self, sample_event_data):
        """测试价格更新事件"""
        sample_event_data['event_type'] = EVENT_TYPES.PRICEUPDATE
        sample_event_data['name'] = "PriceUpdate"

        event = EventBase(**sample_event_data)
        assert event.event_type == EVENT_TYPES.PRICEUPDATE

    def test_signal_event(self, sample_event_data):
        """测试信号事件"""
        sample_event_data['event_type'] = EVENT_TYPES.SIGNALGENERATION
        sample_event_data['name'] = "SignalGenerated"

        event = EventBase(**sample_event_data)
        assert event.event_type == EVENT_TYPES.SIGNALGENERATION

    def test_order_event(self, sample_event_data):
        """测试订单事件"""
        sample_event_data['event_type'] = EVENT_TYPES.ORDER
        sample_event_data['name'] = "OrderCreated"

        event = EventBase(**sample_event_data)
        assert event.event_type == EVENT_TYPES.ORDER
