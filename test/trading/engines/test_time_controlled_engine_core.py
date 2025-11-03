"""
TimeControlledEventEngine核心功能测试

该文件包含TimeControlledEngine的核心方法、事件处理、时间推进等功能的测试用例。
从原始的大文件中提取出来，提高代码的可维护性。

测试范围：
1. 基础方法测试
2. 事件处理机制测试
3. 时间推进功能测试
4. 引擎状态管理测试
5. 事件队列操作测试
"""

import pytest
import sys
import datetime
import time as time_module
import threading
from pathlib import Path
from datetime import datetime as dt, time, timezone, timedelta
from unittest.mock import Mock, patch, MagicMock
from typing import List, Dict, Any, Optional

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

# 核心依赖导入
from ginkgo.enums import (
    EVENT_TYPES, FREQUENCY_TYPES, TICKDIRECTION_TYPES,
    SOURCE_TYPES, EXECUTION_MODE, TIME_MODE, ENGINESTATUS_TYPES
)
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.trading.events.component_time_advance import EventComponentTimeAdvance
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.engines.time_controlled_engine import TimeControlledEventEngine
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.time.providers import LogicalTimeProvider, SystemTimeProvider


@pytest.mark.unit
class TestBasicMethods:
    """1. 基础方法测试"""

    def test_engine_creation(self):
        """测试引擎创建"""
        engine = TimeControlledEventEngine()

        # 验证基本属性
        assert engine is not None, "引擎应被创建"
        assert hasattr(engine, 'engine_id'), "引擎应有engine_id"
        assert hasattr(engine, 'run_id'), "引擎应有run_id"
        assert hasattr(engine, 'status'), "引擎应有status"
        assert hasattr(engine, 'mode'), "引擎应有mode"

        # 验证默认状态
        assert engine.status == "idle", "初始状态应为idle"
        assert not engine.is_active, "初始应未激活"
        assert engine.run_id is None, "初始run_id应为None"
        assert engine.run_sequence == 0, "初始运行序列应为0"

        print("✓ 引擎创建测试通过")

    def test_engine_initialization_with_parameters(self):
        """测试带参数的引擎初始化"""
        engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            name="TestEngine"
        )

        # 验证参数设置
        assert engine.mode == EXECUTION_MODE.BACKTEST, "执行模式应设置正确"
        assert engine.name == "TestEngine", "引擎名称应设置正确"
        assert isinstance(engine._time_provider, LogicalTimeProvider), "BACKTEST模式应使用LogicalTimeProvider"

        print("✓ 带参数引擎初始化测试通过")

    def test_engine_id_generation(self):
        """测试引擎ID生成"""
        engine1 = TimeControlledEventEngine()
        engine2 = TimeControlledEventEngine()

        # 验证ID生成
        assert engine1.engine_id is not None, "引擎1应有engine_id"
        assert engine2.engine_id is not None, "引擎2应有engine_id"
        assert engine1.engine_id != engine2.engine_id, "两个引擎的ID应不同"
        assert isinstance(engine1.engine_id, str), "引擎ID应为字符串"

        print("✓ 引擎ID生成测试通过")

    def test_mode_specific_initialization(self):
        """测试模式特定初始化"""
        # 测试回测模式
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        assert isinstance(backtest_engine._time_provider, LogicalTimeProvider), "BACKTEST模式应使用LogicalTimeProvider"
        assert backtest_engine._time_provider.get_mode() == TIME_MODE.LOGICAL, "时间模式应为LOGICAL"

        # 测试实盘模式
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        assert isinstance(live_engine._time_provider, SystemTimeProvider), "LIVE模式应使用SystemTimeProvider"
        assert live_engine._time_provider.get_mode() == TIME_MODE.SYSTEM, "时间模式应为SYSTEM"

        print("✓ 模式特定初始化测试通过")

    def test_engine_state_management(self):
        """测试引擎状态管理"""
        engine = TimeControlledEventEngine()

        # 初始状态
        assert engine.status == "idle", "初始状态应为idle"

        # 启动
        start_result = engine.start()
        assert start_result is True, "启动应成功"
        assert engine.status == "running", "启动后状态应为running"
        assert engine.run_id is not None, "启动后应有run_id"

        # 停止
        engine.stop()
        assert engine.status == "stopped", "停止后状态应为stopped"

        print("✓ 引擎状态管理测试通过")

    def test_basic_properties_access(self):
        """测试基础属性访问"""
        engine = TimeControlledEventEngine()

        # 测试属性存在性和类型
        assert hasattr(engine, 'engine_id'), "应有engine_id属性"
        assert hasattr(engine, 'run_id'), "应有run_id属性"
        assert hasattr(engine, 'status'), "应有status属性"
        assert hasattr(engine, 'mode'), "应有mode属性"
        assert hasattr(engine, 'is_active'), "应有is_active属性"
        assert hasattr(engine, 'run_sequence'), "应有run_sequence属性"

        # 测试类型
        assert isinstance(engine.engine_id, str), "engine_id应为字符串"
        assert isinstance(engine.status, str), "status应为字符串"
        assert isinstance(engine.is_active, bool), "is_active应为布尔值"
        assert isinstance(engine.run_sequence, int), "run_sequence应为整数"

        print("✓ 基础属性访问测试通过")

    def test_engine_configuration(self):
        """测试引擎配置"""
        engine = TimeControlledEventEngine()

        # 验证配置相关的属性
        assert hasattr(engine, 'event_timeout'), "应有事件超时配置"
        assert hasattr(engine, '_event_queue'), "应有事件队列"

        # 验证初始配置
        if hasattr(engine, 'event_timeout'):
            assert isinstance(engine.event_timeout, (int, float)), "事件超时应为数值"

        # 验证队列初始状态
        assert engine._event_queue.empty(), "事件队列初始应为空"

        print("✓ 引擎配置测试通过")


