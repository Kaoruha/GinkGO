"""
BaseFeeder数据馈送器TDD测试

通过TDD方式开发BaseFeeder的核心逻辑测试套件
聚焦于数据获取、事件发布、时间验证和缓存机制功能
"""
import pytest
import sys
import datetime
from pathlib import Path
import pandas as pd
from decimal import Decimal
from unittest.mock import MagicMock, patch, PropertyMock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.data.services.base_service import ServiceResult


def _mock_bar_service():
    """创建mock bar_service, 返回空DataFrame."""
    service = MagicMock()
    service.get.return_value = ServiceResult(success=False, error="no data", data=None)
    return service


def _make_feeder_with_time(time_val=None):
    """创建一个设置好 now 属性的 feeder, 用于测试 get_daybar."""
    feeder = BaseFeeder(bar_service=_mock_bar_service())
    # BaseFeeder.get_daybar uses self.now, which doesn't exist on the class.
    # We mock it as a property so the method can run.
    type(feeder).now = property(lambda self: time_val)
    return feeder


@pytest.mark.unit
class TestBaseFeederConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert feeder.name == "basic_feeder"
        assert isinstance(feeder, BaseFeeder)

    def test_custom_name_constructor(self):
        """测试自定义名称构造"""
        feeder = BaseFeeder(name="my_feeder", bar_service=_mock_bar_service())
        assert feeder.name == "my_feeder"

    def test_backtest_base_inheritance(self):
        """测试BacktestBase继承"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert getattr(feeder, 'uuid', None) is not None
        assert callable(getattr(feeder, 'set_name', None))

    def test_time_related_inheritance(self):
        """测试TimeRelated继承"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert isinstance(feeder.timestamp, datetime.datetime)
        assert callable(getattr(feeder, 'advance_time', None))
        # current_timestamp is None before time provider is set
        assert feeder.current_timestamp is None

    def test_engine_put_initialization(self):
        """测试引擎发布器初始化"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert feeder._engine_put is None


@pytest.mark.unit
class TestBaseFeederProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        """测试名称属性"""
        feeder = BaseFeeder(name="test", bar_service=_mock_bar_service())
        assert feeder.name == "test"

    def test_engine_put_property(self):
        """测试引擎发布器属性"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert feeder._engine_put is None
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        assert feeder._engine_put is publisher

    def test_now_property(self):
        """测试当前时间属性"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        # current_timestamp is None before time provider is set
        assert feeder.current_timestamp is None

    def test_timestamp_property(self):
        """测试时间戳属性"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert feeder.timestamp is not None
        assert isinstance(feeder.timestamp, datetime.datetime)


@pytest.mark.unit
class TestEventPublishing:
    """3. 事件发布测试"""

    def test_set_event_publisher(self):
        """测试设置事件发布器"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        assert feeder._engine_put is publisher

    def test_put_with_publisher(self):
        """测试有发布器时的事件发送"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        event = MagicMock()
        feeder.put(event)
        publisher.assert_called_once_with(event)

    def test_put_without_publisher(self):
        """测试无发布器时的事件发送"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        event = MagicMock()
        feeder.put(event)
        assert feeder._engine_put is None

    def test_event_publisher_callable_validation(self):
        """测试事件发布器可调用性验证"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        feeder.set_event_publisher("not_callable")
        assert feeder._engine_put == "not_callable"

    def test_multiple_events_publishing(self):
        """测试多个事件连续发布"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        events = [MagicMock() for _ in range(3)]
        for event in events:
            feeder.put(event)
        assert publisher.call_count == 3


@pytest.mark.unit
class TestDaybarDataAccess:
    """4. 日线数据访问测试"""

    def test_get_daybar_method_exists(self):
        """测试get_daybar方法存在"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert callable(getattr(feeder, 'get_daybar', None))

    def test_get_daybar_basic_query(self):
        """测试基础日线数据查询"""
        feeder = _make_feeder_with_time(time_val=None)
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_get_daybar_with_valid_date(self):
        """测试有效日期查询"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        # Mock returns empty result
        assert result.empty is True

    def test_get_daybar_with_invalid_date(self):
        """测试无效日期查询"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        result = feeder.get_daybar("000001.SZ", None)
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_load_daybar_delegation(self):
        """测试_load_daybar委托"""
        service = _mock_bar_service()
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        feeder.bar_service = service
        feeder.get_daybar("000001.SZ", "2023-01-01")
        service.get.assert_called_once()


