"""
EngineMixin功能测试

测试EngineMixin的事件追踪、性能监控和调试支持功能。
遵循TDD方法，先写测试验证功能需求。
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any
from unittest.mock import Mock, patch

# 导入Mixin类
from ginkgo.trading.interfaces.mixins.engine_mixin import EngineMixin, EventContext, PerformanceMetrics

# 导入测试工厂
from test.fixtures.trading_factories import EventFactory, PortfolioFactory


@pytest.mark.tdd
@pytest.mark.mixin
class TestEngineMixin:
    """EngineMixin功能测试类"""

    @tdd_phase('red')
    def test_mixin_initialization_requirements(self):
        """TDD Red阶段：测试Mixin初始化要求"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine_123"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        # 创建带有Mixin的引擎
        class TestEngine(MockBaseEngine, EngineMixin):
            def __init__(self, **kwargs):
                MockBaseEngine.__init__(self)
                # EngineMixin.__init__会在这里被调用

        # 这个测试应该成功
        engine = TestEngine()
        assert engine._engine_id == "test_engine_123"
        assert hasattr(engine, '_event_contexts')
        assert hasattr(engine, '_performance_metrics')

    @tdd_phase('red')
    def test_event_context_tracking(self):
        """TDD Red阶段：测试事件上下文追踪功能"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = EventFactory.create_price_update_event(code="000001.SZ", close_price=10.50)

        # 测试事件追踪开始
        event_id = engine._track_event_start(mock_event)
        assert event_id is not None, "应该返回事件ID"
        assert isinstance(event_id, str), "事件ID应该是字符串"
        assert event_id.startswith("evt_"), "事件ID应该以evt_开头"

        # 验证上下文被正确创建
        with engine._context_lock:
            context = engine._event_contexts.get(event_id)
            assert context is not None, "应该创建事件上下文"
            assert context.event_type == "EventPriceUpdate", "事件类型应该正确"
            assert context.event_id == event_id, "上下文ID应该匹配"

        # 测试事件追踪结束
        engine._track_event_end(event_id, success=True, processing_time=0.1)
        with engine._processing_times_lock:
            assert event_id in engine._event_processing_times, "应该记录处理时间"

    @tdd_phase('red')
    def test_performance_metrics_collection(self):
        """TDD Red阶段：测试性能指标收集"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = EventFactory.create_price_update_event()

        # 模拟事件处理
        for i in range(10):
            event_id = engine._track_event_start(mock_event)
            processing_time = 0.01 + (i * 0.001)  # 递增的处理时间
            success = i < 8  # 最后2个失败

            engine._track_event_end(event_id, success=success, processing_time=processing_time)

        # 验证性能指标
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == 10, "应该处理10个事件"
        assert metrics['processed_events'] == 8, "应该成功处理8个事件"
        assert metrics['failed_events'] == 2, "应该失败2个事件"
        assert metrics['success_rate'] == 80.0, "成功率应该是80%"
        assert metrics['error_rate'] == 20.0, "错误率应该是20%"

    @tdd_phase('red')
    def test_error_tracking_and_logging(self):
        """TDD Red阶段：测试错误追踪和日志记录"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = EventFactory.create_price_update_event()

        # 模拟错误
        event_id = engine._track_event_start(mock_event)
        test_error = ValueError("测试错误")
        engine._track_event_end(event_id, success=False, error=test_error)

        # 验证错误记录
        recent_errors = engine.get_recent_errors(limit=1)
        assert len(recent_errors) == 1, "应该记录1个错误"
        assert recent_errors[0]['error_type'] == 'ValueError', "错误类型应该正确"
        assert recent_errors[0]['error_message'] == '测试错误', "错误消息应该正确"

    @tdd_phase('red')
    def test_performance_monitoring_thread(self):
        """TDD Red阶段：测试性能监控线程"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()

        # 启动性能监控
        engine.start_performance_monitoring(interval=0.1)
        assert engine._monitoring_active == True, "监控应该已启动"
        assert engine._monitoring_thread is not None, "监控线程应该存在"

        # 等待一些监控样本
        time.sleep(0.3)

        # 停止监控
        engine.stop_performance_monitoring()
        assert engine._monitoring_active == False, "监控应该已停止"

    @tdd_phase('red')
    def test_debug_mode_functionality(self):
        """TDD Red阶段：测试调试模式功能"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()

        # 启用调试模式
        engine.enable_debug_mode(trace_events=True)
        assert engine._debug_mode == True, "调试模式应该启用"
        assert engine._trace_events == True, "事件追踪应该启用"

        # 禁用调试模式
        engine.disable_debug_mode()
        assert engine._debug_mode == False, "调试模式应该禁用"
        assert engine._trace_events == False, "事件追踪应该禁用"

    @tdd_phase('red')
    def test_enhanced_event_handling(self):
        """TDD Red阶段：测试增强的事件处理"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"
                self.handled_events = []

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                self.handled_events.append(event)

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()
        mock_event = EventFactory.create_price_update_event()

        # 使用增强的事件处理方法
        engine.handle_event_with_monitoring(mock_event)

        # 验证事件被处理
        assert len(engine.handled_events) == 1, "应该处理1个事件"
        assert engine.handled_events[0] == mock_event, "应该处理正确的事件"

    @tdd_phase('red')
    def test_event_statistics_collection(self):
        """TDD Red阶段：测试事件统计收集"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()

        # 模拟不同类型的事件
        price_event = EventFactory.create_price_update_event()
        order_event = Mock()  # 模拟订单事件
        order_event.__class__.__name__ = "OrderEvent"

        # 追踪事件
        for _ in range(5):
            engine._track_event_start(price_event)
        for _ in range(3):
            engine._track_event_start(order_event)

        # 获取统计信息
        stats = engine.get_event_statistics()
        assert stats['EventPriceUpdate'] == 5, "应该记录5个价格事件"
        assert stats['OrderEvent'] == 3, "应该记录3个订单事件"
        assert stats['total_events'] == 8, "总共应该记录8个事件"

    @tdd_phase('red')
    def test_lifecycle_integration(self):
        """TDD Red阶段：测试生命周期集成"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"
                self.start_called = False
                self.stop_called = False

            def start(self):
                self.start_called = True
                return True

            def stop(self):
                self.stop_called = True
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()

        # 测试启动（应该调用父类start）
        result = engine.start()
        assert result == True, "启动应该成功"
        assert engine.start_called == True, "应该调用父类start方法"

        # 测试停止（应该调用父类stop）
        result = engine.stop()
        assert result == True, "停止应该成功"
        assert engine.stop_called == True, "应该调用父类stop方法"

    @tdd_phase('red')
    def test_concurrent_event_processing(self):
        """TDD Red阶段：测试并发事件处理"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                time.sleep(0.01)  # 模拟处理时间

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()
        processed_events = []

        def event_worker():
            for i in range(5):
                mock_event = EventFactory.create_price_update_event()
                event_id = engine._track_event_start(mock_event)
                engine.handle_event(mock_event)
                engine._track_event_end(event_id, success=True, processing_time=0.01)
                processed_events.append(i)

        # 启动多个工作线程
        threads = [threading.Thread(target=event_worker) for _ in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(processed_events) == 15, "应该处理15个事件"
        metrics = engine.get_performance_metrics()
        assert metrics['total_events'] == 15, "性能指标应该记录15个事件"

    @tdd_phase('red')
    def test_cleanup_and_resource_management(self):
        """TDD Red阶段：测试清理和资源管理"""

        class MockBaseEngine:
            def __init__(self):
                self._engine_id = "test_engine"
                self.name = "TestEngine"

            def start(self):
                return True

            def stop(self):
                return True

            def put(self, event):
                pass

            def handle_event(self, event):
                pass

            def log(self, level, message):
                pass

        class TestEngine(MockBaseEngine, EngineMixin):
            pass

        engine = TestEngine()

        # 创建一些数据
        mock_event = EventFactory.create_price_update_event()
        for i in range(5):
            event_id = engine._track_event_start(mock_event)
            engine._track_event_end(event_id, success=True)

        # 验证数据存在
        assert len(engine._event_contexts) > 0, "应该有事件上下文"
        assert len(engine._event_processing_times) > 0, "应该有处理时间记录"

        # 执行清理
        engine.cleanup_monitoring_data()

        # 验证数据被清理
        assert len(engine._event_contexts) == 0, "事件上下文应该被清理"
        assert len(engine._event_processing_times) == 0, "处理时间记录应该被清理"


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator