"""
TimeRelated时间验证功能测试

测试TimeRelated类的时间边界验证、缓存优化和装饰器功能。
使用真实的LogicalTimeProvider和TimeBoundaryValidator进行集成测试。
"""

import pytest
from collections import OrderedDict
from datetime import datetime, date
from ginkgo.trading.entities.time_related import TimeRelated
from ginkgo.trading.time.providers import LogicalTimeProvider, TimeBoundaryValidator


# ==================== 测试Fixtures ====================

@pytest.fixture
def clean_cache():
    """清空跨实例共享缓存"""
    from ginkgo.trading.time.providers import TimeBoundaryValidator
    TimeBoundaryValidator.clear_cache()
    yield
    TimeBoundaryValidator.clear_cache()


# ==================== 测试类1: ITimeAwareComponent接口 ====================

@pytest.mark.tdd
class TestTimeRelatedITimeAwareComponent:
    """测试ITimeAwareComponent接口实现"""

    def test_set_run_id(self, clean_cache):
        """测试设置run_id并更新validator（协作式多重继承）"""
        from ginkgo.trading.core.backtest_base import BacktestBase

        # 创建继承两者的组件
        class Component(BacktestBase, TimeRelated):
            def __init__(self):
                BacktestBase.__init__(self, name="test_comp")
                TimeRelated.__init__(self)

        component = Component()
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)

        run_id = "test_run_123"
        component.set_run_id(run_id)

        # 验证：BacktestBase的_run_id已设置
        assert component.run_id == run_id

        # 验证：TimeRelated的validator run_id已更新
        assert component._time_validator._run_id == run_id

        # 验证：缓存空间已初始化
        stats = TimeBoundaryValidator.get_cache_stats(run_id)
        assert stats['size'] == 0  # 初始为空

    def test_set_time_provider(self):
        """测试设置时间提供者并自动创建验证器"""
        component = TimeRelated()
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1, 9, 30))

        component.set_time_provider(provider)

        assert component._time_validator is not None
        assert isinstance(component._time_validator, TimeBoundaryValidator)
        assert component._time_validator._time_provider is provider

    def test_on_time_update(self):
        """测试时间更新回调调用advance_time"""
        component = TimeRelated()
        new_time = datetime(2023, 6, 1, 9, 30)

        # 初始时now为None
        assert component.now is None

        component.on_time_update(new_time)

        assert component.now == new_time

    def test_get_current_time(self):
        """测试获取当前时间"""
        component = TimeRelated()

        # 场景A：未设置时间，返回None
        assert component.get_current_time() is None

        # 场景B：设置时间后，返回设置的时间
        test_time = datetime(2023, 6, 1, 9, 30)
        component.advance_time(test_time)
        assert component.get_current_time() == test_time

    def test_multiple_components_share_cache(self, clean_cache):
        """测试同一run_id的多个组件共享缓存"""
        from ginkgo.trading.core.backtest_base import BacktestBase

        # 创建两个继承BacktestBase的组件（有run_id）
        class Component1(BacktestBase, TimeRelated):
            def __init__(self):
                BacktestBase.__init__(self, name="comp1", run_id="shared_run")
                TimeRelated.__init__(self)

        class Component2(BacktestBase, TimeRelated):
            def __init__(self):
                BacktestBase.__init__(self, name="comp2", run_id="shared_run")
                TimeRelated.__init__(self)

        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))

        component1 = Component1()
        component1.set_time_provider(provider)
        component1.advance_time(datetime(2023, 6, 1))

        component2 = Component2()
        component2.set_time_provider(provider)
        component2.advance_time(datetime(2023, 6, 1))

        # 初始状态：缓存为空
        stats = TimeBoundaryValidator.get_cache_stats("shared_run")
        assert stats['size'] == 0

        # component1验证后：缓存有1条
        component1.validate_data_time(datetime(2023, 5, 31), "test")
        stats = TimeBoundaryValidator.get_cache_stats("shared_run")
        assert stats['size'] == 1

        # component2验证同一时间：缓存仍是1条（命中）
        component2.validate_data_time(datetime(2023, 5, 31), "test")
        stats = TimeBoundaryValidator.get_cache_stats("shared_run")
        assert stats['size'] == 1


# ==================== 测试类2: 时间验证功能 ====================

