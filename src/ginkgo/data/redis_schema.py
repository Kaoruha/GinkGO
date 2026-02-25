# Upstream: Redis (键存储)
# Downstream: DataWorker, BacktestWorker, ExecutionNode, Scheduler, TaskTimer, RedisService, API
# Role: Redis键命名规范和数据结构定义，统一管理所有Redis键的命名和数据格式


"""
Redis Schema - 统一管理 Redis 键命名和数据结构

提供：
1. 键名常量和生成器
2. 心跳数据结构定义
3. TTL 配置
4. 所有 Redis 键的集中管理
"""

from dataclasses import dataclass, asdict
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum
import json


# ==================== 键前缀定义 ====================

class RedisKeyPrefix:
    """Redis 键前缀常量"""
    # Worker 心跳
    DATA_WORKER_HEARTBEAT = "heartbeat:data_worker"
    BACKTEST_WORKER_HEARTBEAT = "backtest:worker"
    EXECUTION_NODE_HEARTBEAT = "heartbeat:node"
    SCHEDULER_HEARTBEAT = "heartbeat:scheduler"
    TASK_TIMER_HEARTBEAT = "heartbeat:task_timer"
    COMPONENT_HEARTBEAT = "heartbeat:component"
    PROCESS_HEARTBEAT = "ginkgo:heartbeat"

    # 进程管理
    MAIN_CONTROL = "ginkgo:maincontrol"
    WATCHDOG = "ginkgo:watchdog"
    THREAD_POOL = "ginkgo:thread_pool"
    DATA_WORKER_POOL = "ginkgo:dataworker_pool"
    WORKER_STATUS = "ginkgo:worker_status"

    # 任务状态
    TASK_STATUS = "ginkgo:task_status"
    BACKTEST_TASK = "backtest:task"

    # 同步进度 (实际格式: {data_type}_update_{code})
    SYNC_PROGRESS = ""  # 前缀为空，直接使用格式

    # 函数缓存 (实际格式: ginkgo_func_cache_{func_name}_{cache_key})
    FUNC_CACHE = "ginkgo_func_cache"


class RedisKeyPattern:
    """Redis 键匹配模式"""
    # 心跳
    DATA_WORKER_HEARTBEAT_ALL = f"{RedisKeyPrefix.DATA_WORKER_HEARTBEAT}:*"
    BACKTEST_WORKER_HEARTBEAT_ALL = f"{RedisKeyPrefix.BACKTEST_WORKER_HEARTBEAT}:*"
    EXECUTION_NODE_HEARTBEAT_ALL = f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:*"
    SCHEDULER_HEARTBEAT_ALL = f"{RedisKeyPrefix.SCHEDULER_HEARTBEAT}:*"
    TASK_TIMER_HEARTBEAT_ALL = f"{RedisKeyPrefix.TASK_TIMER_HEARTBEAT}:*"
    ALL_HEARTBEATS = "heartbeat:*"

    # 任务
    TASK_STATUS_ALL = f"{RedisKeyPrefix.TASK_STATUS}:*"

    # 缓存
    FUNC_CACHE_ALL = f"{RedisKeyPrefix.FUNC_CACHE}_*"
    SYNC_PROGRESS_ALL = "*_update_*"  # 匹配 {data_type}_update_{code}

    # Ginkgo 相关
    ALL_GINKGO_KEYS = "ginkgo:*"


