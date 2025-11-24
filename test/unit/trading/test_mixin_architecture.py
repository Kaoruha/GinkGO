"""
Mixin架构功能组合测试

本测试验证新的三层架构中各个Base类的Mixin组合是否按预期工作。
测试覆盖：
1. TimeMixin功能
2. ContextMixin功能
3. EngineBindableMixin功能
4. NamedMixin功能
5. LoggableMixin功能
6. Base类的Mixin组合
7. 业务实现的继承功能
"""

import pytest
import datetime
import uuid
from unittest.mock import Mock

# 设置路径
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'src'))

# 导入被测试的组件
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.mixins.context_mixin import ContextMixin
from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.trading.core.base import Base

# 导入Base类
from ginkgo.trading.bases.portfolio_base import PortfolioBase
from ginkgo.trading.bases.signal_base import SignalBase
from ginkgo.trading.bases.order_base import OrderBase
from ginkgo.trading.bases.position_base import PositionBase
from ginkgo.trading.bases.event_base import EventBase

# 导入业务实现
from ginkgo.trading.entities.signal import Signal
from ginkgo.trading.entities.order import Order
from ginkgo.trading.entities.position import Position
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick


class MockTimeProvider:
    """模拟时间提供者"""
    def __init__(self, start_time):
        self._current_time = start_time

    def now(self):
        return self._current_time

    def advance_time(self, new_time):
        self._current_time = new_time

    def can_access_time(self, request_time):
        """检查是否可以访问指定时间"""
        return self._current_time >= request_time


class MockEngine:
    """模拟引擎"""
    def __init__(self, engine_id="test_engine", run_id="test_run"):
        self.engine_id = engine_id
        self.run_id = run_id
        self.put = Mock()  # 添加put方法


@pytest.mark.tdd
class TestTimeMixinFunctionality:
    """测试TimeMixin功能"""

    def test_timestamp_initialization(self):
        """测试时间戳初始化"""
        mixin = TimeMixin()

        # 检查现实时间戳初始化
        assert mixin.timestamp is not None
        assert isinstance(mixin.timestamp, datetime.datetime)

        # 检查业务时间戳默认为None
        assert mixin.business_timestamp is None

        # 检查其他时间属性
        assert mixin.init_time is not None
        assert mixin.last_update is not None

    def test_business_timestamp_setting(self):
        """测试业务时间戳设置"""
        mixin = TimeMixin()
        business_time = datetime.datetime(2024, 1, 1, 10, 0, 0)

        # 测试set_business_timestamp方法
        mixin.set_business_timestamp(business_time)
        assert mixin.business_timestamp == business_time

        # 验证现实时间戳已更新
        assert mixin.timestamp > business_time

    def test_time_provider_binding(self):
        """测试时间提供者绑定"""
        mixin = TimeMixin()
        time_provider = MockTimeProvider(datetime.datetime(2024, 1, 1))

        # 绑定时间提供者
        mixin.set_time_provider(time_provider)

        # 验证now属性返回时间提供者的时间
        assert mixin.now == datetime.datetime(2024, 1, 1)

        # 测试时间推进
        time_provider.advance_time(datetime.datetime(2024, 1, 2))
        assert mixin.now == datetime.datetime(2024, 1, 2)

    def test_time_provider_validation(self):
        """测试时间提供者验证"""
        mixin = TimeMixin()

        # 未绑定时间提供者时调用now应该抛出错误
        with pytest.raises(RuntimeError, match="未绑定时间提供者"):
            _ = mixin.now


@pytest.mark.tdd
class TestContextMixinFunctionality:
    """测试ContextMixin功能"""

    def test_context_properties_initialization(self):
        """测试上下文属性初始化"""
        mixin = ContextMixin()

        # 检查默认值
        assert mixin.engine_id is None
        assert mixin.run_id is None
        assert mixin.portfolio_id is None

    def test_context_properties_setting(self):
        """测试上下文属性设置"""
        mixin = ContextMixin()

        # 设置上下文信息
        mixin.engine_id = "test_engine_001"
        mixin.run_id = "test_run_001"
        mixin.portfolio_id = "test_portfolio_001"

        # 验证设置成功
        assert mixin.engine_id == "test_engine_001"
        assert mixin.run_id == "test_run_001"
        assert mixin.portfolio_id == "test_portfolio_001"

    def test_engine_context_synchronization(self):
        """测试引擎上下文同步"""
        mixin = ContextMixin()
        engine = MockEngine("sync_engine", "sync_run")

        # 同步引擎上下文
        mixin.sync_engine_context(engine)

        # 验证同步结果
        assert mixin.engine_id == "sync_engine"
        assert mixin.run_id == "sync_run"


