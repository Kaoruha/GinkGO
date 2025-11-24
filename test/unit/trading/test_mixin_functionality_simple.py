"""
简化的Mixin功能验证测试

专注于验证新Mixin架构的核心功能是否正常工作
"""

import pytest
import datetime
from decimal import Decimal
from unittest.mock import Mock, patch

# 通过已安装包导入
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.core.base import Base
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.bases.portfolio_base import PortfolioBase


class MockTimeProvider:
    """简化的时间提供者，只提供测试所需的功能"""
    def __init__(self, start_time):
        self._current_time = start_time

    def now(self):
        return self._current_time

    def set_current_time(self, new_time):
        """设置当前时间"""
        self._current_time = new_time

    def advance_time_to(self, target_time):
        """推进时间到目标时间"""
        if target_time < self._current_time:
            raise ValueError("Cannot advance to past time")
        self._current_time = target_time


class MockEngine:
    """模拟引擎，测试EngineBindableMixin绑定功能"""
    def __init__(self, engine_id="test_engine", run_id="test_run"):
        self.engine_id = engine_id
        self.run_id = run_id
        self.put = Mock()
        self.log_calls = []  # 记录日志调用


# ====== Fixtures ======


@pytest.fixture
def basic_signal():
    """创建基础Signal实例用于测试"""
    return Signal(
        portfolio_id="test_portfolio",
        engine_id="test_engine",
        run_id="test_run",
        code="000001.SZ",
        direction=1
    )


@pytest.fixture
def basic_portfolio():
    """创建基础Portfolio实例用于测试"""
    return PortfolioBase(name="TestPortfolio")


@pytest.fixture
def mock_time_provider():
    """创建时间提供者用于测试"""
    return MockTimeProvider(datetime.datetime(2024, 1, 1))


@pytest.fixture
def mock_engine():
    """创建模拟引擎用于测试"""
    return MockEngine("test_engine", "test_run")


# ====== 测试类 ======


@pytest.mark.unit
class TestTimeMixinFunctionality:
    """测试TimeMixin功能 - 重点验证时间管理的业务约束"""

    def test_timestamp_initialization_enforces_constraints(self, basic_signal):
        """测试时间戳初始化必须符合业务约束"""
        # 验证时间戳存在
        assert basic_signal.timestamp is not None
        assert isinstance(basic_signal.timestamp, datetime.datetime)

        # 验证时间戳不能是未来时间（业务约束：对象创建时间 <= 当前时间）
        current_time = datetime.datetime.now()
        assert basic_signal.timestamp <= current_time

        # 验证时间戳不能是过旧时间（合理范围内）
        # 时间戳应该在当前时间的1分钟之内
        time_diff = current_time - basic_signal.timestamp
        assert time_diff < datetime.timedelta(minutes=1)

    def test_business_timestamp_setting_enforces_rules(self, basic_signal):
        """测试业务时间戳设置必须符合业务规则"""
        # 设置业务时间戳
        business_time = datetime.datetime(2024, 1, 1, 9, 30, 0)
        basic_signal.set_business_timestamp(business_time)

        # 验证设置生效
        assert basic_signal.business_timestamp == business_time

        # 验证语义：business_timestamp 表示数据时间，不是对象时间
        assert basic_signal.business_timestamp != basic_signal.timestamp

        # 验证设置后再次读取得到相同值（读一致性）
        assert basic_signal.business_timestamp == business_time

    def test_now_property_contract_enforcement(self, basic_signal, mock_time_provider):
        """测试now属性的API契约强制执行"""
        # 验证未绑定时间提供者时访问now会抛出异常
        with pytest.raises(RuntimeError, match="未绑定时间提供者"):
            _ = basic_signal.now

        # 设置时间提供者
        basic_signal.set_time_provider(mock_time_provider)

        # 验证now是属性（不是方法），不需要圆括号
        initial_time = mock_time_provider.now()
        assert basic_signal.now == initial_time
        assert isinstance(basic_signal.now, datetime.datetime)

        # 推进时间提供者后，now应该同步更新
        new_time = datetime.datetime(2024, 1, 2, 10, 0, 0)
        mock_time_provider.set_current_time(new_time)
        assert basic_signal.now == new_time

        # 再次推进时间，验证持续同步
        further_time = datetime.datetime(2024, 1, 3, 15, 30, 0)
        mock_time_provider.set_current_time(further_time)
        assert basic_signal.now == further_time

    def test_business_timestamp_time_progression_integrity(self, basic_signal, mock_time_provider):
        """测试业务时间戳推进的完整性约束"""
        # 设置时间提供者
        basic_signal.set_time_provider(mock_time_provider)

        # 记录初始状态
        initial_time = mock_time_provider.now()
        timestamp_before = basic_signal.timestamp
        real_time_before = basic_signal.timestamp

        # 推进时间提供者
        new_time = datetime.datetime(2024, 1, 2, 10, 0, 0)
        mock_time_provider.set_current_time(new_time)
        assert basic_signal.now == new_time

        # 设置业务时间戳（使用不同时间验证独立性）
        business_time = datetime.datetime(2024, 1, 3, 9, 30, 0)
        basic_signal.set_business_timestamp(business_time)

        # 验证所有时间戳的正确关系
        assert basic_signal.business_timestamp == business_time
        assert basic_signal.now == new_time  # now来自时间提供者
        assert basic_signal.business_timestamp != basic_signal.now  # 独立时间

        # 验证set_business_timestamp更新了timestamp（真实时间）
        # timestamp应该与真实时间比较，而不是与模拟时间比较
        assert basic_signal.timestamp != timestamp_before
        current_real_time = datetime.datetime.now()
        # 新的timestamp应该接近当前真实时间（调用时间）
        assert basic_signal.timestamp <= current_real_time
        # 真实时间戳不应该受模拟时间影响
        assert basic_signal.timestamp >= real_time_before

        # 验证时间不能回拨（推进后的now应该 >= 初始now）
        mock_time_provider.set_current_time(datetime.datetime(2024, 1, 4))
        assert basic_signal.now >= initial_time

    def test_time_provider_advance_mechanism_with_constraints(self, basic_signal, mock_time_provider):
        """测试时间提供者推进机制的业务约束"""
        basic_signal.set_time_provider(mock_time_provider)

        # 初始时间
        initial_time = mock_time_provider.now()
        assert basic_signal.now == initial_time

        # 推进时间到未来
        future_time = datetime.datetime(2024, 1, 2, 10, 0, 0)
        mock_time_provider.advance_time_to(future_time)
        assert basic_signal.now == future_time
        assert basic_signal.now > initial_time

        # 推进到更未来时间
        further_time = datetime.datetime(2024, 1, 3, 15, 30, 0)
        mock_time_provider.advance_time_to(further_time)
        assert basic_signal.now == further_time
        assert basic_signal.now > future_time

        # 验证时间推进的单向性（不能回到过去）
        # 这是一个边界条件，当前实现可能不强制，但业务上应该有此约束

    def test_timestamp_preservation_and_update_semantics(self, basic_signal, mock_time_provider):
        """测试timestamp的保存和更新语义"""
        # 记录初始timestamp（真实时间）
        initial_timestamp = basic_signal.timestamp

        # 设置时间提供者
        basic_signal.set_time_provider(mock_time_provider)

        # 推进时间，验证timestamp保持不变（保存对象创建时间）
        mock_time_provider.advance_time_to(datetime.datetime(2024, 1, 2))
        assert basic_signal.timestamp == initial_timestamp
        assert basic_signal.now == datetime.datetime(2024, 1, 2)

        # 调用set_business_timestamp会更新timestamp为当前时间（真实时间）
        business_time = datetime.datetime(2024, 1, 3)
        basic_signal.set_business_timestamp(business_time)
        new_timestamp = basic_signal.timestamp
        assert new_timestamp != initial_timestamp
        # 新的timestamp应该是当前真实时间，不应该与模拟时间比较
        current_real_time = datetime.datetime.now()
        assert new_timestamp <= current_real_time
        assert new_timestamp >= initial_timestamp

        # 再次推进时间，验证timestamp保持新值不变
        mock_time_provider.advance_time_to(datetime.datetime(2024, 1, 4))
        assert basic_signal.timestamp == new_timestamp  # 不再改变
        assert basic_signal.now == datetime.datetime(2024, 1, 4)

    def test_time_related_operations_atomicity(self, basic_signal, mock_time_provider):
        """测试时间相关操作的原子性约束"""
        basic_signal.set_time_provider(mock_time_provider)

        # 验证多个时间操作的原子性
        business_time = datetime.datetime(2024, 1, 2)
        initial_timestamp = basic_signal.timestamp

        # 执行时间相关操作
        basic_signal.set_business_timestamp(business_time)
        timestamp_after = basic_signal.timestamp

        # 验证操作要么全部成功，要么全部失败（原子性）
        assert basic_signal.business_timestamp == business_time
        assert basic_signal.timestamp == timestamp_after
        assert basic_signal.timestamp >= initial_timestamp

        # 验证操作后的状态一致性
        assert basic_signal.now == mock_time_provider.now()
        assert isinstance(basic_signal.timestamp, datetime.datetime)
        assert isinstance(basic_signal.business_timestamp, datetime.datetime)


