"""
流式查询引擎抽象基类

提供流式查询的标准接口和通用框架，定义了流式查询的核心流程，
支持多数据库的统一接口和插件化扩展。

设计模式：
- Template Method: 标准化查询流程
- Strategy: 支持不同数据库策略
- Observer: 支持进度监听
- State: 管理查询状态
"""

import time
import uuid
import threading
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Iterator, Optional, Callable, Union
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from .. import StreamingState, ProgressInfo, QueryState, StreamingEngineError
from ..config import StreamingConfig


class CursorType(Enum):
    """游标类型"""

    CLIENT_SIDE = "client_side"
    SERVER_SIDE = "server_side"
    NATIVE_STREAMING = "native_streaming"


@dataclass
class StreamingMetrics:
    """流式查询指标"""

    query_id: str
    total_processed: int = 0
    total_batches: int = 0
    start_time: float = 0.0
    end_time: Optional[float] = None
    average_batch_size: float = 0.0
    processing_rate: float = 0.0  # records per second
    memory_peak_mb: float = 0.0
    error_count: int = 0

    @property
    def elapsed_time(self) -> float:
        """已用时间"""
        if self.end_time:
            return self.end_time - self.start_time
        return time.time() - self.start_time

    @property
    def is_completed(self) -> bool:
        """是否已完成"""
        return self.end_time is not None


class ProgressObserver(ABC):
    """进度观察者接口"""

    @abstractmethod
    def on_progress_update(self, progress: ProgressInfo) -> None:
        """进度更新回调"""
        pass

    @abstractmethod
    def on_batch_processed(self, batch_index: int, batch_size: int) -> None:
        """批次处理完成回调"""
        pass

    @abstractmethod
    def on_error(self, error: Exception) -> None:
        """错误发生回调"""
        pass


