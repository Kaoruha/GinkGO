from abc import ABC, abstractmethod
import threading
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.libs import base_repr
from ginkgo.trading.core.status import EngineStatus, EventStats, QueueInfo
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from queue import Queue, Empty, Full
from ginkgo.enums import ENGINESTATUS_TYPES, COMPONENT_TYPES, EXECUTION_MODE
import time


class BaseEngine(BacktestBase, ABC):
    """
    Enhanced Base Engine with Unified ID Management
    
    统一的引擎基类，支持：
    - 基于配置的稳定engine_id生成
    - 动态run_id会话管理
    - 多次执行支持
    """

    def __init__(self, name: str = "BaseEngine", mode: EXECUTION_MODE = EXECUTION_MODE.BACKTEST,
                 engine_id: Optional[str] = None, *args, **kwargs):
        """
        初始化基础引擎（简化API）

        Args:
            name: 引擎名称
            mode: 运行模式（BACKTEST/LIVE/PAPER等）
            engine_id: 引擎ID（可选，不提供则自动生成）
        """
        from ..core.identity import IdentityUtils

        self._mode = mode

        # 生成或使用提供的引擎ID
        if engine_id:
            calculated_engine_id = engine_id
        else:
            calculated_engine_id = IdentityUtils.generate_component_uuid("engine")

        super(BaseEngine, self).__init__(
            name=name,
            component_type=COMPONENT_TYPES.ENGINE,
            engine_id=calculated_engine_id,
            *args, **kwargs
        )

        self._state: ENGINESTATUS_TYPES = ENGINESTATUS_TYPES.IDLE
        self._run_sequence: int = 0
        self._run_id: str = None

        # 默认事件队列配置
        self._event_timeout: float = 10.0
        self._event_queue = Queue(maxsize=10000)  # 默认队列大小
        self._queue_lock = threading.Lock()  # 队列操作锁

        # 队列调整状态
        self._is_resizing = False
        self._resize_lock = threading.Lock()

        # 通用组件
        self._portfolios: List = []
        self._is_running: bool = False

        # 状态跟踪统计
        self._processed_events_count: int = 0
        self._processing_start_time: Optional[float] = None
        self._last_processing_time: Optional[float] = None

    @property
    def status(self) -> str:
        """返回引擎状态的字符串表示"""
        status_map = {
            ENGINESTATUS_TYPES.VOID: "void",
            ENGINESTATUS_TYPES.IDLE: "idle",
            ENGINESTATUS_TYPES.INITIALIZING: "initializing",
            ENGINESTATUS_TYPES.RUNNING: "running",
            ENGINESTATUS_TYPES.PAUSED: "paused",
            ENGINESTATUS_TYPES.STOPPED: "stopped"
        }
        return status_map.get(self._state, "unknown")

    @property
    def state(self) -> ENGINESTATUS_TYPES:
        """返回引擎当前状态枚举"""
        return self._state

    @property
    def is_active(self) -> bool:
        """检查引擎是否处于活跃状态"""
        return self._state == ENGINESTATUS_TYPES.RUNNING

    @property
    def run_id(self) -> str:
        """获取当前运行会话ID"""
        return self._run_id

    def start(self) -> bool:
        """
        启动引擎

        Returns:
            bool: 操作是否成功
        """
        # 验证状态转换合法性
        valid_states = [ENGINESTATUS_TYPES.IDLE, ENGINESTATUS_TYPES.PAUSED, ENGINESTATUS_TYPES.STOPPED]
        if self._state not in valid_states:
            self.log("ERROR", f"Cannot start from {self.status} state")
            return False

        from ..core.identity import IdentityUtils

        try:
            # 判断是否需要生成新会话
            if self._run_id is None or self._state == ENGINESTATUS_TYPES.STOPPED:
                # 生成新会话
                self._run_sequence += 1
                self._run_id = IdentityUtils.generate_run_id(self._engine_id, self._run_sequence)
                self.log("INFO", f"Engine '{self.name}' started new session: engine_id={self.engine_id}, run_id={self.run_id}")
            else:
                # 从暂停状态恢复，保持原有run_id
                self.log("INFO", f"Engine '{self.name}' resumed: engine_id={self.engine_id}, run_id={self.run_id}")

            self._state = ENGINESTATUS_TYPES.RUNNING
            return True

        except Exception as e:
            self.log("ERROR", f"Failed to start engine: {str(e)}")
            return False

    def pause(self) -> bool:
        """
        暂停引擎

        Returns:
            bool: 操作是否成功
        """
        # 验证状态转换合法性
        if self._state != ENGINESTATUS_TYPES.RUNNING:
            self.log("ERROR", f"Cannot pause from {self.status} state")
            return False

        try:
            self._state = ENGINESTATUS_TYPES.PAUSED
            self.log("INFO", f"Engine {self.name} {self.engine_id} paused.")
            return True
        except Exception as e:
            self.log("ERROR", f"Failed to pause engine: {str(e)}")
            return False

    def stop(self) -> bool:
        """
        停止引擎，结束当前运行会话

        Returns:
            bool: 操作是否成功
        """
        # 验证状态转换合法性
        valid_states = [ENGINESTATUS_TYPES.RUNNING, ENGINESTATUS_TYPES.PAUSED]
        if self._state not in valid_states:
            self.log("ERROR", f"Cannot stop from {self.status} state")
            return False

        try:
            self._state = ENGINESTATUS_TYPES.STOPPED
            self.log("INFO", f"Engine '{self.name}' stopped: engine_id={self.engine_id}, run_id={self.run_id}")
            return True
        except Exception as e:
            self.log("ERROR", f"Failed to stop engine: {str(e)}")
            return False

    @property
    def event_timeout(self) -> float:
        """事件超时时间"""
        return self._event_timeout

    def set_event_timeout(self, timeout: float) -> None:
        """设置事件超时时间（供Service使用）"""
        self._event_timeout = timeout

    @property
    def is_resizing_queue(self) -> bool:
        """检查队列是否正在调整中"""
        return self._is_resizing

    def set_event_queue_size(self, size: int) -> bool:
        """动态调整事件队列大小（双缓冲方案，保证事件不丢失）

        Args:
            size: 新的队列大小

        Returns:
            bool: 是否成功启动调整（False表示正在调整中）
        """
        if size <= 0:
            raise ValueError("Queue size must be positive")

        # 检查是否正在调整中
        if self._is_resizing:
            self.log("WARN", f"Queue resize already in progress, cannot resize to {size}")
            return False

        # 获取调整锁，确保只有一个调整操作
        if not self._resize_lock.acquire(blocking=False):
            self.log("WARN", f"Cannot acquire resize lock, resize in progress")
            return False

        try:
            # 设置调整状态
            self._is_resizing = True

            old_queue = self._event_queue
            old_size = getattr(old_queue, 'maxsize', 0)

            if old_size == size:
                self.log("INFO", f"Queue size already {size}, no resize needed")
                self._is_resizing = False
                self._resize_lock.release()
                return True

            # 创建临时队列接收新事件
            temp_queue = Queue(maxsize=size)
            # 创建目标队列
            new_queue = Queue(maxsize=size)

            with self._queue_lock:
                # 原子性切换到临时队列，新事件将进入temp_queue
                self._event_queue = temp_queue

            self.log("INFO", f"Queue resize started: {old_size} -> {size}, using temporary buffer")

            # 在后台转移事件
            transfer_thread = threading.Thread(
                target=self._transfer_events_with_buffer,
                args=(old_queue, temp_queue, new_queue, old_size, size),
                daemon=True
            )
            transfer_thread.start()
            return True

        except Exception as e:
            # 异常时重置状态
            self._is_resizing = False
            self._resize_lock.release()
            self.log("ERROR", f"Queue resize failed: {e}")
            raise

    def _transfer_events_with_buffer(self, old_queue: Queue, temp_queue: Queue,
                                   new_queue: Queue, old_size: int, new_size: int) -> None:
        """使用双缓冲方案转移事件"""
        events_transferred = 0
        events_from_buffer = 0

        try:
            # 第一阶段：转移旧队列中的事件
            self.log("DEBUG", "Phase 1: Transferring events from old queue")
            while not old_queue.empty():
                try:
                    event = old_queue.get_nowait()
                    new_queue.put(event, block=True)  # 阻塞等待，不丢弃
                    events_transferred += 1
                except Empty:
                    break
                except Exception as e:
                    self.log("ERROR", f"Error transferring old event: {e}")
                    break

            # 第二阶段：转移临时队列中的事件（在调整期间到达的新事件）
            self.log("DEBUG", "Phase 2: Transferring events from temporary buffer")
            while True:
                try:
                    # 短暂超时获取临时队列事件，避免无限等待
                    event = temp_queue.get(timeout=0.1)
                    new_queue.put(event, block=True)  # 阻塞等待，不丢弃
                    events_from_buffer += 1
                except Empty:
                    # 临时队列空了，检查是否还有新事件到来
                    if temp_queue.empty():
                        break
                    continue
                except Exception as e:
                    self.log("ERROR", f"Error transferring buffered event: {e}")
                    break

            # 第三阶段：原子性替换到新队列
            with self._queue_lock:
                # 确保没有其他线程已经替换了队列
                if self._event_queue is temp_queue:
                    self._event_queue = new_queue

            total_events = events_transferred + events_from_buffer
            self.log("INFO", f"Queue resize completed: {old_size} -> {new_size}, "
                     f"transferred {events_transferred} old events, {events_from_buffer} new events, "
                     f"total {total_events} events")

        except Exception as e:
            self.log("ERROR", f"Queue resize failed: {e}")
            # 出错时恢复使用临时队列
            with self._queue_lock:
                if self._event_queue is temp_queue:
                    self._event_queue = temp_queue

        finally:
            # 无论如何都要重置调整状态并释放锁
            self._is_resizing = False
            self._resize_lock.release()

    def put_event(self, event) -> None:
        """向事件队列添加事件（线程安全）"""
        with self._queue_lock:
            self._event_queue.put(event, block=True)  # 阻塞等待，确保不丢失

    def get_event(self, timeout: Optional[float] = None):
        """从事件队列获取事件（线程安全）"""
        with self._queue_lock:
            if timeout:
                return self._event_queue.get(timeout=timeout)
            else:
                return self._event_queue.get()

    @property
    def run_sequence(self) -> int:
        """当前运行序列号"""
        return self._run_sequence

    @property
    def mode(self) -> EXECUTION_MODE:
        """获取引擎运行模式"""
        return self._mode

    @mode.setter
    def mode(self, value: EXECUTION_MODE) -> None:
        """设置引擎运行模式"""
        self._mode = value

    @property
    def portfolios(self) -> List:
        """获取管理的投资组合列表"""
        return self._portfolios

    def add_portfolio(self, portfolio) -> None:
        """添加投资组合"""
        if portfolio not in self._portfolios:
            self._portfolios.append(portfolio)
            self.log("INFO", f"Portfolio {portfolio.name} added to engine {self.name}")

    def remove_portfolio(self, portfolio) -> None:
        """移除投资组合"""
        if portfolio in self._portfolios:
            self._portfolios.remove(portfolio)
            self.log("INFO", f"Portfolio {portfolio.name} removed from engine {self.name}")

    @abstractmethod
    def run(self) -> Any:
        """
        运行引擎的抽象方法
        子类必须实现具体的运行逻辑
        """
        pass

    @abstractmethod
    def handle_event(self, event) -> None:
        """
        处理事件的抽象方法
        子类必须实现具体的事件处理逻辑
        """
        pass

    def put_event(self, event) -> None:
        """向事件队列添加事件"""
        self._event_queue.put(event)

    def get_engine_summary(self) -> Dict[str, Any]:
        """
        获取引擎状态摘要
        
        Returns:
            Dict: 包含引擎状态的详细信息
        """
        return {
            'name': self.name,
            'engine_id': self.engine_id,
            'run_id': self.run_id,
            'status': self.status,
            'is_active': self.is_active,
            'run_sequence': self.run_sequence,
            'component_type': self.component_type,
            'uuid': self.uuid,
            'mode': self.mode.value,
            'portfolios_count': len(self._portfolios)
        }

    def get_engine_status(self) -> EngineStatus:
        """
        获取引擎基础状态信息

        Returns:
            EngineStatus: 引擎状态对象
        """
        return EngineStatus(
            is_running=self._is_running,
            current_time=None,  # BaseEngine不包含时间信息
            execution_mode=self._mode,
            processed_events=self._processed_events_count,
            queue_size=self._event_queue.qsize(),
            status=self._state
        )

    def get_event_stats(self) -> EventStats:
        """
        获取事件处理统计信息

        Returns:
            EventStats: 事件统计对象
        """
        current_time = time.time()

        # 计算处理速率
        processing_rate = 0.0
        if self._processing_start_time is not None and self._processed_events_count > 0:
            elapsed_time = current_time - self._processing_start_time
            if elapsed_time > 0:
                processing_rate = self._processed_events_count / elapsed_time

        return EventStats(
            processed_events=self._processed_events_count,
            registered_handlers=0,  # BaseEngine不包含处理器注册
            queue_size=self._event_queue.qsize(),
            processing_rate=processing_rate
        )

    def get_queue_info(self) -> QueueInfo:
        """
        获取事件队列信息

        Returns:
            QueueInfo: 队列信息对象
        """
        queue_size = self._event_queue.qsize()
        max_size = self._event_queue.maxsize if hasattr(self._event_queue, 'maxsize') else 10000

        return QueueInfo(
            queue_size=queue_size,
            max_size=max_size,
            is_full=queue_size >= max_size,
            is_empty=queue_size == 0
        )

    def _increment_event_count(self) -> None:
        """内部方法：递增事件处理计数"""
        self._processed_events_count += 1
        self._last_processing_time = time.time()

        # 记录开始处理时间
        if self._processing_start_time is None:
            self._processing_start_time = time.time()

    def __repr__(self) -> str:
        return base_repr(self, self._name, 16, 60)
