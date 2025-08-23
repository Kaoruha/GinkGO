"""
流式查询断点续传和进度跟踪系统

提供完整的查询状态持久化、断点管理和实时进度跟踪功能，
确保长时间流式查询的可靠性和可恢复性。

核心功能：
- 查询状态持久化和恢复
- 基于时间戳的精确断点定位
- 实时进度跟踪和性能监控
- 多查询并发断点管理
"""

import json
import time
import uuid
import hashlib
from typing import Any, Dict, List, Optional, Callable, Union
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from contextlib import contextmanager

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from . import QueryState, ProgressInfo, StreamingState


@dataclass
class CheckpointInfo:
    """断点信息"""

    checkpoint_id: str
    query_hash: str
    query_text: str
    filters: Dict[str, Any]
    batch_size: int

    # 断点位置信息
    processed_count: int
    last_offset: int
    last_timestamp: Optional[str]
    last_record_id: Optional[str]

    # 时间信息
    created_at: float
    updated_at: float
    expires_at: Optional[float]

    # 状态信息
    state: StreamingState
    progress_percentage: float
    estimated_total: Optional[int]

    # 性能指标
    processing_rate: float
    elapsed_time: float
    memory_peak_mb: float

    # 元数据
    database_type: str
    engine_type: str
    user_context: Optional[Dict[str, Any]] = None


@dataclass
class ProgressTracker:
    """进度跟踪器"""

    tracker_id: str
    query_hash: str

    # 进度信息
    total_processed: int = 0
    current_batch: int = 0
    estimated_total: Optional[int] = None

    # 时间信息
    start_time: float = 0.0
    last_update_time: float = 0.0
    estimated_completion_time: Optional[float] = None

    # 性能指标
    processing_rate: float = 0.0  # records per second
    average_batch_time: float = 0.0
    peak_memory_mb: float = 0.0

    # 回调函数
    progress_callbacks: List[Callable[[ProgressInfo], None]] = None

    def __post_init__(self):
        if self.progress_callbacks is None:
            self.progress_callbacks = []
        if self.start_time == 0.0:
            self.start_time = time.time()
            self.last_update_time = self.start_time


