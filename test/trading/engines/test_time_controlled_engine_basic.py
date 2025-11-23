"""
TimeControlledEngine基础功能测试

包含引擎的构造、属性、配置管理、数据设置和验证功能测试。
这部分测试专注于引擎的基础功能和配置。
"""
import pytest
import sys
import pytz
from datetime import datetime as dt, time, timezone, timedelta
from pathlib import Path
import time as time_module
import threading
from unittest.mock import Mock

# 添加项目路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ginkgo.trading.engines.time_controlled_engine import (
    TimeControlledEventEngine,
)
from ginkgo.enums import EXECUTION_MODE, ENGINESTATUS_TYPES
from ginkgo.trading.engines.event_engine import EventEngine
from ginkgo.trading.time.interfaces import ITimeProvider, ITimeAwareComponent
from ginkgo.trading.time.providers import LogicalTimeProvider, SystemTimeProvider
from ginkgo.trading.events.base_event import EventBase
from ginkgo.trading.events.time_advance import EventTimeAdvance
from ginkgo.trading.events.price_update import EventPriceUpdate
from ginkgo.enums import EVENT_TYPES, TIME_MODE, TICKDIRECTION_TYPES, FREQUENCY_TYPES
from ginkgo.libs import GLOG
from ginkgo.trading.entities.tick import Tick
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.core.status import EngineStatus, EventStats, QueueInfo, TimeInfo, ComponentSyncInfo


def safe_get_event(engine, timeout=0.1):
    """安全获取事件，避免queue.Empty异常"""
    try:
        return engine.get_event(timeout=timeout)
    except Exception:
        return None


