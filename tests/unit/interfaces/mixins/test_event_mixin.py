"""
EventMixin功能测试

测试EventMixin的事件追踪、关联管理和链路追踪功能。
遵循pytest最佳实践，使用fixtures和参数化测试。
"""

import pytest
import time
import threading
import uuid
from datetime import datetime
from decimal import Decimal

# 导入Mixin类
from ginkgo.trading.interfaces.mixins.event_mixin import (
    EventMixin, EventTraceInfo, EventProcessingNode
)


# ===== Fixtures =====

@pytest.fixture
def mock_event_base():
    """模拟事件基类fixture - 提供EventMixin所需的属性"""
    class MockBaseEvent:
        def __init__(self, **kwargs):
            # EventMixin需要_uuid属性
            self._uuid = kwargs.get('uuid', f"event_{uuid.uuid4().hex[:12]}")
            self.event_type = kwargs.get('event_type', 'MockEvent')
            self.timestamp = kwargs.get('timestamp', datetime.now())
            self.code = kwargs.get('code', 'DEFAULT')
            self.task_id = kwargs.get('task_id', 'test_run')
            # EventMixin is later in MRO, call super() to initialize it
            super().__init__(**kwargs)

    return MockBaseEvent


# ===== 初始化测试 =====

@pytest.mark.unit
class TestEventMixinInitialization:
    """EventMixin初始化测试"""

    def test_mixin_initialization_requirements(self, mock_event_base):
        """测试Mixin初始化要求"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent(
            correlation_id="test_correlation_123",
            session_id="test_session_456",
            priority=8,
            weight=1.5
        )

        # 验证基础属性
        assert getattr(event, '_uuid', None) is not None
        assert getattr(event, 'event_type', None) is not None

        # 验证Mixin功能
        assert getattr(event, '_trace_info', None) is not None
        assert getattr(event, '_processing_chain', None) is not None
        assert getattr(event, '_related_events', None) is not None
        assert getattr(event, '_tags', None) is not None
        assert getattr(event, '_categories', None) is not None

        # 验证初始化的追踪信息
        assert event._trace_info is not None
        assert event.correlation_id == "test_correlation_123"
        assert event.session_id == "test_session_456"


# ===== 追踪属性测试 =====

@pytest.mark.unit
class TestEventMixinTraceProperties:
    """EventMixin追踪属性测试"""

    def test_trace_id_properties(self, mock_event_base):
        """测试追踪ID属性"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent(trace_id="trace_123456")

        # 测试只读属性
        assert event.trace_id == "trace_123456"
        assert isinstance(event.trace_id, str)

        # 测试默认值
        event_default = TestEvent()
        assert event_default.trace_id is not None
        assert len(event_default.trace_id) > 0

    @pytest.mark.parametrize("correlation_id,session_id", [
        ("corr_789", None),
        ("corr_999", "session_123"),
        (None, "session_456"),
        ("corr_multi", "session_multi")
    ])
    def test_correlation_id_management(self, mock_event_base, correlation_id, session_id):
        """测试关联ID管理 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent(correlation_id=correlation_id, session_id=session_id)

        if correlation_id:
            assert event.correlation_id == correlation_id

        if session_id:
            assert event.session_id == session_id

    def test_causation_id_management(self, mock_event_base):
        """测试因果事件ID管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试设置和获取因果ID
        event.causation_id = "cause_123"
        assert event.causation_id == "cause_123"

        # 测试便捷方法
        event.set_causation_id("cause_456")
        assert event.causation_id == "cause_456"


# ===== 关联关系测试 =====

@pytest.mark.unit
class TestEventMixinRelationships:
    """EventMixin关联关系测试"""

    def test_event_relationships_management(self, mock_event_base):
        """测试事件关联关系管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试添加关联事件
        event.add_related_event("related_1", "related")
        event.add_related_event("related_2", "child")
        event.add_related_event("related_3", "child")

        # 测试获取关联事件
        related_events = event.get_related_events()
        child_events = event.get_child_events()

        assert len(related_events) == 1
        assert "related_1" in related_events
        assert len(child_events) == 2
        assert "related_2" in child_events
        assert "related_3" in child_events

        # 测试关联检查
        assert event.is_related_to("related_1")
        assert event.is_related_to("related_2")
        assert not event.is_related_to("unrelated")

    @pytest.mark.parametrize("relation_type", ["related", "child", "parent"])
    def test_add_multiple_related_events(self, mock_event_base, relation_type):
        """测试添加多个关联事件 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()
        count = 5

        for i in range(count):
            event.add_related_event(f"event_{i}", relation_type)

        if relation_type == "related":
            related_events = event.get_related_events()
            assert len(related_events) == count
        elif relation_type == "child":
            child_events = event.get_child_events()
            assert len(child_events) == count


# ===== 处理链路测试 =====

