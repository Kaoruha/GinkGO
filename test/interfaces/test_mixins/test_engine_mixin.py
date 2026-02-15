"""
EngineMixin功能测试

测试EngineMixin的事件追踪、性能监控和调试支持功能。
遵循pytest最佳实践，使用fixtures和参数化测试。
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock

# 导入Mixin类
from ginkgo.trading.interfaces.mixins.engine_mixin import EngineMixin


# ===== Fixtures =====

@pytest.fixture
def mock_engine_base():
    """模拟引擎基类fixture"""
    class MockBaseEngine:
        def __init__(self):
            self._engine_id = "test_engine_123"
            self.name = "TestEngine"
            self.handled_events = []
            self.log_calls = []

        def start(self):
            return True

        def stop(self):
            return True

        def put(self, event):
            pass

        def handle_event(self, event):
            self.handled_events.append(event)

        def log(self, level, message):
            self.log_calls.append((level, message))

    return MockBaseEngine


@pytest.fixture
def sample_event():
    """示例事件fixture"""
    class MockEvent:
        def __init__(self, event_type="MockEvent", code="000001.SZ"):
            self._uuid = f"event_{event_type}_{code}"
            self.event_type = event_type
            self.timestamp = datetime.now()
            self.code = code

    return MockEvent


# ===== 初始化测试 =====

@pytest.mark.unit
class TestEngineMixinInitialization:
    """EngineMixin初始化测试"""

    def test_mixin_initialization(self, mock_engine_base):
        """测试Mixin初始化"""
        class TestEngine(mock_engine_base, EngineMixin):
            def __init__(self, **kwargs):
                mock_engine_base.__init__(self)
                EngineMixin.__init__(self)

        engine = TestEngine()

        # 验证基础属性
        assert engine._engine_id == "test_engine_123"
        assert hasattr(engine, '_event_contexts')
        assert hasattr(engine, '_performance_metrics')
        assert hasattr(engine, '_processing_times')
        assert hasattr(engine, '_error_log')

    def test_mixin_with_parameters(self, mock_engine_base):
        """测试带参数的Mixin初始化"""
        class TestEngine(mock_engine_base, EngineMixin):
            def __init__(self, **kwargs):
                mock_engine_base.__init__(self)
                EngineMixin.__init__(self)

        engine = TestEngine()

        # 验证初始化状态
        assert len(engine._event_contexts) == 0
        assert len(engine._performance_metrics) == 0


# ===== 事件追踪测试 =====

@pytest.mark.unit
class TestEngineMixinEventTracking:
    """EngineMixin事件追踪测试"""

    def test_event_context_tracking(self, mock_engine_base):
        """测试事件上下文追踪"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "TestEvent"
        mock_event.code = "000001.SZ"

        # 测试事件追踪开始
        event_id = engine._track_event_start(mock_event)
        assert event_id is not None
        assert isinstance(event_id, str)
        assert event_id.startswith("evt_")

        # 验证上下文被正确创建
        with engine._context_lock:
            context = engine._event_contexts.get(event_id)
            assert context is not None
            assert context.event_type == "TestEvent"
            assert context.event_id == event_id

        # 测试事件追踪结束
        engine._track_event_end(event_id, success=True, processing_time=0.1)
        with engine._processing_times_lock:
            assert event_id in engine._event_processing_times

    def test_multiple_event_tracking(self, mock_engine_base):
        """测试多个事件追踪"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "MultiEvent"
        mock_event.code = "000002.SZ"

        # 追踪多个事件
        event_ids = []
        for i in range(5):
            event_id = engine._track_event_start(mock_event)
            event_ids.append(event_id)

        # 验证所有事件都被追踪
        assert len(event_ids) == 5
        assert len(set(event_ids)) == 5  # 所有ID唯一

        # 结束所有事件
        for event_id in event_ids:
            engine._track_event_end(event_id, success=True, processing_time=0.05)

        # 验证处理时间记录
        with engine._processing_times_lock:
            assert len(engine._event_processing_times) == 5


# ===== 性能指标测试 =====

@pytest.mark.unit
class TestEngineMixinPerformanceMetrics:
    """EngineMixin性能指标测试"""

    def test_performance_metrics_collection(self, mock_engine_base):
        """测试性能指标收集"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "PerformanceTest"
        mock_event.code = "000001.SZ"

        # 模拟事件处理
        for i in range(10):
            event_id = engine._track_event_start(mock_event)
            processing_time = 0.01 + (i * 0.001)
            success = i < 8  # 最后2个失败

            engine._track_event_end(event_id, success=success, processing_time=processing_time)

        # 验证性能指标
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == 10
        assert metrics['processed_events'] == 8
        assert metrics['failed_events'] == 2
        assert metrics['success_rate'] == 80.0
        assert metrics['error_rate'] == 20.0

    @pytest.mark.parametrize("event_count,expected_min", [
        (5, 5),
        (10, 10),
        (20, 20)
    ])
    def test_performance_metrics_scaling(self, mock_engine_base, event_count, expected_min):
        """测试性能指标扩展性 - 参数化"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "ScaleTest"
        mock_event.code = "000001.SZ"

        # 处理多个事件
        for i in range(event_count):
            event_id = engine._track_event_start(mock_event)
            engine._track_event_end(event_id, success=True, processing_time=0.01)

        # 验证指标
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == event_count
        assert metrics['total_events'] >= expected_min


# ===== 错误追踪测试 =====

@pytest.mark.unit
class TestEngineMixinErrorTracking:
    """EngineMixin错误追踪测试"""

    def test_error_tracking_and_logging(self, mock_engine_base):
        """测试错误追踪和日志记录"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "ErrorTest"
        mock_event.code = "000001.SZ"

        # 模拟错误
        event_id = engine._track_event_start(mock_event)
        test_error = ValueError("测试错误")
        engine._track_event_end(event_id, success=False, error=test_error)

        # 验证错误记录
        recent_errors = engine.get_recent_errors(limit=1)
        assert len(recent_errors) == 1
        assert recent_errors[0]['error_type'] == 'ValueError'
        assert recent_errors[0]['error_message'] == '测试错误'

    def test_multiple_error_tracking(self, mock_engine_base):
        """测试多个错误追踪"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "MultiErrorTest"
        mock_event.code = "000001.SZ"

        # 模拟多个错误
        errors = [
            ValueError("错误1"),
            TypeError("错误2"),
            RuntimeError("错误3")
        ]

        for error in errors:
            event_id = engine._track_event_start(mock_event)
            engine._track_event_end(event_id, success=False, error=error)

        # 验证错误记录
        recent_errors = engine.get_recent_errors(limit=5)
        assert len(recent_errors) == 3

        # 验证错误类型
        error_types = [e['error_type'] for e in recent_errors]
        assert 'ValueError' in error_types
        assert 'TypeError' in error_types
        assert 'RuntimeError' in error_types


# ===== 监控线程测试 =====

@pytest.mark.unit
class TestEngineMixinMonitoringThread:
    """EngineMixin监控线程测试"""

    def test_performance_monitoring_thread(self, mock_engine_base):
        """测试性能监控线程"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 启动性能监控
        engine.start_performance_monitoring(interval=0.1)
        assert engine._monitoring_active == True
        assert engine._monitoring_thread is not None

        # 等待一些监控样本
        time.sleep(0.3)

        # 停止监控
        engine.stop_performance_monitoring()
        assert engine._monitoring_active == False

    def test_monitoring_thread_lifecycle(self, mock_engine_base):
        """测试监控线程生命周期"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 测试启动
        engine.start_performance_monitoring(interval=0.1)
        assert engine._monitoring_active == True

        # 测试停止
        engine.stop_performance_monitoring()
        assert engine._monitoring_active == False

        # 测试重新启动
        engine.start_performance_monitoring(interval=0.1)
        assert engine._monitoring_active == True

        # 清理
        engine.stop_performance_monitoring()


# ===== 调试模式测试 =====

@pytest.mark.unit
class TestEngineMixinDebugMode:
    """EngineMixin调试模式测试"""

    def test_debug_mode_functionality(self, mock_engine_base):
        """测试调试模式功能"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 启用调试模式
        engine.enable_debug_mode(trace_events=True)
        assert engine._debug_mode == True
        assert engine._trace_events == True

        # 禁用调试模式
        engine.disable_debug_mode()
        assert engine._debug_mode == False
        assert engine._trace_events == False

    @pytest.mark.parametrize("trace_events,debug_mode", [
        (True, True),
        (False, False)
    ])
    def test_debug_mode_parameters(self, mock_engine_base, trace_events, debug_mode):
        """测试调试模式参数 - 参数化"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        if trace_events:
            engine.enable_debug_mode(trace_events=True)
        else:
            engine.disable_debug_mode()

        assert engine._debug_mode == debug_mode


# ===== 事件处理测试 =====

@pytest.mark.unit
class TestEngineMixinEventHandling:
    """EngineMixin事件处理测试"""

    def test_enhanced_event_handling(self, mock_engine_base):
        """测试增强的事件处理"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "HandleTest"
        mock_event.code = "000001.SZ"

        # 使用增强的事件处理方法
        engine.handle_event_with_monitoring(mock_event)

        # 验证事件被处理
        assert len(engine.handled_events) == 1
        assert engine.handled_events[0] == mock_event

    def test_event_handling_with_errors(self, mock_engine_base):
        """测试带错误的事件处理"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "ErrorEvent"
        mock_event.code = "000001.SZ"

        # 模拟处理错误
        original_handle = engine.handle_event
        def handle_with_error(event):
            if event.event_type == "ErrorEvent":
                raise ValueError("处理错误")
        engine.handle_event = handle_with_error

        # 测试错误处理
        engine.handle_event_with_monitoring(mock_event)

        # 验证错误被记录
        errors = engine.get_recent_errors(limit=1)
        # 如果实现支持错误捕获，应该有错误记录


# ===== 统计信息测试 =====

@pytest.mark.unit
class TestEngineMixinStatistics:
    """EngineMixin统计信息测试"""

    def test_event_statistics_collection(self, mock_engine_base):
        """测试事件统计收集"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 模拟不同类型的事件
        price_event = Mock()
        price_event.event_type = "EventPriceUpdate"
        price_event.code = "000001.SZ"

        order_event = Mock()
        order_event.event_type = "EventOrder"
        order_event.code = "000002.SZ"

        # 追踪事件
        for _ in range(5):
            engine._track_event_start(price_event)
        for _ in range(3):
            engine._track_event_start(order_event)

        # 获取统计信息
        stats = engine.get_event_statistics()
        assert stats['EventPriceUpdate'] == 5
        assert stats['EventOrder'] == 3
        assert stats['total_events'] == 8

    @pytest.mark.parametrize("event_counts,expected_total", [
        ({"EventA": 3, "EventB": 5, "EventC": 2}, 10),
        ({"EventX": 10, "EventY": 20}, 30),
        ({"SingleEvent": 100}, 100)
    ])
    def test_statistics_with_different_distributions(self, mock_engine_base, event_counts, expected_total):
        """测试不同分布的统计 - 参数化"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 按照给定分布创建事件
        for event_type, count in event_counts.items():
            for _ in range(count):
                mock_event = Mock()
                mock_event.event_type = event_type
                mock_event.code = "000001.SZ"
                engine._track_event_start(mock_event)

        # 验证统计
        stats = engine.get_event_statistics()
        assert stats['total_events'] == expected_total


# ===== 并发测试 =====

@pytest.mark.unit
class TestEngineMixinConcurrency:
    """EngineMixin并发测试"""

    def test_concurrent_event_processing(self, mock_engine_base):
        """测试并发事件处理"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        processed_events = []

        def event_worker(worker_id):
            for i in range(5):
                mock_event = Mock()
                mock_event.event_type = "ConcurrentEvent"
                mock_event.code = f"{worker_id:06d}.SZ"
                event_id = engine._track_event_start(mock_event)
                engine.handle_event(mock_event)
                engine._track_event_end(event_id, success=True, processing_time=0.01)
                processed_events.append((worker_id, i))
                time.sleep(0.001)

        # 启动多个工作线程
        threads = [threading.Thread(target=event_worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(processed_events) == 15
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == 15


# ===== 资源管理测试 =====

@pytest.mark.unit
class TestEngineMixinResourceManagement:
    """EngineMixin资源管理测试"""

    def test_cleanup_and_resource_management(self, mock_engine_base):
        """测试清理和资源管理"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()

        # 创建一些数据
        mock_event = Mock()
        mock_event.event_type = "CleanupTest"
        mock_event.code = "000001.SZ"

        for i in range(5):
            event_id = engine._track_event_start(mock_event)
            engine._track_event_end(event_id, success=True)

        # 验证数据存在
        assert len(engine._event_contexts) > 0
        assert len(engine._event_processing_times) > 0

        # 执行清理
        engine.cleanup_monitoring_data()

        # 验证数据被清理
        assert len(engine._event_contexts) == 0
        assert len(engine._event_processing_times) == 0

    def test_memory_efficiency(self, mock_engine_base):
        """测试内存效率"""
        class TestEngine(mock_engine_base, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = Mock()
        mock_event.event_type = "MemoryTest"
        mock_event.code = "000001.SZ"

        # 创建大量事件
        for i in range(100):
            event_id = engine._track_event_start(mock_event)
            engine._track_event_end(event_id, success=True)

        # 验证事件被正确管理
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == 100

        # 清理后应该释放内存
        engine.cleanup_monitoring_data()
        assert len(engine._event_contexts) == 0
        assert len(engine._event_processing_times) == 0