class CheckpointManager:
    """断点管理器"""

    def __init__(self, storage_backend: Optional[Any] = None, default_ttl: int = 86400):  # 24小时默认TTL
        """
        初始化断点管理器

        Args:
            storage_backend: 存储后端（Redis/文件系统等）
            default_ttl: 断点默认存活时间（秒）
        """
        self.storage_backend = storage_backend
        self.default_ttl = default_ttl
        self.active_checkpoints: Dict[str, CheckpointInfo] = {}
        self.checkpoint_prefix = "ginkgo:streaming:checkpoint:"

        # 如果没有存储后端，使用内存存储
        if self.storage_backend is None:
            self._use_memory_storage = True
            self._memory_storage: Dict[str, str] = {}
        else:
            self._use_memory_storage = False

        GLOG.DEBUG("CheckpointManager initialized")

    def create_checkpoint(
        self, query: str, filters: Dict[str, Any], batch_size: int, database_type: str, engine_type: str, **kwargs
    ) -> str:
        """
        创建新的查询断点

        Args:
            query: SQL查询语句
            filters: 查询过滤条件
            batch_size: 批处理大小
            database_type: 数据库类型
            engine_type: 引擎类型
            **kwargs: 其他参数

        Returns:
            断点ID
        """
        try:
            # 生成查询哈希
            query_hash = self._generate_query_hash(query, filters)

            # 检查是否存在现有断点
            existing_checkpoint = self._find_existing_checkpoint(query_hash)
            if existing_checkpoint:
                GLOG.INFO(f"Found existing checkpoint: {existing_checkpoint.checkpoint_id}")
                return existing_checkpoint.checkpoint_id

            # 创建新断点
            checkpoint_id = str(uuid.uuid4())
            current_time = time.time()

            checkpoint = CheckpointInfo(
                checkpoint_id=checkpoint_id,
                query_hash=query_hash,
                query_text=query,
                filters=filters,
                batch_size=batch_size,
                processed_count=0,
                last_offset=0,
                last_timestamp=None,
                last_record_id=None,
                created_at=current_time,
                updated_at=current_time,
                expires_at=current_time + self.default_ttl,
                state=StreamingState.INITIALIZING,
                progress_percentage=0.0,
                estimated_total=kwargs.get("estimated_total"),
                processing_rate=0.0,
                elapsed_time=0.0,
                memory_peak_mb=0.0,
                database_type=database_type,
                engine_type=engine_type,
                user_context=kwargs.get("user_context"),
            )

            # 保存断点
            self._save_checkpoint(checkpoint)
            self.active_checkpoints[checkpoint_id] = checkpoint

            GLOG.INFO(f"Created checkpoint: {checkpoint_id} for query hash: {query_hash[:8]}...")
            return checkpoint_id

        except Exception as e:
            GLOG.ERROR(f"Failed to create checkpoint: {e}")
            raise

    def update_checkpoint(self, checkpoint_id: str, **updates) -> bool:
        """
        更新断点信息

        Args:
            checkpoint_id: 断点ID
            **updates: 更新的字段

        Returns:
            是否更新成功
        """
        try:
            checkpoint = self.get_checkpoint(checkpoint_id)
            if not checkpoint:
                GLOG.WARNING(f"Checkpoint not found: {checkpoint_id}")
                return False

            # 更新字段
            current_time = time.time()
            updates["updated_at"] = current_time

            # 计算进度百分比
            if "processed_count" in updates and checkpoint.estimated_total:
                updates["progress_percentage"] = min(
                    (updates["processed_count"] / checkpoint.estimated_total) * 100, 100.0
                )

            # 计算处理速率
            if "processed_count" in updates:
                elapsed = current_time - checkpoint.created_at
                if elapsed > 0:
                    updates["processing_rate"] = updates["processed_count"] / elapsed
                    updates["elapsed_time"] = elapsed

            # 应用更新
            for field, value in updates.items():
                if hasattr(checkpoint, field):
                    setattr(checkpoint, field, value)

            # 保存更新
            self._save_checkpoint(checkpoint)
            self.active_checkpoints[checkpoint_id] = checkpoint

            GLOG.DEBUG(f"Updated checkpoint: {checkpoint_id}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update checkpoint {checkpoint_id}: {e}")
            return False

    def get_checkpoint(self, checkpoint_id: str) -> Optional[CheckpointInfo]:
        """
        获取断点信息

        Args:
            checkpoint_id: 断点ID

        Returns:
            断点信息
        """
        try:
            # 先检查内存缓存
            if checkpoint_id in self.active_checkpoints:
                return self.active_checkpoints[checkpoint_id]

            # 从存储后端加载
            checkpoint_data = self._load_checkpoint_data(checkpoint_id)
            if checkpoint_data:
                checkpoint = CheckpointInfo(**checkpoint_data)

                # 检查是否过期
                if checkpoint.expires_at and time.time() > checkpoint.expires_at:
                    GLOG.WARNING(f"Checkpoint {checkpoint_id} has expired")
                    self.delete_checkpoint(checkpoint_id)
                    return None

                self.active_checkpoints[checkpoint_id] = checkpoint
                return checkpoint

            return None

        except Exception as e:
            GLOG.ERROR(f"Failed to get checkpoint {checkpoint_id}: {e}")
            return None

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除断点

        Args:
            checkpoint_id: 断点ID

        Returns:
            是否删除成功
        """
        try:
            # 从内存缓存删除
            if checkpoint_id in self.active_checkpoints:
                del self.active_checkpoints[checkpoint_id]

            # 从存储后端删除
            self._delete_checkpoint_data(checkpoint_id)

            GLOG.INFO(f"Deleted checkpoint: {checkpoint_id}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to delete checkpoint {checkpoint_id}: {e}")
            return False

    def list_checkpoints(
        self, query_hash: Optional[str] = None, state: Optional[StreamingState] = None
    ) -> List[CheckpointInfo]:
        """
        列出断点

        Args:
            query_hash: 查询哈希过滤
            state: 状态过滤

        Returns:
            断点列表
        """
        try:
            checkpoints = []

            # 获取所有断点
            all_checkpoint_ids = self._list_all_checkpoint_ids()

            for checkpoint_id in all_checkpoint_ids:
                checkpoint = self.get_checkpoint(checkpoint_id)
                if not checkpoint:
                    continue

                # 应用过滤条件
                if query_hash and checkpoint.query_hash != query_hash:
                    continue
                if state and checkpoint.state != state:
                    continue

                checkpoints.append(checkpoint)

            # 按创建时间排序
            checkpoints.sort(key=lambda x: x.created_at, reverse=True)
            return checkpoints

        except Exception as e:
            GLOG.ERROR(f"Failed to list checkpoints: {e}")
            return []

    def cleanup_expired_checkpoints(self) -> int:
        """
        清理过期断点

        Returns:
            清理的断点数量
        """
        try:
            current_time = time.time()
            expired_count = 0

            # 获取所有断点
            all_checkpoints = self.list_checkpoints()

            for checkpoint in all_checkpoints:
                if checkpoint.expires_at and current_time > checkpoint.expires_at:
                    self.delete_checkpoint(checkpoint.checkpoint_id)
                    expired_count += 1

            if expired_count > 0:
                GLOG.INFO(f"Cleaned up {expired_count} expired checkpoints")

            return expired_count

        except Exception as e:
            GLOG.ERROR(f"Failed to cleanup expired checkpoints: {e}")
            return 0

    def _generate_query_hash(self, query: str, filters: Dict[str, Any]) -> str:
        """生成查询哈希"""
        query_content = {"query": query.strip(), "filters": sorted(filters.items()) if filters else []}
        content_str = json.dumps(query_content, sort_keys=True)
        return hashlib.sha256(content_str.encode()).hexdigest()

    def _find_existing_checkpoint(self, query_hash: str) -> Optional[CheckpointInfo]:
        """查找现有断点"""
        checkpoints = self.list_checkpoints(query_hash=query_hash)

        # 返回最新的未完成断点
        for checkpoint in checkpoints:
            if checkpoint.state in [StreamingState.RUNNING, StreamingState.PAUSED]:
                return checkpoint

        return None

    def _save_checkpoint(self, checkpoint: CheckpointInfo):
        """保存断点到存储后端"""
        try:
            key = self.checkpoint_prefix + checkpoint.checkpoint_id
            data = json.dumps(asdict(checkpoint), default=str)

            if self._use_memory_storage:
                self._memory_storage[key] = data
            else:
                # 使用外部存储后端（如Redis）
                if hasattr(self.storage_backend, "setex"):
                    # Redis backend
                    ttl = int(checkpoint.expires_at - time.time()) if checkpoint.expires_at else self.default_ttl
                    self.storage_backend.setex(key, ttl, data)
                elif hasattr(self.storage_backend, "set"):
                    # 简单key-value存储
                    self.storage_backend.set(key, data)
                else:
                    GLOG.WARNING("Storage backend does not support set operation")

        except Exception as e:
            GLOG.ERROR(f"Failed to save checkpoint: {e}")
            raise

    def _load_checkpoint_data(self, checkpoint_id: str) -> Optional[Dict]:
        """从存储后端加载断点数据"""
        try:
            key = self.checkpoint_prefix + checkpoint_id

            if self._use_memory_storage:
                data_str = self._memory_storage.get(key)
            else:
                # 使用外部存储后端
                if hasattr(self.storage_backend, "get"):
                    data_str = self.storage_backend.get(key)
                    if isinstance(data_str, bytes):
                        data_str = data_str.decode("utf-8")
                else:
                    GLOG.WARNING("Storage backend does not support get operation")
                    return None

            if data_str:
                return json.loads(data_str)

            return None

        except Exception as e:
            GLOG.ERROR(f"Failed to load checkpoint data: {e}")
            return None

    def _delete_checkpoint_data(self, checkpoint_id: str):
        """从存储后端删除断点数据"""
        try:
            key = self.checkpoint_prefix + checkpoint_id

            if self._use_memory_storage:
                self._memory_storage.pop(key, None)
            else:
                # 使用外部存储后端
                if hasattr(self.storage_backend, "delete"):
                    self.storage_backend.delete(key)
                elif hasattr(self.storage_backend, "pop"):
                    self.storage_backend.pop(key, None)

        except Exception as e:
            GLOG.ERROR(f"Failed to delete checkpoint data: {e}")

    def _list_all_checkpoint_ids(self) -> List[str]:
        """列出所有断点ID"""
        try:
            if self._use_memory_storage:
                # 内存存储
                keys = [key for key in self._memory_storage.keys() if key.startswith(self.checkpoint_prefix)]
                return [key.replace(self.checkpoint_prefix, "") for key in keys]
            else:
                # 外部存储后端
                if hasattr(self.storage_backend, "keys"):
                    # Redis-like backend
                    pattern = self.checkpoint_prefix + "*"
                    keys = self.storage_backend.keys(pattern)
                    return [
                        (
                            key.decode("utf-8").replace(self.checkpoint_prefix, "")
                            if isinstance(key, bytes)
                            else key.replace(self.checkpoint_prefix, "")
                        )
                        for key in keys
                    ]
                else:
                    # 简单存储，无法列出所有键
                    return []

        except Exception as e:
            GLOG.ERROR(f"Failed to list checkpoint IDs: {e}")
            return []


class ProgressTrackingManager:
    """进度跟踪管理器"""

    def __init__(self):
        self.active_trackers: Dict[str, ProgressTracker] = {}
        self.global_callbacks: List[Callable[[str, ProgressInfo], None]] = []

        GLOG.DEBUG("ProgressTrackingManager initialized")

    def create_tracker(self, query_hash: str, estimated_total: Optional[int] = None) -> str:
        """
        创建进度跟踪器

        Args:
            query_hash: 查询哈希
            estimated_total: 预估总数

        Returns:
            跟踪器ID
        """
        tracker_id = str(uuid.uuid4())

        tracker = ProgressTracker(
            tracker_id=tracker_id, query_hash=query_hash, estimated_total=estimated_total, progress_callbacks=[]
        )

        self.active_trackers[tracker_id] = tracker
        GLOG.DEBUG(f"Created progress tracker: {tracker_id}")

        return tracker_id

    def update_progress(
        self, tracker_id: str, processed_count: int, batch_size: Optional[int] = None, memory_mb: Optional[float] = None
    ) -> bool:
        """
        更新进度信息

        Args:
            tracker_id: 跟踪器ID
            processed_count: 已处理数量
            batch_size: 批次大小
            memory_mb: 内存使用

        Returns:
            是否更新成功
        """
        try:
            tracker = self.active_trackers.get(tracker_id)
            if not tracker:
                GLOG.WARNING(f"Progress tracker not found: {tracker_id}")
                return False

            current_time = time.time()

            # 更新基础信息
            prev_processed = tracker.total_processed
            tracker.total_processed = processed_count
            tracker.last_update_time = current_time

            if batch_size:
                tracker.current_batch += 1

                # 计算平均批次时间
                elapsed = current_time - tracker.start_time
                if tracker.current_batch > 0:
                    tracker.average_batch_time = elapsed / tracker.current_batch

            # 计算处理速率
            elapsed_total = current_time - tracker.start_time
            if elapsed_total > 0:
                tracker.processing_rate = processed_count / elapsed_total

            # 更新内存峰值
            if memory_mb and memory_mb > tracker.peak_memory_mb:
                tracker.peak_memory_mb = memory_mb

            # 估算完成时间
            if tracker.estimated_total and tracker.processing_rate > 0:
                remaining = tracker.estimated_total - processed_count
                eta_seconds = remaining / tracker.processing_rate
                tracker.estimated_completion_time = current_time + eta_seconds

            # 创建进度信息
            progress_info = ProgressInfo(
                processed=processed_count,
                total=tracker.estimated_total,
                rate=tracker.processing_rate,
                elapsed=elapsed_total,
                eta=tracker.estimated_completion_time - current_time if tracker.estimated_completion_time else None,
                memory_mb=memory_mb or 0.0,
            )

            # 通知回调函数
            self._notify_progress_callbacks(tracker, progress_info)

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to update progress for tracker {tracker_id}: {e}")
            return False

    def add_progress_callback(self, tracker_id: str, callback: Callable[[ProgressInfo], None]) -> bool:
        """
        添加进度回调函数

        Args:
            tracker_id: 跟踪器ID
            callback: 回调函数

        Returns:
            是否添加成功
        """
        try:
            tracker = self.active_trackers.get(tracker_id)
            if not tracker:
                GLOG.WARNING(f"Progress tracker not found: {tracker_id}")
                return False

            if callback not in tracker.progress_callbacks:
                tracker.progress_callbacks.append(callback)
                GLOG.DEBUG(f"Added progress callback to tracker: {tracker_id}")

            return True

        except Exception as e:
            GLOG.ERROR(f"Failed to add progress callback: {e}")
            return False

    def add_global_callback(self, callback: Callable[[str, ProgressInfo], None]):
        """
        添加全局进度回调函数

        Args:
            callback: 回调函数，参数为(tracker_id, progress_info)
        """
        if callback not in self.global_callbacks:
            self.global_callbacks.append(callback)
            GLOG.DEBUG("Added global progress callback")

    def get_tracker(self, tracker_id: str) -> Optional[ProgressTracker]:
        """获取进度跟踪器"""
        return self.active_trackers.get(tracker_id)

    def remove_tracker(self, tracker_id: str) -> bool:
        """移除进度跟踪器"""
        try:
            if tracker_id in self.active_trackers:
                del self.active_trackers[tracker_id]
                GLOG.DEBUG(f"Removed progress tracker: {tracker_id}")
                return True
            return False
        except Exception as e:
            GLOG.ERROR(f"Failed to remove progress tracker {tracker_id}: {e}")
            return False

    def _notify_progress_callbacks(self, tracker: ProgressTracker, progress_info: ProgressInfo):
        """通知进度回调函数"""
        # 跟踪器特定回调
        for callback in tracker.progress_callbacks:
            try:
                callback(progress_info)
            except Exception as e:
                GLOG.WARNING(f"Progress callback failed: {e}")

        # 全局回调
        for callback in self.global_callbacks:
            try:
                callback(tracker.tracker_id, progress_info)
            except Exception as e:
                GLOG.WARNING(f"Global progress callback failed: {e}")


# 全局实例
checkpoint_manager = CheckpointManager()
progress_tracking_manager = ProgressTrackingManager()