@pytest.mark.unit
class TestEventMixinProcessingChain:
    """EventMixin处理链路测试"""

    def test_processing_chain_tracking(self, mock_event_base):
        """测试事件处理链路追踪"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试添加处理节点
        node1_id = event.add_processing_node(
            node_type="engine",
            node_name="test_engine",
            processing_duration=0.1,
            status="started"
        )

        assert node1_id is not None
        assert isinstance(node1_id, str)

        node2_id = event.add_processing_node(
            node_type="portfolio",
            node_name="test_portfolio",
            processing_duration=0.05,
            status="completed"
        )

        # 测试获取处理链路
        chain = event.get_processing_chain()
        assert len(chain) == 2
        assert chain[0].node_type == "engine"
        assert chain[1].node_type == "portfolio"

    @pytest.mark.parametrize("node_type,expected_count", [
        ("engine", 2),
        ("portfolio", 1),
        ("strategy", 0)
    ])
    def test_get_nodes_by_type(self, mock_event_base, node_type, expected_count):
        """测试按类型获取节点 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 添加不同类型的节点
        event.add_processing_node("engine", "engine_1", 0.1)
        event.add_processing_node("portfolio", "portfolio_1", 0.05)
        event.add_processing_node("engine", "engine_2", 0.08)

        nodes = event.get_processing_nodes_by_type(node_type)
        assert len(nodes) == expected_count

    def test_update_processing_node(self, mock_event_base):
        """测试更新处理节点"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()
        node_id = event.add_processing_node("engine", "test_engine", 0.1, "started")

        # 更新节点
        update_result = event.update_processing_node(
            node_id,
            status="completed",
            processing_duration=0.15
        )

        assert update_result == True

        updated_chain = event.get_processing_chain()
        assert updated_chain[0].status == "completed"
        assert updated_chain[0].processing_duration == 0.15


# ===== 标签和分类测试 =====

@pytest.mark.unit
class TestEventMixinTagsAndCategories:
    """EventMixin标签和分类测试"""

    def test_tags_management(self, mock_event_base):
        """测试标签管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 添加标签
        event.add_tag("urgent")
        event.add_tag("high_priority")
        event.add_tag("debug")

        assert event.has_tag("urgent")
        assert event.has_tag("high_priority")
        assert not event.has_tag("normal")

        tags = event.get_tags()
        assert len(tags) == 3
        assert "urgent" in tags

        # 测试标签移除
        event.remove_tag("high_priority")
        assert not event.has_tag("high_priority")
        assert len(event.get_tags()) == 2

    def test_categories_management(self, mock_event_base):
        """测试分类管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 添加分类
        event.add_category("trading")
        event.add_category("risk_management")
        event.add_category("performance")

        categories = event.get_categories()
        assert len(categories) == 3
        assert "trading" in categories


# ===== 优先级和权重测试 =====

@pytest.mark.unit
class TestEventMixinPriorityAndWeight:
    """EventMixin优先级和权重测试"""

    def test_priority_and_weight(self, mock_event_base):
        """测试优先级和权重功能"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试默认值
        assert event.priority == 5
        assert event.weight == 1.0

        # 测试设置优先级
        event.priority = 8
        assert event.priority == 8

        # 测试设置权重
        event.weight = 2.5
        assert event.weight == 2.5

    @pytest.mark.parametrize("priority,should_fail", [
        (1, False),
        (5, False),
        (10, False),
        (0, True),
        (11, True),
        (15, True)
    ])
    def test_priority_validation(self, mock_event_base, priority, should_fail):
        """测试优先级验证 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        if should_fail:
            with pytest.raises(ValueError, match="Priority must be between 1 and 10"):
                event.priority = priority
        else:
            event.priority = priority
            assert event.priority == priority

    @pytest.mark.parametrize("weight,should_fail", [
        (0.001, False),
        (1.0, False),
        (1000.0, False),
        (-1.0, True),
        (0.0, True)
    ])
    def test_weight_validation(self, mock_event_base, weight, should_fail):
        """测试权重验证 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        if should_fail:
            with pytest.raises(ValueError, match="Weight must be positive"):
                event.weight = weight
        else:
            event.weight = weight
            assert event.weight == weight


# ===== 调试支持测试 =====

@pytest.mark.unit
class TestEventMixinDebugSupport:
    """EventMixin调试支持测试"""

    def test_debug_info_management(self, mock_event_base):
        """测试调试信息管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试调试信息
        event.add_debug_info("debug_key", "debug_value")
        assert event.get_debug_info("debug_key") == "debug_value"

        assert event.get_debug_info("nonexistent") is None

    def test_annotation_management(self, mock_event_base):
        """测试注释管理"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试注释
        event.add_annotation("note", "This is a test note", "debug")
        annotation = event.get_annotation("note")

        assert annotation is not None
        assert annotation['value'] == "This is a test note"
        assert annotation['type'] == "debug"

        assert event.get_annotation("nonexistent") is None


# ===== 摘要测试 =====