class BaseStreamingEngine(ABC):
    """流式查询引擎抽象基类"""

    def __init__(self, connection, config: StreamingConfig):
        """
        初始化流式查询引擎

        Args:
            connection: 数据库连接或连接池
            config: 流式查询配置
        """
        self.connection = connection
        self.config = config
        self.query_id = str(uuid.uuid4())
        self.state = StreamingState.IDLE
        self.metrics = StreamingMetrics(query_id=self.query_id)
        self.observers: List[ProgressObserver] = []
        self._lock = threading.Lock()

        # 内部状态
        self._current_batch_index = 0
        self._total_processed = 0
        self._last_progress_update = 0.0

        GLOG.DEBUG(f"StreamingEngine initialized with query_id: {self.query_id}")

    # ==================== 抽象方法 - 子类必须实现 ====================

    @abstractmethod
    def _create_streaming_cursor(self, query: str, params: Optional[Dict] = None) -> Any:
        """
        创建流式查询游标

        Args:
            query: SQL查询语句
            params: 查询参数

        Returns:
            数据库特定的流式游标对象
        """
        pass

    @abstractmethod
    def _optimize_query_for_streaming(self, query: str, filters: Dict[str, Any]) -> str:
        """
        优化查询语句用于流式处理

        Args:
            query: 原始查询语句
            filters: 查询过滤条件

        Returns:
            优化后的查询语句
        """
        pass

    @abstractmethod
    def _execute_streaming_query(self, cursor: Any, batch_size: int) -> Iterator[List[Any]]:
        """
        执行流式查询并返回批次迭代器

        Args:
            cursor: 流式查询游标
            batch_size: 批次大小

        Yields:
            每批查询结果
        """
        pass

    @abstractmethod
    def _cleanup_cursor(self, cursor: Any) -> None:
        """
        清理游标资源

        Args:
            cursor: 需要清理的游标
        """
        pass

    @abstractmethod
    def get_db_type(self) -> str:
        """获取数据库类型"""
        pass

    # ==================== 模板方法 - 标准流程实现 ====================

    def execute_stream(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        batch_size: Optional[int] = None,
        params: Optional[Dict] = None,
    ) -> Iterator[List[Any]]:
        """
        执行流式查询的标准流程

        Args:
            query: SQL查询语句
            filters: 查询过滤条件
            batch_size: 批次大小
            params: 查询参数

        Yields:
            每批查询结果

        Raises:
            StreamingEngineError: 查询执行失败
        """
        # 参数初始化和验证
        filters = filters or {}
        batch_size = batch_size or self.config.performance.default_batch_size
        params = params or {}

        # 重置状态
        self._reset_state()

        try:
            # 1. 查询前准备
            self._pre_query_setup()

            # 2. 优化查询
            optimized_query = self._optimize_query_for_streaming(query, filters)
            GLOG.DEBUG(f"Optimized query for streaming: {optimized_query[:200]}...")

            # 3. 创建游标
            cursor = self._create_streaming_cursor(optimized_query, params)

            # 4. 执行流式查询
            self.state = StreamingState.RUNNING
            self.metrics.start_time = time.time()

            try:
                for batch in self._execute_streaming_query(cursor, batch_size):
                    # 处理批次结果
                    processed_batch = self._process_batch(batch)

                    # 更新统计信息
                    self._update_metrics(len(processed_batch))

                    # 通知观察者
                    self._notify_batch_processed(len(processed_batch))

                    # 检查是否需要更新进度
                    self._check_and_update_progress()

                    yield processed_batch

                # 查询完成
                self.state = StreamingState.COMPLETED
                self.metrics.end_time = time.time()

                GLOG.INFO(
                    f"Streaming query completed. Total processed: {self.metrics.total_processed}, "
                    f"Time: {self.metrics.elapsed_time:.2f}s, "
                    f"Rate: {self.metrics.processing_rate:.1f} records/sec"
                )

            finally:
                # 清理游标
                self._cleanup_cursor(cursor)

        except Exception as e:
            self.state = StreamingState.FAILED
            self.metrics.error_count += 1
            error_msg = f"Streaming query failed: {e}"
            GLOG.ERROR(error_msg)

            # 通知观察者
            self._notify_error(e)

            raise StreamingEngineError(error_msg) from e
        finally:
            # 后处理清理
            self._post_query_cleanup()

    def execute_stream_with_checkpoint(
        self, query: str, checkpoint_state: Optional[QueryState] = None, **kwargs
    ) -> Iterator[List[Any]]:
        """
        执行支持断点续传的流式查询

        Args:
            query: SQL查询语句
            checkpoint_state: 断点状态
            **kwargs: 其他参数

        Yields:
            每批查询结果
        """
        if checkpoint_state:
            # 从断点继续
            GLOG.INFO(
                f"Resuming streaming query from checkpoint. "
                f"Processed: {checkpoint_state.processed_count}, "
                f"Offset: {checkpoint_state.last_offset}"
            )

            # 调整查询起始位置
            filters = kwargs.get("filters", {})
            if checkpoint_state.last_timestamp:
                filters["timestamp__gte"] = checkpoint_state.last_timestamp

            kwargs["filters"] = filters
            kwargs["batch_size"] = checkpoint_state.batch_size

            # 更新内部状态
            self._total_processed = checkpoint_state.processed_count
            self._current_batch_index = checkpoint_state.last_offset // checkpoint_state.batch_size

        # 执行常规流式查询
        yield from self.execute_stream(query, **kwargs)

    # ==================== 观察者模式支持 ====================

    def add_observer(self, observer: ProgressObserver) -> None:
        """添加进度观察者"""
        with self._lock:
            if observer not in self.observers:
                self.observers.append(observer)
                GLOG.DEBUG(f"Added progress observer: {observer.__class__.__name__}")

    def remove_observer(self, observer: ProgressObserver) -> None:
        """移除进度观察者"""
        with self._lock:
            if observer in self.observers:
                self.observers.remove(observer)
                GLOG.DEBUG(f"Removed progress observer: {observer.__class__.__name__}")

    def _notify_progress_update(self, progress: ProgressInfo) -> None:
        """通知进度更新"""
        for observer in self.observers:
            try:
                observer.on_progress_update(progress)
            except Exception as e:
                GLOG.WARNING(f"Observer {observer.__class__.__name__} failed to handle progress update: {e}")

    def _notify_batch_processed(self, batch_size: int) -> None:
        """通知批次处理完成"""
        for observer in self.observers:
            try:
                observer.on_batch_processed(self._current_batch_index, batch_size)
            except Exception as e:
                GLOG.WARNING(f"Observer {observer.__class__.__name__} failed to handle batch processed: {e}")

    def _notify_error(self, error: Exception) -> None:
        """通知错误发生"""
        for observer in self.observers:
            try:
                observer.on_error(error)
            except Exception as e:
                GLOG.WARNING(f"Observer {observer.__class__.__name__} failed to handle error: {e}")

    # ==================== 内部辅助方法 ====================

    def _reset_state(self) -> None:
        """重置查询状态"""
        self.state = StreamingState.INITIALIZING
        self.metrics = StreamingMetrics(query_id=self.query_id)
        self._current_batch_index = 0
        self._total_processed = 0
        self._last_progress_update = 0.0

    def _pre_query_setup(self) -> None:
        """查询前设置（子类可重写）"""
        GLOG.DEBUG(f"Pre-query setup for {self.get_db_type()} streaming engine")

    def _post_query_cleanup(self) -> None:
        """查询后清理（子类可重写）"""
        GLOG.DEBUG(f"Post-query cleanup for {self.get_db_type()} streaming engine")

    def _process_batch(self, batch: List[Any]) -> List[Any]:
        """处理批次数据（子类可重写以进行数据转换）"""
        return batch

    def _update_metrics(self, batch_size: int) -> None:
        """更新查询指标"""
        with self._lock:
            self._current_batch_index += 1
            self._total_processed += batch_size

            # 更新指标
            self.metrics.total_processed = self._total_processed
            self.metrics.total_batches = self._current_batch_index

            if self.metrics.total_batches > 0:
                self.metrics.average_batch_size = self.metrics.total_processed / self.metrics.total_batches

            # 计算处理速率
            elapsed = time.time() - self.metrics.start_time
            if elapsed > 0:
                self.metrics.processing_rate = self.metrics.total_processed / elapsed

    def _check_and_update_progress(self) -> None:
        """检查并更新进度"""
        current_time = time.time()

        # 根据配置的间隔更新进度
        if (current_time - self._last_progress_update) >= self.config.monitoring.progress_update_interval:
            progress = ProgressInfo(
                processed=self.metrics.total_processed,
                rate=self.metrics.processing_rate,
                elapsed=self.metrics.elapsed_time,
            )

            self._notify_progress_update(progress)
            self._last_progress_update = current_time

    # ==================== 公共接口方法 ====================

    def get_metrics(self) -> StreamingMetrics:
        """获取查询指标"""
        return self.metrics

    def get_state(self) -> StreamingState:
        """获取当前状态"""
        return self.state

    def is_running(self) -> bool:
        """是否正在运行"""
        return self.state == StreamingState.RUNNING

    def is_completed(self) -> bool:
        """是否已完成"""
        return self.state == StreamingState.COMPLETED

    def is_failed(self) -> bool:
        """是否失败"""
        return self.state == StreamingState.FAILED

    @contextmanager
    def streaming_session(self):
        """流式查询会话上下文管理器"""
        session_start = time.time()
        GLOG.DEBUG(f"Starting streaming session for {self.get_db_type()}")

        try:
            yield self
        finally:
            session_duration = time.time() - session_start
            GLOG.DEBUG(f"Streaming session completed in {session_duration:.2f}s")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"query_id={self.query_id[:8]}..., "
            f"state={self.state.value}, "
            f"processed={self.metrics.total_processed})"
        )


class StreamingCursor(ABC):
    """流式查询游标抽象基类"""

    @abstractmethod
    def __iter__(self):
        """迭代器接口"""
        pass

    @abstractmethod
    def __next__(self):
        """获取下一条记录"""
        pass

    @abstractmethod
    def close(self):
        """关闭游标"""
        pass

    @abstractmethod
    def fetchmany(self, size: int) -> List[Any]:
        """批量获取记录"""
        pass