@pytest.mark.unit
class TestTimeControlledEngineConstruction:
    """1. 构造和初始化测试"""

    def test_default_constructor(self):
        """测试TimeControlledEngine默认构造函数（使用公共接口）

        场景：使用默认参数创建TimeControlledEngine
        预期：
        - 引擎正确初始化基类组件
        - 根据默认模式(BACKTEST)创建LogicalTimeProvider
        - 引擎状态为Idle
        - BACKTEST模式下不创建并发控制组件
        """
        # 创建引擎
        engine = TimeControlledEventEngine()

        # 验证基础属性（使用公共接口）
        assert engine.name == "TimeControlledEngine", "默认引擎名称应为'TimeControlledEngine'"
        assert engine.mode == EXECUTION_MODE.BACKTEST, "默认模式应为BACKTEST"

        # 使用公共查询接口验证引擎状态
        engine_status = engine.get_engine_status()
        assert engine_status.status == ENGINESTATUS_TYPES.IDLE, "新创建的引擎状态应为IDLE"
        assert engine_status.execution_mode == EXECUTION_MODE.BACKTEST, "执行模式应为BACKTEST"
        assert engine_status.processed_events == 0, "初始处理事件数应为0"

        # 使用公共时间信息接口验证时间提供者
        time_info = engine.get_time_info()
        assert time_info.is_logical_time == True, "BACKTEST模式应使用逻辑时间"
        assert time_info.time_mode == TIME_MODE.LOGICAL, "时间模式应为LOGICAL"
        assert time_info.time_provider_type == "LogicalTimeProvider", "应创建LogicalTimeProvider"
        assert time_info.current_time is not None, "当前时间不应为空"

        # 使用时间提供者详细信息接口
        provider_info = engine.get_time_provider_info()
        assert provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert provider_info['is_logical_time'] == True, "应为逻辑时间"
        assert provider_info['supports_time_control'] == True, "应支持时间控制"
        assert provider_info['mode'] == EXECUTION_MODE.BACKTEST.value, "模式应为BACKTEST"

        # 验证队列信息（使用公共接口）
        queue_info = engine.get_queue_info()
        assert queue_info.is_empty == True, "初始队列应为空"
        assert queue_info.queue_size == 0, "初始队列大小应为0"

        # 验证事件统计（使用公共接口）
        event_stats = engine.get_event_stats()
        assert event_stats.processed_events == 0, "初始处理事件数应为0"
        assert event_stats.registered_handlers >= 0, "已注册处理器数应非负"

        print(f"✓ 引擎初始化验证完成: {engine.name}")
        print(f"  - 状态: {engine_status.status}")
        print(f"  - 时间模式: {time_info.time_mode}")
        print(f"  - 时间提供者: {time_info.time_provider_type}")
        print(f"  - 队列状态: {queue_info.queue_size}/{queue_info.max_size}")

    def test_custom_config_constructor(self):
        """测试TimeControlledEngine自定义参数构造（使用公共接口）

        场景：使用自定义name和timer_interval参数创建引擎
        预期：
        - 引擎使用提供的名称和timer_interval
        - 验证参数正确传递到父类
        - 默认BACKTEST模式下正确初始化组件
        """
        # 使用自定义参数创建引擎
        custom_name = "MyCustomEngine"
        custom_timer_interval = 2.5
        engine = TimeControlledEventEngine(
            name=custom_name,
            timer_interval=custom_timer_interval,
            mode=EXECUTION_MODE.BACKTEST
        )

        # 验证自定义参数被正确应用
        assert engine.name == custom_name, "自定义引擎名称应生效"
        assert engine.mode == EXECUTION_MODE.BACKTEST, "模式应为BACKTEST"

        # 使用公共接口验证引擎状态
        engine_status = engine.get_engine_status()
        assert engine_status.execution_mode == EXECUTION_MODE.BACKTEST, "执行模式应为BACKTEST"
        assert engine_status.status == ENGINESTATUS_TYPES.IDLE, "引擎状态应为IDLE"

        # 使用时间信息接口验证时间提供者
        time_info = engine.get_time_info()
        assert time_info.time_provider_type == "LogicalTimeProvider", "BACKTEST模式应创建LogicalTimeProvider"
        assert time_info.is_logical_time == True, "应使用逻辑时间"

        # 使用时间提供者详细信息接口验证配置
        provider_info = engine.get_time_provider_info()
        assert provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert provider_info['mode'] == EXECUTION_MODE.BACKTEST.value, "模式应为BACKTEST"

        print(f"✓ 自定义引擎验证完成: {engine.name}")
        print(f"  - 执行模式: {engine_status.execution_mode}")
        print(f"  - 时间提供者: {time_info.time_provider_type}")
        print(f"  - 引擎状态: {engine_status.status}")

    def test_backtest_mode_constructor(self):
        """测试TimeControlledEngine回测模式构造

        场景：显式创建BACKTEST模式的引擎
        预期：
        - 创建LogicalTimeProvider
        - 不创建并发控制组件
        - 引擎配置为回测模式
        """
        # 显式创建BACKTEST模式引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 验证模式设置
        assert engine.mode == EXECUTION_MODE.BACKTEST, "模式应为BACKTEST"
        assert engine.status == "idle", "引擎状态应为idle"

        # 验证时间提供者
        assert isinstance(engine._time_provider, LogicalTimeProvider), "BACKTEST模式应创建LogicalTimeProvider"

        # 验证无并发控制组件
        assert engine._executor is None, "BACKTEST模式不应有线程池"
        assert engine._concurrent_semaphore is None, "BACKTEST模式不应有信号量"

        # 验证增强处理创建
        assert engine._enhanced_processing_enabled is not None, "增强处理应被启用"

    def test_live_mode_constructor(self):
        """测试TimeControlledEngine实盘模式构造函数

        场景：创建LIVE模式的TimeControlledEngine
        预期：
        - 引擎正确初始化为LIVE模式
        - 创建SystemTimeProvider
        - 创建并发控制组件（ThreadPoolExecutor和Semaphore）
        - 引擎状态为Idle
        """
        # 创建LIVE模式引擎
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)

        # 验证基础属性
        assert engine.name == "TimeControlledEngine", "引擎名称应为'TimeControlledEngine'"
        assert engine.mode == EXECUTION_MODE.LIVE, "模式应为LIVE"
        assert engine.status == "idle", "新创建的引擎状态应为idle"

        # 验证时间提供者（实盘模式使用SystemTimeProvider）
        assert engine._time_provider is not None, "时间提供者应该被创建"
        assert isinstance(engine._time_provider, SystemTimeProvider), "LIVE模式应创建SystemTimeProvider"

        # 验证并发控制组件（LIVE模式需要）
        assert engine._executor is not None, "LIVE模式需要线程池"
        assert engine._concurrent_semaphore is not None, "LIVE模式需要并发信号量"

        # 验证线程池配置
        from concurrent.futures import ThreadPoolExecutor
        assert isinstance(engine._executor, ThreadPoolExecutor), "应创建ThreadPoolExecutor"
        assert engine._executor._max_workers > 1, "LIVE模式线程池应支持多线程"

        # 验证信号量配置
        import threading
        assert isinstance(engine._concurrent_semaphore, threading.Semaphore), "应创建Semaphore"
        assert engine._concurrent_semaphore._value > 1, "LIVE模式信号量应支持并发"

        # 验证引擎模式
        assert engine.mode == EXECUTION_MODE.LIVE, "引擎模式应为LIVE"

    def test_event_engine_inheritance(self):
        """测试TimeControlledEngine的EventEngine继承功能

        场景：验证TimeControlledEngine正确继承EventEngine
        预期：
        - 是EventEngine的实例
        - 具有EventEngine的核心方法
        - 可以注册事件处理器
        - 具有事件队列功能
        """
        # 创建引擎
        engine = TimeControlledEventEngine()

        # 验证继承关系
        assert isinstance(engine, EventEngine), "TimeControlledEngine应继承EventEngine"

        # 验证EventEngine核心功能可用
        assert hasattr(engine, 'register'), "应有register方法"
        assert hasattr(engine, 'unregister'), "应有unregister方法"
        assert hasattr(engine, 'put'), "应有put方法"
        assert hasattr(engine, 'start'), "应有start方法"
        assert hasattr(engine, 'stop'), "应有stop方法"

        # 验证事件队列
        assert hasattr(engine, '_event_queue'), "应有事件队列"
        assert engine._event_queue is not None, "事件队列不应为空"

        # 验证事件处理器注册功能
        def dummy_handler(event):
            pass

        # 测试注册处理器（使用TIME_ADVANCE事件，因为引擎会自动注册）
        from ginkgo.enums import EVENT_TYPES
        success = engine.register(EVENT_TYPES.TIME_ADVANCE, dummy_handler)
        assert isinstance(success, bool), "register应返回布尔值"

        # 验证处理器计数
        assert engine.handler_count >= 1, "至少应有time_advance处理器"