@pytest.mark.tdd
class TestNamedMixinFunctionality:
    """测试NamedMixin功能"""

    def test_name_initialization(self):
        """测试名称初始化"""
        # 测试默认名称
        mixin1 = NamedMixin()
        assert mixin1.name == ""

        # 测试自定义名称
        mixin2 = NamedMixin(name="TestComponent")
        assert mixin2.name == "TestComponent"

    def test_name_setting(self):
        """测试名称设置"""
        mixin = NamedMixin()

        # 设置名称
        mixin.name = "NewName"
        assert mixin.name == "NewName"


@pytest.mark.tdd
class TestLoggableMixinFunctionality:
    """测试LoggableMixin功能"""

    def test_logger_initialization(self):
        """测试日志器初始化"""
        # 测试默认初始化
        mixin = LoggableMixin()
        assert hasattr(mixin, 'loggers')
        assert isinstance(mixin.loggers, list)

    def test_logger_customization(self):
        """测试日志器定制"""
        custom_logger = Mock()
        mixin = LoggableMixin(loggers=[custom_logger])

        assert custom_logger in mixin.loggers


@pytest.mark.tdd
class TestEngineBindableMixinFunctionality:
    """测试EngineBindableMixin功能"""

    def test_bind_engine_success(self):
        """测试成功绑定引擎"""
        from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin

        # 创建一个同时有EngineBindableMixin和ContextMixin的对象
        class TestComponent(EngineBindableMixin, ContextMixin, NamedMixin, Base):
            def __init__(self, **kwargs):
                ContextMixin.__init__(self, **kwargs)
                EngineBindableMixin.__init__(self, **kwargs)
                NamedMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent()
        engine = MockEngine("test_engine", "test_run")

        # 绑定引擎
        component.bind_engine(engine)

        # 验证绑定成功
        assert component.engine_put == engine.put

        # 验证上下文同步
        assert component.engine_id == "test_engine"
        assert component.run_id == "test_run"

    def test_bind_engine_with_context_sync(self):
        """测试引擎绑定时的上下文同步"""
        from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin
        from ginkgo.trading.mixins.context_mixin import ContextMixin
        from ginkgo.trading.mixins.named_mixin import NamedMixin
        from ginkgo.trading.core.base import Base

        class TestComponent(EngineBindableMixin, ContextMixin, NamedMixin, Base):
            def __init__(self, **kwargs):
                ContextMixin.__init__(self, **kwargs)
                EngineBindableMixin.__init__(self, **kwargs)
                NamedMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent(name="TestComponent")
        engine = MockEngine("sync_engine", "sync_run")

        # 绑定引擎前，验证初始状态
        assert component.engine_id is None
        assert component.run_id is None

        # 绑定引擎
        component.bind_engine(engine)

        # 验证同步成功
        assert component.engine_id == "sync_engine"
        assert component.run_id == "sync_run"

    def test_engine_put_property(self):
        """测试engine_put属性访问"""
        from ginkgo.trading.mixins.engine_bindable_mixin import EngineBindableMixin

        mixin = EngineBindableMixin()

        # 未绑定引擎时，engine_put为None
        assert mixin.engine_put is None

        # 绑定引擎后，engine_put应该指向引擎的put方法
        engine = MockEngine("test", "run")
        mixin.bind_engine(engine)
        assert mixin.engine_put is not None
        assert mixin.engine_put == engine.put