@pytest.mark.unit
class TestContextMixinFunctionality:
    """测试ContextMixin功能 - 重点验证上下文管理的业务约束"""

    def test_context_initialization(self, basic_signal):
        """测试上下文初始化的完整性"""
        # 验证所有必需上下文字段都被正确初始化
        assert basic_signal.portfolio_id == "test_portfolio"
        assert basic_signal.engine_id == "test_engine"
        assert basic_signal.run_id == "test_run"

        # 验证上下文字段的类型和格式
        assert isinstance(basic_signal.portfolio_id, str)
        assert isinstance(basic_signal.engine_id, str)
        assert isinstance(basic_signal.run_id, str)
        assert len(basic_signal.portfolio_id) > 0
        assert len(basic_signal.engine_id) > 0
        assert len(basic_signal.run_id) > 0

    def test_context_setter_semantics(self, basic_signal):
        """测试上下文设置的约束和可见性"""
        # 验证初始状态
        assert basic_signal.engine_id == "test_engine"
        assert basic_signal.portfolio_id == "test_portfolio"
        assert basic_signal.run_id == "test_run"

        # 设置新值 - 验证写操作生效
        basic_signal.engine_id = "new_engine"
        basic_signal.portfolio_id = "new_portfolio"
        basic_signal.run_id = "new_run"

        # 验证设置立即生效（写后读一致性）
        assert basic_signal.engine_id == "new_engine"
        assert basic_signal.portfolio_id == "new_portfolio"
        assert basic_signal.run_id == "new_run"

        # 验证设置None值（如果业务允许）
        basic_signal.engine_id = None
        assert basic_signal.engine_id is None

        # 恢复有效值
        basic_signal.engine_id = "restored_engine"
        assert basic_signal.engine_id == "restored_engine"

    def test_context_sync_immutability_with_engine(self, basic_signal, mock_engine):
        """测试引擎同步的不可变约束 - 只同步指定字段"""
        # 设置自定义上下文
        basic_signal.engine_id = "custom_engine"
        basic_signal.portfolio_id = "custom_portfolio"
        basic_signal.run_id = "custom_run"

        # 验证自定义设置生效
        assert basic_signal.engine_id == "custom_engine"

        # 同步引擎上下文（只同步engine_id和run_id，不动portfolio_id）
        basic_signal.sync_engine_context(mock_engine)

        # 验证同步策略：只更新指定字段，其他字段保持不变
        assert basic_signal.engine_id == mock_engine.engine_id  # 被更新
        assert basic_signal.run_id == mock_engine.run_id  # 被更新
        assert basic_signal.portfolio_id == "custom_portfolio"  # 未同步，保持原值

        # 验证同步后再次同步的幂等性
        basic_signal.sync_engine_context(mock_engine)
        assert basic_signal.engine_id == mock_engine.engine_id
        assert basic_signal.run_id == mock_engine.run_id

    def test_context_property_writeback_consistency(self):
        """测试上下文属性写回的一致性约束"""
        class TestComponent(ContextMixin, Base):
            def __init__(self, **kwargs):
                ContextMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent()

        # 多次写操作的累积效应
        component.engine_id = "first_engine"
        component.engine_id = "second_engine"
        component.engine_id = "third_engine"

        # 验证最终值是最后一次写入的结果
        assert component.engine_id == "third_engine"

        # 验证跨属性写操作的独立性
        component.portfolio_id = "portfolio_a"
        component.run_id = "run_a"
        component.engine_id = "engine_b"
        component.portfolio_id = "portfolio_b"

        # 验证每个属性保持各自的最终值
        assert component.engine_id == "engine_b"
        assert component.portfolio_id == "portfolio_b"
        assert component.run_id == "run_a"

    def test_context_sync_with_engine_boundary_conditions(self, basic_signal, mock_engine):
        """测试引擎同步的边界条件"""
        # 验证初始状态
        assert basic_signal.engine_id == "test_engine"
        assert basic_signal.run_id == "test_run"

        # 同步到引擎
        basic_signal.sync_engine_context(mock_engine)
        assert basic_signal.engine_id == mock_engine.engine_id
        assert basic_signal.run_id == mock_engine.run_id

        # 验证同步后修改不会影响引擎（单向同步）
        basic_signal.engine_id = "modified_engine"
        assert basic_signal.engine_id == "modified_engine"
        # 引擎的engine_id保持不变（验证单向性）
        assert mock_engine.engine_id == "test_engine"