@pytest.mark.unit
class TestTimeControlledEngineProperties:
    """2. 属性访问测试"""

    def test_execution_mode_property(self):
        """测试执行模式属性
        验证execution_mode属性的读取功能，确认返回的枚举值类型。
        """
        engine = TimeControlledEventEngine()

        # 测试默认值
        assert engine.mode == EXECUTION_MODE.BACKTEST, "默认执行模式应为BACKTEST"

        # 测试设置值
        engine.mode = EXECUTION_MODE.LIVE
        assert engine.mode == EXECUTION_MODE.LIVE, "设置后执行模式应为LIVE"

        engine.mode = EXECUTION_MODE.PAPER
        assert engine.mode == EXECUTION_MODE.PAPER, "设置后执行模式应为PAPER"

    def test_config_property(self):
        """测试配置属性
        验证config属性的读取功能，包含引擎的完整配置信息。
        """
        engine = TimeControlledEventEngine()

        # 验证config属性存在并可访问
        config = engine.config
        assert config is not None, "config属性不应为None"

        # 验证config包含基本信息
        assert hasattr(config, 'name'), "config应包含name字段"
        assert hasattr(config, 'mode'), "config应包含mode字段"
        assert hasattr(config, 'timer_interval'), "config应包含timer_interval字段"

        # 验证基本配置值
        assert config.name == "TimeControlledEngine", "config.name应正确"
        assert config.mode == EXECUTION_MODE.BACKTEST, "config.mode应为BACKTEST"

    def test_time_provider_property(self):
        """测试时间提供者属性
        验证time_provider属性的正确设置和类型。
        """
        # 测试BACKTEST模式
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        assert isinstance(backtest_engine._time_provider, LogicalTimeProvider), "BACKTEST模式应使用LogicalTimeProvider"

        # 测试LIVE模式
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        assert isinstance(live_engine._time_provider, SystemTimeProvider), "LIVE模式应使用SystemTimeProvider"

        # 测试PAPER模式
        paper_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.PAPER)
        assert isinstance(paper_engine._time_provider, LogicalTimeProvider), "PAPER模式应使用LogicalTimeProvider"

    def test_engine_state_tracking(self):
        """测试引擎状态跟踪功能
        验证引擎运行时状态的正确跟踪和更新。
        """
        engine = TimeControlledEventEngine()

        # 验证初始状态
        assert engine.status == "idle", "初始状态应为idle"

        # 验证状态变化（通过公共接口）
        engine.start()
        assert engine.status == "running", "启动后状态应为running"

        engine.pause()
        assert engine.status == "paused", "暂停后状态应为paused"

        engine.stop()
        assert engine.status == "stopped", "停止后状态应为stopped"

    def test_engine_id_property(self):
        """测试引擎ID属性
        验证engine_id的唯一性和格式。
        """
        engine1 = TimeControlledEventEngine()
        engine2 = TimeControlledEventEngine()

        # 验证ID唯一性
        assert engine1.engine_id != engine2.engine_id, "引擎ID应唯一"

        # 验证ID格式
        assert isinstance(engine1.engine_id, str), "引擎ID应为字符串类型"
        assert len(engine1.engine_id) > 0, "引擎ID不应为空"

        # 验证自定义engine_id
        custom_id = "custom_engine_123"
        engine3 = TimeControlledEventEngine(engine_id=custom_id)
        assert engine3.engine_id == custom_id, "自定义engine_id应生效"

    def test_run_id_property(self):
        """测试运行ID属性
        验证run_id的会话管理和唯一性。
        """
        engine = TimeControlledEventEngine()

        # 初始状态run_id应为None
        assert engine.run_id is None, "初始run_id应为None"

        # 启动引擎应生成run_id
        engine.start()
        assert engine.run_id is not None, "启动后应生成run_id"
        assert isinstance(engine.run_id, str), "run_id应为字符串类型"

        # 停止后run_id应保持
        current_run_id = engine.run_id
        engine.stop()
        assert engine.run_id == current_run_id, "停止后run_id应保持"

        # 重新启动应生成新run_id
        engine.start()
        assert engine.run_id != current_run_id, "重新启动应生成新run_id"


