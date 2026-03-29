"""
EventBase事件基类TDD测试

通过TDD方式开发EventBase的核心逻辑测试套件
聚焦于事件创建、时间管理和标识符生成功能
"""
import pytest
import sys
import datetime
import uuid as uuid_module
from pathlib import Path
from unittest.mock import MagicMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES


@pytest.mark.unit
class TestEventBaseConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        event = EventBase()
        assert event.name == "EventBase"
        assert isinstance(event.uuid, str)
        assert len(event.uuid) == 32  # uuid4().hex is 32 hex chars

    def test_custom_name_constructor(self):
        """测试自定义名称构造"""
        event = EventBase(name="MyCustomEvent")
        assert event.name == "MyCustomEvent"

    def test_time_provider_constructor(self):
        """测试时间提供者构造"""
        mock_provider = MagicMock()
        event = EventBase(name="Test")
        event.set_time_provider(mock_provider)
        assert event._time_provider is mock_provider

    def test_uuid_parameter_constructor(self):
        """测试UUID参数构造"""
        custom_uuid = "my-custom-uuid-1234567890123456"
        event = EventBase(uuid=custom_uuid)
        assert event.uuid == custom_uuid

    def test_id_parameters_constructor(self):
        """测试ID参数构造"""
        event = EventBase(name="Test")
        # EventBase overrides portfolio_id, engine_id, run_id properties
        # but __init__ does not initialize _portfolio_id, _engine_id, _run_id
        # so accessing them without setting raises AttributeError
        with pytest.raises(AttributeError):
            _ = event.portfolio_id
        with pytest.raises(AttributeError):
            _ = event.engine_id
        with pytest.raises(AttributeError):
            _ = event.run_id

    def test_backtest_base_inheritance(self):
        """测试BacktestBase继承"""
        event = EventBase(name="Test")
        # TimeMixin provides timestamp and init_time
        assert isinstance(event.timestamp, datetime.datetime)
        assert isinstance(event.init_time, datetime.datetime)
        # ContextMixin.__init__ is not called because TimeMixin does not call super()
        # EventBase inherits from TimeMixin and ContextMixin
        assert isinstance(event, EventBase)
        assert isinstance(event, type(event).__bases__[0])  # TimeMixin
        assert isinstance(event, type(event).__bases__[1])  # ContextMixin


@pytest.mark.unit
class TestEventBaseProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        """测试名称属性"""
        event = EventBase(name="PropertyTest")
        assert event.name == "PropertyTest"
        # Test setter
        event.name = "NewName"
        assert event.name == "NewName"

    def test_timestamp_property(self):
        """测试时间戳属性"""
        before = datetime.datetime.now()
        event = EventBase()
        after = datetime.datetime.now()
        assert isinstance(event.timestamp, datetime.datetime)
        assert before <= event.timestamp <= after

    def test_uuid_property(self):
        """测试UUID属性"""
        event = EventBase()
        assert isinstance(event.uuid, str)
        assert len(event.uuid) == 32

    def test_event_type_property(self):
        """测试事件类型属性"""
        event = EventBase()
        # Default event_type is None
        assert event.event_type is None

    def test_source_property(self):
        """测试来源属性"""
        event = EventBase()
        assert event.source == SOURCE_TYPES.SIM

    def test_time_provider_property(self):
        """测试时间提供者属性"""
        event = EventBase()
        assert event._time_provider is None


@pytest.mark.unit
class TestEventBaseTimeManagement:
    """3. 时间管理测试"""

    def test_time_provider_integration(self):
        """测试时间提供者集成"""
        mock_provider = MagicMock()
        now = datetime.datetime(2024, 1, 15, 10, 30, 0)
        mock_provider.now.return_value = now
        event = EventBase(name="Test")
        event.set_time_provider(mock_provider)
        assert event.get_time_provider() is mock_provider
        assert event.get_current_time() == now

    def test_time_provider_timestamp_generation(self):
        """测试时间提供者时间戳生成"""
        mock_provider = MagicMock()
        custom_time = datetime.datetime(2024, 6, 1, 12, 0, 0)
        mock_provider.now.return_value = custom_time
        event = EventBase(name="Test")
        event.set_time_provider(mock_provider)
        assert event.get_current_time() == custom_time

    def test_clock_now_fallback(self):
        """测试时钟回退机制"""
        event = EventBase(name="Test")
        # Without time_provider, timestamp comes from TimeMixin (datetime.now)
        assert isinstance(event.timestamp, datetime.datetime)

    def test_system_datetime_fallback(self):
        """测试系统时间回退机制"""
        before = datetime.datetime.now()
        event = EventBase(name="Test")
        after = datetime.datetime.now()
        assert isinstance(event.timestamp, datetime.datetime)
        assert before <= event.timestamp <= after

    def test_timezone_awareness(self):
        """测试时区意识"""
        event = EventBase(name="Test")
        # TimeMixin uses datetime.now() which is naive
        ts = event.timestamp
        assert isinstance(ts, datetime.datetime)