@pytest.mark.tdd
class TestTimeRelatedValidation:
    """测试validate_data_time方法的核心验证逻辑"""

    def test_validate_data_time_success(self, clean_cache):
        """测试合法时间验证返回True"""
        component = TimeRelated()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1, 9, 30))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1, 9, 30))

        # 验证过去时间（合法）
        result = component.validate_data_time(datetime(2023, 5, 31), "test_context")

        assert result is True

    def test_validate_data_time_future_fails(self, clean_cache):
        """测试未来时间验证返回False"""
        component = TimeRelated()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1, 9, 30))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1, 9, 30))

        # 验证未来时间（非法）
        result = component.validate_data_time(datetime(2023, 7, 1), "test_context")

        assert result is False

    def test_validate_data_time_without_provider(self, clean_cache):
        """测试未设置provider时返回False"""
        component = TimeRelated()
        component.set_run_id("test_run")
        # 故意不设置provider

        result = component.validate_data_time(datetime(2023, 5, 31), "test_context")

        assert result is False

    def test_validate_data_time_without_run_id(self, clean_cache):
        """测试未设置run_id时验证仍然工作（但不启用缓存）"""
        component = TimeRelated()
        # 故意不设置run_id
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 合法时间仍然返回True（验证逻辑不依赖run_id）
        result = component.validate_data_time(datetime(2023, 5, 31), "test_context")
        assert result is True

        # 验证：没有run_id意味着不使用缓存（validator._run_id为None）
        assert component._time_validator._run_id is None

    def test_validate_data_time_with_date_type(self, clean_cache):
        """测试支持date类型参数"""
        component = TimeRelated()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 使用date类型（非datetime）
        result = component.validate_data_time(date(2023, 5, 31), "test_context")

        assert result is True

    def test_validate_data_time_with_datetime_type(self, clean_cache):
        """测试支持datetime类型参数"""
        component = TimeRelated()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1, 9, 30))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1, 9, 30))

        # 使用datetime类型
        result = component.validate_data_time(
            datetime(2023, 5, 31, 15, 0), "test_context"
        )

        assert result is True


# ==================== 测试类3: 装饰器功能 ====================

@pytest.mark.tdd
class TestTimeRelatedDecorator:
    """测试@TimeRelated.validate_time()装饰器功能"""

    def test_decorator_valid_time_executes_method(self, clean_cache):
        """测试装饰器：合法时间时方法被执行"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time()
            def fetch_data(self, end_date):
                self.executed = True
                return "data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，传入合法的过去时间
        result = component.fetch_data(datetime(2023, 5, 31))

        assert component.executed is True
        assert result == "data"

    def test_decorator_invalid_time_skips_method(self, clean_cache):
        """测试装饰器：非法时间时方法被跳过"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time()
            def fetch_data(self, end_date):
                self.executed = True
                return "data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，传入非法的未来时间
        result = component.fetch_data(datetime(2023, 7, 1))

        assert component.executed is False
        assert result is None

    def test_decorator_specified_params(self, clean_cache):
        """测试装饰器：指定参数名称进行验证"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time(time_params=["end_date"])
            def query_data(self, code, start_date, end_date):
                self.executed = True
                return f"data_{code}"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，只验证end_date参数
        result = component.query_data(
            "000001.SZ", "2023-05-01", datetime(2023, 5, 31)
        )

        assert component.executed is True
        assert result == "data_000001.SZ"

    def test_decorator_multiple_time_params_all_valid(self, clean_cache):
        """测试装饰器：多个时间参数都合法时方法执行"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time()
            def query_range(self, start_date, end_date):
                self.executed = True
                return "range_data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，传入两个都合法的过去时间
        result = component.query_range(
            datetime(2023, 5, 1), datetime(2023, 5, 31)
        )

        assert component.executed is True
        assert result == "range_data"

    def test_decorator_specified_param_invalid(self, clean_cache):
        """测试装饰器：指定参数不合法时方法被跳过"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time(time_params=["end_date"])
            def query_data(self, code, start_date, end_date):
                self.executed = True
                return f"data_{code}"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，指定的end_date参数为未来时间（不合法）
        result = component.query_data(
            "000001.SZ", "2023-05-01", datetime(2023, 7, 1)
        )

        assert component.executed is False
        assert result is None

    def test_decorator_specified_multiple_one_invalid(self, clean_cache):
        """测试装饰器：指定多个参数，其中一个不合法时方法被跳过"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time(time_params=["start_date", "end_date"])
            def query_range(self, start_date, end_date):
                self.executed = True
                return "range_data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # start_date合法，end_date不合法
        result = component.query_range(
            datetime(2023, 5, 1), datetime(2023, 7, 1)
        )

        assert component.executed is False
        assert result is None

    def test_decorator_unspecified_param_ignored(self, clean_cache):
        """测试装饰器：未指定的参数即使不合法也被忽略"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time(time_params=["end_date"])
            def query_range(self, start_date, end_date):
                self.executed = True
                return "range_data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # start_date未来时间（未指定，被忽略），end_date合法
        result = component.query_range(
            datetime(2023, 7, 1), datetime(2023, 5, 31)
        )

        assert component.executed is True
        assert result == "range_data"

    def test_decorator_non_datetime_params_ignored(self, clean_cache):
        """测试装饰器：自动检测模式下非datetime/date类型参数被忽略"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            @TimeRelated.validate_time()
            def query_data(self, code, count, end_date):
                self.executed = True
                return f"data_{code}_{count}"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 传入str、int、datetime类型，只验证datetime
        result = component.query_data(
            "000001.SZ", 100, datetime(2023, 5, 31)
        )

        assert component.executed is True
        assert result == "data_000001.SZ_100"