@pytest.mark.unit
class TestEngineConfigManagement:
    """3. 引擎配置管理测试"""

    def test_engine_config_creation(self):
        """测试引擎配置创建
        验证引擎配置的完整性和正确性。
        """
        engine = TimeControlledEventEngine(
            name="TestEngine",
            mode=EXECUTION_MODE.BACKTEST,
            timer_interval=2.0,
            event_queue_size=5000
        )

        # 验证配置通过公共接口可访问
        config = engine.config

        # 验证基本配置
        assert config.name == "TestEngine", "引擎名称应正确设置"
        assert config.mode == EXECUTION_MODE.BACKTEST, "执行模式应正确设置"
        assert config.timer_interval == 2.0, "定时器间隔应正确设置"

        # 验证队列配置
        queue_info = engine.get_queue_info()
        assert queue_info.max_size == 5000, "队列大小应正确设置"

    def test_execution_mode_configuration(self):
        """测试执行模式配置
        验证不同执行模式的配置差异。
        """
        # 测试BACKTEST模式配置
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        backtest_config = backtest_engine.config
        backtest_time_info = backtest_engine.get_time_info()

        assert backtest_config.mode == EXECUTION_MODE.BACKTEST, "BACKTEST模式配置应正确"
        assert backtest_time_info.is_logical_time == True, "BACKTEST模式应使用逻辑时间"
        assert backtest_time_info.time_provider_type == "LogicalTimeProvider", "时间提供者类型应正确"

        # 测试LIVE模式配置
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        live_config = live_engine.config
        live_time_info = live_engine.get_time_info()

        assert live_config.mode == EXECUTION_MODE.LIVE, "LIVE模式配置应正确"
        assert live_time_info.is_logical_time == False, "LIVE模式应使用系统时间"
        assert live_time_info.time_provider_type == "SystemTimeProvider", "时间提供者类型应正确"

        # 测试PAPER模式配置
        paper_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.PAPER)
        paper_config = paper_engine.config
        paper_time_info = paper_engine.get_time_info()

        assert paper_config.mode == EXECUTION_MODE.PAPER, "PAPER模式配置应正确"
        assert paper_time_info.is_logical_time == True, "PAPER模式应使用逻辑时间"

    def test_event_queue_size_configuration(self):
        """测试事件队列大小配置
        验证队列大小配置的动态调整功能。
        """
        # 测试默认队列大小
        default_engine = TimeControlledEventEngine()
        default_queue_info = default_engine.get_queue_info()
        assert default_queue_info.max_size == 10000, "默认队列大小应为10000"

        # 测试自定义队列大小
        custom_size = 5000
        custom_engine = TimeControlledEventEngine(event_queue_size=custom_size)
        custom_queue_info = custom_engine.get_queue_info()
        assert custom_queue_info.max_size == custom_size, "自定义队列大小应正确设置"

        # 测试队列大小调整
        new_size = 2000
        custom_engine.set_event_queue_size(new_size)
        adjusted_queue_info = custom_engine.get_queue_info()
        assert adjusted_queue_info.max_size == new_size, "调整后队列大小应正确"

    def test_timeout_configuration(self):
        """测试超时配置
        验证事件处理超时配置的有效性。
        """
        # 测试默认超时配置
        default_engine = TimeControlledEventEngine()
        assert default_engine.event_timeout == 10.0, "默认超时应为10秒"

        # 测试自定义超时配置
        custom_timeout = 5.0
        custom_engine = TimeControlledEventEngine(event_timeout=custom_timeout)
        assert custom_engine.event_timeout == custom_timeout, "自定义超时应正确设置"

        # 测试超时配置修改
        new_timeout = 15.0
        custom_engine.set_event_timeout(new_timeout)
        assert custom_engine.event_timeout == new_timeout, "修改后超时应正确"

    def test_max_concurrent_handlers_configuration(self):
        """测试最大并发处理器配置
        验证并发处理器数量限制配置。
        """
        # 测试BACKTEST模式（通常不需要并发限制）
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        # BACKTEST模式通常不需要并发处理器限制，或使用较小的值

        # 测试LIVE模式（需要并发处理器管理）
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        # 验证LIVE模式创建了并发控制组件
        assert live_engine._concurrent_semaphore is not None, "LIVE模式应有并发信号量"
        assert live_engine._executor is not None, "LIVE模式应有线程池"

    def test_logical_time_start_configuration(self):
        """测试逻辑时间开始配置
        验证回测模式下逻辑时间起始点的设置。
        """
        # 测试默认逻辑时间开始
        default_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        default_time_info = default_engine.get_time_info()
        assert default_time_info.logical_start_time is not None, "应有默认逻辑开始时间"

        # 测试自定义逻辑时间开始
        custom_start = dt(2023, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
        custom_engine = TimeControlledEventEngine(
            mode=EXECUTION_MODE.BACKTEST,
            logical_time_start=custom_start
        )
        custom_time_info = custom_engine.get_time_info()
        assert custom_time_info.logical_start_time == custom_start, "自定义逻辑开始时间应正确设置"

    def test_priority_configuration(self):
        """测试优先级配置
        验证事件处理优先级的设置和影响。
        """
        # 测试默认优先级
        default_engine = TimeControlledEventEngine()
        # 验证默认优先级设置（具体值取决于实现）

        # 测试自定义优先级
        custom_priority = 5
        custom_engine = TimeControlledEventEngine(priority=custom_priority)
        # 验证优先级配置（具体影响取决于实现）

    def test_metrics_configuration(self):
        """测试指标配置
        验证性能指标收集和报告的配置。
        """
        # 测试默认指标配置
        default_engine = TimeControlledEventEngine()

        # 验证基础统计功能通过公共接口可用
        event_stats = default_engine.get_event_stats()
        assert event_stats.processed_events >= 0, "应能获取处理事件数统计"
        assert event_stats.registered_handlers >= 0, "应能获取注册处理器统计"
        assert event_stats.queue_size >= 0, "应能获取队列大小统计"

        # 验证引擎状态信息
        engine_status = default_engine.get_engine_status()
        assert engine_status.processed_events >= 0, "引擎状态应包含处理事件数"
        assert engine_status.queue_size >= 0, "引擎状态应包含队列大小"


@pytest.mark.unit
class TestTimeControllerDataSetting:
    """4. 时间控制器数据设置测试"""

    def test_time_provider_initialization(self):
        """测试时间提供者初始化
        验证时间提供者的正确初始化和配置。
        """
        # 测试LogicalTimeProvider初始化
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        assert backtest_engine._time_provider is not None, "BACKTEST模式应有时间提供者"
        assert isinstance(backtest_engine._time_provider, LogicalTimeProvider), "BACKTEST模式应使用LogicalTimeProvider"

        # 测试SystemTimeProvider初始化
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        assert live_engine._time_provider is not None, "LIVE模式应有时间提供者"
        assert isinstance(live_engine._time_provider, SystemTimeProvider), "LIVE模式应使用SystemTimeProvider"

    def test_backtest_time_provider_setup(self):
        """测试回测时间提供者设置
        验证回测模式下时间提供者的特定配置。
        """
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)

        # 验证时间提供者类型
        assert isinstance(engine._time_provider, LogicalTimeProvider), "应使用LogicalTimeProvider"

        # 验证时间提供者状态
        time_info = engine.get_time_info()
        assert time_info.is_logical_time == True, "应标记为逻辑时间"
        assert time_info.time_mode == TIME_MODE.LOGICAL, "时间模式应为LOGICAL"

        # 验证时间提供者能力
        provider_info = engine.get_time_provider_info()
        assert provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert provider_info['supports_time_control'] == True, "应支持时间控制"
        assert provider_info['can_advance_time'] == True, "应支持时间推进"

    def test_live_time_provider_setup(self):
        """测试实盘时间提供者设置
        验证实盘模式下时间提供者的特定配置。
        """
        engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)

        # 验证时间提供者类型
        assert isinstance(engine._time_provider, SystemTimeProvider), "应使用SystemTimeProvider"

        # 验证时间提供者状态
        time_info = engine.get_time_info()
        assert time_info.is_logical_time == False, "应标记为实时时间"
        assert time_info.time_mode == TIME_MODE.SYSTEM, "时间模式应为SYSTEM"

        # 验证时间提供者能力
        provider_info = engine.get_time_provider_info()
        assert provider_info['is_initialized'] == True, "时间提供者应已初始化"
        assert provider_info['is_logical_time'] == False, "应标记为实时时间"
        assert provider_info['supports_time_control'] == True, "应支持时间控制接口"
        assert provider_info['can_advance_time'] == False, "实时模式不应支持手动时间推进"