class RedisKeyBuilder:
    """Redis 键构建器 - 统一的键生成方法"""

    # ==================== 心跳键 ====================

    @staticmethod
    def data_worker_heartbeat(node_id: str) -> str:
        """DataWorker 心跳键"""
        return f"{RedisKeyPrefix.DATA_WORKER_HEARTBEAT}:{node_id}"

    @staticmethod
    def backtest_worker_heartbeat(worker_id: str) -> str:
        """BacktestWorker 心跳键"""
        return f"{RedisKeyPrefix.BACKTEST_WORKER_HEARTBEAT}:{worker_id}"

    @staticmethod
    def execution_node_heartbeat(node_id: str) -> str:
        """ExecutionNode 心跳键"""
        return f"{RedisKeyPrefix.EXECUTION_NODE_HEARTBEAT}:{node_id}"

    @staticmethod
    def scheduler_heartbeat(node_id: str) -> str:
        """Scheduler 心跳键"""
        return f"{RedisKeyPrefix.SCHEDULER_HEARTBEAT}:{node_id}"

    @staticmethod
    def task_timer_heartbeat(node_id: str) -> str:
        """TaskTimer 心跳键"""
        return f"{RedisKeyPrefix.TASK_TIMER_HEARTBEAT}:{node_id}"

    @staticmethod
    def component_heartbeat(component_type: str, component_id: str) -> str:
        """通用组件心跳键"""
        return f"{RedisKeyPrefix.COMPONENT_HEARTBEAT}:{component_type}:{component_id}"

    @staticmethod
    def process_heartbeat(pid: int) -> str:
        """进程心跳键"""
        return f"{RedisKeyPrefix.PROCESS_HEARTBEAT}:{pid}"

    # ==================== 进程管理键 ====================

    @staticmethod
    def main_control() -> str:
        """主控进程键"""
        return RedisKeyPrefix.MAIN_CONTROL

    @staticmethod
    def watchdog() -> str:
        """看门狗进程键"""
        return RedisKeyPrefix.WATCHDOG

    @staticmethod
    def thread_pool() -> str:
        """线程池键"""
        return RedisKeyPrefix.THREAD_POOL

    @staticmethod
    def data_worker_pool() -> str:
        """DataWorker池键"""
        return RedisKeyPrefix.DATA_WORKER_POOL

    @staticmethod
    def worker_status(pid: int) -> str:
        """Worker状态键"""
        return f"{RedisKeyPrefix.WORKER_STATUS}:{pid}"

    # ==================== 任务状态键 ====================

    @staticmethod
    def task_status(task_id: str) -> str:
        """任务状态键"""
        return f"{RedisKeyPrefix.TASK_STATUS}:{task_id}"

    @staticmethod
    def backtest_task_progress(task_id: str) -> str:
        """回测任务进度键"""
        return f"{RedisKeyPrefix.BACKTEST_TASK}:{task_id}:progress"

    # ==================== 缓存键 ====================

    @staticmethod
    def sync_progress(data_type: str, code: str) -> str:
        """数据同步进度键 (格式: {data_type}_update_{code})"""
        return f"{data_type}_update_{code}"

    @staticmethod
    def func_cache(func_name: str, cache_key: str) -> str:
        """函数缓存键 (格式: ginkgo_func_cache_{func_name}_{cache_key})"""
        return f"{RedisKeyPrefix.FUNC_CACHE}_{func_name}_{cache_key}"


# ==================== TTL 配置 ====================

class RedisTTL:
    """Redis TTL 配置（秒）"""
    # 心跳 TTL（应大于心跳间隔的2-3倍）
    DATA_WORKER_HEARTBEAT = 30
    BACKTEST_WORKER_HEARTBEAT = 30
    EXECUTION_NODE_HEARTBEAT = 30
    SCHEDULER_HEARTBEAT = 30
    TASK_TIMER_HEARTBEAT = 30
    COMPONENT_HEARTBEAT = 30
    PROCESS_HEARTBEAT = 30

    # 任务状态 TTL
    TASK_STATUS = 3600 * 24  # 1天
    BACKTEST_TASK_PROGRESS = 3600 * 2  # 2小时

    # 同步进度 TTL (与 RedisService 中 expire(cache_key, 60 * 60 * 24 * 30) 一致)
    SYNC_PROGRESS = 60 * 60 * 24 * 30  # 30天

    # 函数缓存 TTL
    FUNC_CACHE_DEFAULT = 3600  # 1小时


# ==================== 状态枚举 ====================

class WorkerStatus(str, Enum):
    """Worker 状态枚举"""
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    ERROR = "error"


# ==================== 心跳数据结构 ====================

@dataclass
class BaseHeartbeat:
    """心跳数据基类"""
    status: str
    timestamp: str

    def to_json(self) -> str:
        """序列化为 JSON"""
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def from_json(cls, data: str) -> "BaseHeartbeat":
        """从 JSON 反序列化"""
        if isinstance(data, str):
            d = json.loads(data)
        else:
            d = data
        return cls(**d)


