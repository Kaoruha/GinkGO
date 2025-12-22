"""
流式查询内存监控和会话管理系统

提供实时内存监控、智能会话管理和资源优化功能，
确保流式查询在大数据处理时的系统稳定性和资源利用效率。

核心功能：
- 实时内存使用监控和告警
- 智能数据库会话生命周期管理
- 自适应资源调节和优化
- 系统性能指标收集和分析
"""

import time
import threading
import psutil
import gc
from typing import Any, Dict, List, Optional, Callable, NamedTuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from contextlib import contextmanager
from collections import deque, defaultdict
from enum import Enum

try:
    from ginkgo.libs import GLOG

    _has_ginkgo_logger = True
except ImportError:
    _has_ginkgo_logger = False
    import logging

    GLOG = logging.getLogger(__name__)

from ginkgo.data.streaming import StreamingState


class MemoryLevel(Enum):
    """内存使用级别"""

    NORMAL = "normal"  # < 70%
    WARNING = "warning"  # 70-85%
    CRITICAL = "critical"  # 85-95%
    EMERGENCY = "emergency"  # > 95%


class SessionState(Enum):
    """会话状态"""

    IDLE = "idle"
    ACTIVE = "active"
    EXPIRED = "expired"
    CLOSED = "closed"


@dataclass
class MemorySnapshot:
    """内存快照"""

    timestamp: float
    used_mb: float
    available_mb: float
    percent: float
    process_mb: float
    level: MemoryLevel

    @property
    def total_mb(self) -> float:
        """总内存"""
        return self.used_mb + self.available_mb


@dataclass
class SessionInfo:
    """会话信息"""

    session_id: str
    database_type: str
    created_at: float
    last_active: float
    query_count: int
    state: SessionState
    connection_pool_id: Optional[str] = None
    streaming_query_id: Optional[str] = None
    memory_peak_mb: float = 0.0

    @property
    def age_seconds(self) -> float:
        """会话年龄"""
        return time.time() - self.created_at

    @property
    def idle_seconds(self) -> float:
        """空闲时间"""
        return time.time() - self.last_active


@dataclass
class ResourceMetrics:
    """资源指标"""

    memory_snapshots: deque = field(default_factory=lambda: deque(maxlen=100))
    active_sessions: Dict[str, SessionInfo] = field(default_factory=dict)
    performance_counters: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    alert_history: List[Dict] = field(default_factory=list)

    def add_memory_snapshot(self, snapshot: MemorySnapshot):
        """添加内存快照"""
        self.memory_snapshots.append(snapshot)

    def get_memory_trend(self, minutes: int = 5) -> List[MemorySnapshot]:
        """获取内存趋势"""
        cutoff_time = time.time() - (minutes * 60)
        return [s for s in self.memory_snapshots if s.timestamp >= cutoff_time]