@pytest.mark.unit
class TestEventMixinSummary:
    """EventMixin摘要测试"""

    def test_event_summary(self, mock_event_base):
        """测试事件摘要功能"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent(
            correlation_id="test_corr",
            priority=8,
            weight=1.5
        )

        # 添加测试数据
        event.add_tag("test_tag")
        event.add_category("test_category")
        event.add_processing_node("engine", "test_engine", 0.1, "completed")
        event.add_debug_info("test", "value")

        # 获取摘要
        summary = event.get_event_summary()

        # 验证摘要结构
        assert isinstance(summary, dict)

        # 验证必需字段存在
        required_fields = [
            'event_uuid', 'event_type', 'trace_info', 'timing',
            'relationships', 'processing_chain', 'classification', 'debug_info'
        ]
        for field in required_fields:
            assert field in summary, f"摘要应包含{field}字段"

        # 验证分类信息
        classification = summary['classification']
        assert classification['priority'] == 8
        assert classification['weight'] == 1.5
        assert "test_tag" in classification['tags']


# ===== 静态方法测试 =====

@pytest.mark.unit
class TestEventStaticMethods:
    """EventMixin静态方法测试"""

    def test_create_child_event(self, mock_event_base):
        """测试创建子事件"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        parent_event = TestEvent(
            correlation_id="parent_corr",
            session_id="parent_session"
        )

        child_event = TestEvent.create_child_event(
            parent_event,
            TestEvent,
            code="CHILD_001",
            priority=7
        )

        # 验证子事件继承关系
        assert child_event.parent_trace_id == parent_event.trace_id
        assert child_event.root_trace_id == parent_event.root_trace_id
        assert child_event.correlation_id == parent_event.correlation_id
        assert child_event.causation_id == parent_event._uuid

        # 验证双向关联
        assert parent_event.is_related_to(child_event._uuid)
        assert child_event.is_related_to(parent_event._uuid)

    def test_create_correlated_event(self, mock_event_base):
        """测试创建关联事件"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        parent_event = TestEvent(
            correlation_id="parent_corr",
            session_id="parent_session"
        )

        related_event = TestEvent.create_correlated_event(
            parent_event,
            TestEvent,
            code="RELATED_001",
            priority=6
        )

        # 验证关联事件关系
        assert parent_event.is_related_to(related_event._uuid)
        assert related_event.is_related_to(parent_event._uuid)


# ===== 并发测试 =====

@pytest.mark.unit
class TestEventMixinConcurrency:
    """EventMixin并发测试"""

    def test_concurrent_event_modifications(self, mock_event_base):
        """测试事件的并发修改安全性"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()
        results = []
        errors = []

        def modification_worker(worker_id):
            try:
                for i in range(10):
                    event.add_tag(f"tag_{worker_id}_{i}")
                    event.add_related_event(f"related_{worker_id}_{i}", "related")
                    node_id = event.add_processing_node("test", f"worker_{worker_id}", 0.001)
                    event.add_debug_info(f"key_{worker_id}_{i}", f"value_{worker_id}_{i}")

                    results.append({
                        'worker_id': worker_id,
                        'iteration': i
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
        assert len(errors) == 0, f"并发修改不应产生错误: {errors}"
        assert len(results) == 30


# ===== 边界情况测试 =====

@pytest.mark.unit
class TestEventMixinEdgeCases:
    """EventMixin边界情况测试"""

    def test_event_with_empty_trace_info(self, mock_event_base):
        """测试空追踪信息的事件"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 强制清空追踪信息
        event._trace_info = None

        # 测试各方法鲁棒性
        assert event.trace_id == event._uuid
        assert event.parent_trace_id is None
        assert event.root_trace_id is None
        assert event.correlation_id is None

        # 测试摘要生成
        summary = event.get_event_summary()
        assert isinstance(summary, dict)

    @pytest.mark.parametrize("long_string_length", [100, 1000, 10000])
    def test_event_with_long_strings(self, mock_event_base, long_string_length):
        """测试极长字符串 - 参数化"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()
        long_string = "x" * long_string_length

        event.add_debug_info("long_key", long_string)
        assert event.get_debug_info("long_key") == long_string

    def test_event_with_unicode_content(self, mock_event_base):
        """测试包含Unicode内容的事件"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 测试Unicode标签和注释
        unicode_tag = "测试标签_🔥_emoji"
        unicode_annotation = "测试注释_🚀_特殊字符"

        event.add_tag(unicode_tag)
        event.add_annotation("unicode_note", unicode_annotation)

        assert event.has_tag(unicode_tag)
        annotation = event.get_annotation("unicode_note")
        assert annotation['value'] == unicode_annotation

    def test_event_summary_with_missing_components(self, mock_event_base):
        """测试缺少组件时的事件摘要生成"""
        class TestEvent(mock_event_base, EventMixin):
            pass

        event = TestEvent()

        # 清空组件
        event._tags.clear()
        event._categories.clear()
        event._processing_chain.clear()
        event._debug_info.clear()
        event._annotations.clear()

        # 测试在这种情况下生成摘要
        summary = event.get_event_summary()

        assert isinstance(summary, dict)
        assert summary['classification']['tags'] == []
        assert summary['classification']['categories'] == []
        assert summary['processing_chain']['nodes_count'] == 0