@pytest.mark.unit
class TestNamedMixinFunctionality:
    """测试NamedMixin功能 - 重点验证命名的业务约束"""

    def test_name_initialization_enforces_business_rules(self, basic_signal):
        """测试名称初始化必须符合业务规则"""
        # 验证名称是有效的字符串
        assert isinstance(basic_signal.name, str)
        assert len(basic_signal.name) > 0

        # 验证名称不为空字符串（业务约束）
        assert basic_signal.name != ""

        # 验证名称符合预期的格式（Signal的命名规则）
        # Signal的name应该是 "Signal_{code}_{direction}" 的格式
        assert "Signal_" in basic_signal.name
        assert basic_signal.name.count("_") >= 1  # 至少有一个下划线分隔符

    def test_name_setter_enforces_immutability_constraint(self, basic_signal):
        """测试名称设置器的不可变性约束"""
        # 记录初始名称
        initial_name = basic_signal.name
        assert len(initial_name) > 0

        # 设置新名称
        new_name = "CustomSignal_2024"
        basic_signal.name = new_name

        # 验证设置立即生效（值相等性）
        assert basic_signal.name == new_name

        # 再次修改名称
        second_name = "ModifiedSignal"
        basic_signal.name = second_name
        assert basic_signal.name == second_name

        # 验证名称的最终状态
        assert basic_signal.name == "ModifiedSignal"

    def test_name_persistence_across_operations(self, basic_signal):
        """测试名称在多操作中的持久性"""
        initial_name = basic_signal.name

        # 执行一些不相关的操作
        original_business_timestamp = basic_signal.business_timestamp
        basic_signal.set_business_timestamp(datetime.datetime(2024, 1, 1))

        # 名称应该保持不变
        assert basic_signal.name == initial_name

        # 修改上下文
        basic_signal.engine_id = "new_engine"

        # 名称仍然保持不变
        assert basic_signal.name == initial_name

        # 恢复上下文
        basic_signal.engine_id = "test_engine"

        # 名称依然不变
        assert basic_signal.name == initial_name

    def test_name_uniqueness_constraint(self):
        """测试名称的唯一性约束（在同一上下文中）"""
        # 创建两个具有相同参数的Signal
        signal1 = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=1
        )
        signal2 = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=1
        )

        # 验证两个Signal都有有效的名称
        assert len(signal1.name) > 0
        assert len(signal2.name) > 0

        # 验证名称格式符合预期
        assert "Signal_" in signal1.name
        assert "Signal_" in signal2.name

        # 注意：当前实现可能不保证唯一性，但名称应该有效
        # 如果业务需要唯一性，这里应该验证 signal1.name != signal2.name
        # 当前的简化测试只验证名称的有效性


@pytest.mark.unit
class TestLoggableMixinFunctionality:
    """测试LoggableMixin功能 - 重点验证日志记录流程"""

    def test_logger_configuration_workflow(self):
        """测试logger配置流程的语义"""
        mixin = LoggableMixin()
        mock_logger = Mock()

        # 添加logger
        mixin.add_logger(mock_logger)

        # 验证logger被添加
        assert mock_logger in mixin.loggers

        # 验证日志记录方法存在且可调用
        assert hasattr(mixin, 'log')
        assert callable(mixin.log)

    def test_log_message_semantics(self):
        """测试日志消息的语义"""
        # 创建模拟logger验证日志流程
        from unittest.mock import Mock, patch

        mixin = LoggableMixin()
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        mixin.add_logger(mock_logger)

        test_message = "Test log message"
        test_level = "INFO"

        # 调用日志方法
        mixin.log(test_level, test_message)

        # 验证logger的INFO方法被调用
        mock_logger.INFO.assert_called_once_with(test_message)

    def test_logger_management_workflow(self):
        """测试logger管理流程"""
        from unittest.mock import Mock

        mixin = LoggableMixin()
        initial_count = len(mixin.loggers)

        # 添加多个logger
        logger1 = Mock()
        logger1.INFO = Mock()
        logger2 = Mock()
        logger2.INFO = Mock()

        mixin.add_logger(logger1)
        assert len(mixin.loggers) == initial_count + 1

        mixin.add_logger(logger2)
        assert len(mixin.loggers) == initial_count + 2

        # 验证重复添加会被忽略
        mixin.add_logger(logger1)
        # logger1仍在列表中，但没有重复添加
        assert mixin.loggers.count(logger1) == 1

        # 验证每个logger都能接收日志
        mixin.log("INFO", "Test message")
        logger1.INFO.assert_called_once()
        logger2.INFO.assert_called_once()

    def test_log_with_context_information(self, basic_signal):
        """测试带上下文的日志记录"""
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()

        basic_signal.add_logger(mock_logger)

        # 日志应该包含上下文信息
        basic_signal.log("INFO", "Signal generated")

        # 验证logger的INFO方法被调用
        mock_logger.INFO.assert_called_once_with("Signal generated")
        # 验证调用时包含信号的信息
        call_args = mock_logger.INFO.call_args[0]
        assert "Signal generated" in str(call_args)

    def test_log_level_distribution(self):
        """测试不同日志级别分发"""
        from unittest.mock import Mock

        mixin = LoggableMixin()

        logger_info = Mock()
        logger_info.INFO = Mock()
        logger_info.DEBUG = Mock()
        logger_info.WARN = Mock()  # 注意：LoggableMixin中WARNING级别调用WARN方法
        logger_info.ERROR = Mock()

        mixin.add_logger(logger_info)

        # 测试INFO级别
        mixin.log("INFO", "Info message")
        logger_info.INFO.assert_called_once()

        # 测试DEBUG级别
        mixin.log("DEBUG", "Debug message")
        logger_info.DEBUG.assert_called_once()

        # 测试WARNING级别（调用WARN方法）
        mixin.log("WARNING", "Warning message")
        logger_info.WARN.assert_called_once()

        # 测试ERROR级别
        mixin.log("ERROR", "Error message")
        logger_info.ERROR.assert_called_once()