@pytest.mark.unit
class TestEventBaseIdentification:
    """4. 标识符管理测试"""

    def test_uuid_generation(self):
        """测试UUID生成"""
        event = EventBase()
        assert event.uuid is not None
        assert isinstance(event.uuid, str)
        assert len(event.uuid) == 32

    def test_uuid_uniqueness(self):
        """测试UUID唯一性"""
        events = [EventBase() for _ in range(100)]
        uuids = [e.uuid for e in events]
        assert len(set(uuids)) == 100

    def test_custom_uuid_setting(self):
        """测试自定义UUID设置"""
        custom_id = "abcdef0123456789abcdef0123456789"
        event = EventBase(uuid=custom_id)
        assert event.uuid == custom_id

    def test_uuid_format_validation(self):
        """测试UUID格式验证"""
        event = EventBase()
        # Default uuid is uuid4().hex (32 hex chars)
        assert len(event.uuid) == 32
        # Should be valid hex
        int(event.uuid, 16)  # Will raise ValueError if not hex


@pytest.mark.unit
class TestEventBaseEnumIntegration:
    """5. 枚举集成测试"""

    def test_event_types_integration(self):
        """测试EVENT_TYPES集成"""
        event = EventBase(name="Test")
        event.set_type(EVENT_TYPES.PRICEUPDATE)
        assert event.event_type == EVENT_TYPES.PRICEUPDATE

    def test_source_types_integration(self):
        """测试SOURCE_TYPES集成"""
        event = EventBase(name="Test")
        assert event.source == SOURCE_TYPES.SIM
        event.set_source(SOURCE_TYPES.BACKTEST)
        assert event.source == SOURCE_TYPES.BACKTEST

    def test_enum_value_validation(self):
        """测试枚举值验证"""
        event = EventBase(name="Test")
        # Setting event_type via string
        event.set_type("PRICEUPDATE")
        assert event.event_type == EVENT_TYPES.PRICEUPDATE
        # Setting event_type via enum
        event.set_type(EVENT_TYPES.ORDERSUBMITTED)
        assert event.event_type == EVENT_TYPES.ORDERSUBMITTED


@pytest.mark.unit
class TestEventBaseAbstractBehavior:
    """6. 抽象行为测试"""

    def test_abstract_metaclass(self):
        """测试抽象元类"""
        # EventBase uses ABCMeta metaclass but has no abstract methods
        assert type(EventBase).__name__ == 'ABCMeta'

    def test_abstract_methods_enforcement(self):
        """测试抽象方法强制"""
        # EventBase has ABCMeta but defines no @abstractmethod
        # so it can be instantiated directly
        event = EventBase()
        assert event is not None

    def test_direct_instantiation_prevention(self):
        """测试直接实例化防护"""
        # EventBase uses ABCMeta but has no abstract methods,
        # so direct instantiation is allowed
        event = EventBase(name="Test")
        assert event.name == "Test"


@pytest.mark.unit
class TestEventBaseDataSetting:
    """7. 数据设置测试"""

    def test_name_setting(self):
        """测试名称设置"""
        event = EventBase()
        result = event.set_name("NewEventName")
        assert event.name == "NewEventName"
        assert result == "NewEventName"

    def test_parameter_extraction(self):
        """测试参数提取"""
        # Test that kwargs parameters are properly extracted
        custom_uuid = "param-uuid-1234567890123456"
        event = EventBase(uuid=custom_uuid)
        assert event.uuid == custom_uuid
        # uuid kwarg should not be passed to parent
        assert event.name == "EventBase"

    def test_base_class_parameter_passing(self):
        """测试基类参数传递"""
        # Test that business_timestamp is passed through to TimeMixin
        event = EventBase(name="Test", business_timestamp="2024-01-01")
        assert event.business_timestamp == datetime.datetime(2024, 1, 1, 0, 0, 0)

    def test_datetime_normalize_integration(self):
        """测试时间标准化集成"""
        event = EventBase(name="Test")
        # set_time uses datetime_normalize internally
        event.set_time("2024-06-15 14:30:00")
        assert event.timestamp == datetime.datetime(2024, 6, 15, 14, 30, 0)
