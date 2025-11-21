from abc import ABC, abstractmethod
import threading
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.mixins.named_mixin import NamedMixin
from ginkgo.trading.mixins.loggable_mixin import LoggableMixin
from ginkgo.libs import base_repr
from ginkgo.trading.core.status import EngineStatus, EventStats, QueueInfo
from typing import Dict, Any, Optional, List, Tuple
from enum import Enum
from queue import Queue, Empty, Full
from ginkgo.enums import ENGINESTATUS_TYPES, COMPONENT_TYPES, EXECUTION_MODE
import time


class BaseEngine(NamedMixin, LoggableMixin, BacktestBase, ABC):
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
            self._engine_id = engine_id
        else:
            self._engine_id = IdentityUtils.generate_component_uuid("engine")

        self._run_id = None
        self._run_sequence: int = 0
        self._state: ENGINESTATUS_TYPES = ENGINESTATUS_TYPES.IDLE
        self._datafeeder = None  # 数据馈送器引用

        # 初始化Mixin（按继承顺序：NamedMixin → LoggableMixin → BacktestBase）
        NamedMixin.__init__(self, name=name, *args, **kwargs)
        LoggableMixin.__init__(self, *args, **kwargs)
        BacktestBase.__init__(self, name=name, component_type=COMPONENT_TYPES.ENGINE, *args, **kwargs)

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
    def engine_id(self) -> str:
        """获取引擎ID"""
        return self._engine_id

    @property
    def run_id(self) -> str:
        """获取当前运行会话ID"""
        return self._run_id

    def generate_run_id(self, force: bool = False) -> str:
        """
        生成新的运行会话ID

        Args:
            force (bool): 是否强制生成新的run_id（即使当前已存在）

        Returns:
            str: 生成的run_id
        """
        from ..core.identity import IdentityUtils

        # 只有在强制生成或当前run_id为空时才生成新的
        if force or self._run_id is None:
            self._run_sequence += 1
            self._run_id = IdentityUtils.generate_run_id(self._engine_id, self._run_sequence)
            self.log("INFO", f"Generated new run_id: {self._run_id} for engine_id={self.engine_id}")

        return self._run_id

    def set_engine_id(self, engine_id: str) -> None:
        """
        手动设置引擎ID（仅在start前调用）

        Args:
            engine_id: 新的引擎ID
        """
        if self._state != ENGINESTATUS_TYPES.IDLE:
            raise RuntimeError("Cannot change engine_id after engine has started")

        self._engine_id = engine_id
        self.log("INFO", f"Engine ID updated to: {engine_id}")

    def set_run_id(self, run_id: str) -> None:
        """
        手动设置运行会话ID（仅在start前调用）

        Args:
            run_id: 新的运行会话ID
        """
        if self._state != ENGINESTATUS_TYPES.IDLE:
            raise RuntimeError("Cannot change run_id after engine has started")

        self._run_id = run_id
        self.log("INFO", f"Run ID updated to: {run_id}")

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
                self.generate_run_id()
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

    def check_components_binding(self) -> None:
        """
        检查所有组件的绑定状态、时间设置和事件注册

        在引擎启动前调用，用于诊断组件绑定问题
        """
        print(f"\n🔍 引擎运行前综合检查: {self.name}")
        print("=" * 70)

        # 1. 检查引擎基本状态
        print(f"📊 1️⃣ 引擎基本信息:")
        print(f"  模式: {self.mode}")
        print(f"  状态: {self.status}")
        print(f"  当前时间: {self.now}")
        print(f"  引擎ID: {getattr(self, 'engine_id', 'Not set')}")
        print(f"  运行ID: {getattr(self, 'run_id', 'Not set')}")

        # 2. 检查TimeProvider
        print(f"\n📊 2️⃣ TimeProvider状态:")
        if hasattr(self, '_time_provider') and self._time_provider:
            print(f"  ✅ 类型: {type(self._time_provider).__name__}")
            print(f"  ✅ 当前时间: {self._time_provider.now()}")
        else:
            print(f"  ❌ TimeProvider未设置")

        # 3. 检查DataFeeder
        print(f"\n📊 3️⃣ DataFeeder状态:")
        if hasattr(self, '_datafeeder') and self._datafeeder:
            feeder = self._datafeeder
            print(f"  ✅ 名称: {feeder.name}")
            print(f"  ✅ 类型: {type(feeder).__name__}")

            # 检查TimeProvider绑定
            tp_status = "✅" if hasattr(feeder, 'time_controller') and feeder.time_controller else "❌"
            tp_name = type(feeder.time_controller).__name__ if hasattr(feeder, 'time_controller') and feeder.time_controller else "None"
            print(f"  {tp_status} TimeProvider: {tp_name}")

            # 检查EventPublisher绑定
            pub_status = "✅" if hasattr(feeder, 'event_publisher') and feeder.event_publisher else "❌"
            print(f"  {pub_status} EventPublisher: {'已设置' if hasattr(feeder, 'event_publisher') and feeder.event_publisher else '未设置'}")

            # 检查BarService
            if hasattr(feeder, 'bar_service'):
                bar_status = "✅" if feeder.bar_service else "❌"
                print(f"  {bar_status} BarService: {'已设置' if feeder.bar_service else '未设置'}")

            # 检查感兴趣的股票
            codes = getattr(feeder, '_interested_codes', [])
            print(f"  ℹ️  感兴趣的股票: {codes}")

            # 检查engine绑定
            engine_bound = hasattr(feeder, '_bound_engine') and feeder._bound_engine is not None
            engine_status = "✅" if engine_bound else "❌"
            print(f"  {engine_status} Engine绑定: {'已绑定' if engine_bound else '未绑定'}")

        else:
            print(f"  ❌ DataFeeder未设置")

        # 4. 检查Portfolio及其所有组件
        print(f"\n📊 4️⃣ Portfolio及组件状态:")
        if self.portfolios:
            for i, portfolio in enumerate(self.portfolios):
                print(f"  📦 Portfolio {i+1}: {portfolio.name}")
                print(f"    ✅ 类型: {type(portfolio).__name__}")
                print(f"    ✅ Portfolio ID: {getattr(portfolio, 'portfolio_id', 'Not set')}")

                # 检查Portfolio的TimeProvider
                tp_status = "✅" if hasattr(portfolio, '_time_provider') and portfolio._time_provider else "❌"
                tp_name = type(portfolio._time_provider).__name__ if hasattr(portfolio, '_time_provider') and portfolio._time_provider else "None"
                print(f"    {tp_status} TimeProvider: {tp_name}")

                # 检查Portfolio的engine_put
                put_status = "✅" if hasattr(portfolio, '_engine_put') and portfolio._engine_put else "❌"
                print(f"    {put_status} Engine事件发布: {'已设置' if hasattr(portfolio, '_engine_put') and portfolio._engine_put else '未设置'}")

                # 检查Portfolio的engine绑定
                engine_bound = hasattr(portfolio, '_bound_engine') and portfolio._bound_engine is not None
                engine_status = "✅" if engine_bound else "❌"
                print(f"    {engine_status} Engine绑定: {'已绑定' if engine_bound else '未绑定'}")

                print(f"    💰 现金: {portfolio.cash}")
                print(f"    💎 价值: {portfolio.worth}")

                # 检查策略组件
                strategies = getattr(portfolio, 'strategies', [])
                print(f"    🎯 策略数量: {len(strategies)}")
                for j, strategy in enumerate(strategies):
                    print(f"      策略 {j+1}: {strategy.name}")
                    print(f"        类型: {type(strategy).__name__}")
                    signal_count = getattr(strategy, 'signal_count', 'Unknown')
                    print(f"        信号数: {signal_count}")

                    # 检查策略的engine绑定
                    strategy_engine_bound = hasattr(strategy, '_bound_engine') and strategy._bound_engine is not None
                    strategy_engine_status = "✅" if strategy_engine_bound else "❌"
                    print(f"        {strategy_engine_status} Engine绑定: {'已绑定' if strategy_engine_bound else '未绑定'}")

                    # 检查策略的TimeProvider
                    strategy_tp = hasattr(strategy, '_time_provider') and strategy._time_provider
                    strategy_tp_status = "✅" if strategy_tp else "❌"
                    print(f"        {strategy_tp_status} TimeProvider: {'已设置' if strategy_tp else '未设置'}")

                # 检查Selector组件
                selectors = getattr(portfolio, '_selectors', [])
                print(f"    🔍 Selector数量: {len(selectors)}")
                for j, selector in enumerate(selectors):
                    print(f"      Selector {j+1}: {selector.name}")
                    print(f"        类型: {type(selector).__name__}")
                    selected = getattr(selector, '_interested', [])
                    print(f"        选择股票: {selected}")

                    # 检查selector的engine绑定
                    selector_engine_bound = hasattr(selector, '_bound_engine') and selector._bound_engine is not None
                    selector_engine_status = "✅" if selector_engine_bound else "❌"
                    print(f"        {selector_engine_status} Engine绑定: {'已绑定' if selector_engine_bound else '未绑定'}")

                    # 检查selector的TimeProvider
                    selector_tp = hasattr(selector, '_time_provider') and selector._time_provider
                    selector_tp_status = "✅" if selector_tp else "❌"
                    print(f"        {selector_tp_status} TimeProvider: {'已设置' if selector_tp else '未设置'}")

                    # 检查selector的engine_put
                    selector_put = hasattr(selector, '_engine_put') and selector._engine_put
                    selector_put_status = "✅" if selector_put else "❌"
                    print(f"        {selector_put_status} Engine事件发布: {'已设置' if selector_put else '未设置'}")

                # 检查Sizer组件
                sizer = getattr(portfolio, '_sizer', None)
                print(f"    📏 Sizer: {'已设置' if sizer else '未设置'}")
                if sizer:
                    print(f"      类型: {type(sizer).__name__}")

                    # 检查sizer的engine绑定
                    sizer_engine_bound = hasattr(sizer, '_bound_engine') and sizer._bound_engine is not None
                    sizer_engine_status = "✅" if sizer_engine_bound else "❌"
                    print(f"      {sizer_engine_status} Engine绑定: {'已绑定' if sizer_engine_bound else '未绑定'}")

                    # 检查sizer的TimeProvider
                    sizer_tp = hasattr(sizer, '_time_provider') and sizer._time_provider
                    sizer_tp_status = "✅" if sizer_tp else "❌"
                    print(f"      {sizer_tp_status} TimeProvider: {'已设置' if sizer_tp else '未设置'}")
        else:
            print(f"  ❌ 没有Portfolio")

        # 5. 检查事件处理器注册
        print(f"\n📊 5️⃣ 事件处理器注册状态:")
        if hasattr(self, '_handlers') and self._handlers:
            from ginkgo.enums import EVENT_TYPES

            # 定义关键事件类型
            critical_events = [
                EVENT_TYPES.TIME_ADVANCE,
                EVENT_TYPES.COMPONENT_TIME_ADVANCE,
                EVENT_TYPES.INTERESTUPDATE,
                EVENT_TYPES.PRICEUPDATE,
                EVENT_TYPES.SIGNALGENERATION,
                EVENT_TYPES.ORDERACK,
                EVENT_TYPES.ORDERPARTIALLYFILLED,
            ]

            for event_type in critical_events:
                handlers = self._handlers.get(event_type, [])
                status = "✅" if handlers else "❌"
                event_name = getattr(event_type, 'name', str(event_type))
                print(f"  {status} {event_name}: {len(handlers)} 个处理器")

                # 显示处理器详情（仅有关键事件）
                if handlers and event_type in [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.SIGNALGENERATION]:
                    for j, handler in enumerate(handlers):
                        print(f"    处理器 {j+1}: {handler}")
        else:
            print(f"  ❌ 事件处理器未初始化")

        # 6. 检查队列状态
        print(f"\n📊 6️⃣ 事件队列状态:")
        queue_info = self.get_queue_info()
        print(f"  队列大小: {queue_info.queue_size}/{queue_info.max_size}")
        queue_status = "正常"
        if queue_info.is_full:
            queue_status = "满"
        elif queue_info.is_empty:
            queue_status = "空"
        print(f"  队列状态: {queue_status}")

        # 7. 总结
        print(f"\n📋 7️⃣ 综合检查总结:")
        issues = []

        # 检查关键组件
        if not hasattr(self, '_time_provider') or not self._time_provider:
            issues.append("❌ TimeProvider未设置")
        if not hasattr(self, '_datafeeder') or not self._datafeeder:
            issues.append("❌ DataFeeder未设置")
        if not self.portfolios:
            issues.append("❌ 没有Portfolio")

        # 检查Portfolio组件
        for portfolio in self.portfolios:
            if not hasattr(portfolio, '_engine_put') or not portfolio._engine_put:
                issues.append(f"❌ Portfolio {portfolio.name} 缺少engine_put")
            for selector in getattr(portfolio, '_selectors', []):
                if not hasattr(selector, '_engine_put') or not selector._engine_put:
                    issues.append(f"❌ Selector {selector.name} 缺少engine_put")

        # 检查关键事件处理器
        critical_events = [EVENT_TYPES.PRICEUPDATE, EVENT_TYPES.SIGNALGENERATION]
        for event_type in critical_events:
            if not hasattr(self, '_handlers') or not self._handlers.get(event_type):
                issues.append(f"❌ 缺少 {event_type.name} 事件处理器")

        if issues:
            print(f"  发现问题:")
            for issue in issues:
                print(f"    {issue}")
            print(f"  ⚠️  请在启动引擎前修复上述问题")
        else:
            print(f"  ✅ 所有关键组件和事件处理器都已正确设置")
            print(f"  🚀 引擎可以安全启动")

        print(f"\n" + "=" * 70)
        print(f"✅ 引擎运行前综合检查完成")
        print(f"🚀 引擎准备启动\n")

        # 3秒倒数已取消，直接启动引擎
        # import time
        # print("⏰ 引擎启动倒数: ", end="", flush=True)
        # for i in range(3, 0, -1):
        #     print(f"{i}... ", end="", flush=True)
        #     time.sleep(1)
        # print("启动引擎!\n")

    def set_data_feeder(self, feeder) -> None:
        """
        设置数据馈送器（通用引擎功能）

        Args:
            feeder: 数据馈送器实例
        """
        # 统一使用_datafeeder字段名
        self._datafeeder = feeder
        self.log("INFO", f"Data feeder {feeder.name} bound to engine")

        # 绑定引擎到feeder
        if hasattr(feeder, 'bind_engine'):
            try:
                feeder.bind_engine(self)
                self.log("INFO", f"Engine bound for feeder {feeder.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to bind engine for feeder {feeder.name}: {e}")
                raise

        # 绑定Engine的put方法作为event_publisher（向后兼容）
        if hasattr(feeder, 'set_event_publisher'):
            try:
                feeder.set_event_publisher(self.put)
                self.log("INFO", f"Event publisher bound for feeder {feeder.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to set event publisher for feeder {feeder.name}: {e}")
                raise

    def __repr__(self) -> str:
        # Safe repr that avoids circular references
        try:
            return f"<{self.__class__.__name__} name={getattr(self, '_name', 'Unknown')} id={id(self)}>"
        except Exception:
            return f"<{self.__class__.__name__} id={id(self)}>"