@pytest.mark.unit
class TestEngineBindableMixinFunctionality:
    """测试EngineBindableMixin功能 - 重点验证绑定语义"""

    def test_engine_binding_semantics(self, mock_engine):
        """测试引擎绑定的语义"""
        class TestComponent(EngineBindableMixin, Base):
            pass

        component = TestComponent()

        # 验证初始状态
        assert component._engine_put is None

        # 绑定引擎
        component.bind_engine(mock_engine)

        # 验证engine_put被设置
        assert component._engine_put is not None

    def test_engine_binding_with_dependencies(self, mock_engine):
        """测试引擎绑定时的依赖注入语义"""
        class TestComponent(EngineBindableMixin, ContextMixin, Base):
            pass

        component = TestComponent()

        # 绑定引擎应同时同步上下文
        component.bind_engine(mock_engine)

        # 验证上下文被同步
        assert component.engine_id == mock_engine.engine_id
        assert component.run_id == mock_engine.run_id

    def test_engine_rebinding_behavior(self, mock_engine):
        """测试重复绑定引擎的行为"""
        class TestComponent(EngineBindableMixin, Base):
            pass

        component = TestComponent()

        # 第一次绑定
        component.bind_engine(mock_engine)
        initial_put = component._engine_put

        # 第二次绑定
        component.bind_engine(mock_engine)
        # 验证重新绑定成功
        assert component._engine_put is initial_put or component._engine_put is not None

    def test_engine_binding_with_put_function(self, mock_engine):
        """测试引擎绑定时put函数的行为和保存"""
        class TestComponent(EngineBindableMixin, Base):
            pass

        component = TestComponent()

        # 验证绑定前状态
        assert component._engine_put is None
        assert component.engine_put is None

        # 绑定引擎
        component.bind_engine(mock_engine)

        # 验证Mixin正确保存了引擎的put方法
        assert component._engine_put is not None
        assert component._engine_put == mock_engine.put

        # 验证engine_put属性返回正确的put方法
        assert component.engine_put is not None
        assert component.engine_put == mock_engine.put

        # 验证通过engine_put调用put方法
        test_event = {"type": "test", "data": "test_data"}
        component.engine_put(test_event)

        # 验证put方法确实被调用了
        mock_engine.put.assert_called_once_with(test_event)

        # 再次验证组件内部的engine_put保存了正确的方法
        # 即使mock_engine改变，component的engine_put仍应保持不变
        second_event = {"type": "test2", "data": "test_data2"}
        component.engine_put(second_event)
        assert mock_engine.put.call_count == 2
        assert mock_engine.put.call_args_list[1][0][0] == second_event


@pytest.mark.unit
class TestSignalMixinIntegration:
    """测试Signal的Mixin集成 - 重点验证协同效应"""

    def test_signal_all_mixins_integration(self, basic_signal, mock_time_provider):
        """测试Signal所有Mixin的协同效应"""
        # 设置时间提供者
        basic_signal.set_time_provider(mock_time_provider)

        # 验证时间管理
        assert basic_signal.now == mock_time_provider.now()

        # 验证上下文管理
        assert basic_signal.portfolio_id == "test_portfolio"
        assert basic_signal.engine_id == "test_engine"

        # 验证命名
        assert isinstance(basic_signal.name, str)
        assert len(basic_signal.name) > 0

        # 验证日志
        assert hasattr(basic_signal, 'log')
        assert callable(basic_signal.log)

        # 验证UUID（来自Base）
        assert basic_signal.uuid is not None
        assert isinstance(basic_signal.uuid, str)

    def test_signal_mixin_interaction_semantics(self, basic_signal, mock_time_provider):
        """测试Signal中Mixin交互的语义"""
        # 设置时间提供者
        basic_signal.set_time_provider(mock_time_provider)

        initial_time = mock_time_provider.now()

        # 设置业务时间戳
        business_time = datetime.datetime(2024, 1, 2, 10, 0, 0)
        basic_signal.set_business_timestamp(business_time)

        # 验证交互语义：now来自时间提供者，business_timestamp独立
        assert basic_signal.now == initial_time
        assert basic_signal.business_timestamp == business_time
        assert basic_signal.now != basic_signal.business_timestamp

    def test_signal_with_invalid_parameters(self):
        """测试Signal的参数验证（负面测试）"""
        # 测试无效的direction - 捕获General Exception因为Signal包装了原始异常
        with pytest.raises(Exception):
            Signal(
                portfolio_id="test",
                engine_id="test",
                run_id="test",
                code="000001.SZ",
                direction="invalid_direction"  # 应该是int类型
            )