@pytest.mark.tdd
class TestBaseClassMixinCombinations:
    """测试Base类的Mixin组合"""

    def test_portfolio_base_mixin_combination(self):
        """测试PortfolioBase的Mixin组合"""
        portfolio = PortfolioBase(name="TestPortfolio")

        # 验证TimeMixin功能
        assert hasattr(portfolio, 'timestamp')
        assert hasattr(portfolio, 'business_timestamp')
        assert hasattr(portfolio, 'set_time_provider')

        # 验证ContextMixin功能
        assert hasattr(portfolio, 'engine_id')
        assert hasattr(portfolio, 'run_id')
        assert hasattr(portfolio, 'portfolio_id')
        assert hasattr(portfolio, 'sync_engine_context')

        # 验证EngineBindableMixin功能
        assert hasattr(portfolio, 'bind_engine')
        assert hasattr(portfolio, 'engine_put')

        # 验证NamedMixin功能
        assert portfolio.name == "TestPortfolio"

        # 验证LoggableMixin功能
        assert hasattr(portfolio, 'loggers')

        # 验证Base功能
        assert hasattr(portfolio, 'uuid')
        assert portfolio.uuid is not None

    def test_signal_base_mixin_combination(self):
        """测试SignalBase的Mixin组合"""
        signal_base = SignalBase()

        # 验证TimeMixin功能
        assert hasattr(signal_base, 'timestamp')
        assert hasattr(signal_base, 'business_timestamp')

        # 验证Base功能
        assert hasattr(signal_base, 'uuid')

    def test_order_base_mixin_combination(self):
        """测试OrderBase的Mixin组合"""
        order_base = OrderBase()

        # 验证TimeMixin功能
        assert hasattr(order_base, 'timestamp')

        # 验证Base功能
        assert hasattr(order_base, 'uuid')
        assert order_base.uuid is not None

    def test_position_base_mixin_combination(self):
        """测试PositionBase的Mixin组合"""
        position_base = PositionBase()

        # 验证TimeMixin功能
        assert hasattr(position_base, 'timestamp')

        # 验证Base功能
        assert hasattr(position_base, 'uuid')
        assert position_base.uuid is not None

    def test_event_base_mixin_combination(self):
        """测试EventBase的Mixin组合"""
        event_base = EventBase()

        # 验证TimeMixin功能
        assert hasattr(event_base, 'timestamp')

        # 验证Base功能
        assert hasattr(event_base, 'uuid')
        assert event_base.uuid is not None