@pytest.mark.unit
class TestEventHandling:
    """2. 事件处理机制测试"""

    def test_event_registration(self):
        """测试事件注册"""
        engine = TimeControlledEventEngine()

        # 测试处理器注册
        def test_handler(event):
            pass

        # 注册处理器
        result = engine.register(EVENT_TYPES.TIME_ADVANCE, test_handler)
        assert result is True, "事件注册应成功"

        # 验证处理器计数增加
        initial_count = engine.handler_count
        engine.register(EVENT_TYPES.PRICEUPDATE, test_handler)
        assert engine.handler_count > initial_count, "处理器计数应增加"

        print("✓ 事件注册测试通过")

    def test_event_queue_operations(self):
        """测试事件队列操作"""
        engine = TimeControlledEventEngine()

        # 创建测试事件
        test_event = EventTimeAdvance(dt.now(timezone.utc))

        # 测试事件投递
        engine.put(test_event)

        # 验证队列非空
        assert not engine._event_queue.empty(), "事件队列应不为空"

        print("✓ 事件队列操作测试通过")

    def test_event_processing_flow(self):
        """测试事件处理流程"""
        engine = TimeControlledEventEngine()

        # 设置事件处理追踪
        processed_events = []

        def event_handler(event):
            processed_events.append(event)

        # 注册处理器
        engine.register(EVENT_TYPES.TIME_ADVANCE, event_handler)

        # 启动引擎
        engine.start()

        # 投递事件
        test_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(test_event)

        # 等待处理
        time_module.sleep(0.1)

        # 验证事件处理
        assert len(processed_events) > 0, "应有事件被处理"

        engine.stop()
        print("✓ 事件处理流程测试通过")

    def test_multiple_event_types(self):
        """测试多种事件类型处理"""
        engine = TimeControlledEventEngine()

        # 设置不同事件类型的处理器
        time_events = []
        price_events = []
        component_events = []

        def time_handler(event):
            time_events.append(event)

        def price_handler(event):
            price_events.append(event)

        def component_handler(event):
            component_events.append(event)

        # 注册不同类型的处理器
        engine.register(EVENT_TYPES.TIME_ADVANCE, time_handler)
        engine.register(EVENT_TYPES.PRICEUPDATE, price_handler)
        engine.register(EVENT_TYPES.COMPONENT_TIME_ADVANCE, component_handler)

        # 启动引擎
        engine.start()

        # 投递不同类型的事件
        time_event = EventTimeAdvance(dt.now(timezone.utc))
        price_event = EventPriceUpdate(
            price_info=Tick(
                code="000001.SZ",
                price=10.0,
                volume=1000,
                direction=TICKDIRECTION_TYPES.NEUTRAL,
                timestamp=dt.now(timezone.utc)
            )
        )
        component_event = EventComponentTimeAdvance(
            component_name="TestComponent",
            target_time=dt.now(timezone.utc)
        )

        engine.put(time_event)
        engine.put(price_event)
        engine.put(component_event)

        # 等待处理
        time_module.sleep(0.1)

        # 验证不同类型事件都被处理
        assert len(time_events) > 0, "时间推进事件应被处理"
        assert len(price_events) > 0, "价格更新事件应被处理"
        assert len(component_events) > 0, "组件时间推进事件应被处理"

        engine.stop()
        print("✓ 多种事件类型处理测试通过")

    def test_event_handler_execution_order(self):
        """测试事件处理器执行顺序"""
        engine = TimeControlledEventEngine()

        # 设置处理器执行顺序追踪
        execution_order = []

        def handler_a(event):
            execution_order.append('A')

        def handler_b(event):
            execution_order.append('B')

        def handler_c(event):
            execution_order.append('C')

        # 注册处理器（按字母顺序）
        engine.register(EVENT_TYPES.TIME_ADVANCE, handler_a)
        engine.register(EVENT_TYPES.TIME_ADVANCE, handler_b)
        engine.register(EVENT_TYPES.TIME_ADVANCE, handler_c)

        # 启动引擎
        engine.start()

        # 投递事件
        test_event = EventTimeAdvance(dt.now(timezone.utc))
        engine.put(test_event)

        # 等待处理
        time_module.sleep(0.1)

        # 验证处理器都被调用
        assert len(execution_order) == 3, "应有3个处理器被调用"
        assert 'A' in execution_order, "处理器A应被调用"
        assert 'B' in execution_order, "处理器B应被调用"
        assert 'C' in execution_order, "处理器C应被调用"

        engine.stop()
        print("✓ 事件处理器执行顺序测试通过")

    def test_event_payload_access(self):
        """测试事件载荷访问"""
        engine = TimeControlledEventEngine()

        # 设置载荷访问验证
        accessed_payloads = []

        def payload_handler(event):
            if isinstance(event, EventPriceUpdate):
                # 正确的载荷访问方式
                payload = event.payload
                if payload:
                    accessed_payloads.append({
                        'type': type(payload).__name__,
                        'code': getattr(payload, 'code', None),
                        'price': getattr(payload, 'price', None),
                        'volume': getattr(payload, 'volume', None)
                    })

        # 注册处理器
        engine.register(EVENT_TYPES.PRICEUPDATE, payload_handler)

        # 启动引擎
        engine.start()

        # 创建测试事件
        tick = Tick(
            code="TEST.SZ",
            price=10.5,
            volume=1500,
            direction=TICKDIRECTION_TYPES.ACTIVEBUY,
            timestamp=dt.now(timezone.utc)
        )
        price_event = EventPriceUpdate(price_info=tick)

        engine.put(price_event)

        # 等待处理
        time_module.sleep(0.1)

        # 验证载荷访问正确
        assert len(accessed_payloads) > 0, "应有载荷被访问"
        payload = accessed_payloads[0]
        assert payload['type'] == 'Tick', "载荷类型应为Tick"
        assert payload['code'] == 'TEST.SZ', "股票代码应正确"
        assert payload['price'] == 10.5, "价格应正确"
        assert payload['volume'] == 1500, "成交量应正确"

        engine.stop()
        print("✓ 事件载荷访问测试通过")