@pytest.mark.unit
class TestTimeControllerValidation:
    """5. 时间控制器验证测试"""

    def test_execution_mode_enum_validation(self):
        """测试执行模式枚举验证
        验证执行模式枚举值的有效性和边界检查。
        """
        # 测试所有有效的执行模式
        valid_modes = [EXECUTION_MODE.BACKTEST, EXECUTION_MODE.LIVE, EXECUTION_MODE.PAPER]

        for mode in valid_modes:
            engine = TimeControlledEventEngine(mode=mode)
            assert engine.mode == mode, f"模式{mode}应正确设置"

        # 验证执行模式属性类型
        engine = TimeControlledEventEngine()
        assert isinstance(engine.mode, EXECUTION_MODE), "执行模式应为枚举类型"

    def test_time_mode_consistency(self):
        """测试时间模式一致性
        验证时间模式与执行模式的一致性关系。
        """
        # BACKTEST模式应使用逻辑时间
        backtest_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.BACKTEST)
        backtest_time_info = backtest_engine.get_time_info()
        assert backtest_time_info.time_mode == TIME_MODE.LOGICAL, "BACKTEST模式应使用LOGICAL时间"
        assert backtest_time_info.is_logical_time == True, "BACKTEST模式应标记为逻辑时间"

        # LIVE模式应使用系统时间
        live_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.LIVE)
        live_time_info = live_engine.get_time_info()
        assert live_time_info.time_mode == TIME_MODE.SYSTEM, "LIVE模式应使用SYSTEM时间"
        assert live_time_info.is_logical_time == False, "LIVE模式应标记为实时时间"

        # PAPER模式应使用逻辑时间
        paper_engine = TimeControlledEventEngine(mode=EXECUTION_MODE.PAPER)
        paper_time_info = paper_engine.get_time_info()
        assert paper_time_info.time_mode == TIME_MODE.LOGICAL, "PAPER模式应使用LOGICAL时间"
        assert paper_time_info.is_logical_time == True, "PAPER模式应标记为逻辑时间"

    def test_config_parameter_validation(self):
        """测试配置参数验证
        验证引擎配置参数的类型和边界检查。
        """
        # 测试有效的配置参数
        valid_configs = [
            {"name": "ValidEngine", "mode": EXECUTION_MODE.BACKTEST},
            {"timer_interval": 1.0, "event_queue_size": 1000, "event_timeout": 5.0}
        ]

        for config in valid_configs:
            engine = TimeControlledEventEngine(**config)
            assert engine is not None, "有效配置应能创建引擎"

        # 测试无效参数（具体行为取决于实现）
        # engine = TimeControlledEventEngine(timer_interval=-1.0)  # 可能抛出异常或自动修正

    def test_timeout_value_validation(self):
        """测试超时值验证
        验证超时时间设置的有效范围和边界值。
        """
        # 测试有效超时值
        valid_timeouts = [0.1, 1.0, 5.0, 10.0, 60.0]

        for timeout in valid_timeouts:
            engine = TimeControlledEventEngine(event_timeout=timeout)
            assert engine.event_timeout == timeout, f"超时值{timeout}应正确设置"
            assert engine.event_timeout > 0, "超时值应大于0"

        # 测试边界情况
        min_timeout = 0.001
        max_timeout = 300.0
        engine_min = TimeControlledEventEngine(event_timeout=min_timeout)
        engine_max = TimeControlledEventEngine(event_timeout=max_timeout)
        assert engine_min.event_timeout == min_timeout, "最小超时值应正确设置"
        assert engine_max.event_timeout == max_timeout, "最大超时值应正确设置"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])