@dataclass
class DataWorkerHeartbeat(BaseHeartbeat):
    """DataWorker 心跳数据结构"""
    node_id: str
    stats: Dict[str, Any]

    @classmethod
    def create(cls, node_id: str, status: WorkerStatus, stats: Dict[str, Any] = None) -> "DataWorkerHeartbeat":
        """创建心跳数据"""
        return cls(
            node_id=node_id,
            status=status.value if isinstance(status, WorkerStatus) else status,
            timestamp=datetime.now().isoformat(),
            stats=stats or {}
        )


@dataclass
class BacktestWorkerHeartbeat(BaseHeartbeat):
    """BacktestWorker 心跳数据结构"""
    worker_id: str
    running_tasks: int
    max_tasks: int
    started_at: str
    last_heartbeat: str

    @classmethod
    def create(cls, worker_id: str, status: WorkerStatus,
               running_tasks: int = 0, max_tasks: int = 5,
               started_at: str = None) -> "BacktestWorkerHeartbeat":
        """创建心跳数据"""
        now = datetime.now().isoformat()
        return cls(
            worker_id=worker_id,
            status=status.value if isinstance(status, WorkerStatus) else status,
            timestamp=now,
            running_tasks=running_tasks,
            max_tasks=max_tasks,
            started_at=started_at or now,
            last_heartbeat=now
        )

    def update_heartbeat(self, running_tasks: int = None) -> "BacktestWorkerHeartbeat":
        """更新心跳时间"""
        if running_tasks is not None:
            self.running_tasks = running_tasks
        now = datetime.now().isoformat()
        self.last_heartbeat = now
        self.timestamp = now
        return self


@dataclass
class ExecutionNodeHeartbeat(BaseHeartbeat):
    """ExecutionNode 心跳数据结构"""
    node_id: str
    host: str
    port: int
    active_strategies: int

    @classmethod
    def create(cls, node_id: str, host: str, port: int,
               status: WorkerStatus, active_strategies: int = 0) -> "ExecutionNodeHeartbeat":
        """创建心跳数据"""
        return cls(
            node_id=node_id,
            host=host,
            port=port,
            status=status.value if isinstance(status, WorkerStatus) else status,
            timestamp=datetime.now().isoformat(),
            active_strategies=active_strategies
        )


@dataclass
class SchedulerHeartbeat(BaseHeartbeat):
    """Scheduler 心跳数据结构"""
    node_id: str
    running_tasks: int
    pending_tasks: int

    @classmethod
    def create(cls, node_id: str, status: WorkerStatus,
               running_tasks: int = 0, pending_tasks: int = 0) -> "SchedulerHeartbeat":
        """创建心跳数据"""
        return cls(
            node_id=node_id,
            status=status.value if isinstance(status, WorkerStatus) else status,
            timestamp=datetime.now().isoformat(),
            running_tasks=running_tasks,
            pending_tasks=pending_tasks
        )


@dataclass
class TaskTimerHeartbeat(BaseHeartbeat):
    """TaskTimer 心跳数据结构"""
    node_id: str
    jobs_count: int

    @classmethod
    def create(cls, node_id: str, status: WorkerStatus, jobs_count: int = 0) -> "TaskTimerHeartbeat":
        """创建心跳数据"""
        return cls(
            node_id=node_id,
            status=status.value if isinstance(status, WorkerStatus) else status,
            timestamp=datetime.now().isoformat(),
            jobs_count=jobs_count
        )


# ==================== 便捷函数 ====================

def parse_heartbeat_data(data: Any) -> Dict[str, Any]:
    """
    解析心跳数据（通用）

    Args:
        data: Redis 返回的数据（可能是 str 或 dict）

    Returns:
        解析后的字典
    """
    if data is None:
        return {}
    if isinstance(data, dict):
        return data
    if isinstance(data, str):
        try:
            return json.loads(data)
        except json.JSONDecodeError:
            return {"raw": data}
    if isinstance(data, bytes):
        try:
            return json.loads(data.decode('utf-8'))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return {"raw": str(data)}
    return {"raw": str(data)}


def extract_id_from_key(key: str, prefix: str) -> str:
    """
    从键中提取 ID

    Args:
        key: 完整的键名
        prefix: 键前缀

    Returns:
        提取的 ID

    Example:
        extract_id_from_key("heartbeat:node:node_123", "heartbeat:node:")
        -> "node_123"
    """
    if key.startswith(prefix):
        return key[len(prefix):]
    return key.split(":")[-1] if ":" in key else key
