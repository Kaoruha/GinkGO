# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: EventMixin事件混入类提供事件处理能力支持事件订阅/发布和分发机制集成实现事件通信支持交易系统功能和组件集成提供完整业务支持






"""
EventMixin - 事件数据模型增强

提供事件关联ID和会话追踪功能，增强事件系统的可追踪性和调试能力。

主要功能：
1. 关联ID管理 - 支持事件间的关联追踪
2. 会话追踪 - 跟踪事件在会话中的流转
3. 事件链路追踪 - 追踪事件的完整处理链路
4. 元数据增强 - 为事件添加丰富的元数据
5. 调试支持 - 提供事件调试和诊断信息

使用方式：
    class EnhancedPriceUpdate(EventPriceUpdate, EventMixin):
        def __init__(self, **kwargs):
            super().__init__(**kwargs)
            # 自动获得EventMixin的所有功能

Author: TDD Framework
Created: 2024-01-17
"""

import uuid
import time
from typing import Dict, Any, List, Optional, Set
from datetime import datetime
from dataclasses import dataclass, field
import threading


@dataclass
class EventTraceInfo:
    """事件追踪信息"""
    trace_id: str
    parent_trace_id: Optional[str] = None
    root_trace_id: Optional[str] = None
    correlation_id: Optional[str] = None
    causation_id: Optional[str] = None  # 引起此事件的事件ID
    session_id: Optional[str] = None
    chain_id: Optional[str] = None  # 事件链ID
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EventProcessingNode:
    """事件处理节点信息"""
    node_id: str
    node_type: str  # 'engine', 'portfolio', 'strategy', 'risk'
    node_name: str
    timestamp: datetime
    processing_duration: float = 0.0
    status: str = 'started'  # 'started', 'completed', 'failed'
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class EventMixin:
    """
    事件数据模型增强混入类

    为事件类提供关联ID、会话追踪和链路追踪功能。
    """

    def __init__(self, *args, **kwargs):
        """
        初始化事件增强功能

        注意：这个方法会在具体事件类.__init__之后调用
        """
        # 确保父类已经初始化
        if not hasattr(self, '_uuid'):
            raise RuntimeError("EventMixin requires EventBase to be initialized first")

        # 事件追踪信息
        self._trace_info: Optional[EventTraceInfo] = None

        # 事件处理链路
        self._processing_chain: List[EventProcessingNode] = []
        self._chain_lock = threading.Lock()

        # 事件关联信息
        self._related_events: Set[str] = set()
        self._child_events: Set[str] = set()
        self._related_lock = threading.Lock()

        # 事件标签和分类
        self._tags: Set[str] = set()
        self._categories: Set[str] = set()

        # 性能指标
        self._creation_time: datetime = datetime.now()
        self._first_processed_time: Optional[datetime] = None
        self._last_processed_time: Optional[datetime] = None
        self._total_processing_time: float = 0.0

        # 优先级和权重
        self._priority: int = kwargs.get('priority', 5)  # 1-10, 10最高
        self._weight: float = kwargs.get('weight', 1.0)

        # 调试信息
        self._debug_info: Dict[str, Any] = {}
        self._annotations: Dict[str, Any] = {}

        # 初始化追踪信息
        self._initialize_trace_info(kwargs)

    def _initialize_trace_info(self, kwargs: Dict[str, Any]):
        """初始化事件追踪信息"""
        # 从参数中获取追踪相关信息
        trace_id = kwargs.get('trace_id') or f"trace_{uuid.uuid4().hex[:12]}"
        parent_trace_id = kwargs.get('parent_trace_id')
        correlation_id = kwargs.get('correlation_id') or kwargs.get('correlation_id')
        causation_id = kwargs.get('causation_id')
        session_id = kwargs.get('session_id') or getattr(self, 'run_id', None)
        chain_id = kwargs.get('chain_id') or f"chain_{uuid.uuid4().hex[:12]}"

        # 确定根追踪ID
        root_trace_id = kwargs.get('root_trace_id')
        if not root_trace_id:
            if parent_trace_id:
                root_trace_id = parent_trace_id
            else:
                root_trace_id = trace_id

        self._trace_info = EventTraceInfo(
            trace_id=trace_id,
            parent_trace_id=parent_trace_id,
            root_trace_id=root_trace_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
            session_id=session_id,
            chain_id=chain_id,
            metadata=kwargs.get('trace_metadata', {})
        )

    # ========== 关联ID管理 ==========

    @property
    def trace_id(self) -> str:
        """获取事件追踪ID"""
        return self._trace_info.trace_id if self._trace_info else self._uuid

    @property
    def parent_trace_id(self) -> Optional[str]:
        """获取父事件追踪ID"""
        return self._trace_info.parent_trace_id if self._trace_info else None

    @property
    def root_trace_id(self) -> Optional[str]:
        """获取根事件追踪ID"""
        return self._trace_info.root_trace_id if self._trace_info else None

    @property
    def correlation_id(self) -> Optional[str]:
        """获取关联ID"""
        return self._trace_info.correlation_id if self._trace_info else None

    @correlation_id.setter
    def correlation_id(self, value: str) -> None:
        """设置关联ID"""
        if self._trace_info:
            self._trace_info.correlation_id = value

    @property
    def causation_id(self) -> Optional[str]:
        """获取因果事件ID"""
        return self._trace_info.causation_id if self._trace_info else None

    @causation_id.setter
    def causation_id(self, value: str) -> None:
        """设置因果事件ID"""
        if self._trace_info:
            self._trace_info.causation_id = value

    @property
    def chain_id(self) -> Optional[str]:
        """获取事件链ID"""
        return self._trace_info.chain_id if self._trace_info else None

    @property
    def session_id(self) -> Optional[str]:
        """获取会话ID"""
        return self._trace_info.session_id if self._trace_info else None

    def set_correlation_id(self, correlation_id: str) -> None:
        """设置关联ID（便捷方法）"""
        self.correlation_id = correlation_id

    def set_causation_id(self, causation_id: str) -> None:
        """设置因果事件ID（便捷方法）"""
        self.causation_id = causation_id

    # ========== 事件关联管理 ==========

    def add_related_event(self, event_id: str, relation_type: str = 'related') -> None:
        """
        添加关联事件

        Args:
            event_id: 关联事件ID
            relation_type: 关系类型 ('related', 'child', 'parent')
        """
        with self._related_lock:
            if relation_type == 'child':
                self._child_events.add(event_id)
            else:
                self._related_events.add(event_id)

    def get_related_events(self) -> List[str]:
        """获取所有关联事件ID"""
        with self._related_lock:
            return list(self._related_events)

    def get_child_events(self) -> List[str]:
        """获取所有子事件ID"""
        with self._related_lock:
            return list(self._child_events)

    def is_related_to(self, event_id: str) -> bool:
        """检查是否与指定事件关联"""
        with self._related_lock:
            return event_id in self._related_events or event_id in self._child_events

    # ========== 事件链路追踪 ==========

    def add_processing_node(self, node_type: str, node_name: str,
                          processing_duration: float = 0.0,
                          status: str = 'started',
                          error_message: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        添加事件处理节点

        Args:
            node_type: 节点类型 ('engine', 'portfolio', 'strategy', 'risk')
            node_name: 节点名称
            processing_duration: 处理时长（秒）
            status: 处理状态 ('started', 'completed', 'failed')
            error_message: 错误信息（如果有）
            metadata: 节点元数据

        Returns:
            str: 节点ID
        """
        node_id = f"node_{uuid.uuid4().hex[:8]}_{int(time.time() * 1000)}"

        node = EventProcessingNode(
            node_id=node_id,
            node_type=node_type,
            node_name=node_name,
            timestamp=datetime.now(),
            processing_duration=processing_duration,
            status=status,
            error_message=error_message,
            metadata=metadata or {}
        )

        with self._chain_lock:
            self._processing_chain.append(node)

        # 更新处理时间统计
        self._update_processing_stats(processing_duration, status)

        return node_id

    def update_processing_node(self, node_id: str, status: str = None,
                             processing_duration: float = None,
                             error_message: str = None) -> bool:
        """
        更新事件处理节点

        Args:
            node_id: 节点ID
            status: 新状态
            processing_duration: 处理时长
            error_message: 错误信息

        Returns:
            bool: 是否更新成功
        """
        with self._chain_lock:
            for node in self._processing_chain:
                if node.node_id == node_id:
                    if status is not None:
                        node.status = status
                    if processing_duration is not None:
                        node.processing_duration = processing_duration
                    if error_message is not None:
                        node.error_message = error_message
                    node.timestamp = datetime.now()

                    self._update_processing_stats(processing_duration, status)
                    return True
        return False

    def get_processing_chain(self) -> List[EventProcessingNode]:
        """获取事件处理链路"""
        with self._chain_lock:
            return self._processing_chain.copy()

    def get_processing_nodes_by_type(self, node_type: str) -> List[EventProcessingNode]:
        """根据类型获取处理节点"""
        with self._chain_lock:
            return [node for node in self._processing_chain if node.node_type == node_type]

    def _update_processing_stats(self, duration: float, status: str):
        """更新处理统计信息"""
        now = datetime.now()

        if self._first_processed_time is None:
            self._first_processed_time = now

        self._last_processed_time = now

        if duration > 0:
            self._total_processing_time += duration

    # ========== 标签和分类 ==========

    def add_tag(self, tag: str) -> None:
        """添加事件标签"""
        self._tags.add(tag)

    def remove_tag(self, tag: str) -> None:
        """移除事件标签"""
        self._tags.discard(tag)

    def has_tag(self, tag: str) -> bool:
        """检查是否包含指定标签"""
        return tag in self._tags

    def get_tags(self) -> List[str]:
        """获取所有标签"""
        return list(self._tags)

    def add_category(self, category: str) -> None:
        """添加事件分类"""
        self._categories.add(category)

    def get_categories(self) -> List[str]:
        """获取所有分类"""
        return list(self._categories)

    # ========== 优先级和权重 ==========

    @property
    def priority(self) -> int:
        """获取事件优先级"""
        return self._priority

    @priority.setter
    def priority(self, value: int) -> None:
        """设置事件优先级 (1-10)"""
        if 1 <= value <= 10:
            self._priority = value
        else:
            raise ValueError("Priority must be between 1 and 10")

    @property
    def weight(self) -> float:
        """获取事件权重"""
        return self._weight

    @weight.setter
    def weight(self, value: float) -> None:
        """设置事件权重"""
        if value > 0:
            self._weight = value
        else:
            raise ValueError("Weight must be positive")

    # ========== 调试支持 ==========

    def add_debug_info(self, key: str, value: Any) -> None:
        """添加调试信息"""
        self._debug_info[key] = value

    def get_debug_info(self, key: str) -> Any:
        """获取调试信息"""
        return self._debug_info.get(key)

    def add_annotation(self, key: str, value: Any, annotation_type: str = 'general') -> None:
        """添加事件注释"""
        self._annotations[key] = {
            'value': value,
            'type': annotation_type,
            'timestamp': datetime.now()
        }

    def get_annotation(self, key: str) -> Optional[Dict[str, Any]]:
        """获取事件注释"""
        return self._annotations.get(key)

    def get_event_summary(self) -> Dict[str, Any]:
        """
        获取事件摘要信息

        Returns:
            Dict: 事件的详细摘要
        """
        processing_duration = 0.0
        if self._first_processed_time and self._last_processed_time:
            processing_duration = (self._last_processed_time - self._first_processed_time).total_seconds()

        return {
            'event_uuid': self._uuid,
            'event_type': getattr(self, 'event_type', 'Unknown'),
            'trace_info': {
                'trace_id': self.trace_id,
                'parent_trace_id': self.parent_trace_id,
                'root_trace_id': self.root_trace_id,
                'correlation_id': self.correlation_id,
                'causation_id': self.causation_id,
                'chain_id': self.chain_id,
                'session_id': self.session_id
            },
            'timing': {
                'created_at': self._creation_time,
                'first_processed': self._first_processed_time,
                'last_processed': self._last_processed_time,
                'total_processing_time': self._total_processing_time,
                'processing_duration': processing_duration
            },
            'relationships': {
                'related_events_count': len(self._related_events),
                'child_events_count': len(self._child_events),
                'related_events': list(self._related_events),
                'child_events': list(self._child_events)
            },
            'processing_chain': {
                'nodes_count': len(self._processing_chain),
                'nodes': [
                    {
                        'node_id': node.node_id,
                        'node_type': node.node_type,
                        'node_name': node.node_name,
                        'timestamp': node.timestamp,
                        'duration': node.processing_duration,
                        'status': node.status
                    }
                    for node in self._processing_chain
                ]
            },
            'classification': {
                'tags': list(self._tags),
                'categories': list(self._categories),
                'priority': self._priority,
                'weight': self._weight
            },
            'debug_info': {
                'annotations': self._annotations,
                'debug_data': self._debug_info
            }
        }

    # ========== 静态方法：事件创建 ==========

    @staticmethod
    def create_child_event(parent_event, event_class, **kwargs):
        """
        创建子事件

        Args:
            parent_event: 父事件
            event_class: 子事件类
            **kwargs: 子事件构造参数

        Returns:
            子事件实例
        """
        # 继承父事件的追踪信息
        child_kwargs = {
            'parent_trace_id': parent_event.trace_id,
            'root_trace_id': parent_event.root_trace_id,
            'correlation_id': parent_event.correlation_id,
            'causation_id': parent_event._uuid,
            'session_id': parent_event.session_id,
            'chain_id': parent_event.chain_id,
            **kwargs
        }

        child = event_class(**child_kwargs)

        # 建立父子关系
        parent_event.add_related_event(child._uuid, 'child')
        child.add_related_event(parent_event._uuid, 'parent')

        return child

    @staticmethod
    def create_correlated_event(source_event, event_class, **kwargs):
        """
        创建关联事件

        Args:
            source_event: 源事件
            event_class: 事件类
            **kwargs: 事件构造参数

        Returns:
            关联事件实例
        """
        correlated_kwargs = {
            'correlation_id': source_event.correlation_id or source_event._uuid,
            'session_id': source_event.session_id,
            **kwargs
        }

        correlated_event = event_class(**correlated_kwargs)

        # 建立关联关系
        source_event.add_related_event(correlated_event._uuid, 'related')
        correlated_event.add_related_event(source_event._uuid, 'related')

        return correlated_event

    # ========== 兼容性方法 ==========

    def __str__(self) -> str:
        """字符串表示"""
        base_info = f"{self.__class__.__name__}(uuid={self._uuid[:8]})"
        if self.correlation_id:
            base_info += f"[corr={self.correlation_id[:8]}]"
        return base_info

    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"<{self.__class__.__name__} uuid={self._uuid} trace={self.trace_id} correlation={self.correlation_id}>"