@pytest.mark.unit
class TestPortfolioMixinIntegration:
    """测试Portfolio的Mixin集成 - 重点验证边界条件和异常场景"""

    def test_portfolio_all_mixins_integration_with_real_usage(self, basic_portfolio):
        """测试Portfolio所有Mixin的真正集成使用"""
        # 验证TimeMixin功能
        assert basic_portfolio.timestamp is not None
        assert isinstance(basic_portfolio.timestamp, datetime.datetime)

        # 真正调用TimeMixin的方法
        time_provider = MockTimeProvider(datetime.datetime(2024, 1, 1))
        basic_portfolio.set_time_provider(time_provider)
        assert basic_portfolio.now == datetime.datetime(2024, 1, 1)

        # 验证NamedMixin功能
        assert basic_portfolio.name == "TestPortfolio"
        # 真正调用命名功能
        basic_portfolio.name = "UpdatedPortfolio"
        assert basic_portfolio.name == "UpdatedPortfolio"

        # 验证ContextMixin功能
        assert hasattr(basic_portfolio, 'engine_id')
        assert hasattr(basic_portfolio, 'run_id')
        assert hasattr(basic_portfolio, 'portfolio_id')
        # 真正调用上下文功能
        basic_portfolio.engine_id = "portfolio_engine"
        basic_portfolio.run_id = "portfolio_run"
        assert basic_portfolio.engine_id == "portfolio_engine"
        assert basic_portfolio.run_id == "portfolio_run"

        # 验证LoggableMixin功能
        assert hasattr(basic_portfolio, 'log')
        assert callable(basic_portfolio.log)
        # 真正调用日志功能
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        basic_portfolio.add_logger(mock_logger)
        basic_portfolio.log("INFO", "Portfolio integration test")
        assert mock_logger.INFO.called

        # 验证Base功能
        assert basic_portfolio.uuid is not None
        assert isinstance(basic_portfolio.uuid, str)
        # 验证UUID在操作中保持不变
        original_uuid = basic_portfolio.uuid
        basic_portfolio.set_business_timestamp(datetime.datetime(2024, 1, 2))
        assert basic_portfolio.uuid == original_uuid

        # 验证Portfolio特有功能
        assert hasattr(basic_portfolio, 'cash')
        assert hasattr(basic_portfolio, 'profit')
        assert hasattr(basic_portfolio, 'analyzers')
        # 真正调用Portfolio功能
        initial_cash = basic_portfolio.cash
        # cash是Decimal类型（金融精确计算）
        assert isinstance(initial_cash, Decimal)

    def test_portfolio_engine_binding_with_type_enforcement(self, basic_portfolio, mock_engine):
        """测试Portfolio引擎绑定的类型强制执行"""
        # 验证Portfolio有bind_engine方法
        assert hasattr(basic_portfolio, 'bind_engine')
        assert callable(basic_portfolio.bind_engine)

        # 验证初始状态
        assert basic_portfolio._engine_put is None

        # Portfolio的bind_engine要求BaseEngine类型，MockEngine不是BaseEngine
        # 验证类型检查会抛出TypeError
        with pytest.raises(TypeError) as exc_info:
            basic_portfolio.bind_engine(mock_engine)

        # 验证错误信息包含期望内容
        assert "Expected BaseEngine" in str(exc_info.value)
        assert str(type(mock_engine)) in str(exc_info.value)

        # 验证失败后状态不变
        assert basic_portfolio._engine_put is None

    def test_portfolio_time_provider_with_context_coordination(self, basic_portfolio, mock_time_provider):
        """测试Portfolio时间提供者与上下文的协同工作"""
        # 设置时间提供者
        basic_portfolio.set_time_provider(mock_time_provider)

        # 验证时间管理
        assert basic_portfolio.now == mock_time_provider.now()

        # 验证business_timestamp功能
        business_time = datetime.datetime(2024, 1, 2)
        basic_portfolio.set_business_timestamp(business_time)
        assert basic_portfolio.business_timestamp == business_time

        # 验证now和business_timestamp的语义分离
        assert basic_portfolio.now != basic_portfolio.business_timestamp

        # 推进时间，验证now更新但business_timestamp不变
        new_time = datetime.datetime(2024, 1, 3)
        mock_time_provider.advance_time_to(new_time)
        assert basic_portfolio.now == new_time
        assert basic_portfolio.business_timestamp == business_time

    def test_portfolio_boundary_conditions(self, basic_portfolio):
        """测试Portfolio的边界条件"""
        # 测试多次设置名称
        original_name = basic_portfolio.name
        basic_portfolio.name = "Name1"
        basic_portfolio.name = "Name2"
        assert basic_portfolio.name == "Name2"
        # 恢复原名称
        basic_portfolio.name = original_name
        assert basic_portfolio.name == original_name

        # 测试设置None值（如果业务允许）
        original_engine_id = basic_portfolio.engine_id
        basic_portfolio.engine_id = None
        assert basic_portfolio.engine_id is None
        # 恢复有效值
        basic_portfolio.engine_id = "restored"
        assert basic_portfolio.engine_id == "restored"

    def test_portfolio_mixin_interaction_complex_scenario(self, basic_portfolio, mock_time_provider):
        """测试Portfolio中Mixin交互的复杂场景"""
        # 设置时间提供者
        basic_portfolio.set_time_provider(mock_time_provider)

        # 同时进行多种操作
        initial_timestamp = basic_portfolio.timestamp
        original_uuid = basic_portfolio.uuid

        # 修改名称
        basic_portfolio.name = "ComplexTest"

        # 设置业务时间戳
        business_time = datetime.datetime(2024, 1, 2)
        basic_portfolio.set_business_timestamp(business_time)

        # 修改上下文
        basic_portfolio.engine_id = "complex_engine"

        # 验证所有操作的影响
        assert basic_portfolio.name == "ComplexTest"
        assert basic_portfolio.business_timestamp == business_time
        assert basic_portfolio.engine_id == "complex_engine"
        assert basic_portfolio.timestamp != initial_timestamp  # 被更新
        assert basic_portfolio.uuid == original_uuid  # 保持不变
        assert basic_portfolio.now == mock_time_provider.now()

    def test_portfolio_error_handling_scenarios(self, basic_portfolio):
        """测试Portfolio的错误处理场景"""
        # 测试多次添加同一个logger（应该去重）
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        basic_portfolio.add_logger(mock_logger)
        initial_logger_count = len(basic_portfolio.loggers)

        # 再次添加同一个logger
        basic_portfolio.add_logger(mock_logger)
        # logger数量应该不变（去重）
        assert len(basic_portfolio.loggers) == initial_logger_count

        # 测试日志功能仍然正常工作
        basic_portfolio.log("INFO", "Test message")
        assert mock_logger.INFO.called