# ==================== 测试类4: 上下文管理器功能 ====================

@pytest.mark.tdd
class TestTimeRelatedContextManager:
    """测试with self.time_validation()上下文管理器功能"""

    def test_context_manager_valid_time_yields_true(self, clean_cache):
        """测试上下文管理器：合法时间时yield True"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            def fetch_data(self, end_date):
                with self.time_validation(end_date, "fetch") as valid:
                    if not valid:
                        return None
                    self.executed = True
                    return "data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，传入合法的过去时间
        result = component.fetch_data(datetime(2023, 5, 31))

        assert component.executed is True
        assert result == "data"

    def test_context_manager_invalid_time_yields_false(self, clean_cache):
        """测试上下文管理器：非法时间时yield False，代码块被跳过"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            def fetch_data(self, end_date):
                with self.time_validation(end_date, "fetch") as valid:
                    if not valid:
                        return None
                    self.executed = True
                    return "data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 调用方法，传入非法的未来时间
        result = component.fetch_data(datetime(2023, 7, 1))

        assert component.executed is False
        assert result is None

    def test_context_manager_without_provider(self, clean_cache):
        """测试上下文管理器：缺少provider时yield False"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            def fetch_data(self, end_date):
                with self.time_validation(end_date, "fetch") as valid:
                    if not valid:
                        return None
                    self.executed = True
                    return "data"

        component = TestComponent()
        component.set_run_id("test_run")
        # 故意不设置provider

        result = component.fetch_data(datetime(2023, 5, 31))

        assert component.executed is False
        assert result is None

    def test_context_manager_without_run_id(self, clean_cache):
        """测试上下文管理器：没有run_id时验证仍然工作（但不启用缓存）"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            def fetch_data(self, end_date):
                with self.time_validation(end_date, "fetch") as valid:
                    if not valid:
                        return None
                    self.executed = True
                    return "data"

        component = TestComponent()
        # 故意不设置run_id
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 合法时间仍然返回有效结果（验证逻辑不依赖run_id）
        result = component.fetch_data(datetime(2023, 5, 31))

        assert component.executed is True
        assert result == "data"

        # 验证：没有run_id意味着不使用缓存
        assert component._time_validator._run_id is None

    def test_context_manager_with_conditional_logic(self, clean_cache):
        """测试上下文管理器：实际使用场景中的复杂条件控制流程"""

        class TestComponent(TimeRelated):
            def __init__(self):
                super().__init__()
                self.executed = False

            def query_range(self, start_date, end_date):
                # 第一个验证：start_date
                with self.time_validation(start_date, "query_start") as valid:
                    if not valid:
                        return None

                # 第二个验证：end_date
                with self.time_validation(end_date, "query_end") as valid:
                    if not valid:
                        return None

                # 都合法才执行业务逻辑
                self.executed = True
                return "range_data"

        component = TestComponent()
        component.set_run_id("test_run")
        provider = LogicalTimeProvider(initial_time=datetime(2023, 6, 1))
        component.set_time_provider(provider)
        component.advance_time(datetime(2023, 6, 1))

        # 场景1：两个日期都合法
        component.executed = False
        result1 = component.query_range(datetime(2023, 5, 1), datetime(2023, 5, 31))
        assert component.executed is True
        assert result1 == "range_data"

        # 场景2：start_date不合法（未来时间）
        component.executed = False
        result2 = component.query_range(datetime(2023, 7, 1), datetime(2023, 5, 31))
        assert component.executed is False
        assert result2 is None

        # 场景3：start_date合法，end_date不合法
        component.executed = False
        result3 = component.query_range(datetime(2023, 5, 1), datetime(2023, 7, 31))
        assert component.executed is False
        assert result3 is None
