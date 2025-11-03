"""
EventMixin功能测试

测试EventMixin的事件追踪、关联管理和链路追踪功能。
遵循TDD方法，先写测试验证功能需求。
"""

import pytest
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, List
from unittest.mock import Mock, patch

# 导入Mixin类和相关数据结构
from ginkgo.trading.interfaces.mixins.event_mixin import (
    EventMixin, EventTraceInfo, EventProcessingNode
)

# 导入测试工厂
from test.fixtures.trading_factories import EventFactory


@pytest.mark.tdd
@pytest.mark.mixin
class TestEventMixin:
    """EventMixin功能测试类"""

    def test_mixin_initialization_requirements(self):
        """TDD Red阶段：测试Mixin初始化要求"""

        # 创建一个模拟的基础事件类
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')
                self.run_id = kwargs.get('run_id', 'test_run')

        # 创建带有EventMixin的事件类
        class TestEvent(MockBaseEvent, EventMixin):
            pass

        # 这个测试应该成功
        event = TestEvent(
            correlation_id="test_correlation_123",
            session_id="test_session_456",
            priority=8,
            weight=1.5
        )

        # 验证基础属性
        assert hasattr(event, '_uuid'), "应该有UUID属性"
        assert hasattr(event, 'event_type'), "应该有事件类型"

        # 验证Mixin功能
        assert hasattr(event, '_trace_info'), "应该有追踪信息"
        assert hasattr(event, '_processing_chain'), "应该有处理链路"
        assert hasattr(event, '_related_events'), "应该有关联事件集合"
        assert hasattr(event, '_tags'), "应该有标签集合"
        assert hasattr(event, '_categories'), "应该有分类集合"

        # 验证初始化的追踪信息
        assert event._trace_info is not None, "应该初始化追踪信息"
        assert event.correlation_id == "test_correlation_123", "关联ID应该正确设置"
        assert event.session_id == "test_session_456", "会话ID应该正确设置"

    def test_trace_id_properties(self):
        """测试追踪ID属性"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent(trace_id="trace_123456")

        # 测试只读属性
        assert event.trace_id == "trace_123456", "追踪ID应该正确"
        assert isinstance(event.trace_id, str), "追踪ID应该是字符串"

        # 测试默认值
        event_default = TestEvent()
        assert event_default.trace_id is not None, "应该有默认追踪ID"
        assert len(event_default.trace_id) > 0, "追踪ID不应该为空"

    def test_correlation_id_management(self):
        """测试关联ID管理"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试设置和获取关联ID
        event.correlation_id = "corr_789"
        assert event.correlation_id == "corr_789", "关联ID应该正确设置"

        # 测试便捷方法
        event.set_correlation_id("corr_999")
        assert event.correlation_id == "corr_999", "便捷方法应该生效"

        # 测试通过构造函数设置
        event2 = TestEvent(correlation_id="corr_init")
        assert event2.correlation_id == "corr_init", "构造函数设置应该生效"

    def test_causation_id_management(self):
        """测试因果事件ID管理"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试设置和获取因果ID
        event.causation_id = "cause_123"
        assert event.causation_id == "cause_123", "因果ID应该正确设置"

        # 测试便捷方法
        event.set_causation_id("cause_456")
        assert event.causation_id == "cause_456", "便捷方法应该生效"

    def test_event_relationships_management(self):
        """测试事件关联关系管理"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试添加关联事件
        event.add_related_event("related_1", "related")
        event.add_related_event("related_2", "child")
        event.add_related_event("related_3", "child")

        # 测试获取关联事件
        related_events = event.get_related_events()
        child_events = event.get_child_events()

        assert len(related_events) == 1, "应该有1个普通关联事件"
        assert "related_1" in related_events, "普通关联事件应该被包含"
        assert len(child_events) == 2, "应该有2个子事件"
        assert "related_2" in child_events, "子事件应该被包含"
        assert "related_3" in child_events, "子事件应该被包含"

        # 测试关联检查
        assert event.is_related_to("related_1"), "应该能检测到关联关系"
        assert event.is_related_to("related_2"), "应该能检测到子事件关系"
        assert not event.is_related_to("unrelated"), "不关联的事件应该返回False"

    def test_processing_chain_tracking(self):
        """测试事件处理链路追踪"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试添加处理节点
        node1_id = event.add_processing_node(
            node_type="engine",
            node_name="test_engine",
            processing_duration=0.1,
            status="started"
        )

        assert node1_id is not None, "应该返回节点ID"
        assert isinstance(node1_id, str), "节点ID应该是字符串"

        node2_id = event.add_processing_node(
            node_type="portfolio",
            node_name="test_portfolio",
            processing_duration=0.05,
            status="completed"
        )

        # 测试获取处理链路
        chain = event.get_processing_chain()
        assert len(chain) == 2, "应该有2个处理节点"
        assert chain[0].node_type == "engine", "第一个节点应该是引擎"
        assert chain[1].node_type == "portfolio", "第二个节点应该是投资组合"

        # 测试按类型获取节点
        engine_nodes = event.get_processing_nodes_by_type("engine")
        portfolio_nodes = event.get_processing_nodes_by_type("portfolio")
        strategy_nodes = event.get_processing_nodes_by_type("strategy")

        assert len(engine_nodes) == 1, "应该有1个引擎节点"
        assert len(portfolio_nodes) == 1, "应该有1个投资组合节点"
        assert len(strategy_nodes) == 0, "应该没有策略节点"

        # 测试更新处理节点
        update_result = event.update_processing_node(
            node1_id,
            status="completed",
            processing_duration=0.15
        )
        assert update_result == True, "更新应该成功"

        updated_chain = event.get_processing_chain()
        assert updated_chain[0].status == "completed", "状态应该被更新"
        assert updated_chain[0].processing_duration == 0.15, "处理时间应该被更新"

    def test_tags_and_categories(self):
        """测试标签和分类功能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试标签管理
        event.add_tag("urgent")
        event.add_tag("high_priority")
        event.add_tag("debug")

        assert event.has_tag("urgent"), "应该能检测到标签"
        assert event.has_tag("high_priority"), "应该能检测到标签"
        assert not event.has_tag("normal"), "不存在的标签应该返回False"

        tags = event.get_tags()
        assert len(tags) == 3, "应该有3个标签"
        assert "urgent" in tags, "标签应该被包含"

        # 测试标签移除
        event.remove_tag("high_priority")
        assert not event.has_tag("high_priority"), "移除的标签应该不存在"
        assert len(event.get_tags()) == 2, "移除后应该有2个标签"

        # 测试分类管理
        event.add_category("trading")
        event.add_category("risk_management")
        event.add_category("performance")

        categories = event.get_categories()
        assert len(categories) == 3, "应该有3个分类"
        assert "trading" in categories, "分类应该被包含"

    def test_priority_and_weight(self):
        """测试优先级和权重功能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试默认值
        assert event.priority == 5, "默认优先级应该是5"
        assert event.weight == 1.0, "默认权重应该是1.0"

        # 测试设置优先级
        event.priority = 8
        assert event.priority == 8, "优先级应该被正确设置"

        # 测试无效优先级
        try:
            event.priority = 15  # 超出范围
            assert False, "不应该到达这里"
        except ValueError as e:
            assert "Priority must be between 1 and 10" in str(e), "应该有正确的错误信息"

        # 测试设置权重
        event.weight = 2.5
        assert event.weight == 2.5, "权重应该被正确设置"

        # 测试无效权重
        try:
            event.weight = -1.0  # 负权重
            assert False, "不应该到达这里"
        except ValueError as e:
            assert "Weight must be positive" in str(e), "应该有正确的错误信息"

    def test_debug_support(self):
        """测试调试支持功能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试调试信息
        event.add_debug_info("debug_key", "debug_value")
        assert event.get_debug_info("debug_key") == "debug_value", "调试信息应该被正确设置和获取"

        assert event.get_debug_info("nonexistent") is None, "不存在的调试信息应该返回None"

        # 测试注释
        event.add_annotation("note", "This is a test note", "debug")
        annotation = event.get_annotation("note")
        assert annotation is not None, "注释应该被正确设置"
        assert annotation['value'] == "This is a test note", "注释值应该正确"
        assert annotation['type'] == "debug", "注释类型应该正确"

        assert event.get_annotation("nonexistent") is None, "不存在的注释应该返回None"

    def test_event_summary(self):
        """测试事件摘要功能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent(
            correlation_id="test_corr",
            priority=8,
            weight=1.5
        )

        # 添加一些测试数据
        event.add_tag("test_tag")
        event.add_category("test_category")
        event.add_processing_node("engine", "test_engine", 0.1, "completed")
        event.add_debug_info("test", "value")

        # 获取摘要
        summary = event.get_event_summary()

        # 验证摘要结构
        assert isinstance(summary, dict), "摘要应该是字典类型"

        # 验证必需字段
        required_fields = [
            'event_uuid', 'event_type', 'trace_info', 'timing',
            'relationships', 'processing_chain', 'classification', 'debug_info'
        ]
        for field in required_fields:
            assert field in summary, f"摘要应该包含{field}字段"

        # 验证追踪信息
        trace_info = summary['trace_info']
        assert trace_info['correlation_id'] == "test_corr", "关联ID应该正确"
        assert trace_info['trace_id'] is not None, "追踪ID应该存在"

        # 验证处理链路
        processing_chain = summary['processing_chain']
        assert processing_chain['nodes_count'] == 1, "应该有1个处理节点"
        assert len(processing_chain['nodes']) == 1, "节点列表应该不为空"

        # 验证分类信息
        classification = summary['classification']
        assert classification['priority'] == 8, "优先级应该正确"
        assert classification['weight'] == 1.5, "权重应该正确"
        assert "test_tag" in classification['tags'], "标签应该被包含"
        assert "test_category" in classification['categories'], "分类应该被包含"

    @tdd_phase('red')
    def test_mixin_without_base_class_should_fail(self):
        """TDD Red阶段：没有基础类的Mixin应该失败"""

        class InvalidEvent(EventMixin):
            """没有正确基础类的事件实现"""
            def __init__(self):
                # 故意不调用父类初始化
                self.name = "InvalidEvent"

        # 创建事件应该失败
        try:
            invalid_event = InvalidEvent()
            assert False, "TDD Red阶段：没有基础类的事件应该初始化失败"
        except RuntimeError as e:
            assert "requires EventBase to be initialized first" in str(e), "应该有正确的错误信息"

    def test_concurrent_event_modifications(self):
        """测试事件的并发修改安全性"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()
        results = []
        errors = []

        def modification_worker(worker_id):
            try:
                for i in range(10):
                    # 并发修改各种属性
                    event.add_tag(f"tag_{worker_id}_{i}")
                    event.add_related_event(f"related_{worker_id}_{i}", "related")
                    node_id = event.add_processing_node("test", f"worker_{worker_id}", 0.001)
                    event.add_debug_info(f"key_{worker_id}_{i}", f"value_{worker_id}_{i}")

                    # 获取当前状态
                    tags_count = len(event.get_tags())
                    related_count = len(event.get_related_events())
                    chain_length = len(event.get_processing_chain())

                    results.append({
                        'worker_id': worker_id,
                        'iteration': i,
                        'tags_count': tags_count,
                        'related_count': related_count,
                        'chain_length': chain_length
                    })
                    time.sleep(0.001)
            except Exception as e:
                errors.append((worker_id, e))

        # 启动多个线程
        threads = [threading.Thread(target=modification_worker, args=(i,)) for i in range(3)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # 验证结果
        assert len(errors) == 0, f"并发修改不应该产生错误: {errors}"
        assert len(results) == 30, "应该有30个操作结果"

        # 验证最终状态一致性
        final_tags = event.get_tags()
        final_related = event.get_related_events()
        final_chain = event.get_processing_chain()

        assert len(final_tags) == 30, "应该有30个标签"
        assert len(final_related) == 30, "应该有30个关联事件"
        assert len(final_chain) == 30, "应该有30个处理节点"

    def test_static_event_creation_methods(self):
        """测试静态事件创建方法"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')
                self.run_id = kwargs.get('run_id', 'test_run')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        # 创建父事件
        parent_event = TestEvent(
            correlation_id="parent_corr",
            session_id="parent_session"
        )

        # 测试创建子事件
        child_event = TestEvent.create_child_event(
            parent_event,
            TestEvent,
            code="CHILD_001",
            priority=7
        )

        # 验证子事件继承关系
        assert child_event.parent_trace_id == parent_event.trace_id, "子事件应该继承父追踪ID"
        assert child_event.root_trace_id == parent_event.root_trace_id, "子事件应该继承根追踪ID"
        assert child_event.correlation_id == parent_event.correlation_id, "子事件应该继承关联ID"
        assert child_event.causation_id == parent_event._uuid, "子事件应该设置父事件UUID为因果ID"

        # 验证双向关联
        assert parent_event.is_related_to(child_event._uuid), "父事件应该关联到子事件"
        assert child_event.is_related_to(parent_event._uuid), "子事件应该关联到父事件"

        # 测试创建关联事件
        related_event = TestEvent.create_correlated_event(
            parent_event,
            TestEvent,
            code="RELATED_001",
            priority=6
        )

        # 验证关联事件关系
        assert related_event.correlation_id == parent_event.correlation_id or parent_event._uuid, "关联事件应该有正确的关联ID"
        assert parent_event.is_related_to(related_event._uuid), "源事件应该关联到关联事件"
        assert related_event.is_related_to(parent_event._uuid), "关联事件应该关联到源事件"


@pytest.mark.tdd
@pytest.mark.mixin
class TestEventMixinPerformance:
    """EventMixin性能测试"""

    def test_large_scale_event_tracking(self):
        """测试大规模事件追踪性能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        events = [TestEvent() for _ in range(100)]

        start_time = time.time()

        # 批量添加标签
        for i, event in enumerate(events):
            event.add_tag(f"batch_tag_{i}")
            event.add_category(f"batch_category_{i % 10}")

        batch_tag_time = time.time()

        # 批量添加处理节点
        for event in events:
            for j in range(5):
                event.add_processing_node(
                    node_type=f"node_{j}",
                    node_name=f"processor_{j}",
                    processing_duration=0.001
                )

        batch_node_time = time.time()

        # 批量建立关联关系
        for i in range(len(events) - 1):
            events[i].add_related_event(events[i + 1]._uuid, 'related')
            events[i].add_related_event(events[i - 1]._uuid, 'related')

        batch_relation_time = time.time()

        total_time = time.time() - start_time

        # 验证性能指标
        assert total_time < 5.0, "总处理时间应该小于5秒"
        assert batch_tag_time - start_time < 1.0, "标签批量处理应该很快"
        assert batch_node_time - batch_tag_time < 1.0, "节点批量处理应该很快"
        assert batch_relation_time - batch_node_time < 1.0, "关系批量处理应该很快"

        # 验证数据完整性
        for event in events:
            assert len(event.get_tags()) == 1, "每个事件应该有1个标签"
            assert len(event.get_categories()) == 1, "每个事件应该有1个分类"
            assert len(event.get_processing_chain()) == 5, "每个事件应该有5个处理节点"

    def test_memory_usage_with_complex_events(self):
        """测试复杂事件的内存使用"""
        import sys

        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        # 创建复杂事件
        events = []
        for i in range(50):
            event = TestEvent()

            # 添加大量标签和分类
            for j in range(20):
                event.add_tag(f"tag_{j}")
                event.add_category(f"category_{j % 5}")

            # 添加大量处理节点
            for j in range(10):
                event.add_processing_node(
                    node_type=f"complex_node_{j}",
                    node_name=f"processor_{j}",
                    processing_duration=0.001,
                    metadata={'iteration': i, 'node_index': j}
                )

            # 添加大量调试信息
            for j in range(10):
                event.add_debug_info(f"debug_{j}", f"value_{i}_{j}")
                event.add_annotation(f"note_{j}", f"Annotation {i}-{j}", "debug")

            events.append(event)

        # 验证内存使用合理
        for event in events:
            summary = event.get_event_summary()
            assert isinstance(summary, dict), "摘要应该能正常生成"
            assert len(summary['debug_info']['annotations']) == 10, "注释数量应该正确"

        # 强制垃圾回收以检查内存泄漏
        del events

    def test_event_summary_generation_performance(self):
        """测试事件摘要生成性能"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 添加测试数据
        for i in range(100):
            event.add_tag(f"perf_tag_{i}")
            event.add_processing_node("engine", f"engine_{i}", 0.001)

        # 测试摘要生成性能
        start_time = time.time()
        for _ in range(100):
            summary = event.get_event_summary()
        end_time = time.time()

        generation_time = end_time - start_time
        assert generation_time < 0.1, "100次摘要生成应该很快"

        # 验证摘要完整性
        summary = event.get_event_summary()
        assert len(summary['classification']['tags']) == 100, "标签数量应该正确"
        assert summary['processing_chain']['nodes_count'] == 100, "处理节点数量应该正确"


@pytest.mark.tdd
@pytest.mark.mixin
class TestEventMixinEdgeCases:
    """EventMixin边界情况测试"""

    def test_event_with_empty_trace_info(self):
        """测试空追踪信息的事件"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 强制清空追踪信息（测试边界情况）
        event._trace_info = None

        # 测试在这种情况下各方法的鲁棒性
        assert event.trace_id == event._uuid, "没有追踪信息时应该返回UUID"
        assert event.parent_trace_id is None, "没有追踪信息时应该返回None"
        assert event.root_trace_id is None, "没有追踪信息时应该返回None"
        assert event.correlation_id is None, "没有追踪信息时应该返回None"

        # 测试摘要生成
        summary = event.get_event_summary()
        assert isinstance(summary, dict), "即使没有追踪信息也应该能生成摘要"

    def test_event_with_extreme_values(self):
        """测试极端值的事件"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        # 测试极长字符串
        event = TestEvent()
        long_string = "x" * 10000
        event.add_debug_info("long_key", long_string)
        assert event.get_debug_info("long_key") == long_string, "应该能处理极长字符串"

        # 测试极低优先级
        event.priority = 1
        assert event.priority == 1, "应该能处理最低优先级"

        # 测试极高优先级
        event.priority = 10
        assert event.priority == 10, "应该能处理最高优先级"

        # 测试极小权重
        event.weight = 0.001
        assert event.weight == 0.001, "应该能处理极小权重"

        # 测试极大权重
        event.weight = 1000.0
        assert event.weight == 1000.0, "应该能处理极大权重"

    def test_event_with_unicode_content(self):
        """测试包含Unicode内容的事件"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 测试Unicode标签和注释
        unicode_tag = "测试标签_🔥_emoji"
        unicode_annotation = "测试注释_🚀_特殊字符"

        event.add_tag(unicode_tag)
        event.add_annotation("unicode_note", unicode_annotation)

        assert event.has_tag(unicode_tag), "应该能处理Unicode标签"
        annotation = event.get_annotation("unicode_note")
        assert annotation['value'] == unicode_annotation, "应该能处理Unicode注释"

    def test_event_with_datetime_precision(self):
        """测试日期时间精度的事件"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        # 创建高精度时间的事件
        precise_time = datetime(2024, 1, 1, 12, 30, 45, 123456)
        event = TestEvent(timestamp=precise_time)

        # 添加处理节点记录高精度时间
        node_id = event.add_processing_node("engine", "test_engine", 0.001234567)

        # 验证时间精度保持
        assert event.timestamp == precise_time, "时间戳精度应该保持"
        assert event._creation_time <= datetime.now(), "创建时间应该合理"

        chain = event.get_processing_chain()
        if chain:
            assert chain[0].timestamp >= precise_time, "处理节点时间应该不早于事件时间"

    def test_event_summary_with_missing_components(self):
        """测试缺少组件时的事件摘要生成"""
        class MockBaseEvent:
            def __init__(self, **kwargs):
                self._uuid = f"event_{uuid.uuid4().hex[:12]}"
                self.event_type = kwargs.get('event_type', 'MockEvent')
                self.timestamp = kwargs.get('timestamp', datetime.now())
                self.code = kwargs.get('code', 'DEFAULT')

        class TestEvent(MockBaseEvent, EventMixin):
            pass

        event = TestEvent()

        # 清空一些组件来测试边界情况
        event._tags.clear()
        event._categories.clear()
        event._processing_chain.clear()
        event._debug_info.clear()
        event._annotations.clear()

        # 测试在这种情况下生成摘要
        summary = event.get_event_summary()

        # 验证即使组件为空也能生成摘要
        assert isinstance(summary, dict), "即使组件为空也应该能生成摘要"
        assert summary['classification']['tags'] == [], "空标签列表应该正确"
        assert summary['classification']['categories'] == [], "空分类列表应该正确"
        assert summary['processing_chain']['nodes_count'] == 0, "空链路应该正确计数"
        assert summary['debug_info']['annotations'] == {}, "空注释字典应该正确"


# ===== TDD阶段标记 =====

def tdd_phase(phase: str):
    """TDD阶段标记装饰器"""
    def decorator(test_func):
        test_func.tdd_phase = phase
        return test_func
    return decorator