class MemoryMonitor:
    """内存监控器"""

    def __init__(
        self,
        check_interval: float = 5.0,
        warning_threshold: float = 70.0,
        critical_threshold: float = 85.0,
        emergency_threshold: float = 95.0,
    ):
        """
        初始化内存监控器

        Args:
            check_interval: 监控间隔（秒）
            warning_threshold: 警告阈值（百分比）
            critical_threshold: 严重阈值（百分比）
            emergency_threshold: 紧急阈值（百分比）
        """
        self.check_interval = check_interval
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.emergency_threshold = emergency_threshold

        self.metrics = ResourceMetrics()
        self.callbacks: Dict[MemoryLevel, List[Callable]] = defaultdict(list)

        self._monitoring = False
        self._monitor_thread = None
        self._lock = threading.Lock()

        # 获取当前进程信息
        self.process = psutil.Process()

        GLOG.DEBUG("MemoryMonitor initialized")

    def start_monitoring(self):
        """启动内存监控"""
        with self._lock:
            if self._monitoring:
                GLOG.WARN("Memory monitoring is already running")
                return

            self._monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitoring_loop, daemon=True, name="MemoryMonitor")
            self._monitor_thread.start()

        GLOG.INFO("Memory monitoring started")

    def stop_monitoring(self):
        """停止内存监控"""
        with self._lock:
            if not self._monitoring:
                return

            self._monitoring = False

        if self._monitor_thread:
            self._monitor_thread.join(timeout=10)

        GLOG.INFO("Memory monitoring stopped")

    def add_callback(self, level: MemoryLevel, callback: Callable[[MemorySnapshot], None]):
        """
        添加内存级别回调

        Args:
            level: 内存级别
            callback: 回调函数，参数为MemorySnapshot
        """
        self.callbacks[level].append(callback)
        GLOG.DEBUG(f"Added callback for memory level: {level.value}")

    def get_current_snapshot(self) -> MemorySnapshot:
        """获取当前内存快照"""
        try:
            # 系统内存信息
            memory = psutil.virtual_memory()

            # 进程内存信息
            process_memory = self.process.memory_info()
            process_mb = process_memory.rss / (1024 * 1024)

            # 确定内存级别
            level = self._determine_memory_level(memory.percent)

            snapshot = MemorySnapshot(
                timestamp=time.time(),
                used_mb=memory.used / (1024 * 1024),
                available_mb=memory.available / (1024 * 1024),
                percent=memory.percent,
                process_mb=process_mb,
                level=level,
            )

            return snapshot

        except Exception as e:
            GLOG.ERROR(f"Failed to get memory snapshot: {e}")
            # 返回默认快照避免监控中断
            return MemorySnapshot(
                timestamp=time.time(),
                used_mb=0.0,
                available_mb=0.0,
                percent=0.0,
                process_mb=0.0,
                level=MemoryLevel.NORMAL,
            )

    def force_garbage_collection(self) -> Dict[str, int]:
        """强制垃圾回收"""
        try:
            before_objects = len(gc.get_objects())
            collected = gc.collect()
            after_objects = len(gc.get_objects())

            result = {
                "collected": collected,
                "before_objects": before_objects,
                "after_objects": after_objects,
                "freed_objects": before_objects - after_objects,
            }

            GLOG.INFO(f"Garbage collection completed: {result}")
            self.metrics.performance_counters["gc_forced"] += 1

            return result

        except Exception as e:
            GLOG.ERROR(f"Failed to force garbage collection: {e}")
            return {}

    def get_memory_statistics(self) -> Dict[str, Any]:
        """获取内存统计信息"""
        snapshots = list(self.metrics.memory_snapshots)

        if not snapshots:
            return {"error": "No memory data available"}

        recent_snapshots = self.metrics.get_memory_trend(5)  # 最近5分钟

        return {
            "current": snapshots[-1].__dict__ if snapshots else None,
            "total_snapshots": len(snapshots),
            "recent_average_percent": (
                sum(s.percent for s in recent_snapshots) / len(recent_snapshots) if recent_snapshots else 0
            ),
            "peak_memory_mb": max((s.used_mb for s in snapshots), default=0),
            "peak_process_mb": max((s.process_mb for s in snapshots), default=0),
            "memory_trend": [
                {"timestamp": s.timestamp, "percent": s.percent, "level": s.level.value}
                for s in recent_snapshots[-10:]  # 最近10个快照
            ],
            "performance_counters": dict(self.metrics.performance_counters),
        }

    def _monitoring_loop(self):
        """监控循环"""
        GLOG.DEBUG("Memory monitoring loop started")

        while self._monitoring:
            try:
                # 获取内存快照
                snapshot = self.get_current_snapshot()

                # 添加到历史记录
                self.metrics.add_memory_snapshot(snapshot)

                # 触发级别回调
                self._trigger_level_callbacks(snapshot)

                # 记录警告级别及以上的内存状态
                if snapshot.level != MemoryLevel.NORMAL:
                    alert = {
                        "timestamp": snapshot.timestamp,
                        "level": snapshot.level.value,
                        "percent": snapshot.percent,
                        "process_mb": snapshot.process_mb,
                    }
                    self.metrics.alert_history.append(alert)

                    # 保持警告历史记录在合理大小
                    if len(self.metrics.alert_history) > 100:
                        self.metrics.alert_history = self.metrics.alert_history[-50:]

                # 更新性能计数器
                self.metrics.performance_counters["monitoring_cycles"] += 1

                time.sleep(self.check_interval)

            except Exception as e:
                GLOG.ERROR(f"Error in memory monitoring loop: {e}")
                time.sleep(self.check_interval)

        GLOG.DEBUG("Memory monitoring loop stopped")

    def _determine_memory_level(self, percent: float) -> MemoryLevel:
        """确定内存级别"""
        if percent >= self.emergency_threshold:
            return MemoryLevel.EMERGENCY
        elif percent >= self.critical_threshold:
            return MemoryLevel.CRITICAL
        elif percent >= self.warning_threshold:
            return MemoryLevel.WARNING
        else:
            return MemoryLevel.NORMAL

    def _trigger_level_callbacks(self, snapshot: MemorySnapshot):
        """触发级别回调"""
        for callback in self.callbacks[snapshot.level]:
            try:
                callback(snapshot)
            except Exception as e:
                GLOG.WARN(f"Memory level callback failed: {e}")