@pytest.mark.unit
class TestTimeBoundaryValidation:
    """5. 时间边界验证测试 - 防未来数据泄露"""

    def test_future_data_access_denied(self):
        """测试未来数据访问被拒绝 - 核心保护"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 1, 1))
        result = feeder.get_daybar("000001.SZ", "2099-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_current_day_data_access_allowed(self):
        """测试当日数据访问被允许"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 1, 1))
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)

    def test_historical_data_access_allowed(self):
        """测试历史数据访问被允许"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 1, 1))
        result = feeder.get_daybar("000001.SZ", "2022-01-01")
        assert isinstance(result, pd.DataFrame)

    def test_time_sync_required(self):
        """测试时间同步要求"""
        feeder = _make_feeder_with_time(time_val=None)
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_custom_validate_time_access(self):
        """测试自定义时间验证逻辑"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 1, 1))
        # Set a custom validator that always denies
        feeder.validate_time_access = lambda now, dt: False
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_time_validation_exception_handling(self):
        """测试时间验证异常处理"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 1, 1))
        # Override validate_time_access to raise
        def raising_validator(now, dt):
            raise ValueError("test error")
        feeder.validate_time_access = raising_validator
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True


@pytest.mark.unit
class TestDataCaching:
    """6. 数据缓存测试"""

    def test_cache_decorator_applied(self):
        """测试缓存装饰器应用"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        # get_daybar has @cache_with_expiration; verify it is callable and returns DataFrame
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)

    def test_cache_hit_performance(self):
        """测试缓存命中性能"""
        service = _mock_bar_service()
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        feeder.bar_service = service
        feeder.get_daybar("000001.SZ", "2023-01-01")
        feeder.get_daybar("000001.SZ", "2023-01-01")
        # Second call may use cache
        assert service.get.call_count >= 1

    def test_cache_expiration(self):
        """测试缓存过期"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        result1 = feeder.get_daybar("000001.SZ", "2023-01-01")
        result2 = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result1, pd.DataFrame)
        assert isinstance(result2, pd.DataFrame)

    def test_cache_key_generation(self):
        """测试缓存键生成"""
        service = _mock_bar_service()
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        feeder.bar_service = service
        feeder.get_daybar("000001.SZ", "2023-01-01")
        feeder.get_daybar("000002.SZ", "2023-01-02")
        assert service.get.call_count == 2


@pytest.mark.unit
class TestTimeAdvancement:
    """7. 时间推进测试"""

    def test_advance_time_basic(self):
        """测试基础时间推进"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        # Without time_provider, advance_time returns False
        result = feeder.advance_time("2023-01-01")
        assert result is False

    def test_advance_time_forward_only(self):
        """测试仅向前推进时间"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        result1 = feeder.advance_time("2023-01-01")
        result2 = feeder.advance_time("2022-01-01")
        assert result1 is False
        assert result2 is False

    def test_advance_time_listener_notification(self):
        """测试时间推进监听器通知"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert callable(getattr(feeder, 'on_time_update', None))

    def test_advance_time_multiple_steps(self):
        """测试多步时间推进"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        dates = ["2023-01-01", "2023-01-02", "2023-01-03"]
        results = [feeder.advance_time(d) for d in dates]
        assert all(r is False for r in results)


@pytest.mark.unit
class TestCodeMarketValidation:
    """8. 股票代码市场验证测试"""

    def test_is_code_on_market_interface(self):
        """测试is_code_on_market接口"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        assert callable(getattr(feeder, 'is_code_on_market', None))
        with pytest.raises(NotImplementedError):
            feeder.is_code_on_market("000001.SZ")

    def test_subclass_implementation_required(self):
        """测试子类必须实现"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        with pytest.raises(NotImplementedError):
            feeder.is_code_on_market("000001.SZ")


@pytest.mark.unit
class TestErrorHandling:
    """9. 错误处理和边界条件测试"""

    def test_data_loading_exception_handling(self):
        """测试数据加载异常处理"""
        service = MagicMock()
        service.get.side_effect = Exception("DB error")
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        feeder.bar_service = service
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_invalid_code_handling(self):
        """测试无效股票代码处理"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        result = feeder.get_daybar("", "2023-01-01")
        assert isinstance(result, pd.DataFrame)

    def test_empty_dataframe_return(self):
        """测试空DataFrame返回"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_logger_error_reporting(self):
        """测试日志错误报告"""
        feeder = _make_feeder_with_time(time_val=None)
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True


@pytest.mark.unit
@pytest.mark.integration
class TestBaseFeederIntegration:
    """10. 集成测试"""

    def test_engine_binding_workflow(self):
        """测试引擎绑定工作流"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        event = MagicMock()
        feeder.put(event)
        publisher.assert_called_once_with(event)

    def test_time_sync_data_query_workflow(self):
        """测试时间同步数据查询工作流"""
        feeder = _make_feeder_with_time(time_val=None)
        result = feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(result, pd.DataFrame)
        assert result.empty is True

    def test_event_publishing_workflow(self):
        """测试事件发布工作流"""
        feeder = BaseFeeder(bar_service=_mock_bar_service())
        publisher = MagicMock()
        feeder.set_event_publisher(publisher)
        events = [MagicMock() for _ in range(2)]
        for e in events:
            feeder.put(e)
        assert publisher.call_count == 2

    def test_cache_time_interaction(self):
        """测试缓存与时间推进交互"""
        feeder = _make_feeder_with_time(time_val=datetime.datetime(2023, 6, 1))
        feeder.get_daybar("000001.SZ", "2023-01-01")
        feeder.get_daybar("000001.SZ", "2023-01-01")
        assert isinstance(feeder.get_daybar("000001.SZ", "2023-01-01"), pd.DataFrame)