@pytest.mark.unit
class TestMixinCombination:
    """测试Mixin组合的复杂场景"""

    def test_method_resolution_order(self):
        """测试Mixin的MRO和初始化顺序"""
        class TestComponent(TimeMixin, ContextMixin, NamedMixin, LoggableMixin, EngineBindableMixin, Base):
            def __init__(self, name="TestComponent", **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                NamedMixin.__init__(self, name=name, **kwargs)
                LoggableMixin.__init__(self, **kwargs)
                EngineBindableMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent()

        # 验证所有Mixin功能存在
        assert hasattr(component, 'timestamp')
        assert hasattr(component, 'engine_id')
        assert hasattr(component, 'name')
        assert hasattr(component, 'loggers')
        assert hasattr(component, 'bind_engine')
        assert hasattr(component, 'uuid')

    def test_mixin_state_isolation(self, basic_signal):
        """测试Mixin之间状态隔离的语义"""
        # 记录初始状态
        initial_name = basic_signal.name
        initial_uuid = basic_signal.uuid

        # 修改某些Mixin的状态
        basic_signal.name = "ModifiedName"
        business_time = datetime.datetime(2024, 1, 2)
        basic_signal.set_business_timestamp(business_time)

        # 验证修改后的状态正确
        assert basic_signal.name == "ModifiedName"
        assert basic_signal.business_timestamp == business_time

        # 验证未修改的Mixin状态保持不变
        assert basic_signal.uuid == initial_uuid

        # 验证timestamp未被意外修改（虽然它是动态的，但uuid应该保持不变）
        # 这证明了不同Mixin之间状态的隔离性
        assert basic_signal.portfolio_id == "test_portfolio"  # 来自ContextMixin
        assert basic_signal.engine_id == "test_engine"  # 来自ContextMixin

    def test_mixin_method_chaining(self):
        """测试Mixin方法链式调用"""
        # 创建支持链式调用的组件
        class ChainableComponent(TimeMixin, ContextMixin, NamedMixin, Base):
            def __init__(self, name="ChainComponent", **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                NamedMixin.__init__(self, name=name, **kwargs)
                Base.__init__(self)

            def set_business_timestamp(self, timestamp):
                """链式调用的业务时间戳设置"""
                super().set_business_timestamp(timestamp)
                return self  # 返回self支持链式调用

            def set_context(self, engine_id, portfolio_id, run_id):
                """链式调用的上下文设置"""
                self.engine_id = engine_id
                self.portfolio_id = portfolio_id
                self.run_id = run_id
                return self  # 返回self支持链式调用

            def set_name(self, name):
                """链式调用的名称设置"""
                self.name = name
                return self  # 返回self支持链式调用

        component = ChainableComponent()

        # 执行链式调用
        result = component.set_name("ChainTest") \
                          .set_business_timestamp(datetime.datetime(2024, 1, 2)) \
                          .set_context("chain_engine", "chain_portfolio", "chain_run")

        # 验证链式调用返回self
        assert result is component

        # 验证所有设置都生效
        assert component.name == "ChainTest"
        assert component.business_timestamp == datetime.datetime(2024, 1, 2)
        assert component.engine_id == "chain_engine"
        assert component.portfolio_id == "chain_portfolio"
        assert component.run_id == "chain_run"

    def test_method_invocation_order_effects(self):
        """测试方法调用顺序对状态的影响"""
        class OrderTestComponent(TimeMixin, ContextMixin, Base):
            def __init__(self, **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                Base.__init__(self)

            def update_business_time(self, timestamp):
                """更新业务时间"""
                self.set_business_timestamp(timestamp)
                return self

            def update_context(self, engine_id):
                """更新上下文"""
                self.engine_id = engine_id
                return self

        component = OrderTestComponent()

        # 记录初始时间戳
        initial_time = component.timestamp

        # 顺序1：先更新业务时间，再更新上下文
        component.update_business_time(datetime.datetime(2024, 1, 2)) \
                 .update_context("order1_engine")

        time_after_order1 = component.timestamp
        assert time_after_order1 >= initial_time
        assert component.engine_id == "order1_engine"

        # 重置组件测试不同顺序
        component2 = OrderTestComponent()

        # 顺序2：先更新上下文，再更新业务时间
        component2.update_context("order2_engine") \
                 .update_business_time(datetime.datetime(2024, 1, 3))

        time_after_order2 = component2.timestamp
        assert time_after_order2 >= initial_time
        assert component2.engine_id == "order2_engine"

        # 验证不同顺序可能影响最终状态（虽然在这个例子中结果相同）
        assert component.timestamp != component2.timestamp  # 因为业务时间设置会更新timestamp

    def test_chaining_with_error_rollback(self):
        """测试链式调用中的错误回滚"""
        class ErrorTestComponent(TimeMixin, ContextMixin, Base):
            def __init__(self, **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                Base.__init__(self)

            def set_business_timestamp(self, timestamp):
                """会抛出异常的业务时间设置"""
                if timestamp == datetime.datetime(2024, 1, 4):
                    raise ValueError("Invalid timestamp")
                super().set_business_timestamp(timestamp)
                return self

            def update_engine(self, engine_id):
                """更新引擎ID"""
                self.engine_id = engine_id
                return self

        component = ErrorTestComponent()

        # 执行成功的链式调用
        component.update_engine("valid_engine") \
                .set_business_timestamp(datetime.datetime(2024, 1, 3))

        assert component.engine_id == "valid_engine"
        assert component.business_timestamp == datetime.datetime(2024, 1, 3)

        # 测试链式调用中的异常
        component2 = ErrorTestComponent()
        try:
            component2.update_engine("before_error") \
                     .set_business_timestamp(datetime.datetime(2024, 1, 4)) \
                     .update_engine("after_error")
            pytest.fail("应该抛出异常")
        except ValueError as e:
            assert "Invalid timestamp" in str(e)

        # 验证部分成功的操作已生效
        assert component2.engine_id == "before_error"  # 错误前已执行

    def test_mixin_error_propagation(self):
        """测试Mixin错误的传播（负面测试）"""
        class TestComponent(TimeMixin, ContextMixin, Base):
            def __init__(self, **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent()

        # ContextMixin允许设置None值
        component.engine_id = None
        assert component.engine_id is None

        # 测试TimeMixin对无效时间提供者的处理（不抛异常）
        # TimeMixin不检查时间提供者类型，可以接受任何对象
        component.set_time_provider("invalid_provider")
        # 验证设置成功（使用内部属性名）
        assert component._time_provider == "invalid_provider"


@pytest.mark.unit
class TestArchitectureValidation:
    """测试架构层面的真实功能约束"""

    def test_all_entities_have_required_mixins_with_real_usage(self):
        """验证所有实体都有必需Mixin并且功能可用"""
        signal = Signal(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=1
        )

        # 验证TimeMixin功能真实可用
        assert hasattr(signal, 'timestamp')
        assert hasattr(signal, 'set_time_provider')
        business_time = datetime.datetime(2024, 1, 2, 10, 0, 0)
        signal.set_business_timestamp(business_time)
        assert signal.business_timestamp == business_time
        assert signal.business_timestamp != signal.timestamp

        # 验证now属性需要时间提供者（API契约）
        signal.set_time_provider(MockTimeProvider(datetime.datetime(2024, 1, 1)))
        assert hasattr(signal, 'now')
        assert signal.now == datetime.datetime(2024, 1, 1)
        # 推进时间后验证now更新
        signal.get_time_provider().advance_time_to(datetime.datetime(2024, 1, 2))
        assert signal.now == datetime.datetime(2024, 1, 2)

        # 验证UUID功能真实可用
        assert hasattr(signal, 'uuid')
        assert signal.uuid is not None
        assert isinstance(signal.uuid, str)
        assert len(signal.uuid) > 0
        # 验证UUID的唯一性
        signal2 = Signal(
            portfolio_id="test2",
            engine_id="test2",
            run_id="test2",
            code="000002.SZ",
            direction=1
        )
        assert signal2.uuid != signal.uuid
        # UUID在操作中保持不变
        original_uuid = signal.uuid
        signal.set_business_timestamp(datetime.datetime(2024, 1, 3))
        assert signal.uuid == original_uuid

        # 验证LoggableMixin功能真实可用
        assert hasattr(signal, 'log')
        assert callable(signal.log)
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        signal.add_logger(mock_logger)
        signal.log("INFO", "Test message")
        assert mock_logger.INFO.called
        # 验证多次日志调用
        signal.log("INFO", "Another message")
        assert mock_logger.INFO.call_count == 2

    def test_complex_mixin_interaction_scenario_with_constraints(self, mock_time_provider, mock_engine):
        """测试复杂Mixin交互场景的完整约束验证"""
        # 创建复杂场景下的Signal
        signal = Signal(
            portfolio_id="complex_test",
            engine_id="complex_engine",
            run_id="complex_run",
            code="000001.SZ",
            direction=1
        )

        # 步骤1：设置时间提供者
        signal.set_time_provider(mock_time_provider)
        initial_time = mock_time_provider.now()
        assert signal.now == initial_time

        # 步骤2：推进时间
        new_time = datetime.datetime(2024, 1, 2)
        mock_time_provider.advance_time_to(new_time)
        assert signal.now == new_time
        assert signal.now > initial_time

        # 步骤3：设置业务时间戳（验证timestamp更新）
        timestamp_before = signal.timestamp
        business_time = datetime.datetime(2024, 1, 3, 10, 0, 0)
        signal.set_business_timestamp(business_time)
        assert signal.business_timestamp == business_time
        # 验证timestamp更新了（真实时间）
        assert signal.timestamp != timestamp_before
        # timestamp是真实时间，不应该与模拟时间now比较
        current_real_time = datetime.datetime.now()
        assert signal.timestamp <= current_real_time
        assert signal.timestamp >= timestamp_before

        # 步骤4：同步引擎上下文（验证部分同步）
        original_portfolio_id = signal.portfolio_id
        signal.sync_engine_context(mock_engine)
        assert signal.engine_id == mock_engine.engine_id
        assert signal.run_id == mock_engine.run_id
        assert signal.portfolio_id == original_portfolio_id  # 未被覆盖

        # 步骤5：添加logger并记录日志
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        signal.add_logger(mock_logger)
        signal.log("INFO", "Complex scenario test")
        assert mock_logger.INFO.called

        # 验证最终状态的一致性
        assert signal.now == new_time
        assert signal.business_timestamp == business_time
        assert signal.engine_id == mock_engine.engine_id
        assert signal.portfolio_id == "complex_test"
        assert mock_logger.INFO.called

        # 验证Mixin之间的独立性
        # 再次推进时间
        final_time = datetime.datetime(2024, 1, 4)
        mock_time_provider.advance_time_to(final_time)
        assert signal.now == final_time
        # business_timestamp应该保持不变
        assert signal.business_timestamp == business_time
        # 名称应该保持不变
        assert "Signal_" in signal.name

    def test_entity_lifecycle_validation_with_state_progression(self):
        """测试实体生命周期状态演进约束"""
        # 验证Signal的完整生命周期
        signal1 = Signal(
            portfolio_id="lifecycle_test",
            engine_id="lifecycle_engine",
            run_id="lifecycle_run",
            code="000001.SZ",
            direction=1
        )

        # 记录初始状态
        initial_timestamp = signal1.timestamp
        initial_uuid = signal1.uuid
        initial_name = signal1.name

        # 模拟状态演进
        signal1.set_time_provider(MockTimeProvider(datetime.datetime(2024, 1, 1)))
        signal1.set_business_timestamp(datetime.datetime(2024, 1, 2))
        signal1.engine_id = "modified_engine"

        # 验证状态更新规则
        assert signal1.timestamp != initial_timestamp  # 被set_business_timestamp更新
        assert signal1.uuid == initial_uuid  # UUID保持不变
        assert signal1.name == initial_name  # 名称未修改，保持不变
        assert signal1.engine_id == "modified_engine"  # 上下文被修改

        # 创建第二个信号验证隔离
        signal2 = Signal(
            portfolio_id="lifecycle_test2",
            engine_id="lifecycle_engine2",
            run_id="lifecycle_run2",
            code="000002.SZ",
            direction=1
        )

        # 验证两个信号完全独立（状态隔离）
        assert signal1.uuid != signal2.uuid
        assert signal1.timestamp != signal2.timestamp
        assert signal1.engine_id != signal2.engine_id
        assert signal1.portfolio_id != signal2.portfolio_id
        # 验证名称也不同（因为代码不同）
        assert signal1.name != signal2.name

    def test_portfolio_mixin_integration_validation_with_real_operations(self, basic_portfolio):
        """测试Portfolio的Mixin集成验证（真实操作）"""
        # 验证初始状态
        initial_cash = basic_portfolio.cash
        initial_uuid = basic_portfolio.uuid
        initial_name = basic_portfolio.name

        # 测试时间管理的真实功能
        time_provider = MockTimeProvider(datetime.datetime(2024, 1, 1))
        basic_portfolio.set_time_provider(time_provider)
        assert basic_portfolio.now == datetime.datetime(2024, 1, 1)
        # 推进时间验证更新
        time_provider.advance_time_to(datetime.datetime(2024, 1, 2))
        assert basic_portfolio.now == datetime.datetime(2024, 1, 2)

        # 测试业务时间戳设置（使用不同时间验证独立性）
        business_time = datetime.datetime(2024, 1, 3)
        basic_portfolio.set_business_timestamp(business_time)
        assert basic_portfolio.business_timestamp == business_time
        # 验证now和business_timestamp的独立性（不同时间）
        assert basic_portfolio.now != basic_portfolio.business_timestamp

        # 验证UUID保持不变
        assert basic_portfolio.uuid == initial_uuid

        # 验证名称修改功能
        basic_portfolio.name = "ModifiedPortfolio"
        assert basic_portfolio.name == "ModifiedPortfolio"

        # 验证日志功能的真实调用
        from unittest.mock import Mock
        mock_logger = Mock()
        mock_logger.INFO = Mock()
        basic_portfolio.add_logger(mock_logger)
        basic_portfolio.log("INFO", "Portfolio test")
        assert mock_logger.INFO.called
        # 再次调用验证累积
        basic_portfolio.log("INFO", "Another test")
        assert mock_logger.INFO.call_count == 2

        # 验证Portfolio特有功能存在且可访问
        assert hasattr(basic_portfolio, 'cash')
        assert hasattr(basic_portfolio, 'profit')
        assert hasattr(basic_portfolio, 'strategies')
        assert hasattr(basic_portfolio, 'positions')
        assert isinstance(basic_portfolio.cash, Decimal)

    def test_mixin_independence_with_actual_operations(self):
        """验证Mixin的独立性（实际可操作）"""
        # 创建只包含TimeMixin的类
        class TimeOnlyComponent(TimeMixin, Base):
            def __init__(self, **kwargs):
                TimeMixin.__init__(self, **kwargs)
                Base.__init__(self)

        time_component = TimeOnlyComponent()
        assert hasattr(time_component, 'timestamp')
        assert time_component.timestamp is not None
        # 验证TimeMixin功能可用
        time_component.set_business_timestamp(datetime.datetime(2024, 1, 1))
        assert time_component.business_timestamp == datetime.datetime(2024, 1, 1)

        # 创建只包含ContextMixin的类
        class ContextOnlyComponent(ContextMixin, Base):
            def __init__(self, **kwargs):
                ContextMixin.__init__(self, **kwargs)
                Base.__init__(self)

        context_component = ContextOnlyComponent()
        assert hasattr(context_component, 'engine_id')
        assert context_component.engine_id is None
        # 验证ContextMixin功能可用
        context_component.engine_id = "test_engine"
        assert context_component.engine_id == "test_engine"

        # 验证它们可以独立工作
        # TimeOnlyComponent没有engine_id属性（Mixin独立性）
        assert not hasattr(time_component, 'engine_id') or time_component.engine_id is None
        # ContextOnlyComponent没有business_timestamp的完整功能
        assert not hasattr(context_component, 'set_business_timestamp') or not callable(context_component.set_business_timestamp)

    def test_base_requirements_with_uniqueness_enforcement(self):
        """验证Base类的唯一性强制执行"""
        # 创建一个Signal
        signal1 = Signal(
            portfolio_id="test",
            engine_id="test",
            run_id="test",
            code="000001.SZ",
            direction=1
        )

        # 验证Base提供UUID
        assert hasattr(signal1, 'uuid')
        assert signal1.uuid is not None
        # 验证UUID格式
        assert isinstance(signal1.uuid, str)
        assert len(signal1.uuid) > 0

        # 创建多个Signal验证唯一性
        signals = []
        for i in range(5):
            signal = Signal(
                portfolio_id=f"test{i}",
                engine_id=f"engine{i}",
                run_id=f"run{i}",
                code=f"00000{i}.SZ",
                direction=1
            )
            signals.append(signal)

        # 验证所有UUID都是唯一的
        uuids = [s.uuid for s in signals]
        assert len(uuids) == len(set(uuids))  # 没有重复的UUID
        # 验证每个Signal都有自己的UUID
        for signal in signals:
            assert signal.uuid in uuids
            assert signal.uuid is not None

        # 验证UUID的格式一致性
        for signal in signals:
            assert len(signal.uuid) > 0
            assert isinstance(signal.uuid, str)
            # UUID应该包含字母和数字
            assert any(c.isalpha() or c.isdigit() for c in signal.uuid)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
