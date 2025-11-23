"""
流式查询会话上下文管理器

提供流式查询专用的会话生命周期管理，集成内存监控、
资源优化和异常处理功能，确保查询执行的稳定性和效率。

核心功能：
- 自动会话创建和清理
- 实时内存监控和优化
- 异常恢复和资源释放
- 查询性能指标收集
"""

import time
import uuid
from typing import Any, Dict, Optional, Generator, Union
from contextlib import contextmanager
from dataclasses import dataclass

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from ginkgo.data.streaming.monitoring import memory_monitor, session_manager, resource_optimizer, MemoryLevel, SessionState, MemorySnapshot
from ginkgo.data.streaming import StreamingState


@dataclass
class StreamingSessionContext:
    """流式查询会话上下文"""

    session_id: str
    database_type: str
    query_id: Optional[str]
    start_time: float
    memory_start_mb: float

    # 性能指标
    batches_processed: int = 0
    records_processed: int = 0
    memory_peak_mb: float = 0.0

    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        return time.time() - self.start_time

    @property
    def processing_rate(self) -> float:
        """处理速率（记录/秒）"""
        if self.elapsed_time > 0:
            return self.records_processed / self.elapsed_time
        return 0.0


class StreamingSessionManager:
    """流式查询会话管理器"""

    def __init__(self):
        self.active_contexts: Dict[str, StreamingSessionContext] = {}
        self._memory_warnings_count = 0
        self._auto_optimization_enabled = True

        # 确保监控器启动
        if not memory_monitor._monitoring:
            memory_monitor.start_monitoring()

        if not session_manager._cleanup_enabled:
            session_manager.start_cleanup()

        GLOG.DEBUG("StreamingSessionManager initialized")

    @contextmanager
    def create_streaming_session(
        self, database_type: str, query_id: Optional[str] = None, auto_optimize: bool = True
    ) -> Generator[StreamingSessionContext, None, None]:
        """
        创建流式查询会话上下文管理器

        Args:
            database_type: 数据库类型
            query_id: 查询ID（用于断点续传）
            auto_optimize: 是否启用自动优化

        Yields:
            StreamingSessionContext: 会话上下文
        """
        session_id = None
        context = None

        try:
            # 1. 创建会话
            session_id = session_manager.create_session(database_type=database_type, streaming_query_id=query_id)

            # 2. 获取初始内存状态
            initial_snapshot = memory_monitor.get_current_snapshot()

            # 3. 创建会话上下文
            context = StreamingSessionContext(
                session_id=session_id,
                database_type=database_type,
                query_id=query_id,
                start_time=time.time(),
                memory_start_mb=initial_snapshot.process_mb,
            )

            # 4. 激活会话
            session_manager.activate_session(session_id)
            self.active_contexts[session_id] = context

            # 5. 设置自动优化回调
            if auto_optimize:
                self._setup_session_optimization(context)

            GLOG.INFO(f"Created streaming session: {session_id} for {database_type}")

            yield context

        except Exception as e:
            GLOG.ERROR(f"Error in streaming session {session_id}: {e}")
            raise

        finally:
            # 清理会话
            if context:
                self._cleanup_session_context(context)

    def update_session_progress(self, session_id: str, batch_size: int, memory_mb: Optional[float] = None):
        """
        更新会话进度

        Args:
            session_id: 会话ID
            batch_size: 本批次处理的记录数
            memory_mb: 当前内存使用
        """
        context = self.active_contexts.get(session_id)
        if not context:
            return

        # 更新统计信息
        context.batches_processed += 1
        context.records_processed += batch_size

        if memory_mb and memory_mb > context.memory_peak_mb:
            context.memory_peak_mb = memory_mb

        # 检查内存状态
        if self._auto_optimization_enabled:
            self._check_memory_optimization(context)

    def get_session_metrics(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        获取会话指标

        Args:
            session_id: 会话ID

        Returns:
            会话指标字典
        """
        context = self.active_contexts.get(session_id)
        if not context:
            return None

        current_snapshot = memory_monitor.get_current_snapshot()

        return {
            "session_id": session_id,
            "database_type": context.database_type,
            "query_id": context.query_id,
            "elapsed_time": context.elapsed_time,
            "batches_processed": context.batches_processed,
            "records_processed": context.records_processed,
            "processing_rate": context.processing_rate,
            "memory_start_mb": context.memory_start_mb,
            "memory_current_mb": current_snapshot.process_mb,
            "memory_peak_mb": context.memory_peak_mb,
            "memory_delta_mb": current_snapshot.process_mb - context.memory_start_mb,
            "memory_level": current_snapshot.level.value,
        }

    def list_active_sessions(self) -> List[Dict[str, Any]]:
        """列出所有活跃会话"""
        return [self.get_session_metrics(session_id) for session_id in self.active_contexts.keys()]

    def force_session_cleanup(self, session_id: str) -> bool:
        """
        强制清理会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功清理
        """
        context = self.active_contexts.get(session_id)
        if context:
            self._cleanup_session_context(context)
            return True
        return False

    def _setup_session_optimization(self, context: StreamingSessionContext):
        """设置会话优化"""
        # 这里可以根据会话类型设置特定的优化策略
        GLOG.DEBUG(f"Set up optimization for session: {context.session_id}")

    def _check_memory_optimization(self, context: StreamingSessionContext):
        """检查内存优化"""
        current_snapshot = memory_monitor.get_current_snapshot()

        # 如果内存使用过高，记录警告
        if current_snapshot.level in [MemoryLevel.CRITICAL, MemoryLevel.EMERGENCY]:
            self._memory_warnings_count += 1

            GLOG.WARNING(
                f"High memory usage in session {context.session_id}: "
                f"{current_snapshot.percent:.1f}% "
                f"(processed: {context.records_processed} records)"
            )

            # 如果连续警告，考虑降低批次大小等优化措施
            if self._memory_warnings_count >= 3:
                GLOG.WARNING(f"Multiple memory warnings for session {context.session_id}, consider optimization")
                self._memory_warnings_count = 0  # 重置计数器

    def _cleanup_session_context(self, context: StreamingSessionContext):
        """清理会话上下文"""
        try:
            session_id = context.session_id

            # 1. 取消激活会话
            session_manager.deactivate_session(session_id, memory_used_mb=context.memory_peak_mb)

            # 2. 从活跃会话中移除
            self.active_contexts.pop(session_id, None)

            # 3. 记录会话统计
            GLOG.INFO(
                f"Session {session_id} completed: "
                f"{context.records_processed} records processed, "
                f"{context.batches_processed} batches, "
                f"{context.elapsed_time:.2f}s elapsed, "
                f"rate: {context.processing_rate:.1f} records/sec, "
                f"peak memory: {context.memory_peak_mb:.1f}MB"
            )

            # 4. 关闭会话
            session_manager.close_session(session_id)

        except Exception as e:
            GLOG.ERROR(f"Error cleaning up session context: {e}")


class MemoryAwareSessionContext:
    """内存感知的会话上下文装饰器"""

    def __init__(self, memory_limit_mb: Optional[float] = None, batch_size_auto_adjust: bool = True):
        """
        初始化内存感知会话上下文

        Args:
            memory_limit_mb: 内存限制（MB），超出时自动优化
            batch_size_auto_adjust: 是否自动调整批次大小
        """
        self.memory_limit_mb = memory_limit_mb
        self.batch_size_auto_adjust = batch_size_auto_adjust
        self._initial_batch_size = None
        self._current_batch_size = None

    def __call__(self, func):
        """装饰器函数"""

        def wrapper(*args, **kwargs):
            # 提取批次大小参数
            if "batch_size" in kwargs:
                self._initial_batch_size = kwargs["batch_size"]
                self._current_batch_size = kwargs["batch_size"]

            # 添加内存监控回调
            if self.memory_limit_mb:
                memory_monitor.add_callback(MemoryLevel.WARNING, self._handle_memory_pressure)

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                # 清理回调
                pass  # 回调会在监控器停止时自动清理

        return wrapper

    def _handle_memory_pressure(self, snapshot: MemorySnapshot):
        """处理内存压力"""
        if not self.batch_size_auto_adjust or not self._current_batch_size:
            return

        if snapshot.process_mb > (self.memory_limit_mb or 1000):
            # 减小批次大小
            new_batch_size = max(int(self._current_batch_size * 0.8), 100)  # 最小批次大小

            if new_batch_size != self._current_batch_size:
                GLOG.WARNING(
                    f"Reducing batch size due to memory pressure: " f"{self._current_batch_size} -> {new_batch_size}"
                )
                self._current_batch_size = new_batch_size


# 全局会话管理器实例
streaming_session_manager = StreamingSessionManager()


# 便利函数
@contextmanager
def streaming_session(database_type: str, query_id: Optional[str] = None, auto_optimize: bool = True):
    """
    便利的流式查询会话上下文管理器

    Args:
        database_type: 数据库类型
        query_id: 查询ID
        auto_optimize: 是否自动优化

    Yields:
        StreamingSessionContext: 会话上下文
    """
    with streaming_session_manager.create_streaming_session(
        database_type=database_type, query_id=query_id, auto_optimize=auto_optimize
    ) as session_context:
        yield session_context


def memory_aware(memory_limit_mb: Optional[float] = None, batch_size_auto_adjust: bool = True):
    """
    内存感知装饰器

    Args:
        memory_limit_mb: 内存限制
        batch_size_auto_adjust: 是否自动调整批次大小

    Returns:
        装饰器函数
    """
    return MemoryAwareSessionContext(memory_limit_mb=memory_limit_mb, batch_size_auto_adjust=batch_size_auto_adjust)
