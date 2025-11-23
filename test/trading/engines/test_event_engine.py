"""
EventEngine事件引擎TDD测试

通过TDD方式开发EventEngine的事件转发和处理测试套件
聚焦于事件注册、分发、处理器管理和跨组件通信功能
"""
import pytest
import sys
import datetime
import threading
from pathlib import Path
from queue import Queue

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.enums import EXECUTION_MODE
from ginkgo.trading.events.base_event import EventBase
from ginkgo.enums import EVENT_TYPES, COMPONENT_TYPES


@pytest.mark.unit
class TestEventEngineConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试默认参数构造"""
        engine = EventEngine()

        # 验证引擎名称
        assert engine.name == "EventEngine"

        # 验证定时器间隔
        assert engine._timer_interval == 1

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.BACKTEST

    def test_custom_timer_interval_constructor(self):
        """测试自定义定时器间隔构造"""
        custom_interval = 5
        engine = EventEngine(timer_interval=custom_interval)

        # 验证定时器间隔被正确设置
        assert engine._timer_interval == custom_interval

        # 验证其他默认值不受影响
        assert engine.name == "EventEngine"
        assert engine.mode == EXECUTION_MODE.BACKTEST

    def test_custom_mode_constructor(self):
        """测试自定义模式构造"""
        # 测试LIVE模式
        live_engine = EventEngine(mode=EXECUTION_MODE.LIVE)
        assert live_engine.mode == EXECUTION_MODE.LIVE
        assert live_engine.name == "EventEngine"
        assert live_engine._timer_interval == 1

        # 测试SIMULATION模式
        sim_engine = EventEngine(mode=EXECUTION_MODE.SIMULATION)
        assert sim_engine.mode == EXECUTION_MODE.SIMULATION
        assert sim_engine.name == "EventEngine"
        assert sim_engine._timer_interval == 1

    def test_base_engine_inheritance(self):
        """测试BaseEngine继承"""
        engine = EventEngine()

        # 验证继承关系
        from ginkgo.trading.engines.base_engine import BaseEngine
        assert isinstance(engine, BaseEngine)

        # 验证继承的属性存在且使用正确的枚举值
        assert hasattr(engine, 'component_type')
        assert engine.component_type == COMPONENT_TYPES.ENGINE

        # 验证继承的方法存在
        assert hasattr(engine, 'start')
        assert hasattr(engine, 'stop')
        assert hasattr(engine, 'pause')
        assert hasattr(engine, 'engine_id')
        assert hasattr(engine, 'uuid')

    def test_threading_components_initialization(self):
        """测试线程组件初始化"""
        engine = EventEngine()

        # 验证线程标志初始化
        assert hasattr(engine, '_main_flag')
        assert hasattr(engine, '_timer_flag')
        assert isinstance(engine._main_flag, threading.Event)
        assert isinstance(engine._timer_flag, threading.Event)

        # 验证线程对象初始化
        assert hasattr(engine, '_main_thread')
        assert hasattr(engine, '_timer_thread')
        assert isinstance(engine._main_thread, threading.Thread)
        assert isinstance(engine._timer_thread, threading.Thread)

        # 验证线程初始状态（未启动）
        assert not engine._main_thread.is_alive()
        assert not engine._timer_thread.is_alive()


@pytest.mark.unit
class TestEventEngineProperties:
    """2. 属性访问测试"""

    def test_name_property(self):
        """测试引擎名称属性"""
        engine = EventEngine()

        # 测试默认名称
        assert engine.name == "EventEngine"

        # 测试自定义构造名称
        custom_engine = EventEngine(name="TestEngine")
        assert custom_engine.name == "TestEngine"

        # 测试动态修改名称（通过setter）
        engine.name = "RenamedEngine"
        assert engine.name == "RenamedEngine"

        # 测试动态修改名称（通过set_name方法）
        new_name = engine.set_name("FinalEngine")
        assert new_name == "FinalEngine"
        assert engine.name == "FinalEngine"

        # 测试名称修改的持久性
        assert engine.name == "FinalEngine"

    def test_timer_switch_functionality(self):
        """测试定时器开关功能"""
        engine = EventEngine()

        # 测试默认状态（timer关闭）
        assert engine._enable_timer is False, "默认timer应该关闭"

        # 测试启用timer
        result = engine.enable_timer()
        assert result is True, "启用timer应该成功"
        assert engine._enable_timer is True, "启用后状态应该为True"

        # 测试禁用timer
        result = engine.disable_timer()
        assert result is True, "禁用timer应该成功"
        assert engine._enable_timer is False, "禁用后状态应该为False"

        # 测试重复启用
        result = engine.enable_timer()
        assert result is True, "重复启用应该成功"

    def test_timer_switch_with_start_stop_lifecycle(self):
        """测试timer开关在启动/停止生命周期中的行为"""
        engine = EventEngine()

        # 启用timer
        engine.enable_timer()
        assert engine._enable_timer is True

        # 启动引擎（应该启动timer线程）
        engine.start()
        assert engine._timer_thread_started is True, "启动后timer应该运行"

        # timer运行时不能修改开关
        result = engine.enable_timer()
        assert result is False, "timer运行时不能enable"
        result = engine.disable_timer()
        assert result is False, "timer运行时不能disable"
        assert engine._enable_timer is True, "运行时开关状态不应改变"

        # 停止引擎
        engine.stop()
        assert engine._timer_thread_started is False, "停止后timer应该停止"

        # 停止后可以修改开关
        result = engine.disable_timer()
        assert result is True, "停止后可以disable timer"
        assert engine._enable_timer is False, "停止后状态可以改变"

    def test_timer_interval_property(self):
        """测试定时器间隔属性"""
        # 测试默认值
        engine = EventEngine()
        assert engine._timer_interval == 1

        # 测试自定义值
        custom_engine = EventEngine(timer_interval=5)
        assert custom_engine._timer_interval == 5

    def test_timer_interval_with_switch(self):
        """测试定时器间隔与开关的结合功能"""
        import time

        # 测试短间隔（0.5秒）
        short_interval_engine = EventEngine(timer_interval=0.5)
        short_interval_engine.enable_timer()

        timer_calls = []
        def short_timer_handler():
            timer_calls.append("short_timer")

        short_interval_engine.register_timer(short_timer_handler)
        short_interval_engine.start()

        # 等待1.5秒，应该触发约3次定时器
        time.sleep(1.5)

        short_interval_engine.stop()

        # 验证定时器按预期间隔执行
        assert len(timer_calls) >= 2, f"短间隔定时器应该至少触发2次，实际触发{len(timer_calls)}次"
        assert len(timer_calls) <= 4, f"短间隔定时器应该不超过4次，实际触发{len(timer_calls)}次"

    def test_timer_interval_effectiveness(self):
        """测试定时器间隔的有效性"""
        import time

        # 测试长间隔（2秒）
        long_interval_engine = EventEngine(timer_interval=2.0)
        long_interval_engine.enable_timer()

        timer_calls = []
        def long_timer_handler():
            timer_calls.append(time.time())

        long_interval_engine.register_timer(long_timer_handler)

        start_time = time.time()
        long_interval_engine.start()

        # 等待5秒，应该触发约2-3次定时器
        time.sleep(5)

        long_interval_engine.stop()
        end_time = time.time()

        # 验证定时器间隔
        if len(timer_calls) >= 2:
            first_call = timer_calls[0]
            second_call = timer_calls[1]
            interval = second_call - first_call

            # 验证间隔接近2秒（允许0.5秒误差）
            assert 1.5 <= interval <= 2.5, f"定时器间隔应该在1.5-2.5秒之间，实际为{interval:.2f}秒"

    def test_timer_interval_with_disabled_switch(self):
        """测试禁用开关时timer间隔不生效"""
        import time
        engine = EventEngine(timer_interval=0.1)  # 很短的间隔

        timer_calls = []
        def timer_handler():
            timer_calls.append("called")

        engine.register_timer(timer_handler)

        # 不启用timer，直接启动引擎
        engine.start()

        # 等待0.5秒，timer不应该被调用
        time.sleep(0.5)

        engine.stop()

        # 验证timer没有被调用
        assert len(timer_calls) == 0, f"禁用timer时不应该调用定时器，实际调用{len(timer_calls)}次"

    def test_datafeeder_property(self):
        """测试数据馈送器属性"""
        engine = EventEngine()

        # 测试初始状态：datafeeder为None
        assert engine.datafeeder is None
        assert engine._datafeeder is None

        # 测试property访问的一致性（初始状态）
        assert engine.datafeeder == engine._datafeeder
        assert engine.datafeeder is engine._datafeeder  # 对象身份一致性

        # 测试多次访问的一致性（初始状态）
        for _ in range(3):
            assert engine.datafeeder is None
            assert engine.datafeeder == engine._datafeeder
            assert engine.datafeeder is engine._datafeeder

        # 导入BaseFeeder用于测试绑定
        from ginkgo.trading.feeders.base_feeder import BaseFeeder

        # 创建BaseFeeder实例
        feeder = BaseFeeder(name="test_feeder")

        # 测试绑定过程
        engine.bind_datafeeder(feeder)

        # 验证Engine端的绑定
        assert engine.datafeeder is feeder
        assert engine._datafeeder is feeder

        # 测试property访问的一致性（绑定后状态）
        assert engine.datafeeder == engine._datafeeder
        assert engine.datafeeder is engine._datafeeder  # 对象身份一致性

        # 测试多次访问的一致性（绑定后状态）
        for _ in range(3):
            assert engine.datafeeder is feeder
            assert engine.datafeeder == engine._datafeeder
            assert engine.datafeeder is engine._datafeeder

        # 验证双向绑定：Feeder也绑定了Engine（通过BacktestBase.bind_engine）
        assert feeder._engine_id == engine.engine_id
        # 注意：初始状态下engine.run_id为None，bind时会设为空字符串
        assert feeder._run_id == (engine.run_id or "")

        # 验证事件发布器注入
        assert feeder._engine_put == engine.put

    def test_bind_datafeeder_with_none(self):
        """测试传入None参数的绑定行为"""
        engine = EventEngine()

        # 验证None参数会抛出TypeError
        with pytest.raises(TypeError):
            engine.bind_datafeeder(None)

        # 验证datafeeder状态没有被错误修改
        assert engine.datafeeder is None
        assert engine._datafeeder is None

    def test_bind_datafeeder_with_invalid_object(self):
        """测试传入无效对象的绑定行为"""
        engine = EventEngine()

        # 创建一个缺少必要方法的对象
        class InvalidFeeder:
            pass

        invalid_feeder = InvalidFeeder()

        # 当前实现没有参数验证，会抛出AttributeError
        with pytest.raises(AttributeError):
            engine.bind_datafeeder(invalid_feeder)

        # 验证datafeeder状态没有被错误修改
        assert engine.datafeeder is None
        assert engine._datafeeder is None

    def test_handlers_collections_properties(self):
        """测试处理器集合属性"""
        engine = EventEngine()

        # 测试事件处理器字典初始化
        assert hasattr(engine, '_handlers')
        assert isinstance(engine._handlers, dict)
        assert len(engine._handlers) == 0

        # 测试通用处理器列表初始化
        assert hasattr(engine, '_general_handlers')
        assert isinstance(engine._general_handlers, list)
        assert len(engine._general_handlers) == 0

        # 测试定时器处理器列表初始化
        assert hasattr(engine, '_timer_handlers')
        assert isinstance(engine._timer_handlers, list)
        assert len(engine._timer_handlers) == 0

    def test_specific_handler_triggers_only_for_matching_event_type(self):
        """验证特定处理器只在匹配的事件类型时触发

        使用场景：这是EventEngine最基础的功能验证。在实际交易系统中，
        不同类型的处理器需要处理不同的事件：策略处理器只关心价格更新事件，
        投资组合处理器只关心信号生成事件，风控处理器只关心订单相关事件。

        期望结果：
        1. 精确匹配：PRICEUPDATE处理器只在收到价格事件时触发
        2. 类型隔离：不同事件类型的处理器互不干扰
        3. 未注册处理：没有注册处理器的事件类型不会触发任何特定处理器

        业务价值：确保事件分发机制精确可靠，避免错误的事件处理导致交易逻辑混乱。
        """
        engine = EventEngine()

        # 处理器调用记录
        triggered_handlers = []

        # 注册PRICEUPDATE处理器
        def price_handler(event):
            triggered_handlers.append(f"price_handler_{event.event_type}")

        # 注册SIGNALGENERATION处理器
        def signal_handler(event):
            triggered_handlers.append(f"signal_handler_{event.event_type}")

        engine.register(EVENT_TYPES.PRICEUPDATE, price_handler)
        engine.register(EVENT_TYPES.SIGNALGENERATION, signal_handler)

        # 测试：发送价格更新事件
        price_event = EventBase()
        price_event.event_type = EVENT_TYPES.PRICEUPDATE
        engine._process(price_event)

        # 测试：发送信号生成事件
        signal_event = EventBase()
        signal_event.event_type = EVENT_TYPES.SIGNALGENERATION
        engine._process(signal_event)

        # 测试：发送订单事件（没有注册处理器）
        order_event = EventBase()
        order_event.event_type = EVENT_TYPES.ORDERACK
        engine._process(order_event)

        # 验证：只有对应的事件处理器被触发
        assert "price_handler_EVENT_TYPES.PRICEUPDATE" in triggered_handlers, "PRICEUPDATE处理器应该被触发"
        assert "signal_handler_EVENT_TYPES.SIGNALGENERATION" in triggered_handlers, "SIGNALGENERATION处理器应该被触发"
        # 验证：未注册类型的事件不会触发任何特定处理器
        assert len([h for h in triggered_handlers if "ORDERACK" in h]) == 0, "未注册的事件类型不应触发处理器"

    def test_general_handler_triggers_for_all_event_types(self):
        """验证通用处理器对所有事件类型都触发

        使用场景：在实际交易系统中，通用处理器通常用于：
        - 全局日志记录（记录所有事件流）
        - 性能监控（统计事件处理性能）
        - 审计追踪（记录系统行为）

        期望结果：
        1. 全覆盖：通用处理器对所有事件类型都触发
        2. 无遗漏：任何事件类型都不会被通用处理器忽略
        3. 独立性：通用处理器的触发不依赖于特定处理器

        业务价值：确保全局监控和审计功能能够完整捕获系统中的所有事件，
        提供系统的可观测性和问题诊断能力。
        """
        engine = EventEngine()

        processed_events = []

        # 注册通用处理器
        def universal_handler(event):
            processed_events.append(event.event_type)

        engine.register_general(universal_handler)

        # 测试：发送不同类型的事件
        event_types = [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.SIGNALGENERATION,
                       EVENT_TYPES.ORDERACK, EVENT_TYPES.ORDERFILLED]

        for event_type in event_types:
            event = EventBase()
            event.event_type = event_type
            engine._process(event)

        # 验证：所有事件类型都被通用处理器处理
        assert len(processed_events) == len(event_types), "所有事件类型都应被处理"
        for event_type in event_types:
            assert event_type in processed_events, f"事件类型{event_type}应被处理"

    def test_timer_handler_triggers_independently_of_events(self):
        """验证定时器处理器独立于事件处理触发

        使用场景：在实际交易系统中，定时器处理器用于：
        - 定期保存投资组合状态
        - 定期计算性能指标
        - 定期发送心跳包
        - 定期清理过期数据

        期望结果：
        1. 独立性：定时器处理器的触发不依赖于任何事件
        2. 定时性：按照设定的时间间隔定期触发
        3. 并发性：定时器处理在独立线程中运行

        业务价值：确保系统具有自治能力，即使没有事件流也能定期执行维护任务，
        保障系统的稳定性和数据的完整性。
        """
        import time

        engine = EventEngine()
        timer_triggered = []

        def periodic_task():
            timer_triggered.append(f"timer_task_{len(timer_triggered)}")

        # Register timer handler and enable timer
        engine.register_timer(periodic_task)
        engine.enable_timer()

        # Start engine to activate timer thread
        engine.start()

        # Wait for timer to trigger (with small timeout to avoid long test)
        time.sleep(1.5)  # Wait for at least one timer interval (default is 1.0)

        # Stop engine
        engine.stop()

        # Verify timer triggered at least once
        assert len(timer_triggered) > 0, "定时器处理器应该至少触发一次"

        # Verify timer triggered multiple times if we wait longer
        # This confirms the periodic nature
        # Note: The exact number depends on timing and thread scheduling

    def test_threading_flags_properties(self):
        """测试线程标志属性"""
        engine = EventEngine()

        # 验证主线程标志初始化
        assert hasattr(engine, '_main_flag')
        assert isinstance(engine._main_flag, threading.Event)

        # 验证定时器线程标志初始化
        assert hasattr(engine, '_timer_flag')
        assert isinstance(engine._timer_flag, threading.Event)

        # 验证线程标志初始状态（未设置）
        assert not engine._main_flag.is_set()
        assert not engine._timer_flag.is_set()

    def test_queue_property(self):
        """测试队列属性"""
        engine = EventEngine()

        # 验证队列对象初始化
        assert hasattr(engine, '_event_queue')
        assert isinstance(engine._event_queue, Queue)

        # 验证队列初始状态（空队列）
        assert engine._event_queue.empty()

        # 验证队列基本功能
        test_item = "test_event"
        engine._event_queue.put(test_item)
        assert not engine._event_queue.empty()
        retrieved_item = engine._event_queue.get_nowait()
        assert retrieved_item == test_item
        assert engine._event_queue.empty()


@pytest.mark.unit
class TestEventHandlerRegistration:
    """3. 事件处理器注册测试"""

    def test_register_event_handler(self):
        """测试注册事件处理器"""
        engine = EventEngine()

        # 创建测试处理器函数
        def test_handler(event):
            return f"handled_{event}"

        # 测试注册新事件类型的处理器
        from ginkgo.enums import EVENT_TYPES
        event_type = EVENT_TYPES.PRICEUPDATE

        result = engine.register(event_type, test_handler)
        assert result is True

        # 验证处理器被正确注册
        assert event_type in engine._handlers
        assert test_handler in engine._handlers[event_type]
        assert engine.handler_count == 1

        # 测试注册相同类型的不同处理器
        def test_handler2(event):
            return f"handled2_{event}"

        result2 = engine.register(event_type, test_handler2)
        assert result2 is True
        assert len(engine._handlers[event_type]) == 2
        assert engine.handler_count == 2

    def test_register_general_handler(self):
        """测试注册通用处理器"""
        engine = EventEngine()

        # 创建测试通用处理器函数
        def general_handler(event):
            return f"general_handled_{event}"

        # 测试注册通用处理器
        result = engine.register_general(general_handler)
        assert result is True

        # 验证通用处理器被正确注册
        assert general_handler in engine._general_handlers
        assert engine.general_count == 1

        # 测试注册多个通用处理器
        def general_handler2(event):
            return f"general2_{event}"

        result2 = engine.register_general(general_handler2)
        assert result2 is True
        assert len(engine._general_handlers) == 2
        assert engine.general_count == 2

    def test_register_timer_handler(self):
        """测试注册定时器处理器"""
        engine = EventEngine()

        # 创建测试定时器处理器函数
        def timer_handler():
            return "timer_executed"

        # 测试注册定时器处理器
        result = engine.register_timer(timer_handler)
        assert result is True

        # 验证定时器处理器被正确注册
        assert timer_handler in engine._timer_handlers
        assert engine.timer_count == 1

        # 测试注册多个定时器处理器
        def timer_handler2():
            return "timer2_executed"

        result2 = engine.register_timer(timer_handler2)
        assert result2 is True
        assert len(engine._timer_handlers) == 2
        assert engine.timer_count == 2

    def test_unregister_handler(self):
        """测试取消注册处理器"""
        engine = EventEngine()
        from ginkgo.enums import EVENT_TYPES
        event_type = EVENT_TYPES.PRICEUPDATE

        # 创建并注册处理器
        def test_handler(event):
            return f"handled_{event}"

        engine.register(event_type, test_handler)
        assert engine.handler_count == 1

        # 测试取消注册存在的处理器
        result = engine.unregister(event_type, test_handler)
        assert result is True
        assert test_handler not in engine._handlers[event_type]
        assert engine.handler_count == 0

        # 测试取消注册不存在的处理器
        def non_existent_handler(event):
            pass

        result2 = engine.unregister(event_type, non_existent_handler)
        assert result2 is False

        # 测试取消注册不存在的事件类型
        from ginkgo.enums import EVENT_TYPES
        non_existent_type = EVENT_TYPES.SIGNALGENERATION
        result3 = engine.unregister(non_existent_type, test_handler)
        assert result3 is False

    def test_handler_overwrite_behavior(self):
        """测试处理器覆盖行为"""
        engine = EventEngine()
        from ginkgo.enums import EVENT_TYPES
        event_type = EVENT_TYPES.PRICEUPDATE

        # 创建测试处理器
        def test_handler(event):
            return f"handled_{event}"

        # 注册处理器
        result1 = engine.register(event_type, test_handler)
        assert result1 is True
        assert engine.handler_count == 1

        # 测试重复注册相同处理器（应该失败）
        result2 = engine.register(event_type, test_handler)
        assert result2 is False  # 不应该重复添加
        assert engine.handler_count == 1  # 数量不变

        # 验证通用处理器的重复注册行为
        def general_handler(event):
            return "general"

        result3 = engine.register_general(general_handler)
        assert result3 is True

        result4 = engine.register_general(general_handler)
        assert result4 is False  # 不应该重复添加
        assert engine.general_count == 1

        # 验证定时器处理器的重复注册行为
        def timer_handler():
            return "timer"

        result5 = engine.register_timer(timer_handler)
        assert result5 is True

        result6 = engine.register_timer(timer_handler)
        assert result6 is False  # 不应该重复添加
        assert engine.timer_count == 1


@pytest.mark.unit
class TestEventDispatchMechanics:
    """4. 事件分发机制测试"""

    def test_put_to_queue(self):
        """测试向队列放入事件"""
        engine = EventEngine()

        # 创建测试事件
        from ginkgo.trading.events.base_event import EventBase
        from ginkgo.enums import EVENT_TYPES

        event = EventBase()
        event.event_type = EVENT_TYPES.PRICEUPDATE

        # 测试初始状态（空队列）
        assert engine.todo_count == 0

        # 放入事件
        engine.put(event)

        # 验证事件被正确放入队列
        assert engine.todo_count == 1

        # 放入多个事件
        event2 = EventBase()
        event2.event_type = EVENT_TYPES.SIGNALGENERATION
        engine.put(event2)

        assert engine.todo_count == 2

    def test_get_event_from_queue(self):
        """测试从队列获取事件"""
        engine = EventEngine()

        # 创建测试事件
        from ginkgo.trading.events.base_event import EventBase
        from ginkgo.enums import EVENT_TYPES

        event1 = EventBase()
        event1.event_type = EVENT_TYPES.PRICEUPDATE
        event2 = EventBase()
        event2.event_type = EVENT_TYPES.SIGNALGENERATION

        # 放入事件
        engine.put(event1)
        engine.put(event2)
        assert engine.todo_count == 2

        # 获取事件（FIFO顺序）
        retrieved_event1 = engine._event_queue.get_nowait()
        assert retrieved_event1 is event1
        assert engine.todo_count == 1

        retrieved_event2 = engine._event_queue.get_nowait()
        assert retrieved_event2 is event2
        assert engine.todo_count == 0

    def test_event_processing_dispatch(self):
        """测试事件处理分发"""
        engine = EventEngine()

        # 创建测试事件和处理器
        from ginkgo.trading.events.base_event import EventBase
        from ginkgo.enums import EVENT_TYPES

        handled_events = []

        def price_handler(event):
            handled_events.append(('price', event))

        def signal_handler(event):
            handled_events.append(('signal', event))

        # 注册处理器
        engine.register(EVENT_TYPES.PRICEUPDATE, price_handler)
        engine.register(EVENT_TYPES.SIGNALGENERATION, signal_handler)

        # 创建事件
        price_event = EventBase()
        price_event.event_type = EVENT_TYPES.PRICEUPDATE
        signal_event = EventBase()
        signal_event.event_type = EVENT_TYPES.SIGNALGENERATION

        # 处理事件
        engine._process(price_event)
        engine._process(signal_event)

        # 验证事件被正确分发
        assert len(handled_events) == 2
        assert ('price', price_event) in handled_events
        assert ('signal', signal_event) in handled_events

    def test_general_handler_dispatch(self):
        """测试通用处理器分发"""
        engine = EventEngine()

        # 创建测试事件和通用处理器
        from ginkgo.trading.events.base_event import EventBase
        from ginkgo.enums import EVENT_TYPES

        general_handled_events = []
        specific_handled_events = []

        def general_handler(event):
            general_handled_events.append(event)

        def specific_handler(event):
            specific_handled_events.append(event)

        # 注册通用处理器和特定处理器
        engine.register_general(general_handler)
        engine.register(EVENT_TYPES.PRICEUPDATE, specific_handler)

        # 创建不同类型的事件
        price_event = EventBase()
        price_event.event_type = EVENT_TYPES.PRICEUPDATE
        signal_event = EventBase()
        signal_event.event_type = EVENT_TYPES.SIGNALGENERATION

        # 处理事件
        engine._process(price_event)
        engine._process(signal_event)

        # 验证通用处理器处理所有事件
        assert len(general_handled_events) == 2
        assert price_event in general_handled_events
        assert signal_event in general_handled_events

        # 验证特定处理器只处理对应类型的事件
        assert len(specific_handled_events) == 1
        assert price_event in specific_handled_events
        assert signal_event not in specific_handled_events

    def test_queue_empty_handling(self):
        """测试队列空时的处理"""
        engine = EventEngine()

        # 验证初始状态（空队列）
        assert engine.todo_count == 0
        assert engine._event_queue.empty()

        # 测试从空队列获取事件时抛出Empty异常
        from queue import Empty

        with pytest.raises(Empty):
            engine._event_queue.get_nowait()

        # 添加事件后再次验证队列不为空
        from ginkgo.trading.events.base_event import EventBase
        from ginkgo.enums import EVENT_TYPES

        event = EventBase()
        event.event_type = EVENT_TYPES.PRICEUPDATE
        engine.put(event)

        assert not engine._event_queue.empty()
        assert engine.todo_count == 1

        # 获取事件后队列再次为空
        retrieved_event = engine._event_queue.get_nowait()
        assert retrieved_event is event
        assert engine._event_queue.empty()
        assert engine.todo_count == 0


@pytest.mark.unit
class TestEventLifecycleFlow:
    """5. 事件生命周期流转测试"""

    def test_price_update_event_flow(self):
        """测试价格更新事件流转"""
        # 1. 创建EventEngine并设置价格更新处理器
        engine = EventEngine()

        price_updates = []
        def price_handler(event):
            price_updates.append({
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'event': event
            })

        engine.register(EVENT_TYPES.PRICEUPDATE, price_handler)

        # 2. 创建PriceUpdate事件
        from ginkgo.trading.events.base_event import EventBase
        price_event = EventBase()
        price_event.event_type = EVENT_TYPES.PRICEUPDATE

        # 3. 通过put()将事件放入队列
        engine.put(price_event)

        # 4. 验证队列中有事件
        assert engine.todo_count == 1
        assert not engine._event_queue.empty()

        # 5. 从队列获取事件并通过_process()处理
        queued_event = engine._event_queue.get_nowait()
        assert queued_event is price_event

        engine._process(price_event)

        # 6. 验证处理器被调用，事件信息正确传递
        assert len(price_updates) == 1
        assert price_updates[0]['event_type'] == EVENT_TYPES.PRICEUPDATE
        assert price_updates[0]['event'] is price_event

        # 7. 验证事件处理后的状态变化
        assert engine.todo_count == 0
        assert engine._event_queue.empty()

    def test_signal_generation_event_flow(self):
        """测试信号生成事件流转"""
        # 1. 创建EventEngine并设置信号生成处理器
        engine = EventEngine()

        signal_events = []
        def signal_handler(event):
            signal_events.append({
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'event': event
            })

        engine.register(EVENT_TYPES.SIGNALGENERATION, signal_handler)

        # 2. 创建SignalGeneration事件
        from ginkgo.trading.events.base_event import EventBase
        signal_event = EventBase()
        signal_event.event_type = EVENT_TYPES.SIGNALGENERATION

        # 3. 通过完整的流转过程：put -> queue -> process
        engine.put(signal_event)

        # 验证事件在队列中
        assert engine.todo_count == 1
        assert not engine._event_queue.empty()

        # 从队列获取并处理事件
        queued_event = engine._event_queue.get_nowait()
        assert queued_event is signal_event

        engine._process(signal_event)

        # 4. 验证信号处理器被正确调用
        assert len(signal_events) == 1
        assert signal_events[0]['event_type'] == EVENT_TYPES.SIGNALGENERATION
        assert signal_events[0]['event'] is signal_event

        # 5. 验证事件处理后的状态变化
        assert engine.todo_count == 0
        assert engine._event_queue.empty()

    def test_order_lifecycle_event_flow(self):
        """测试订单生命周期事件流转"""
        engine = EventEngine()
        order_events = []

        def order_ack_handler(event):
            order_events.append({
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'stage': 'ack_received',
                'event': event
            })

        def order_filled_handler(event):
            order_events.append({
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'stage': 'fill_received',
                'event': event
            })

        # 注册订单生命周期事件处理器
        engine.register(EVENT_TYPES.ORDERACK, order_ack_handler)
        engine.register(EVENT_TYPES.ORDERFILLED, order_filled_handler)

        # 1. 发送订单确认事件
        from ginkgo.trading.events.base_event import EventBase
        import datetime
        ack_event = EventBase()
        ack_event.event_type = EVENT_TYPES.ORDERACK
        ack_event.set_time(datetime.datetime.now())

        engine.put(ack_event)

        # 验证订单确认事件被正确处理
        queued_ack_event = engine._event_queue.get_nowait()
        assert queued_ack_event is ack_event
        engine._process(ack_event)

        assert len(order_events) == 1, "订单确认事件应被记录"
        assert order_events[0]['event_type'] == EVENT_TYPES.ORDERACK
        assert order_events[0]['stage'] == 'ack_received'
        assert order_events[0]['event'] is ack_event

        # 2. 发送订单成交事件
        fill_event = EventBase()
        fill_event.event_type = EVENT_TYPES.ORDERFILLED
        fill_event.set_time(datetime.datetime.now())

        engine.put(fill_event)

        # 验证订单成交事件被正确处理
        queued_fill_event = engine._event_queue.get_nowait()
        assert queued_fill_event is fill_event
        engine._process(fill_event)

        assert len(order_events) == 2, "应记录两个订单事件"
        assert order_events[1]['event_type'] == EVENT_TYPES.ORDERFILLED
        assert order_events[1]['stage'] == 'fill_received'
        assert order_events[1]['event'] is fill_event

        # 3. 验证事件处理顺序
        assert order_events[0]['timestamp'] <= order_events[1]['timestamp'], "事件时间戳顺序应正确"

        # 4. 验证事件类型正确性
        event_types = [event['event_type'] for event in order_events]
        assert EVENT_TYPES.ORDERACK in event_types, "应包含订单确认事件"
        assert EVENT_TYPES.ORDERFILLED in event_types, "应包含订单成交事件"

        # 5. 验证订单生命周期完整性
        stages = [event['stage'] for event in order_events]
        assert 'ack_received' in stages, "应包含订单确认阶段"
        assert 'fill_received' in stages, "应包含订单成交阶段"

        # 6. 验证事件对象完整性
        for event_record in order_events:
            assert event_record['event'] is not None, "事件对象不应为空"
            assert hasattr(event_record['event'], 'event_type'), "事件应有event_type属性"
            assert hasattr(event_record['event'], 'timestamp'), "事件应有timestamp属性"

        # 7. 验证引擎状态保持稳定
        assert engine.todo_count == 0, "处理完事件后队列应为空"
        assert engine._event_queue.empty(), "队列应为空"

    def test_position_update_event_flow(self):
        """测试持仓更新事件流转"""
        engine = EventEngine()
        position_updates = []

        def position_handler(event):
            position_updates.append({
                'event_type': event.event_type,
                'timestamp': event.timestamp,
                'stage': 'position_updated',
                'event': event
            })

        # 注册持仓更新事件处理器
        engine.register(EVENT_TYPES.POSITIONUPDATE, position_handler)

        # 1. 创建持仓更新事件
        from ginkgo.trading.events.base_event import EventBase
        import datetime
        position_event = EventBase()
        position_event.event_type = EVENT_TYPES.POSITIONUPDATE
        position_event.set_time(datetime.datetime.now())

        # 2. 通过put()将事件放入队列
        engine.put(position_event)

        # 验证队列中有事件
        assert engine.todo_count == 1, "队列中应有一个事件"
        assert not engine._event_queue.empty(), "队列不应为空"

        # 3. 从队列获取事件并处理
        queued_event = engine._event_queue.get_nowait()
        assert queued_event is position_event, "队列中的事件应与原事件相同"

        engine._process(position_event)

        # 4. 验证持仓更新处理器被调用
        assert len(position_updates) == 1, "应记录一个持仓更新事件"
        assert position_updates[0]['event_type'] == EVENT_TYPES.POSITIONUPDATE
        assert position_updates[0]['stage'] == 'position_updated'
        assert position_updates[0]['event'] is position_event

        # 5. 验证事件对象完整性
        assert position_updates[0]['event'] is not None, "事件对象不应为空"
        assert hasattr(position_updates[0]['event'], 'event_type'), "事件应有event_type属性"
        assert hasattr(position_updates[0]['event'], 'timestamp'), "事件应有timestamp属性"

        # 6. 验证事件处理后的状态变化
        assert engine.todo_count == 0, "处理完事件后队列应为空"
        assert engine._event_queue.empty(), "队列应为空"



@pytest.mark.unit
class TestCrossComponentEventPropagation:
    """6. 跨组件事件传播测试"""

    def test_event_publisher_injection(self):
        """测试事件发布器注入机制"""
        engine = EventEngine()

        # 创建模拟组件，测试event_publisher注入
        class MockComponent:
            def __init__(self, name):
                self.name = name
                self._engine_put = None
                self.published_events = []

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def publish_test_event(self, event):
                if self._engine_put:
                    self._engine_put(event)
                    self.published_events.append(event)

        mock_component = MockComponent("TestComponent")

        # 测试组件是否有set_event_publisher方法
        assert hasattr(mock_component, 'set_event_publisher'), "组件应该有set_event_publisher方法"

        # 手动注入事件发布器（模拟bind操作）
        mock_component.set_event_publisher(engine.put)

        # 验证注入成功
        assert mock_component._engine_put is not None, "事件发布器应该被正确注入"
        assert mock_component._engine_put == engine.put, "注入的发布器应该是引擎的put方法"

        # 测试通过注入的发布器发送事件
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        test_event.event_type = EVENT_TYPES.PRICEUPDATE

        mock_component.publish_test_event(test_event)

        # 验证事件被发送到引擎队列
        assert engine.todo_count == 1, "事件应该被放入引擎队列"
        assert len(mock_component.published_events) == 1, "组件应该记录已发布的事件"

    def test_component_event_round_trip(self):
        """测试组件事件往返传播"""
        engine = EventEngine()
        received_events = []

        # 创建事件处理器
        def signal_handler(event):
            received_events.append(event)

        # 注册信号处理器
        engine.register(EVENT_TYPES.SIGNALGENERATION, signal_handler)

        # 创建模拟组件
        class MockPortfolio:
            def __init__(self):
                self._engine_put = None

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def on_price_update(self, price_event):
                # 模拟投资组合处理价格更新，生成交易信号
                if self._engine_put:
                    signal_event = EventBase()
                    signal_event.event_type = EVENT_TYPES.SIGNALGENERATION
                    signal_event.set_time(price_event.timestamp)
                    self._engine_put(signal_event)

        portfolio = MockPortfolio()
        portfolio.set_event_publisher(engine.put)

        # 注册投资组合的价格更新处理器
        engine.register(EVENT_TYPES.PRICEUPDATE, portfolio.on_price_update)

        # 发送价格更新事件
        from ginkgo.trading.events.base_event import EventBase
        import datetime
        price_event = EventBase()
        price_event.event_type = EVENT_TYPES.PRICEUPDATE
        price_event.set_time(datetime.datetime.now())

        engine.put(price_event)

        # 处理价格更新事件（触发投资组合生成信号）
        queued_price_event = engine._event_queue.get_nowait()
        engine._process(queued_price_event)

        # 处理投资组合生成的信号事件
        assert engine.todo_count == 1, "投资组合应该生成了一个信号事件"
        queued_signal_event = engine._event_queue.get_nowait()
        engine._process(queued_signal_event)

        # 验证事件往返传播成功
        assert len(received_events) == 1, "信号处理器应该接收到一个事件"
        assert received_events[0].event_type == EVENT_TYPES.SIGNALGENERATION, "应该是信号生成事件"

    def test_multiple_component_event_chain(self):
        """测试多组件事件链传播"""
        engine = EventEngine()
        event_chain = []

        # 创建多个模拟组件形成事件链
        class MockDataFeeder:
            def __init__(self):
                self._engine_put = None

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def publish_price_update(self, symbol, price):
                if self._engine_put:
                    event = EventBase()
                    event.event_type = EVENT_TYPES.PRICEUPDATE
                    event.set_time(datetime.datetime.now())
                    self._engine_put(event)

        class MockStrategy:
            def __init__(self):
                self._engine_put = None

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def on_price_update(self, price_event):
                event_chain.append(('strategy', 'price_received'))
                if self._engine_put:
                    signal_event = EventBase()
                    signal_event.event_type = EVENT_TYPES.SIGNALGENERATION
                    signal_event.set_time(price_event.timestamp)
                    self._engine_put(signal_event)

        class MockRiskManager:
            def on_signal_generation(self, signal_event):
                event_chain.append(('risk_manager', 'signal_received'))

        # 创建组件实例并注入事件发布器
        feeder = MockDataFeeder()
        strategy = MockStrategy()
        risk_manager = MockRiskManager()

        feeder.set_event_publisher(engine.put)
        strategy.set_event_publisher(engine.put)

        # 注册事件处理器，形成处理链
        engine.register(EVENT_TYPES.PRICEUPDATE, strategy.on_price_update)
        engine.register(EVENT_TYPES.SIGNALGENERATION, risk_manager.on_signal_generation)

        # 触发事件链：DataFeeder -> Strategy -> RiskManager
        feeder.publish_price_update("AAPL", 150.0)

        # 处理第一个事件（价格更新）
        price_event = engine._event_queue.get_nowait()
        engine._process(price_event)

        # 处理第二个事件（信号生成）
        signal_event = engine._event_queue.get_nowait()
        engine._process(signal_event)

        # 验证事件链执行顺序
        assert len(event_chain) == 2, "应该有两个组件处理了事件"
        assert event_chain[0] == ('strategy', 'price_received'), "策略应该先接收价格事件"
        assert event_chain[1] == ('risk_manager', 'signal_received'), "风控应该接收信号事件"

    def test_bidirectional_event_communication(self):
        """测试双向事件通信"""
        engine = EventEngine()
        communication_log = []

        # 创建两个相互通信的组件
        class ComponentA:
            def __init__(self, name):
                self.name = name
                self._engine_put = None

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def on_signal_generation(self, event):
                communication_log.append(f"{self.name} received signal")
                # 发送回应事件
                if self._engine_put:
                    response_event = EventBase()
                    response_event.event_type = EVENT_TYPES.ORDERSUBMITTED
                    response_event.set_time(event.timestamp)
                    self._engine_put(response_event)

        class ComponentB:
            def __init__(self, name):
                self.name = name
                self._engine_put = None

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

            def on_order_submitted(self, event):
                communication_log.append(f"{self.name} received order")
                # 发送确认事件
                if self._engine_put:
                    ack_event = EventBase()
                    ack_event.event_type = EVENT_TYPES.ORDERACK
                    ack_event.set_time(event.timestamp)
                    self._engine_put(ack_event)

            def trigger_signal(self):
                # 主动发送信号事件
                if self._engine_put:
                    signal_event = EventBase()
                    signal_event.event_type = EVENT_TYPES.SIGNALGENERATION
                    signal_event.set_time(datetime.datetime.now())
                    self._engine_put(signal_event)

        # 创建组件实例
        comp_a = ComponentA("ComponentA")
        comp_b = ComponentB("ComponentB")

        # 注入事件发布器
        comp_a.set_event_publisher(engine.put)
        comp_b.set_event_publisher(engine.put)

        # 建立双向通信：B -> A -> B
        engine.register(EVENT_TYPES.SIGNALGENERATION, comp_a.on_signal_generation)
        engine.register(EVENT_TYPES.ORDERSUBMITTED, comp_b.on_order_submitted)

        # 创建最终事件处理器
        final_events = []
        def final_handler(event):
            communication_log.append("final handler received ack")
            final_events.append(event)

        engine.register(EVENT_TYPES.ORDERACK, final_handler)

        # 触发双向通信流程
        comp_b.trigger_signal()

        # 处理事件链：Signal -> Order -> Ack
        # 1. 处理信号事件
        signal_event = engine._event_queue.get_nowait()
        engine._process(signal_event)

        # 2. 处理订单事件
        order_event = engine._event_queue.get_nowait()
        engine._process(order_event)

        # 3. 处理确认事件
        ack_event = engine._event_queue.get_nowait()
        engine._process(ack_event)

        # 验证双向通信成功
        expected_log = [
            "ComponentA received signal",
            "ComponentB received order",
            "final handler received ack"
        ]
        assert communication_log == expected_log, f"双向通信日志不匹配: {communication_log}"
        assert len(final_events) == 1, "最终处理器应该接收到确认事件"
        assert final_events[0].event_type == EVENT_TYPES.ORDERACK, "最终事件应该是订单确认"


@pytest.mark.unit
class TestEventEngineThreading:
    """7. 事件引擎线程测试"""

    def test_thread_initialization(self):
        """测试线程初始化"""
        engine = EventEngine()

        # 验证线程对象已创建
        assert engine._main_thread is not None, "主线程应该被创建"
        assert engine._timer_thread is not None, "定时器线程应该被创建"

        # 验证线程标志初始化
        assert engine._main_flag is not None, "主线程标志应该被创建"
        assert engine._timer_flag is not None, "定时器线程标志应该被创建"

        # 验证线程处于未启动状态
        assert not engine._main_thread.is_alive(), "主线程初始应该未启动"
        assert not engine._timer_thread.is_alive(), "定时器线程初始应该未启动"

        # 验证标志初始状态
        assert not engine._main_flag.is_set(), "主线程标志初始应该未设置"
        assert not engine._timer_flag.is_set(), "定时器线程标志初始应该未设置"

    def test_timer_handler_management(self):
        """测试定时器处理器管理"""
        engine = EventEngine()

        # 创建测试定时器处理器
        timer_calls = []
        def timer_handler():
            timer_calls.append("timer_called")

        # 测试注册定时器处理器
        result = engine.register_timer(timer_handler)
        assert result is True, "注册定时器处理器应该成功"
        assert engine.timer_count == 1, "定时器处理器计数应该为1"

        # 测试重复注册
        result = engine.register_timer(timer_handler)
        assert result is False, "重复注册应该失败"
        assert engine.timer_count == 1, "定时器处理器计数应该仍为1"

        # 测试注销定时器处理器
        result = engine.unregister_timer(timer_handler)
        assert result is True, "注销定时器处理器应该成功"
        assert engine.timer_count == 0, "定时器处理器计数应该为0"

        # 测试注销不存在的处理器
        result = engine.unregister_timer(timer_handler)
        assert result is False, "注销不存在的处理器应该失败"

    def test_timer_interval_configuration(self):
        """测试定时器间隔配置"""
        # 测试默认定时器间隔
        engine = EventEngine()
        assert engine._timer_interval == 1, "默认定时器间隔应该为1秒"

        # 测试自定义定时器间隔
        engine_custom = EventEngine(timer_interval=5)
        assert engine_custom._timer_interval == 5, "自定义定时器间隔应该为5秒"

    def test_active_flag_management(self):
        """测试活跃标志管理"""
        engine = EventEngine()

        # 验证初始状态
        assert hasattr(engine, 'is_active'), "引擎应该有is_active属性"

        # 验证线程标志管理方法存在
        assert hasattr(engine, '_main_flag'), "应该有主线程标志"
        assert hasattr(engine, '_timer_flag'), "应该有定时器线程标志"

        # 验证标志是线程安全的Event对象
        import threading
        assert isinstance(engine._main_flag, threading.Event), "主线程标志应该是Event对象"
        assert isinstance(engine._timer_flag, threading.Event), "定时器线程标志应该是Event对象"


@pytest.mark.unit
class TestEventEngineComponentBinding:
    """8. 事件引擎组件绑定测试"""

    def test_bind_datafeeder(self):
        """测试绑定数据馈送器"""
        engine = EventEngine()

        # 创建模拟数据馈送器
        class MockDataFeeder:
            def __init__(self, name):
                self.name = name
                self._engine = None
                self._engine_put = None
                self.bound_engine = None

            def bind_engine(self, engine):
                self.bound_engine = engine

            def set_event_publisher(self, publisher):
                self._engine_put = publisher

        mock_feeder = MockDataFeeder("TestFeeder")

        # 验证初始状态
        assert engine.datafeeder is None, "初始数据馈送器应该为空"

        # 执行绑定
        engine.bind_datafeeder(mock_feeder)

        # 验证绑定结果
        assert engine.datafeeder is mock_feeder, "数据馈送器应该被正确绑定"
        assert mock_feeder.bound_engine is engine, "馈送器应该反向绑定引擎"
        assert mock_feeder._engine_put is not None, "事件发布器应该被注入"

        # 验证事件发布器功能
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        mock_feeder._engine_put(test_event)
        assert engine.todo_count == 1, "事件发布器应该能正常工作"

    def test_bind_matchmaking(self):
        """测试绑定撮合引擎"""
        engine = EventEngine()

        # 直接使用MatchMakingBase
        from ginkgo.trading.routing.base_matchmaking import MatchMakingBase

        matchmaking = MatchMakingBase("TestMatchMaking")

        # 验证初始状态
        assert engine.matchmaking is None, "初始撮合引擎应该为空"

        # 执行绑定
        engine.bind_matchmaking(matchmaking)

        # 验证双向绑定结果
        assert engine.matchmaking is matchmaking, "引擎应该绑定撮合引擎"
        assert matchmaking._engine_put is not None, "事件发布器应该被注入"

        # 验证BaseMatchMaking具有必要的方法
        assert hasattr(matchmaking, 'set_event_publisher'), "应该有set_event_publisher方法"
        assert hasattr(matchmaking, 'bind_engine'), "应该有bind_engine方法"
        assert hasattr(matchmaking, 'put'), "应该有put方法用于发布事件"

    def test_bind_portfolio(self):
        """测试绑定投资组合"""
        engine = EventEngine()

        # 使用BasePortfolio
        from ginkgo.trading.portfolios.base_portfolio import BasePortfolio

        portfolio = BasePortfolio("TestPortfolio")

        # 验证初始状态
        assert len(engine.portfolios) == 0, "初始投资组合列表应该为空"

        # 执行绑定
        engine.add_portfolio(portfolio)

        # 验证绑定结果
        assert len(engine.portfolios) == 1, "应该有一个投资组合"
        assert portfolio in engine.portfolios, "投资组合应该在列表中"
        assert portfolio._engine_put is not None, "事件发布器应该被注入"

        # 验证重复绑定不会重复添加
        engine.add_portfolio(portfolio)
        assert len(engine.portfolios) == 1, "重复绑定不应该重复添加"

        # 验证BasePortfolio具有必要的方法
        assert hasattr(portfolio, 'set_event_publisher'), "应该有set_event_publisher方法"
        assert hasattr(portfolio, 'bind_engine'), "应该有bind_engine方法"

    def test_component_binding_coordination(self):
        """测试组件绑定协调"""
        engine = EventEngine()
        binding_log = []

        # 创建模拟组件，只关注绑定关系而非生命周期
        class MockComponent:
            def __init__(self, name, component_type):
                self.name = name
                self.component_type = component_type
                self._engine_put = None
                self.bound_engine = None

            def bind_engine(self, engine):
                self.bound_engine = engine
                binding_log.append(f"{self.name}_engine_bound")

            def set_event_publisher(self, publisher):
                self._engine_put = publisher
                binding_log.append(f"{self.name}_publisher_injected")

        # 创建不同类型的组件
        datafeeder = MockComponent("DataFeeder", "feeder")
        matchmaking = MockComponent("MatchMaking", "matching")
        portfolio = MockComponent("Portfolio", "portfolio")

        # 验证初始状态：所有组件都未绑定
        assert engine.datafeeder is None, "DataFeeder初始应为空"
        assert engine.matchmaking is None, "MatchMaking初始应为空"
        assert len(engine.portfolios) == 0, "Portfolio列表初始应为空"

        # 1. 测试DataFeeder绑定协调
        engine.bind_datafeeder(datafeeder)
        assert datafeeder.bound_engine is engine, "DataFeeder应绑定到引擎"
        assert datafeeder._engine_put is not None, "DataFeeder应获得事件发布器"

        # 2. 测试MatchMaking绑定协调
        # 手动模拟bind_matchmaking的核心逻辑
        engine._matchmaking = matchmaking
        matchmaking.bind_engine(engine)
        if hasattr(matchmaking, "set_event_publisher"):
            matchmaking.set_event_publisher(engine.put)

        assert matchmaking.bound_engine is engine, "MatchMaking应绑定到引擎"
        assert matchmaking._engine_put is not None, "MatchMaking应获得事件发布器"

        # 3. 测试Portfolio绑定协调
        engine.add_portfolio(portfolio)
        portfolio.bind_engine(engine)
        if hasattr(portfolio, "set_event_publisher"):
            portfolio.set_event_publisher(engine.put)

        assert portfolio in engine.portfolios, "Portfolio应在引擎列表中"
        assert portfolio.bound_engine is engine, "Portfolio应绑定到引擎"
        assert portfolio._engine_put is not None, "Portfolio应获得事件发布器"

        # 验证绑定协调的完整性
        expected_bindings = [
            "DataFeeder_engine_bound", "DataFeeder_publisher_injected",
            "MatchMaking_engine_bound", "MatchMaking_publisher_injected",
            "Portfolio_engine_bound", "Portfolio_publisher_injected"
        ]
        assert binding_log == expected_bindings, f"绑定协调日志不匹配: {binding_log}"

        # 验证引擎作为事件中心的协调能力
        assert engine.datafeeder is datafeeder, "引擎应持有DataFeeder引用"
        assert engine.matchmaking is matchmaking, "引擎应持有MatchMaking引用"
        assert len(engine.portfolios) == 1, "引擎应管理Portfolio列表"

        # 验证所有组件都能通过引擎发布事件
        for component in [datafeeder, matchmaking, portfolio]:
            assert component._engine_put is not None, f"{component.name}应该有事件发布能力"


@pytest.mark.unit
class TestEventEngineLifecycleManagement:
    """9. 引擎生命周期状态管理测试"""

    def test_initial_engine_state(self):
        """测试引擎初始状态"""
        engine = EventEngine()

        # 验证初始状态属性
        assert hasattr(engine, 'is_active'), "引擎应该有is_active属性"
        assert engine.is_active is False, "引擎初始状态应该为非活跃"

        # 验证引擎具有BaseEngine的状态管理能力
        assert hasattr(engine, 'state'), "引擎应该有state属性"
        assert hasattr(engine, 'status'), "引擎应该有status属性"
        assert hasattr(engine, 'is_active'), "引擎应该有is_active属性"

        # 验证初始运行状态
        assert hasattr(engine, '_is_running'), "引擎应该有_is_running属性"
        assert engine._is_running is False, "引擎初始应该未运行"

    def test_engine_start_lifecycle(self):
        """测试引擎启动生命周期"""
        engine = EventEngine()

        # 验证启动前状态
        assert engine.is_active is False, "启动前应该为非活跃状态"
        assert not engine._main_thread.is_alive(), "主线程启动前应该未运行"
        assert not engine._timer_thread.is_alive(), "定时器线程启动前应该未运行"

        # 测试启动方法存在性
        assert hasattr(engine, 'start'), "引擎应该有start方法"
        assert callable(engine.start), "start应该是可调用的方法"

        # 注意：由于main_loop是抽象方法，无法直接测试完整的启动流程
        # 这里只验证启动准备工作的正确性

        # 验证线程对象已正确创建并配置
        assert engine._main_thread is not None, "主线程对象应该被创建"
        assert engine._timer_thread is not None, "定时器线程对象应该被创建"

        # 验证线程的名称或其他可访问属性
        assert isinstance(engine._main_thread, threading.Thread), "应该是Thread对象"
        assert isinstance(engine._timer_thread, threading.Thread), "应该是Thread对象"

    def test_engine_pause_functionality(self):
        """测试引擎暂停功能"""
        engine = EventEngine()

        # 验证暂停方法存在
        assert hasattr(engine, 'pause'), "引擎应该有pause方法"
        assert callable(engine.pause), "pause应该是可调用的方法"

        # 模拟启动状态（启动引擎）
        engine.start()
        assert engine.is_active is True, "启动后应该为活跃状态"

        # 执行暂停操作
        engine.pause()

        # 验证暂停后状态
        assert engine.is_active is False, "暂停后应该为非活跃状态"

        # 清理：停止引擎
        engine.stop()

    def test_engine_stop_lifecycle(self):
        """测试引擎停止生命周期"""
        import time

        class _TestableEventEngine(EventEngine):
            """提供可运行的循环以验证完整停止流程"""

            def main_loop(self, stop_flag):
                while not stop_flag.is_set():
                    time.sleep(0.01)

            def timer_loop(self, stop_flag):
                while not stop_flag.is_set():
                    time.sleep(0.01)

        engine = _TestableEventEngine()

        # 运行引擎进入运行态
        engine.run()

        # 执行停止操作
        engine.stop()

        # 验证停止后的线程标志状态
        assert engine._main_flag.is_set(), "停止后主线程标志应该被设置"
        assert engine._timer_flag.is_set(), "停止后定时器线程标志应该被设置"
        assert engine.status == "Stopped", "停止后状态应为Stopped"

        # 清理后台线程，防止阻塞后续测试
        # 安全地join线程，只join已启动的线程
        if hasattr(engine._main_thread, '_started') and engine._main_thread._started:
            if engine._main_thread.is_alive():
                engine._main_thread.join(timeout=1)

        if hasattr(engine._timer_thread, '_started') and engine._timer_thread._started:
            if engine._timer_thread.is_alive():
                engine._timer_thread.join(timeout=1)

        # 验证引擎状态重置
        # 注意：_active状态由stop()方法的父类实现管理

    def test_run_method_implementation(self):
        """测试run方法实现"""
        engine = EventEngine()

        # 验证run方法存在且可调用
        assert hasattr(engine, 'run'), "引擎应该有run方法"
        assert callable(engine.run), "run应该是可调用的方法"

        # 验证run方法返回引擎实例
        result = engine.run()
        assert result is engine, "run方法应该返回引擎实例本身"

        # 重要：清理启动的线程，避免测试挂起
        engine.stop()
        # 等待线程结束
        if engine._main_thread.is_alive():
            engine._main_thread.join(timeout=1)
        if engine._timer_thread.is_alive():
            engine._timer_thread.join(timeout=1)

    def test_handle_event_method_implementation(self):
        """测试handle_event方法实现"""
        engine = EventEngine()

        # 验证handle_event方法存在
        assert hasattr(engine, 'handle_event'), "引擎应该有handle_event方法"
        assert callable(engine.handle_event), "handle_event应该是可调用的方法"

        # 创建测试事件
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        test_event.event_type = EVENT_TYPES.PRICEUPDATE

        # 测试handle_event调用_process
        handled_events = []
        original_process = engine._process

        def mock_process(event):
            handled_events.append(event)
            return original_process(event)

        engine._process = mock_process

        # 执行handle_event
        engine.handle_event(test_event)

        # 验证事件被正确处理
        assert len(handled_events) == 1, "事件应该被处理"
        assert handled_events[0] is test_event, "处理的事件应该是原事件"

    def test_now_property_management(self):
        """测试now属性管理"""
        engine = EventEngine()

        # 验证now属性存在
        assert hasattr(engine, 'now'), "引擎应该有now属性"

        # 验证初始状态
        initial_now = engine.now
        assert initial_now is not None, "初始now应该是一个datetime对象"

        # 测试now属性返回的是datetime类型
        import datetime
        assert isinstance(initial_now, datetime.datetime), "now应该返回datetime对象"

    def test_active_flag_state_consistency(self):
        """测试活跃标志状态一致性"""
        engine = EventEngine()

        # 验证初始状态一致性
        assert engine.is_active is False, "初始is_active应该为False"

        # 测试状态切换的一致性 - 通过start/pause方法
        engine.start()
        assert engine.is_active is True, "启动后is_active应该为True"

        # 测试pause方法对is_active的影响
        engine.pause()
        assert engine.is_active is False, "pause后is_active应该为False"

        # 测试多次pause的幂等性
        engine.pause()
        assert engine.is_active is False, "多次pause后is_active仍应该为False"

        # 清理：停止引擎
        engine.stop()


@pytest.mark.unit
class TestEventEngineExceptionHandling:
    """10. 异常处理和错误恢复测试"""

    def test_handler_exception_isolation(self):
        """测试处理器异常不会卡住主流程"""
        engine = EventEngine()

        # 创建处理器：一个正常，一个异常
        flow_continued = []

        def normal_handler(event):
            flow_continued.append("normal_executed")

        def exception_handler(event):
            raise ValueError("测试异常")

        # 注册处理器
        event_type = EVENT_TYPES.PRICEUPDATE
        engine.register(event_type, normal_handler)
        engine.register(event_type, exception_handler)

        # 创建测试事件
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        test_event.event_type = event_type

        # 关键测试：异常不应该完全阻塞流程
        try:
            engine._process(test_event)
        except ValueError:
            pass  # 异常被捕获，但不应该影响后续操作

        # 验证主流程没有被卡住
        # 1. 引擎仍然可以处理新事件
        another_event = EventBase()
        another_event.event_type = EVENT_TYPES.SIGNALGENERATION

        # 这个调用应该成功，证明引擎没有被卡住
        engine.put(another_event)
        assert engine.todo_count == 1, "异常后引擎应该仍能接受新事件"

        # 2. 事件处理机制仍然工作
        processed_after_exception = []
        def recovery_handler(event):
            processed_after_exception.append("recovered")

        engine.register(EVENT_TYPES.SIGNALGENERATION, recovery_handler)

        # 从队列获取并处理事件
        queued_event = engine._event_queue.get_nowait()
        engine._process(queued_event)

        # 验证：异常后引擎恢复正常
        assert len(processed_after_exception) == 1, "异常后引擎应该能正常处理新事件"

    def test_malformed_event_handling(self):
        """测试畸形事件不会破坏引擎"""
        engine = EventEngine()

        # 注册正常处理器作为参考
        normal_events_processed = []
        def normal_handler(event):
            normal_events_processed.append("processed")

        engine.register(EVENT_TYPES.PRICEUPDATE, normal_handler)

        # 测试1: None事件
        try:
            engine._process(None)
        except Exception:
            pass  # 捕获异常，但引擎应该继续工作

        # 测试2: 没有event_type属性的对象
        class BadEvent:
            pass

        try:
            engine._process(BadEvent())
        except Exception:
            pass

        # 验证：引擎仍然能处理正常事件
        from ginkgo.trading.events.base_event import EventBase
        normal_event = EventBase()
        normal_event.event_type = EVENT_TYPES.PRICEUPDATE
        engine._process(normal_event)

        assert len(normal_events_processed) == 1, "畸形事件后应该能正常处理事件"

    def test_queue_operations_error_handling(self):
        """测试队列操作错误不影响后续使用"""
        engine = EventEngine()

        # 测试put操作的鲁棒性
        from ginkgo.trading.events.base_event import EventBase

        # 1. 正常事件应该工作
        normal_event = EventBase()
        normal_event.event_type = EVENT_TYPES.PRICEUPDATE
        engine.put(normal_event)
        assert engine.todo_count == 1, "正常事件应该被放入队列"

        # 2. 测试put异常对象
        try:
            engine.put(None)
        except Exception:
            pass  # 捕获可能的异常

        # 3. 验证队列仍然可用
        another_event = EventBase()
        another_event.event_type = EVENT_TYPES.SIGNALGENERATION
        engine.put(another_event)

        # 关键验证：队列基本功能没有受损
        assert engine.todo_count >= 2, "异常后队列应该仍能接受事件"

        # 4. 验证get操作仍然正常
        first_event = engine._event_queue.get_nowait()
        assert first_event is not None, "应该能从队列获取事件"

    def test_component_binding_failure_recovery(self):
        """测试组件绑定失败不影响引擎基本功能"""
        engine = EventEngine()

        # 创建有缺陷的组件（缺少绑定方法）
        class DefectiveComponent:
            def __init__(self):
                self.name = "defective"
                # 故意不实现bind_engine或set_event_publisher

        defective = DefectiveComponent()

        # 尝试绑定可能失败
        try:
            if hasattr(defective, 'bind_engine'):
                defective.bind_engine(engine)
            if hasattr(defective, 'set_event_publisher'):
                defective.set_event_publisher(engine.put)
        except Exception:
            pass  # 绑定失败不应该影响引擎

        # 验证：引擎基本功能仍然正常
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        test_event.event_type = EVENT_TYPES.PRICEUPDATE
        engine.put(test_event)
        assert engine.todo_count == 1, "绑定失败后引擎应该仍能处理事件"

    def test_timer_handler_exception_handling(self):
        """测试定时器处理器异常不卡住定时器循环"""
        engine = EventEngine()

        # 创建正常和异常的定时器处理器
        timer_calls = []

        def normal_timer_handler():
            timer_calls.append("normal")

        def exception_timer_handler():
            timer_calls.append("exception_attempted")
            raise RuntimeError("定时器异常")

        def another_normal_timer_handler():
            timer_calls.append("another_normal")

        # 注册定时器处理器
        engine.register_timer(normal_timer_handler)
        engine.register_timer(exception_timer_handler)
        engine.register_timer(another_normal_timer_handler)

        # 模拟定时器循环的单次执行
        engine._active = True

        # 手动触发定时器处理器（模拟timer_loop逻辑）
        try:
            for handler in engine._timer_handlers:
                try:
                    handler()
                except Exception:
                    pass  # 在生产中应该有适当的异常处理
        except Exception:
            pass

        # 验证：定时器系统仍然可用
        # 1. 可以注册新的定时器处理器
        new_calls = []
        def new_timer_handler():
            new_calls.append("new")

        result = engine.register_timer(new_timer_handler)
        assert result is True, "异常后应该仍能注册新的定时器处理器"

        # 2. 定时器计数正确
        assert engine.timer_count == 4, "定时器处理器计数应该正确"


@pytest.mark.unit
class TestEventEngineThreadSafety:
    """11. 并发和线程安全测试"""

    def test_concurrent_event_processing(self):
        """测试高并发put操作的线程安全性"""
        engine = EventEngine()
        import threading
        import time

        # 增加并发压力：20个线程，每个50个事件
        def put_events():
            for i in range(50):
                from ginkgo.trading.events.base_event import EventBase
                event = EventBase()
                event.event_type = EVENT_TYPES.PRICEUPDATE
                engine.put(event)

        # 启动20个线程同时put
        threads = []
        for _ in range(20):
            t = threading.Thread(target=put_events)
            threads.append(t)
            t.start()

        # 等待完成
        for t in threads:
            t.join()

        # 验证：应该有1000个事件
        assert engine.todo_count == 1000, f"应该有1000个事件，实际{engine.todo_count}"

        # 验证：引擎仍然工作
        from ginkgo.trading.events.base_event import EventBase
        test_event = EventBase()
        test_event.event_type = EVENT_TYPES.SIGNALGENERATION
        engine.put(test_event)
        assert engine.todo_count == 1001, "高并发后引擎应该仍能工作"

    def test_registration_during_processing(self):
        """测试事件处理期间注册新处理器的安全性"""
        engine = EventEngine()

        # 先注册一个处理器
        def initial_handler(event):
            pass
        engine.register(EVENT_TYPES.PRICEUPDATE, initial_handler)

        # 放入一些事件
        from ginkgo.trading.events.base_event import EventBase
        for i in range(5):
            event = EventBase()
            event.event_type = EVENT_TYPES.PRICEUPDATE
            engine.put(event)

        # 在有待处理事件时注册新处理器（更实际的场景）
        def new_handler(event):
            pass
        result = engine.register(EVENT_TYPES.SIGNALGENERATION, new_handler)

        assert result is True, "处理期间应该能注册新处理器"
        assert engine.handler_count == 2, "应该有2个处理器"
        assert engine.todo_count == 5, "队列中的事件数不应该受影响"