class SessionManager:
    """会话管理器"""

    def __init__(
        self,
        max_idle_time: float = 1800,  # 30分钟
        cleanup_interval: float = 300,  # 5分钟
        max_sessions_per_type: int = 10,
    ):
        """
        初始化会话管理器

        Args:
            max_idle_time: 最大空闲时间（秒）
            cleanup_interval: 清理间隔（秒）
            max_sessions_per_type: 每种数据库类型的最大会话数
        """
        self.max_idle_time = max_idle_time
        self.cleanup_interval = cleanup_interval
        self.max_sessions_per_type = max_sessions_per_type

        self.sessions: Dict[str, SessionInfo] = {}
        self._lock = threading.Lock()

        # 会话清理
        self._cleanup_enabled = False
        self._cleanup_thread = None

        GLOG.DEBUG("SessionManager initialized")

    def create_session(
        self, database_type: str, connection_pool_id: Optional[str] = None, streaming_query_id: Optional[str] = None
    ) -> str:
        """
        创建新会话

        Args:
            database_type: 数据库类型
            connection_pool_id: 连接池ID
            streaming_query_id: 流式查询ID

        Returns:
            会话ID
        """
        import uuid

        session_id = str(uuid.uuid4())
        current_time = time.time()

        session_info = SessionInfo(
            session_id=session_id,
            database_type=database_type,
            created_at=current_time,
            last_active=current_time,
            query_count=0,
            state=SessionState.IDLE,
            connection_pool_id=connection_pool_id,
            streaming_query_id=streaming_query_id,
        )

        with self._lock:
            # 检查会话数量限制
            type_sessions = [
                s for s in self.sessions.values() if s.database_type == database_type and s.state != SessionState.CLOSED
            ]

            if len(type_sessions) >= self.max_sessions_per_type:
                # 清理最老的空闲会话
                idle_sessions = [s for s in type_sessions if s.state == SessionState.IDLE]
                if idle_sessions:
                    oldest_session = min(idle_sessions, key=lambda x: x.last_active)
                    self._close_session(oldest_session.session_id)
                    GLOG.INFO(f"Closed oldest idle session to make room: {oldest_session.session_id}")

            self.sessions[session_id] = session_info

        GLOG.DEBUG(f"Created session: {session_id} for {database_type}")
        return session_id

    def activate_session(self, session_id: str) -> bool:
        """
        激活会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功激活
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                GLOG.WARN(f"Session not found: {session_id}")
                return False

            if session.state == SessionState.CLOSED:
                GLOG.WARN(f"Cannot activate closed session: {session_id}")
                return False

            session.state = SessionState.ACTIVE
            session.last_active = time.time()
            session.query_count += 1

        GLOG.DEBUG(f"Activated session: {session_id}")
        return True

    def deactivate_session(self, session_id: str, memory_used_mb: Optional[float] = None) -> bool:
        """
        取消激活会话

        Args:
            session_id: 会话ID
            memory_used_mb: 本次查询使用的内存

        Returns:
            是否成功取消激活
        """
        with self._lock:
            session = self.sessions.get(session_id)
            if not session:
                return False

            session.state = SessionState.IDLE
            session.last_active = time.time()

            if memory_used_mb and memory_used_mb > session.memory_peak_mb:
                session.memory_peak_mb = memory_used_mb

        GLOG.DEBUG(f"Deactivated session: {session_id}")
        return True

    def close_session(self, session_id: str) -> bool:
        """
        关闭会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功关闭
        """
        with self._lock:
            return self._close_session(session_id)

    def _close_session(self, session_id: str) -> bool:
        """内部关闭会话方法"""
        session = self.sessions.get(session_id)
        if not session:
            return False

        session.state = SessionState.CLOSED
        GLOG.DEBUG(f"Closed session: {session_id}")
        return True

    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        """获取会话信息"""
        with self._lock:
            return self.sessions.get(session_id)

    def list_sessions(
        self, database_type: Optional[str] = None, state: Optional[SessionState] = None
    ) -> List[SessionInfo]:
        """
        列出会话

        Args:
            database_type: 数据库类型过滤
            state: 状态过滤

        Returns:
            会话列表
        """
        with self._lock:
            sessions = list(self.sessions.values())

        if database_type:
            sessions = [s for s in sessions if s.database_type == database_type]

        if state:
            sessions = [s for s in sessions if s.state == state]

        return sessions

    def start_cleanup(self):
        """启动会话清理"""
        with self._lock:
            if self._cleanup_enabled:
                GLOG.WARN("Session cleanup is already running")
                return

            self._cleanup_enabled = True
            self._cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True, name="SessionCleanup")
            self._cleanup_thread.start()

        GLOG.INFO("Session cleanup started")

    def stop_cleanup(self):
        """停止会话清理"""
        with self._lock:
            if not self._cleanup_enabled:
                return

            self._cleanup_enabled = False

        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=10)

        GLOG.INFO("Session cleanup stopped")

    def _cleanup_loop(self):
        """清理循环"""
        GLOG.DEBUG("Session cleanup loop started")

        while self._cleanup_enabled:
            try:
                self._cleanup_expired_sessions()
                time.sleep(self.cleanup_interval)
            except Exception as e:
                GLOG.ERROR(f"Error in session cleanup loop: {e}")
                time.sleep(self.cleanup_interval)

        GLOG.DEBUG("Session cleanup loop stopped")

    def _cleanup_expired_sessions(self):
        """清理过期会话"""
        current_time = time.time()
        expired_sessions = []

        with self._lock:
            for session_id, session in self.sessions.items():
                if session.state == SessionState.IDLE and session.idle_seconds > self.max_idle_time:
                    expired_sessions.append(session_id)
                elif session.state == SessionState.CLOSED:
                    expired_sessions.append(session_id)

        # 清理过期会话
        for session_id in expired_sessions:
            with self._lock:
                session = self.sessions.pop(session_id, None)
                if session:
                    GLOG.DEBUG(f"Cleaned up expired session: {session_id}")

        if expired_sessions:
            GLOG.INFO(f"Cleaned up {len(expired_sessions)} expired sessions")

    def get_session_statistics(self) -> Dict[str, Any]:
        """获取会话统计信息"""
        with self._lock:
            sessions = list(self.sessions.values())

        stats_by_type = defaultdict(lambda: defaultdict(int))
        stats_by_state = defaultdict(int)

        total_queries = 0
        total_memory_mb = 0.0

        for session in sessions:
            stats_by_type[session.database_type][session.state.value] += 1
            stats_by_state[session.state.value] += 1
            total_queries += session.query_count
            total_memory_mb += session.memory_peak_mb

        return {
            "total_sessions": len(sessions),
            "sessions_by_type": dict(stats_by_type),
            "sessions_by_state": dict(stats_by_state),
            "total_queries": total_queries,
            "total_memory_peak_mb": total_memory_mb,
            "average_memory_per_session": (total_memory_mb / len(sessions) if sessions else 0),
        }


class ResourceOptimizer:
    """资源优化器"""

    def __init__(self, memory_monitor: MemoryMonitor, session_manager: SessionManager):
        """
        初始化资源优化器

        Args:
            memory_monitor: 内存监控器
            session_manager: 会话管理器
        """
        self.memory_monitor = memory_monitor
        self.session_manager = session_manager

        # 注册内存级别回调
        self.memory_monitor.add_callback(MemoryLevel.WARNING, self._handle_memory_warning)
        self.memory_monitor.add_callback(MemoryLevel.CRITICAL, self._handle_memory_critical)
        self.memory_monitor.add_callback(MemoryLevel.EMERGENCY, self._handle_memory_emergency)

        GLOG.DEBUG("ResourceOptimizer initialized")

    def _handle_memory_warning(self, snapshot: MemorySnapshot):
        """处理内存警告"""
        GLOG.WARN(f"Memory usage warning: {snapshot.percent:.1f}% ({snapshot.used_mb:.1f}MB)")

        # 轻量级优化：垃圾回收
        self.memory_monitor.force_garbage_collection()

    def _handle_memory_critical(self, snapshot: MemorySnapshot):
        """处理内存严重警告"""
        GLOG.ERROR(f"Critical memory usage: {snapshot.percent:.1f}% ({snapshot.used_mb:.1f}MB)")

        # 中等优化：关闭空闲会话
        idle_sessions = self.session_manager.list_sessions(state=SessionState.IDLE)
        if idle_sessions:
            # 关闭最老的空闲会话
            oldest_session = min(idle_sessions, key=lambda x: x.last_active)
            self.session_manager.close_session(oldest_session.session_id)
            GLOG.WARN(f"Closed idle session due to critical memory: {oldest_session.session_id}")

        # 强制垃圾回收
        self.memory_monitor.force_garbage_collection()

    def _handle_memory_emergency(self, snapshot: MemorySnapshot):
        """处理内存紧急情况"""
        GLOG.CRITICAL(f"Emergency memory usage: {snapshot.percent:.1f}% ({snapshot.used_mb:.1f}MB)")

        # 紧急优化：关闭多个会话
        all_sessions = self.session_manager.list_sessions()

        # 优先关闭空闲会话
        idle_sessions = [s for s in all_sessions if s.state == SessionState.IDLE]
        for session in sorted(idle_sessions, key=lambda x: x.last_active)[:3]:
            self.session_manager.close_session(session.session_id)
            GLOG.CRITICAL(f"Emergency closed idle session: {session.session_id}")

        # 如果还不够，考虑关闭活跃会话（谨慎操作）
        if snapshot.percent > 98.0:
            active_sessions = [s for s in all_sessions if s.state == SessionState.ACTIVE]
            if active_sessions:
                # 关闭内存使用最大的活跃会话
                memory_heavy_session = max(active_sessions, key=lambda x: x.memory_peak_mb)
                GLOG.CRITICAL(f"Emergency: considering closing active session: {memory_heavy_session.session_id}")

        # 多次强制垃圾回收
        for _ in range(3):
            self.memory_monitor.force_garbage_collection()


# 全局单例实例
memory_monitor = MemoryMonitor()
session_manager = SessionManager()
resource_optimizer = ResourceOptimizer(memory_monitor, session_manager)