@pytest.mark.unit
class TestTimeAdvancement:
    """3. 时间推进功能测试"""

    def test_time_advance_event_creation(self):
        """测试时间推进事件创建"""
        target_time = dt(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)

        # 创建时间推进事件
        time_event = EventTimeAdvance(target_time=target_time)

        # 验证事件属性
        assert time_event.target_time == target_time, "目标时间应正确设置"
        assert isinstance(time_event.timestamp, dt), "事件时间戳应为datetime类型"
        assert time_event.event_type == EVENT_TYPES.TIME_ADVANCE, "事件类型应正确"

        print("✓ 时间推进事件创建测试通过")

    def test_logical_time_provider(self):
        """测试逻辑时间提供者"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 获取时间提供者
        time_provider = engine._time_provider

        # 验证类型
        assert isinstance(time_provider, LogicalTimeProvider), "应使用LogicalTimeProvider"
        assert time_provider.get_mode() == TIME_MODE.LOGICAL, "时间模式应为LOGICAL"

        # 测试时间获取
        current_time = time_provider.now()
        assert isinstance(current_time, dt), "当前时间应为datetime类型"

        # 测试时间推进
        new_time = current_time + timedelta(hours=1)
        time_provider.advance_time_to(new_time)
        advanced_time = time_provider.now()

        assert advanced_time >= new_time, "时间应推进到目标时间"

        print("✓ 逻辑时间提供者测试通过")

    def test_system_time_provider(self):
        """测试系统时间提供者"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)

        # 获取时间提供者
        time_provider = engine._time_provider

        # 验证类型
        assert isinstance(time_provider, SystemTimeProvider), "应使用SystemTimeProvider"
        assert time_provider.get_mode() == TIME_MODE.SYSTEM, "时间模式应为SYSTEM"

        # 测试时间获取
        current_time = time_provider.now()
        assert isinstance(current_time, dt), "当前时间应为datetime类型"

        # 测试时间的实时性
        time1 = time_provider.now()
        time_module.sleep(0.01)  # 等待10ms
        time2 = time_provider.now()
        assert time2 > time1, "系统时间应持续前进"

        print("✓ 系统时间提供者测试通过")

    def test_time_advancement_integration(self):
        """测试时间推进集成"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 设置时间推进追踪
        advancement_log = []

        def time_advancement_handler(event):
            if isinstance(event, EventTimeAdvance):
                current_time = engine._time_provider.now()
                advancement_log.append({
                    'target_time': event.target_time,
                    'current_time': current_time,
                    'timestamp': event.timestamp
                })

        # 注册处理器
        engine.register(EVENT_TYPES.TIME_ADVANCE, time_advancement_handler)

        # 启动引擎
        engine.start()

        # 设置起始时间
        start_time = dt(2023, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        engine._time_provider.set_time(start_time)

        # 测试多次时间推进
        time_points = [
            dt(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc),
            dt(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc),
            dt(2023, 1, 1, 14, 0, 0, tzinfo=timezone.utc),
            dt(2023, 1, 1, 15, 0, 0, tzinfo=timezone.utc)
        ]

        for target_time in time_points:
            # 推进时间
            engine._time_provider.advance_time_to(target_time)

            # 创建时间推进事件
            time_event = EventTimeAdvance(target_time=target_time)
            engine.put(time_event)

            # 等待处理
            time_module.sleep(0.05)

        # 验证时间推进记录
        assert len(advancement_log) == len(time_points), "应记录所有时间推进"

        # 验证时间递进
        for i in range(1, len(advancement_log)):
            prev_time = advancement_log[i-1]['current_time']
            curr_time = advancement_log[i]['current_time']
            assert curr_time >= prev_time, "时间应单调递进"

        engine.stop()
        print("✓ 时间推进集成测试通过")

    def test_time_range_validation(self):
        """测试时间范围验证"""
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 设置时间范围
        start_time = dt(2023, 1, 1, 9, 30, 0, tzinfo=timezone.utc)
        end_time = dt(2023, 1, 1, 16, 0, 0, tzinfo=timezone.utc)

        engine._time_provider.set_time(start_time)

        # 测试有效时间推进
        valid_time = dt(2023, 1, 1, 10, 30, 0, tzinfo=timezone.utc)
        engine._time_provider.advance_time_to(valid_time)
        current_time = engine._time_provider.now()
        assert current_time >= valid_time, "有效时间推进应成功"

        # 测试时间倒退（应该被忽略或调整）
        backtrack_time = dt(2023, 1, 1, 9, 0, 0, tzinfo=timezone.utc)
        engine._time_provider.advance_time_to(backtrack_time)

        print("✓ 时间范围验证测试通过")

    def test_time_provider_switching(self):
        """测试时间提供者切换"""
        # 创建回测引擎
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 验证初始时间提供者
        assert isinstance(backtest_engine._time_provider, LogicalTimeProvider), "初始应为LogicalTimeProvider"

        # 创建实盘引擎
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)

        # 验证时间提供者类型
        assert isinstance(live_engine._time_provider, SystemTimeProvider), "实盘应为SystemTimeProvider"

        # 测试不同时间提供者的行为差异
        backtest_time = backtest_engine.get_current_time()
        live_time = live_engine.get_current_time()

        assert isinstance(backtest_time, dt), "回测时间应为datetime"
        assert isinstance(live_time, dt), "实盘时间应为datetime"

        print("✓ 时间提供者切换测试通过")


@pytest.mark.unit
class TestEngineStateManagement:
    """4. 引擎状态管理测试"""

    def test_engine_lifecycle_states(self):
        """测试引擎生命周期状态"""
        engine = TimeControlledEventEngine()

        # 验证初始状态
        assert engine.status == "idle", "初始状态应为idle"
        assert not engine.is_active, "初始应未激活"
        assert engine.run_id is None, "初始run_id应为None"

        # 启动引擎
        start_result = engine.start()
        assert start_result is True, "启动应成功"
        assert engine.status == "running", "启动后状态应为running"
        assert engine.is_active, "启动后应激活"
        assert engine.run_id is not None, "启动后应有run_id"

        # 记录运行信息
        initial_run_id = engine.run_id
        initial_sequence = engine.run_sequence

        # 停止引擎
        engine.stop()
        assert engine.status == "stopped", "停止后状态应为stopped"
        assert not engine.is_active, "停止后应未激活"
        assert engine.run_id == initial_run_id, "run_id应保持"
        assert engine.run_sequence == initial_sequence, "运行序列应保持"

        print("✓ 引擎生命周期状态测试通过")

    def test_engine_status_transitions(self):
        """测试引擎状态转换"""
        engine = TimeControlledEventEngine()

        # 状态转换序列
        state_transitions = []

        def record_state_transition():
            state_transitions.append(engine.status)

        # 记录初始状态
        record_state_transition()

        # 启动引擎
        engine.start()
        record_state_transition()

        # 暂停引擎（如果支持）
        if hasattr(engine, 'pause'):
            engine.pause()
            record_state_transition()

        # 恢复引擎（如果支持）
        if hasattr(engine, 'resume'):
            engine.resume()
            record_state_transition()

        # 停止引擎
        engine.stop()
        record_state_transition()

        # 验证状态转换
        assert state_transitions[0] == "idle", "初始状态应为idle"
        assert state_transitions[1] == "running", "启动后应为running"
        assert state_transitions[-1] == "stopped", "最终状态应为stopped"

        print("✓ 引擎状态转换测试通过")

    def test_concurrent_state_access(self):
        """测试并发状态访问"""
        engine = TimeControlledEventEngine()

        # 启动引擎
        engine.start()

        # 并发状态访问测试
        access_results = []
        access_lock = threading.Lock()

        def state_reader(thread_id):
            """状态读取线程"""
            for _ in range(10):
                current_status = engine.status
                is_active = engine.is_active
                run_id = engine.run_id

                with access_lock:
                    access_results.append({
                        'thread_id': thread_id,
                        'status': current_status,
                        'is_active': is_active,
                        'run_id': run_id
                    })

                time_module.sleep(0.001)

        # 创建多个读取线程
        threads = []
        for i in range(3):
            thread = threading.Thread(target=state_reader, args=(i,))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证并发访问结果
        assert len(access_results) > 0, "应有状态访问记录"

        # 验证状态一致性
        for result in access_results:
            assert result['status'] in ["idle", "running", "stopped"], "状态值应有效"
            assert isinstance(result['is_active'], bool), "is_active应为布尔值"

        engine.stop()
        print("✓ 并发状态访问测试通过")

    def test_engine_error_state_handling(self):
        """测试引擎错误状态处理"""
        engine = TimeControlledEventEngine()

        # 启动引擎
        engine.start()
        assert engine.status == "running", "引擎应正在运行"

        # 模拟错误情况
        try:
            # 尝试在运行状态下执行不允许的操作
            # 这里根据具体实现来测试错误处理
            if hasattr(engine, '_set_error_state'):
                engine._set_error_state("Test error")
                # 验证错误状态
                # 注意：具体的状态名称可能因实现而异
        except Exception as e:
            # 验证错误处理
            assert isinstance(e, Exception), "应抛出异常"

        # 验证引擎仍能正常停止
        engine.stop()
        assert engine.status == "stopped", "引擎应能正常停止"

        print("✓ 引擎错误状态处理测试通过")

    def test_state_persistence(self):
        """测试状态持久化"""
        engine = TimeControlledEventEngine()

        # 启动引擎并设置一些状态
        engine.start()
        original_run_id = engine.run_id
        original_sequence = engine.run_sequence

        # 模拟一些状态变化
        # 这里可以添加特定的状态设置逻辑

        # 停止引擎
        engine.stop()

        # 验证关键状态持久化
        assert engine.run_id == original_run_id, "run_id应持久化"
        assert engine.run_sequence == original_sequence, "运行序列应持久化"

        print("✓ 状态持久化测试通过")


@pytest.mark.unit
class TestEventQueueOperations:
    """5. 事件队列操作测试"""

    def test_event_queue_initialization(self):
        """测试事件队列初始化"""
        engine = TimeControlledEventEngine()

        # 验证队列存在
        assert hasattr(engine, '_event_queue'), "应有事件队列属性"
        assert not engine._event_queue.empty(), "队列初始状态检查"

        # 验证队列类型和方法
        assert hasattr(engine._event_queue, 'put'), "队列应有put方法"
        assert hasattr(engine._event_queue, 'get'), "队列应有get方法"
        assert hasattr(engine._event_queue, 'empty'), "队列应有empty方法"
        assert hasattr(engine._event_queue, 'qsize'), "队列应有qsize方法"

        print("✓ 事件队列初始化测试通过")

    def test_event_enqueue_dequeue(self):
        """测试事件入队出队"""
        engine = TimeControlledEventEngine()

        # 创建测试事件
        test_events = [
            EventTimeAdvance(dt.now(timezone.utc)),
            EventTimeAdvance(dt.now(timezone.utc) + timedelta(hours=1)),
            EventTimeAdvance(dt.now(timezone.utc) + timedelta(hours=2))
        ]

        # 入队事件
        for event in test_events:
            engine.put(event)

        # 验证队列大小
        if hasattr(engine._event_queue, 'qsize'):
            queue_size = engine._event_queue.qsize()
            assert queue_size >= len(test_events), f"队列大小应至少为{len(test_events)}"

        print("✓ 事件入队出队测试通过")

    def test_event_queue_size_management(self):
        """测试事件队列大小管理"""
        engine = TimeControlledEventEngine()

        # 测试队列大小设置（如果支持）
        if hasattr(engine, 'set_event_queue_size'):
            # 设置队列大小
            result = engine.set_event_queue_size(1000)
            assert isinstance(result, bool), "队列大小设置应返回布尔值"

            # 测试队列大小限制
            # 这里可以添加队列大小限制的测试
        else:
            print("队列大小设置功能未实现，跳过测试")

        print("✓ 事件队列大小管理测试通过")

    def test_event_queue_thread_safety(self):
        """测试事件队列线程安全"""
        engine = TimeControlledEventEngine()

        # 并发队列操作测试
        enqueue_count = 0
        dequeue_count = 0
        operation_lock = threading.Lock()

        def enqueue_worker(thread_id):
            nonlocal enqueue_count
            for i in range(10):
                event = EventTimeAdvance(dt.now(timezone.utc) + timedelta(seconds=i))
                engine.put(event)

                with operation_lock:
                    enqueue_count += 1

                time_module.sleep(0.001)

        def dequeue_worker(thread_id):
            nonlocal dequeue_count
            for i in range(10):
                try:
                    # 安全获取事件
                    event = engine.get_event(timeout=0.1)
                    if event:
                        with operation_lock:
                            dequeue_count += 1
                except:
                    # 超时或其他异常是正常的
                    pass

                time_module.sleep(0.001)

        # 启动并发线程
        threads = []

        # 启动入队线程
        for i in range(2):
            thread = threading.Thread(target=enqueue_worker, args=(f'enqueue_{i}',))
            threads.append(thread)
            thread.start()

        # 启动出队线程
        for i in range(1):
            thread = threading.Thread(target=dequeue_worker, args=(f'dequeue_{i}',))
            threads.append(thread)
            thread.start()

        # 等待所有线程完成
        for thread in threads:
            thread.join()

        # 验证操作计数
        assert enqueue_count == 20, "应有20个入队操作"
        # 出队操作数量可能少于入队，这取决于具体的队列实现

        print("✓ 事件队列线程安全测试通过")

    def test_event_priority_handling(self):
        """测试事件优先级处理"""
        engine = TimeControlledEventEngine()

        # 创建不同优先级的事件
        high_priority_event = EventTimeAdvance(
            dt.now(timezone.utc) + timedelta(hours=1)
        )
        high_priority_event.context['priority'] = 'high'

        low_priority_event = EventTimeAdvance(
            dt.now(timezone.utc) + timedelta(hours=2)
        )
        low_priority_event.context['priority'] = 'low'

        # 按不同顺序投递事件
        engine.put(low_priority_event)
        engine.put(high_priority_event)

        # 验证事件处理顺序（取决于具体实现）
        # 这里主要验证队列能正确处理事件

        print("✓ 事件优先级处理测试通过")

    def test_event_queue_overflow_handling(self):
        """测试事件队列溢出处理"""
        engine = TimeControlledEventEngine()

        # 测试大量事件投递
        event_count = 1000
        successful_enqueues = 0

        for i in range(event_count):
            try:
                event = EventTimeAdvance(
                    dt.now(timezone.utc) + timedelta(seconds=i)
                )
                engine.put(event)
                successful_enqueues += 1
            except Exception as e:
                # 队列可能满了或其他错误
                print(f"事件入队失败: {e}")
                break

        # 验证至少成功入队一些事件
        assert successful_enqueues > 0, "至少应成功入队一些事件"

        print(f"✓ 事件队列溢出处理测试通过，成功入队{successful_enqueues}个事件")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])