@pytest.mark.tdd
class TestBusinessImplementationInheritance:
    """测试业务实现的继承功能"""

    def test_signal_inheritance(self):
        """测试Signal类继承"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=1  # LONG
        )

        # 验证TimeMixin功能
        assert signal.timestamp is not None
        assert signal.business_timestamp is None

        # 测试业务时间戳设置
        business_time = datetime.datetime(2024, 1, 1)
        signal.set_business_timestamp(business_time)
        assert signal.business_timestamp == business_time

        # 验证ContextMixin功能
        assert signal.portfolio_id == "test_portfolio"
        assert signal.engine_id == "test_engine"
        assert signal.run_id == "test_run"

        # 验证NamedMixin功能
        assert "Signal_000001.SZ" in signal.name

        # 验证Base功能
        assert signal.uuid is not None

        # 验证Signal特有功能
        assert signal.code == "000001.SZ"
        assert signal.direction.value == 1  # LONG

    def test_signal_time_provider_integration(self):
        """测试Signal的TimeProvider集成"""
        signal = Signal(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=1
        )

        # 绑定时间提供者
        time_provider = MockTimeProvider(datetime.datetime(2024, 1, 1))
        signal.set_time_provider(time_provider)

        # 验证时间提供者工作
        assert signal.now == datetime.datetime(2024, 1, 1)

        # 设置当前时间状态（这是关键步骤）
        # 将当前时间设置为2024-01-01，这样2024-01-01的数据是合法的，2024-01-2是非法的
        signal.advance_time(datetime.datetime(2024, 1, 1))

        # 测试时间验证功能
        # 验证当前时间（2024-01-01）的数据访问应该是合法的
        assert signal.validate_data_time(datetime.datetime(2024, 1, 1)) == True
        # 验证未来时间（2024-01-02）的数据访问应该是非法的
        assert signal.validate_data_time(datetime.datetime(2024, 1, 2)) == False

    def test_order_inheritance(self):
        """测试Order类继承"""
        order = Order(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ",
            direction=1,
            order_type=1,
            status=1,
            volume=100,
            limit_price=10.0
        )

        # 验证基本继承功能
        assert hasattr(order, 'timestamp')
        assert hasattr(order, 'engine_id')
        assert hasattr(order, 'uuid')
        assert order.uuid is not None

    def test_position_inheritance(self):
        """测试Position类继承"""
        position = Position(
            portfolio_id="test_portfolio",
            engine_id="test_engine",
            run_id="test_run",
            code="000001.SZ"
        )

        # 验证基本继承功能
        assert hasattr(position, 'timestamp')
        assert hasattr(position, 'engine_id')
        assert hasattr(position, 'uuid')
        assert position.uuid is not None


@pytest.mark.tdd
class TestMixinInteraction:
    """测试Mixin间的交互"""

    def test_time_context_interaction(self):
        """测试TimeMixin和ContextMixin的交互"""
        # 创建一个同时具有TimeMixin和ContextMixin的对象
        class TestComponent(TimeMixin, ContextMixin, NamedMixin, LoggableMixin, Base):
            def __init__(self, **kwargs):
                TimeMixin.__init__(self, **kwargs)
                ContextMixin.__init__(self, **kwargs)
                NamedMixin.__init__(self, **kwargs)
                LoggableMixin.__init__(self, **kwargs)
                Base.__init__(self)

        component = TestComponent(name="TestComponent")

        # 设置上下文信息
        component.engine_id = "test_engine"
        component.run_id = "test_run"

        # 设置时间信息
        business_time = datetime.datetime(2024, 1, 1)
        component.set_business_timestamp(business_time)

        # 绑定时间提供者
        time_provider = MockTimeProvider(datetime.datetime(2024, 1, 1))
        component.set_time_provider(time_provider)

        # 验证所有功能都正常工作
        assert component.engine_id == "test_engine"
        assert component.run_id == "test_run"
        assert component.business_timestamp == business_time
        assert component.now == datetime.datetime(2024, 1, 1)
        assert component.name == "TestComponent"
        assert component.uuid is not None


@pytest.mark.tdd
class TestArchitectureConsistency:
    """测试架构一致性"""

    def test_all_components_have_uuid(self):
        """测试所有组件都有UUID"""
        components = [
            SignalBase(),
            OrderBase(),
            PositionBase(),
            EventBase(),
            PortfolioBase(),
            Signal(portfolio_id="test", engine_id="test", run_id="test", code="000001", direction=1),
            Order(
                portfolio_id="test",
                engine_id="test",
                run_id="test",
                code="000001",
                direction=1,
                order_type=1,
                status=1,
                volume=100,
                limit_price=10.0
            ),
            Position(portfolio_id="test", engine_id="test", run_id="test", code="000001")
        ]

        for component in components:
            assert hasattr(component, 'uuid')
            assert component.uuid is not None
            assert isinstance(component.uuid, str)
            assert len(component.uuid) > 0

    def test_all_components_have_timestamp(self):
        """测试所有组件都有时间戳"""
        components = [
            SignalBase(),
            OrderBase(),
            PositionBase(),
            EventBase(),
            PortfolioBase(),
            Signal(portfolio_id="test", engine_id="test", run_id="test", code="000001", direction=1),
            Order(
                portfolio_id="test",
                engine_id="test",
                run_id="test",
                code="000001",
                direction=1,
                order_type=1,
                status=1,
                volume=100,
                limit_price=10.0
            ),
            Position(portfolio_id="test", engine_id="test", run_id="test", code="000001")
        ]

        for component in components:
            assert hasattr(component, 'timestamp')
            assert component.timestamp is not None
            assert isinstance(component.timestamp, datetime.datetime)

    def test_trading_components_have_context(self):
        """测试交易组件都有上下文信息"""
        # 只测试应该有上下文的组件
        context_components = [
            PortfolioBase(),
            Signal(portfolio_id="test", engine_id="test", run_id="test", code="000001", direction=1)
        ]

        for component in context_components:
            assert hasattr(component, 'engine_id')
            assert hasattr(component, 'run_id')
            # portfolio_id可能为空，但属性应该存在
            assert hasattr(component, 'portfolio_id')


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v"])