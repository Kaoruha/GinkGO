# Upstream: Backtest Engines (时间控制回测引擎)、Live Trading Engines (时间控制实盘引擎)
# Downstream: EventEngine (继承提供事件驱动引擎基础能力)、ITimeAwareComponent (实现时间感知组件接口)、LogicalTimeProvider/SystemTimeProvider (逻辑时间/系统时间提供者)、TIME_MODE (时间模式枚举LOGICAL/SYSTEM)
# Role: TimeControlledEventEngine时间控制的事件引擎T5架构核心引擎统一事件驱动引擎支持回测和实盘模式的时间控制






"""
TimeControlledEventEngine - T5架构核心引擎

统一事件驱动引擎，支持回测和实盘模式的时间控制：
- 回测模式：逻辑时间推进 + 同步屏障
- 实盘模式：系统时间驱动 + 异步并发
- 完全兼容现有EventEngine接口
"""

import asyncio
import threading
import uuid
from abc import ABC, abstractmethod
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from queue import Queue, Empty
from typing import Dict, List, Optional, Any, Callable, Set, Union
import time

from .event_engine import EventEngine
from ..events.base_event import EventBase
from ..time.interfaces import ITimeProvider, ITimeAwareComponent
from ..time.providers import LogicalTimeProvider, SystemTimeProvider
from ..time.clock import set_global_time_provider, now as clock_now
from ginkgo.enums import EVENT_TYPES, SOURCE_TYPES, EXECUTION_MODE, TIME_MODE, ENGINESTATUS_TYPES
from ginkgo.trading.core.status import TimeInfo, ComponentSyncInfo


class TimeControlledEventEngine(EventEngine, ITimeAwareComponent):
    """时间控制的事件引擎

    继承现有EventEngine，扩展时间控制能力：
    - 回测模式：逻辑时间推进 + 同步屏障
    - 实盘模式：系统时间驱动 + 异步并发
    - 统一事件流：相同的事件类型和处理接口

    === 使用示例 ===

    创建回测引擎：
        >>> engine = TimeControlledEventEngine(
        ...     name="MyBacktest",
        ...     mode=EXECUTION_MODE.BACKTEST,
        ...     logical_time_start=datetime(2023, 1, 1),
        ...     max_concurrent_handlers=1
        ... )
        >>> engine.set_end_time(datetime(2023, 12, 31))

    创建实盘引擎：
        >>> engine = TimeControlledEventEngine(
        ...     name="MyLiveEngine",
        ...     mode=EXECUTION_MODE.LIVE,
        ...     max_concurrent_handlers=100,
        ...     event_timeout_seconds=5.0
        ... )
    """

    def __init__(
        self,
        name: str = "TimeControlledEngine",
        mode: EXECUTION_MODE = EXECUTION_MODE.BACKTEST,
        timer_interval: float = 1.0,
        max_event_queue_size: int = 10000,
        event_timeout_seconds: float = 30.0,
        max_concurrent_handlers: int = 100,
        logical_time_start: Optional[datetime] = None,
        progress_callback: Optional[callable] = None,
        *args,
        **kwargs,
    ):
        """
        初始化时间控制引擎（简化API）

        Args:
            name: 引擎名称
            mode: 运行模式（BACKTEST/LIVE/PAPER等）
            timer_interval: 定时器间隔（秒）
            max_event_queue_size: 事件队列最大大小
            event_timeout_seconds: 事件超时时间（秒）
            max_concurrent_handlers: 最大并发处理器数量
            logical_time_start: 逻辑时间起始点（仅回测模式）
            progress_callback: 进度回调函数，签名 callback(progress: float, current_date: str)
        """
        # 调用父类构造
        super().__init__(name=name, mode=mode, timer_interval=timer_interval, *args, **kwargs)

        # 调试：记录线程状态
        self.log(
            "DEBUG", f"{self.name}: Initialized - _main_thread_started={getattr(self, '_main_thread_started', 'N/A')}"
        )
        self.log("DEBUG", f"{self.name}: _main_thread.is_alive()={self._main_thread.is_alive()}")

        # mode属性通过继承BaseEngine的mode属性获取

        # 时间提供者
        self._time_provider: Optional[ITimeProvider] = None

        # 并发控制（实盘模式）
        self._executor: Optional[ThreadPoolExecutor] = None
        self._concurrent_semaphore: Optional[threading.Semaphore] = None

        # 运行时状态
        self._enhanced_processing_enabled = True
        # TimeControlledEngine专用的事件序列号（用于时间同步增强）
        self._event_sequence_number = 0
        self._event_sequence_lock = threading.Lock()

        # 自动时间推进配置
        self._backtest_interval: timedelta = timedelta(days=1)  # 回测时间推进间隔（默认日级）
        self._live_idle_sleep: float = 1.0  # 实盘空闲休眠时间（秒，默认1秒）

        # 配置参数
        self._max_event_queue_size = max_event_queue_size
        self._event_timeout_seconds = event_timeout_seconds
        self._max_concurrent_handlers = max_concurrent_handlers
        self._logical_time_start = logical_time_start or datetime(2023, 1, 1, tzinfo=timezone.utc)

        # 应用配置
        self.set_event_queue_size(max_event_queue_size)
        self.set_event_timeout(event_timeout_seconds)

        # 时间范围配置（将在_initialize_components中使用）
        self._start_date = None
        self._end_date = None

        # 进度回调
        self._progress_callback = progress_callback

        # 初始化组件
        self._initialize_components()

    def set_time_range(self, start_date: Optional[datetime] = None, end_date: Optional[datetime] = None) -> None:
        """统一设置时间范围

        Args:
            start_date: 回测开始时间
            end_date: 回测结束时间
        """
        self._start_date = start_date
        self._end_date = end_date

        # 如果时间提供者已存在且是LogicalTimeProvider，直接设置时间范围
        if self.mode == EXECUTION_MODE.BACKTEST and self._time_provider:
            if start_date:
                self._time_provider.set_start_time(start_date)
            if end_date:
                self._time_provider.set_end_time(end_date)

            self.log("INFO", f"Time range set: {start_date} to {end_date}")

    def start(self) -> bool:
        """启动引擎（带调试信息）"""
        self.log(
            "INFO",
            f"{self.name}: 🔥 start() called - _main_thread_started={self._main_thread_started}, is_alive={self._main_thread.is_alive()}",
        )
        result = super().start()
        self.log(
            "INFO",
            f"{self.name}: 🔥 start() completed - result={result}, _main_thread_started={self._main_thread_started}",
        )
        return result

    def stop(self) -> bool:
        """停止引擎（带调试信息）"""
        import traceback

        self.log("ERROR", f"{self.name}: 🔥 stop() called! Call stack:")
        for line in traceback.format_stack()[-3:-1]:  # 显示最近3层调用栈
            self.log("ERROR", f"    {line.strip()}")

        result = super().stop()
        self.log("DEBUG", f"{self.name}: stop() completed - result={result}")
        return result

    def _initialize_components(self):
        """初始化引擎组件"""

        # 根据模式初始化时间提供者
        if self.mode == EXECUTION_MODE.BACKTEST:
            # 回测模式：使用逻辑时间
            self._time_provider = LogicalTimeProvider(self._logical_time_start)
        else:
            self._time_provider = SystemTimeProvider()

        # 注册为时间感知组件
        if hasattr(self._time_provider, "register_time_listener"):
            self._time_provider.register_time_listener(self)
        # 设置全局时钟提供者，便于未完全注入处统一取时
        try:
            set_global_time_provider(self._time_provider)
        except Exception:
            pass

        # 初始化并发控制（实盘模式）
        if self.mode != EXECUTION_MODE.BACKTEST:
            # 实盘模式：使用多线程
            self._executor = ThreadPoolExecutor(
                max_workers=self._max_concurrent_handlers, thread_name_prefix="EventHandler"
            )
            self._concurrent_semaphore = threading.Semaphore(self._max_concurrent_handlers)

        # 注册时间推进事件处理器
        self._register_time_advance_handler()

        # 注册定时时间更新任务（所有模式，复用EventEngine.register_timer）
        self.register_timer(self._live_time_update_task)

    # === 保持兼容性的接口重写 ===

    @property
    def now(self) -> datetime:
        """获取当前时间 - 委托给时间提供者"""
        if self._time_provider:
            return self._time_provider.now()
        # 如果没有时间提供者，返回系统时间
        return datetime.now(timezone.utc)

    def stop(self) -> None:
        """停止事件引擎 - 扩展清理资源"""
        super().stop()

        # 清理线程池资源
        if self._executor:
            self._executor.shutdown(wait=True)

    def put(self, event: Any) -> None:
        """放入事件 - 使用父类的统一处理（包含事件增强）"""
        super().put(event)

    def register(self, event_type: EVENT_TYPES, handler: Callable) -> bool:
        """注册事件处理器 - 直接使用父类方法，移除不必要的包装"""
        # ❌ 移除 _wrap_handler 机制，避免重复注册和性能开销
        # 直接调用父类注册方法，保持与example一致的行为
        return super().register(event_type, handler)

    def unregister(self, event_type: EVENT_TYPES, handler: Callable) -> bool:
        """注销事件处理器 - 直接使用父类方法"""
        # ❌ 移除 _wrap_handler 相关的复杂逻辑，简化为直接调用父类方法
        return super().unregister(event_type, handler)

    def main_loop(self, main_flag: threading.Event) -> None:
        """统一主循环 - 事件驱动架构

        核心机制：
        1. 从事件队列获取事件并处理
        2. 回测模式：短超时快速处理，队列空闲时自动推进时间
        3. 实盘模式：阻塞式等待事件，由timer_loop定时推送时间更新事件
        """
        self.log("INFO", f"{self.name}: Main loop started - Mode: {self.mode}")
        self.log("INFO", f"{self.name}: main_flag.is_set() = {main_flag.is_set()} at start")
        self.log("INFO", f"{self.name}: main_flag id = {id(main_flag)}")

        if main_flag.is_set():
            self.log("ERROR", f"{self.name}: main_flag is already set at start! Exiting immediately.")
            return

        loop_count = 0
        self.log("INFO", f"{self.name}: Entering while loop...")
        self.log("INFO", f"{self.name}: About to enter while not main_flag.is_set(): {not main_flag.is_set()}")

        while not main_flag.is_set():
            loop_count += 1
            self.log("DEBUG", f"{self.name}: Main loop #{loop_count} started, main_flag.is_set()={main_flag.is_set()}")

            # 检查暂停标志，如果设置则阻塞等待直到清除
            if self._pause_flag.is_set():
                self.log("DEBUG", "Engine paused, waiting for resume...")
                self._pause_flag.wait()  # 阻塞直到pause_flag被clear()
                self.log("DEBUG", "Engine resumed")
                continue

            try:
                # 根据模式选择队列获取策略
                if self.mode == EXECUTION_MODE.BACKTEST:
                    # 回测：短超时，如果队列为空会抛出Empty异常
                    event = self._event_queue.get(timeout=0.01)
                else:
                    # 实盘：阻塞等待，事件驱动
                    event = self._event_queue.get(block=True)

                if event:
                    self.log("DEBUG", f"{self.name}: Processing event: {type(event).__name__}")
                    # 根据模式选择处理方式
                    if self.mode == EXECUTION_MODE.BACKTEST:
                        self._process_backtest_event(event)
                        self.log("INFO", f"{self.name}: ✅ Event processed, continuing loop...")
                    else:
                        # 实盘模式：支持并发处理
                        if self._executor and self._concurrent_semaphore:
                            self._concurrent_semaphore.acquire()
                            self._executor.submit(self._process_live_event_safe, event)
                        else:
                            self._process(event)

            except Empty:
                # 回测模式：队列空闲，自动推进时间
                if self.mode == EXECUTION_MODE.BACKTEST:
                    self.log("DEBUG", f"{self.name}: Queue empty, checking time advance")

                    # 统一检查回测是否结束
                    if self._is_backtest_finished():
                        current_time = self._time_provider.now()
                        self.log("INFO", f"🏁 Backtest completed - {current_time.date()}")

                        # 汇总回测结果
                        self._aggregate_backtest_results()

                        # 设置main_flag来退出主循环，让线程自然结束
                        main_flag.set()
                        # 更新引擎状态为STOPPED，这样is_active会返回False
                        self._state = ENGINESTATUS_TYPES.STOPPED
                        self.log("INFO", f"{self.name}: Engine state set to STOPPED")
                        break

                    # 回测还未结束，继续推进时间
                    next_time = self._get_next_time()
                    if next_time:
                        from ginkgo.trading.events.time_advance import EventTimeAdvance

                        event = EventTimeAdvance(next_time)
                        self.log("INFO", f"{self.name}: ⏰ Advancing time to {next_time.date()}")
                        self.put(event)

                        # 调用进度回调
                        self._report_progress(next_time)
                    # else: _get_next_time返回None的情况不会发生，因为_is_backtest_finished已经处理了
                # 实盘模式：继续等待（由timer_loop定时推送事件）
                continue

            except Exception as e:
                self.log("ERROR", f"Main loop error: {e}")

    # === 时间感知组件接口实现 ===

    def set_time_provider(self, time_provider: ITimeProvider) -> None:
        """设置时间提供者（带模式校验）"""
        from ginkgo.trading.time.providers import LogicalTimeProvider, SystemTimeProvider

        # 模式和Provider类型校验
        if self.mode == EXECUTION_MODE.BACKTEST:
            if not isinstance(time_provider, LogicalTimeProvider):
                raise ValueError(f"BACKTEST mode requires LogicalTimeProvider, got {type(time_provider).__name__}")
        else:
            if not isinstance(time_provider, SystemTimeProvider):
                raise ValueError(f"LIVE/PAPER mode requires SystemTimeProvider, got {type(time_provider).__name__}")

        self._time_provider = time_provider
        self.log("INFO", f"Time provider set: {type(time_provider).__name__}")

        # 传递TimeProvider给所有已绑定的Portfolio
        for portfolio in self.portfolios:
            portfolio.set_time_provider(time_provider)
            self.log("DEBUG", f"Time provider propagated to portfolio {portfolio.name}")

        # 如果DataFeeder已存在，把TimeProvider绑定给DataFeeder
        if hasattr(self, "_datafeeder") and self._datafeeder:
            if hasattr(self._datafeeder, "set_time_provider"):
                try:
                    self._datafeeder.set_time_provider(time_provider)
                    self.log("INFO", f"Time provider propagated to data feeder {self._datafeeder.name}")
                except Exception as e:
                    self.log("ERROR", f"Failed to propagate time provider to data feeder {self._datafeeder.name}: {e}")
            else:
                self.log("WARN", f"Data feeder {self._datafeeder.name} does not support set_time_provider")
        else:
            self.log("DEBUG", "No data feeder available for time provider propagation")

    def on_time_update(self, new_time: datetime) -> None:
        """时间更新通知回调"""
        pass  # Provider已更新时间,无需额外操作

    def get_current_time(self) -> datetime:
        """获取当前时间 (ITimeAwareComponent接口)"""
        return self.now

    async def on_time_changed(self, old_time: datetime, new_time: datetime):
        """时间变化回调"""
        self.on_time_update(new_time)

    async def on_heartbeat(self, current_time: datetime):
        """心跳回调"""
        pass  # Provider已管理时间

    # === 事件处理实现 ===

    def _process_backtest_event(self, event: EventBase):
        """处理回测事件"""
        try:
            event_id = getattr(event, "uuid", None)

            # 调用父类处理逻辑
            self._process(event)

            # 回测模式下事件完成由handler包装器负责登记

        except Exception as e:
            self.log("ERROR", f"Backtest event processing error: {e}")

    def _process_live_event_safe(self, event: EventBase):
        """安全处理实盘事件（在线程池中运行）"""
        try:
            self._process(event)
        finally:
            if self._concurrent_semaphore:
                self._concurrent_semaphore.release()

    def _wrap_handler(self, handler: Callable, event_type: EVENT_TYPES) -> Callable:
        """包装处理器以添加增强功能"""

        def enhanced_handler(event):
            try:
                result = handler(event)
                # 事件处理完成计数由父类_process方法自动处理
                return result
            except Exception as e:
                self.log("ERROR", f"Handler error for {event_type}: {e}")
                raise

        return enhanced_handler

    def _get_next_sequence_number(self) -> int:
        """获取下一个序列号"""
        with self._sequence_lock:
            self._event_sequence_number += 1
            return self._event_sequence_number

    # === 时间推进处理方法 ===

    def _register_time_advance_handler(self) -> None:
        """注册时间推进事件处理器"""
        from ginkgo.enums import EVENT_TYPES

        self.register(EVENT_TYPES.TIME_ADVANCE, self._handle_time_advance_event)
        self.register(EVENT_TYPES.COMPONENT_TIME_ADVANCE, self._handle_component_time_advance)
        self.log("INFO", f"{self.name}: 📝 Time advance event handlers registered")

    def _handle_time_advance_event(self, event: "EventTimeAdvance") -> None:
        """处理时间推进事件 - 启动分阶段组件时间推进流程"""
        self.log("INFO", f"{self.name}: ⚡ Processing EventTimeAdvance to {event.target_time.date()}")
        import traceback

        self.log("INFO", f"{self.name}: 🔍 Call stack before processing:")
        for line in traceback.format_stack()[-3:-1]:
            self.log("INFO", f"    {line.strip()}")
        try:
            target_time = event.target_time
            old_time = self._time_provider.now()

            # 1. 更新Provider时间
            if hasattr(self._time_provider, "set_current_time"):
                self._time_provider.set_current_time(target_time)

            # 2. 同步推进Matchmaking（最优先，无依赖）
            if self.matchmaking:
                try:
                    self.matchmaking.advance_time(target_time)
                except Exception as e:
                    self.log("ERROR", f"{self.name}: Matchmaking time advance error: {e}")

            # 3. 发送Portfolio时间推进事件（异步，通过事件队列）
            from ginkgo.trading.events.component_time_advance import EventComponentTimeAdvance

            self.put(EventComponentTimeAdvance(target_time, "portfolio"))

            # 4. Feeder.advance_time通过EventComponentTimeAdvance事件驱动机制处理
            #    统一由事件队列保证时序：Portfolio → Selector更新兴趣集 → Feeder生成价格事件

        except Exception as e:
            self.log("ERROR", f"{self.name}: Error in time advance event handler: {e}")
            raise

    def _handle_component_time_advance(self, event: "EventComponentTimeAdvance") -> None:
        """处理组件时间推进事件 - 分阶段推进Portfolio和Feeder

        分阶段顺序：
        1. Portfolio推进 → 发送EventInterestUpdate → 队列EventComponentTimeAdvance("feeder")
        2. mainloop处理EventInterestUpdate，Feeder更新interested_codes
        3. Feeder推进 → 为interested_codes生成EventPriceUpdate
        """
        try:
            info = event.payload  # 从payload中获取信息
            target_time = info.target_time
            component_type = info.component_type

            if component_type == "portfolio":
                # 阶段1：推进Portfolio时间
                self.log("DEBUG", f"{self.name}: 🔍 [PORTFOLIO LOOP] Found {len(self.portfolios)} portfolios")
                for i, portfolio in enumerate(self.portfolios):
                    try:
                        self.log("DEBUG", f"{self.name}: 🔍 [PORTFOLIO LOOP #{i+1}] About to call advance_time on {portfolio.name} (uuid: {getattr(portfolio, 'uuid', 'N/A')})")
                        portfolio.advance_time(target_time)
                        # Portfolio内部会发送EventInterestUpdate（如果兴趣集有变化）
                        self.log("DEBUG", f"{self.name}: Portfolio {portfolio.name} advanced to {target_time}")
                    except Exception as e:
                        self.log("ERROR", f"{self.name}: Portfolio time advance error: {e}")

                # Portfolio完成，发送Feeder时间推进事件（通过队列FIFO保证EventInterestUpdate先被处理）
                from ginkgo.trading.events.component_time_advance import EventComponentTimeAdvance

                self.put(EventComponentTimeAdvance(target_time, "feeder"))
                self.log("DEBUG", f"{self.name}: Portfolio stage completed, Feeder stage queued")

            elif component_type == "feeder":
                # 阶段2：推进Feeder时间（此时EventInterestUpdate已被mainloop处理）
                if self._datafeeder:
                    try:
                        self._datafeeder.advance_time(target_time)
                        # Feeder内部会为interested_codes生成EventPriceUpdate
                        self.log("DEBUG", f"{self.name}: Feeder advanced to {target_time}")
                    except Exception as e:
                        self.log("ERROR", f"{self.name}: Feeder time advance error: {e}")

                self.log("DEBUG", f"{self.name}: Component time advance sequence completed for {target_time}")

            else:
                self.log("WARN", f"{self.name}: Unknown component_type: {component_type}")

        except Exception as e:
            self.log("ERROR", f"{self.name}: Error in component time advance handler: {e}")
            raise

    # === 扩展接口 ===

    def get_time_controller(self) -> ITimeProvider:
        """获取时间控制器"""
        return self._time_provider

    def advance_time_to(self, target_time: datetime) -> bool:
        """推进时间到目标时间 - 简化版本（依赖Empty异常保证完成）"""
        if self.mode != EXECUTION_MODE.BACKTEST:
            return False

        try:
            # 创建时间推进事件并投递到mainloop
            from ..events.time_advance import EventTimeAdvance

            time_event = EventTimeAdvance(target_time)
            self.put(time_event)
            return True

        except Exception as e:
            self.log("ERROR", f"Time advancement error: {e}")
            return False

    def _check_and_emit_market_status(self, old_time: datetime, new_time: datetime) -> None:
        """检查市场状态变化并发布相应事件"""
        try:
            from ginkgo.trading.events import EventMarketStatus, MarketStatus

            old_status = self._determine_market_status(old_time)
            new_status = self._determine_market_status(new_time)

            if old_status != new_status:
                status_event = EventMarketStatus(new_status, market="上海证券交易所", timestamp=new_time)
                self.put(status_event)
                self.log("INFO", f"Market status changed from {old_status} to {new_status}")

        except Exception as e:
            self.log("ERROR", f"Market status check error: {e}")

    def _determine_market_status(self, time: datetime) -> "MarketStatus":
        """根据时间确定市场状态"""
        from ginkgo.trading.events import MarketStatus

        # 简化的市场状态判断逻辑
        hour = time.hour
        minute = time.minute
        weekday = time.weekday()  # 0=Monday, 6=Sunday

        # 周末休市
        if weekday >= 5:  # Saturday or Sunday
            return MarketStatus.HOLIDAY

        # 工作日交易时间判断
        if (9, 30) <= (hour, minute) <= (11, 30) or (13, 0) <= (hour, minute) <= (15, 0):
            return MarketStatus.OPEN
        elif (9, 15) <= (hour, minute) < (9, 30):
            return MarketStatus.PRE_MARKET
        elif (15, 0) < (hour, minute) <= (15, 30):
            return MarketStatus.AFTER_HOURS
        else:
            return MarketStatus.CLOSED

    def _trigger_data_updates(self, target_time: datetime) -> None:
        """触发数据馈送更新，生成价格更新和K线事件"""
        try:
            # 获取数据馈送器（如果已配置）
            if self._datafeeder is not None:
                # 触发数据更新，并将生成的事件放入引擎
                try:
                    events = self._datafeeder.advance_to_time(target_time)
                    if isinstance(events, list):
                        for ev in events:
                            self.put(ev)
                except TypeError:
                    # 若为异步接口或签名不同，忽略返回值
                    self._datafeeder.advance_to_time(target_time)

            # 检查是否需要触发K线结束事件
            self._check_and_emit_bar_close(target_time)

        except Exception as e:
            self.log("ERROR", f"Data update trigger error: {e}")

    def _check_and_emit_bar_close(self, current_time: datetime) -> None:
        """检查并发出K线结束事件"""
        try:
            from ginkgo.trading.events import EventBarClose

            # 检查分钟K线结束
            if current_time.second == 0 and current_time.microsecond == 0:
                if current_time.minute % 1 == 0:  # 1分钟K线
                    bar_event = EventBarClose(bar_type="1min", timestamp=current_time)
                    self.put(bar_event)

                if current_time.minute % 5 == 0:  # 5分钟K线
                    bar_event = EventBarClose(bar_type="5min", timestamp=current_time)
                    self.put(bar_event)

                if current_time.minute % 15 == 0:  # 15分钟K线
                    bar_event = EventBarClose(bar_type="15min", timestamp=current_time)
                    self.put(bar_event)

            # 检查日K线结束（收盘时）
            if current_time.hour == 15 and current_time.minute == 0:
                bar_event = EventBarClose(bar_type="1day", timestamp=current_time)
                self.put(bar_event)

        except Exception as e:
            self.log("ERROR", f"Bar close event error: {e}")

    def _is_end_of_day(self, old_time: datetime, new_time: datetime) -> bool:
        """判断是否跨越了交易日"""
        # 简化判断：如果跨越了15:00（收盘时间），认为是日终
        old_hour = old_time.hour
        new_hour = new_time.hour

        # 如果从15:00之前跨越到15:00之后，或者跨越了日期
        return (old_hour < 15 and new_hour >= 15) or old_time.date() != new_time.date()

    def _trigger_end_of_day_sequence(self, current_time: datetime) -> None:
        """触发日终事件序列"""
        try:
            from ginkgo.trading.events import EventEndOfDay

            # 发出日终事件
            eod_event = EventEndOfDay(current_time.date())
            self.put(eod_event)

            self.log("INFO", f"End of day sequence triggered for {current_time.date()}")

            # 可以在这里添加日终处理逻辑，如：
            # - 持仓结算
            # - 风险评估
            # - 报表生成
            # - 数据持久化

        except Exception as e:
            self.log("ERROR", f"End of day sequence error: {e}")

    def add_portfolio(self, portfolio) -> None:
        """
        添加投资组合到时间控制引擎

        继承EventEngine的所有事件处理功能，只添加时间控制特有的逻辑
        """
        # 调用父类方法（包含BaseEngine + EventEngine的完整逻辑）
        super().add_portfolio(portfolio)

        # TimeControlledEventEngine特有逻辑：自动注册事件处理器
        self._auto_register_component_events(portfolio)

        # 如果Router已存在，自动注册Portfolio到Router
        router = getattr(self, '_router', None)
        if router is not None:
            try:
                router.register_portfolio(portfolio)
                self.log("INFO", f"Portfolio {portfolio.uuid[:8]} auto-registered to router {router.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to register portfolio {portfolio.uuid[:8]} to router: {e}")
                raise

        self.log("DEBUG", f"Auto-registered event handlers for portfolio {portfolio.name}")

    
    def _auto_register_component_events(self, component) -> None:
        """自动注册组件的事件处理器"""
        from ginkgo.enums import EVENT_TYPES

        # 定义组件到事件处理器的映射
        component_event_mapping = {
            "PortfolioT1Backtest": {
                EVENT_TYPES.PRICEUPDATE: "on_price_received",  # 注意：PortfolioT1Backtest使用on_price_received
                EVENT_TYPES.SIGNALGENERATION: "on_signal",
                # EVENT_TYPES.ORDERPARTIALLYFILLED: "on_order_partially_filled",  # 移除：让Router处理
                EVENT_TYPES.POSITIONUPDATE: "on_position_update",
                EVENT_TYPES.CAPITALUPDATE: "on_capital_update",
                EVENT_TYPES.PORTFOLIOUPDATE: "on_portfolio_update",
            },
            "BacktestFeeder": {
                EVENT_TYPES.INTERESTUPDATE: "on_interest_update",
            },
            "TradeGateway": {
                EVENT_TYPES.PRICEUPDATE: "on_price_received",
                EVENT_TYPES.ORDERACK: "on_order_ack",
                EVENT_TYPES.ORDERPARTIALLYFILLED: "on_order_partially_filled",
            },
        }

        component_type = component.__class__.__name__
        if component_type not in component_event_mapping:
            self.log("DEBUG", f"No event mapping defined for component type: {component_type}")
            return

        event_mapping = component_event_mapping[component_type]
        registered_count = 0

        for event_type, handler_method_name in event_mapping.items():
            if hasattr(component, handler_method_name):
                try:
                    handler = getattr(component, handler_method_name)
                    self.register(event_type, handler)
                    registered_count += 1
                    self.log("INFO", f"Auto-registered {event_type.name} -> {component.name}.{handler_method_name}")
                except Exception as e:
                    self.log(
                        "WARN",
                        f"Failed to auto-register {event_type.name} -> {component.name}.{handler_method_name}: {e}",
                    )
            else:
                self.log("WARN", f"Component {component.name} missing handler method: {handler_method_name}")

        self.log("INFO", f"Auto-registered {registered_count} event handlers for {component.name} ({component_type})")

    def set_data_feeder(self, feeder) -> None:
        """设置数据馈送器"""
        # 统一使用_datafeeder字段名
        self._datafeeder = feeder
        self.log("INFO", f"Data feeder {feeder.name} bound to engine")

        # 绑定引擎到feeder
        feeder.bind_engine(self)
        self.log("INFO", f"Engine bound for feeder {feeder.name}")

        # 绑定Engine的put方法作为event_publisher
        if hasattr(feeder, "set_event_publisher"):
            try:
                feeder.set_event_publisher(self.put)
                self.log("INFO", f"Event publisher bound for feeder {feeder.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to set event publisher for feeder {feeder.name}: {e}")
                raise

        # 如果Engine已有TimeProvider，同时设置给DataFeeder
        if hasattr(feeder, "set_time_provider") and self._time_provider is not None:
            try:
                feeder.set_time_provider(self._time_provider)
                self.log("INFO", f"Time provider propagated to feeder {feeder.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to set time provider for feeder {feeder.name}: {e}")
        else:
            self.log("DEBUG", f"Time provider not available yet for feeder {feeder.name}")

        # 自动注册Feeder的事件处理器
        self._auto_register_component_events(feeder)

        # 传播 data_feeder 给所有 portfolio 的子组件（strategies, sizer, selectors）
        self.log("INFO", f"Propagating data_feeder to {len(self.portfolios)} portfolios")
        for portfolio in self.portfolios:
            if hasattr(portfolio, 'bind_data_feeder'):
                try:
                    portfolio.bind_data_feeder(feeder)
                    self.log("INFO", f"Data feeder propagated to portfolio {portfolio.name} and its components")
                except Exception as e:
                    self.log("ERROR", f"Failed to propagate data_feeder to portfolio {portfolio.name}: {e}")

    def bind_router(self, router) -> None:
        """绑定Router到引擎"""
        # 存储Router引用
        self._router = router

        # Router需要引擎来推送事件
        router.bind_engine(self)
        self.log("INFO", f"Router {router.name} bound to engine")

        # 如果Engine已有TimeProvider，同时设置给Router
        if self._time_provider is not None:
            try:
                router.set_time_provider(self._time_provider)
                self.log("INFO", f"Time provider propagated to router {router.name}")
            except Exception as e:
                self.log("ERROR", f"Failed to set time provider for router {router.name}: {e}")

        # 自动注册Router的事件处理器
        self._auto_register_component_events(router)

        # 如果引擎已有Portfolio，自动注册到Router
        if self.portfolios:
            for portfolio in self.portfolios:
                router.register_portfolio(portfolio)
                self.log("INFO", f"Portfolio {portfolio.uuid[:8]} auto-registered to router {router.name}")

    def get_data_feeder(self):
        """获取数据馈送器"""
        return getattr(self, "_datafeeder", None)

    def get_engine_stats(self) -> Dict[str, Any]:
        """获取引擎统计信息"""
        stats = {
            "mode": self.mode.value,
            "current_time": self.now.isoformat() if self.now else None,
            "event_sequence_number": self._event_sequence_number,
            "handler_count": self.handler_count,
            "general_count": self.general_count,
            "timer_count": self.timer_count,
            "todo_count": self.todo_count,
            "event_stats": self.event_stats,  # 使用父类的统计接口
        }

        if self._time_provider:
            if hasattr(self._time_provider, "get_time_statistics"):
                stats["time_stats"] = self._time_provider.get_time_statistics()

        return stats

    # === 时间推进配置方法 ===
    def set_start_time(self, start_time: datetime) -> None:
        """设置回测起始时间（委托给TimeProvider）

        Args:
            start_time: 回测起始时间
        """
        from ginkgo.trading.time.providers import LogicalTimeProvider

        if isinstance(self._time_provider, LogicalTimeProvider):
            self._time_provider.set_start_time(start_time)
            self.log("INFO", f"Backtest start time set to {start_time}")
        else:
            self.log("WARN", "set_start_time only works with LogicalTimeProvider (BACKTEST mode)")

    def set_end_time(self, end_time: datetime) -> None:
        """设置回测结束时间（委托给TimeProvider）

        Args:
            end_time: 回测结束时间
        """
        from ginkgo.trading.time.providers import LogicalTimeProvider

        if isinstance(self._time_provider, LogicalTimeProvider):
            self._time_provider.set_end_time(end_time)
            self.log("INFO", f"Backtest end time set to {end_time}")
        else:
            self.log("WARN", "set_end_time only works with LogicalTimeProvider (BACKTEST mode)")

    def set_backtest_interval(self, interval: timedelta) -> None:
        """设置回测时间推进间隔

        Args:
            interval: 时间间隔，例如：
                     - timedelta(days=1): 日级回测
                     - timedelta(hours=1): 小时级回测
                     - timedelta(minutes=1): 分钟级回测
        """
        self._backtest_interval = interval
        self.log("INFO", f"Backtest interval set to {interval}")

    def set_live_idle_sleep(self, seconds: float) -> None:
        """设置实盘空闲休眠时间

        Args:
            seconds: 休眠秒数，建议0.01-1.0之间
        """
        self._live_idle_sleep = seconds
        self.log("INFO", f"Live idle sleep set to {seconds}s")

    # === 自动时间推进辅助方法 ===
    def _should_advance_time(self) -> bool:
        """判断是否应该自动推进时间"""
        if self.mode == EXECUTION_MODE.BACKTEST:
            # 回测：检查是否到达结束时间
            return not self._is_backtest_finished()
        else:
            # 实盘：总是推进
            return True

    def _is_backtest_finished(self) -> bool:
        """统一的回测结束检查"""
        if self.mode != EXECUTION_MODE.BACKTEST:
            return False

        _, end_time = self._time_provider.get_time_range()
        current_time = self._time_provider.now()

        # 如果没有设置结束时间，则永远不结束
        if not end_time:
            return False

        # 当前时间已经到达或超过结束时间
        return current_time >= end_time

    def _report_progress(self, current_time: datetime) -> None:
        """
        报告回测进度

        Args:
            current_time: 当前回测时间
        """
        if self._progress_callback is None:
            return

        try:
            # 获取时间范围
            start_time, end_time = self._time_provider.get_time_range()

            if start_time and end_time:
                # 计算进度百分比
                total_days = (end_time - start_time).days
                elapsed_days = (current_time - start_time).days

                if total_days > 0:
                    progress = min(100.0, max(0.0, (elapsed_days / total_days) * 100))
                else:
                    progress = 100.0

                # 调用回调
                self._progress_callback(progress, str(current_time.date()))
        except Exception as e:
            self.log("DEBUG", f"{self.name}: Progress report failed: {e}")

    def _aggregate_backtest_results(self) -> None:
        """
        汇总回测结果

        在回测结束时调用，从分析器读取数据并写回 BacktestTask
        """
        try:
            from ginkgo import service_hub
            from ginkgo.trading.analysis.backtest_result_aggregator import BacktestResultAggregator

            # 获取服务
            analyzer_service = service_hub.data.analyzer_service()
            backtest_task_service = service_hub.data.backtest_task_service()

            # 创建汇总器
            aggregator = BacktestResultAggregator(
                analyzer_service=analyzer_service,
                backtest_task_service=backtest_task_service
            )

            # 获取 portfolio 信息
            portfolio_id = ""
            if self._portfolios and len(self._portfolios) > 0:
                portfolio_id = getattr(self._portfolios[0], 'portfolio_id', '')

            # 汇总结果
            result = aggregator.aggregate_and_save(
                task_id=self.run_id or "",
                portfolio_id=portfolio_id,
                engine_id=self.engine_id,
                status="completed"
            )

            if result.is_success():
                self.log("INFO", f"📊 Backtest results aggregated: {result.data}")
            else:
                self.log("ERROR", f"Failed to aggregate backtest results: {result.error}")

        except Exception as e:
            self.log("ERROR", f"Error during backtest result aggregation: {e}")

    def _get_next_time(self) -> Optional[datetime]:
        """获取下一个时间点"""
        if self.mode == EXECUTION_MODE.BACKTEST:
            # 回测：当前时间 + backtest_interval
            current_time = self._time_provider.now()
            return current_time + self._backtest_interval
        else:
            # 实盘：返回当前系统时间
            return datetime.now(timezone.utc)

    # === Timer任务实现 ===
    def _live_time_update_task(self) -> None:
        """定时时间更新任务（所有模式）

        由EventEngine.timer_loop定时调用（每隔timer_interval秒），推送EventTimeAdvance事件
        - 回测模式：辅助时间推进（主要靠main_loop的Empty异常自动推进）
        - 实盘模式：主要时间推进机制
        """
        try:
            current_time = self._time_provider.now()
            from ginkgo.trading.events.time_advance import EventTimeAdvance

            self.put(EventTimeAdvance(current_time))
            self.log("DEBUG", f"Timer task: EventTimeAdvance pushed for {current_time}")
        except Exception as e:
            self.log("ERROR", f"Timer time update task error: {e}")

    # === 增强的时间和组件同步查询接口 ===

    def get_time_info(self) -> TimeInfo:
        """
        获取时间相关信息（TimeControlledEventEngine专有）

        Returns:
            TimeInfo: 时间信息对象，包含时间模式、提供者类型等
        """
        # 确定时间模式
        if self.mode == EXECUTION_MODE.BACKTEST:
            time_mode = TIME_MODE.LOGICAL
        else:
            time_mode = TIME_MODE.SYSTEM

        # 确定时间提供者类型
        time_provider_type = type(self._time_provider).__name__ if self._time_provider else "Unknown"

        # 是否为逻辑时间
        is_logical_time = time_mode == TIME_MODE.LOGICAL

        # 获取逻辑开始时间（仅回测模式）
        logical_start_time = self._logical_time_start if is_logical_time else None

        # 获取时间推进次数（从时间提供者获取）
        time_advancement_count = 0
        if hasattr(self._time_provider, "get_advancement_count"):
            time_advancement_count = self._time_provider.get_advancement_count()

        return TimeInfo(
            current_time=self.now,
            time_mode=time_mode,
            time_provider_type=time_provider_type,
            is_logical_time=is_logical_time,
            logical_start_time=logical_start_time,
            time_advancement_count=time_advancement_count,
        )

    def get_component_sync_info(self, component_id: str) -> Optional[ComponentSyncInfo]:
        """
        获取指定组件的同步状态信息

        Args:
            component_id: 组件ID

        Returns:
            Optional[ComponentSyncInfo]: 组件同步信息，如果组件不存在则返回None
        """
        # 检查是否为时间感知组件
        if hasattr(self, "_time_aware_components"):
            component = self._time_aware_components.get(component_id)
            if component and hasattr(component, "get_sync_status"):
                sync_status = component.get_sync_status()
                return ComponentSyncInfo(
                    component_id=component_id,
                    component_type=type(component).__name__,
                    is_synced=sync_status.get("is_synced", False),
                    last_sync_time=sync_status.get("last_sync_time"),
                    sync_count=sync_status.get("sync_count", 0),
                    sync_error_count=sync_status.get("sync_error_count", 0),
                    is_registered=True,
                )

        # 检查是否为投资组合组件
        for portfolio in self.portfolios:
            if portfolio.uuid == component_id or portfolio.name == component_id:
                # 投资组合的同步状态基于其是否绑定到引擎
                return ComponentSyncInfo(
                    component_id=component_id,
                    component_type="Portfolio",
                    is_synced=True,  # 如果在 portfolios 列表中，认为已同步
                    last_sync_time=self.now,
                    sync_count=1,
                    sync_error_count=0,
                    is_registered=True,
                )

        # 检查是否为数据馈送器
        if self._datafeeder and (
            hasattr(self._datafeeder, "uuid")
            and self._datafeeder.uuid == component_id
            or hasattr(self._datafeeder, "name")
            and self._datafeeder.name == component_id
        ):
            return ComponentSyncInfo(
                component_id=component_id,
                component_type="DataFeeder",
                is_synced=True,  # 如果已绑定，认为已同步
                last_sync_time=self.now,
                sync_count=1,
                sync_error_count=0,
                is_registered=True,
            )

        # 组件未找到
        return None

    def get_all_components_sync_info(self) -> Dict[str, ComponentSyncInfo]:
        """
        获取所有已注册组件的同步状态信息

        Returns:
            Dict[str, ComponentSyncInfo]: 所有组件的同步信息字典，键为组件ID
        """
        components_info = {}

        # 添加投资组合组件
        for portfolio in self.portfolios:
            component_id = portfolio.uuid or portfolio.name
            components_info[component_id] = self.get_component_sync_info(component_id)

        # 添加数据馈送器组件
        if self._datafeeder:
            component_id = getattr(self._datafeeder, "uuid", None) or getattr(self._datafeeder, "name", "DataFeeder")
            components_info[component_id] = self.get_component_sync_info(component_id)

        # 添加撮合引擎组件
        if self._matchmaking:
            component_id = getattr(self._matchmaking, "uuid", None) or getattr(self._matchmaking, "name", "MatchMaking")
            components_info[component_id] = self.get_component_sync_info(component_id)

        # 添加时间感知组件（如果存在）
        if hasattr(self, "_time_aware_components"):
            for component_id, component in self._time_aware_components.items():
                sync_info = self.get_component_sync_info(component_id)
                if sync_info:
                    components_info[component_id] = sync_info

        return components_info

    def get_time_provider_info(self) -> Dict[str, Any]:
        """
        获取时间提供者的详细信息

        Returns:
            Dict[str, Any]: 时间提供者信息
        """
        if not self._time_provider:
            return {
                "provider_type": None,
                "is_initialized": False,
                "current_time": None,
                "supports_time_control": False,
            }

        info = {
            "provider_type": type(self._time_provider).__name__,
            "is_initialized": True,
            "current_time": self.now,
            "supports_time_control": hasattr(self._time_provider, "advance_time_to"),
            "supports_listeners": hasattr(self._time_provider, "register_time_listener"),
            "mode": self.mode.value,
        }

        # 添加逻辑时间提供者特有信息
        if isinstance(self._time_provider, LogicalTimeProvider):
            info.update(
                {
                    "is_logical_time": True,
                    "start_time": self._logical_time_start,
                    "can_advance_time": True,
                    "advancement_count": getattr(self._time_provider, "get_advancement_count", lambda: 0)(),
                }
            )
        else:
            info.update({"is_logical_time": False, "system_time_zone": self.now.tzinfo, "can_advance_time": False})

        return info

    def is_component_synced(self, component_id: str) -> bool:
        """
        检查指定组件是否已同步

        Args:
            component_id: 组件ID

        Returns:
            bool: 组件是否已同步
        """
        sync_info = self.get_component_sync_info(component_id)
        return sync_info.is_synced if sync_info else False

    def get_sync_summary(self) -> Dict[str, Any]:
        """
        获取组件同步状态摘要

        Returns:
            Dict[str, Any]: 同步状态摘要
        """
        all_components = self.get_all_components_sync_info()

        total_components = len(all_components)
        synced_components = sum(1 for info in all_components.values() if info.is_synced)
        registered_components = sum(1 for info in all_components.values() if info.is_registered)

        return {
            "total_components": total_components,
            "synced_components": synced_components,
            "registered_components": registered_components,
            "sync_rate": (synced_components / total_components) if total_components > 0 else 0.0,
            "components_by_type": {
                component_type: sum(1 for info in all_components.values() if info.component_type == component_type)
                for component_type in set(info.component_type for info in all_components.values())
            },
        }

    # === 对外运行接口 ===
    def run(self) -> Dict[str, Any]:
        """统一运行接口

        回测模式：使用 set_start_time()/set_end_time() 配置时间范围，
                 start() 后 main_loop() 自动推进时间，到达 end_time 后自动停止
        实盘模式：start() 后持续运行，手动 stop() 停止

        Returns:
            运行统计信息
        """
        from datetime import datetime

        start_time = clock_now()

        # 回测模式：启动前创建 BacktestTask 记录
        if self.mode == EXECUTION_MODE.BACKTEST:
            # 确保 run_id 已生成
            if self._run_id is None:
                self.generate_run_id()
            self._create_backtest_task()

        self.start()

        return {"status": "started", "mode": self.mode.value, "start_time": start_time.isoformat()}

    def _create_backtest_task(self) -> None:
        """创建回测任务记录（在回测启动前调用）

        注意：如果任务已存在（由 BacktestWorker 创建），则跳过创建
        """
        try:
            from ginkgo import service_hub

            task_service = service_hub.data.backtest_task_service()

            # 检查任务是否已存在（由 BacktestWorker 创建）
            if self.run_id:
                exists_result = task_service.exists(uuid=self.run_id)
                if exists_result.is_success() and exists_result.data.get("exists"):
                    self.log("INFO", f"Backtest task already exists: {self.run_id}, skipping creation")
                    return

            # 获取 portfolio_id
            portfolio_id = ""
            if self.portfolios:
                portfolio_id = self.portfolios[0].portfolio_id

            # 获取时间范围
            start_time_str = None
            end_time_str = None
            if self._time_provider:
                start_time, end_time = self._time_provider.get_time_range()
                start_time_str = str(start_time) if start_time else None
                end_time_str = str(end_time) if end_time else None

            # 创建任务
            result = task_service.create(
                task_id=self.run_id,
                engine_id=self.engine_id,
                portfolio_id=portfolio_id,
                config_snapshot={
                    "engine_name": self.name,
                    "start_time": start_time_str,
                    "end_time": end_time_str,
                }
            )

            if result.is_success():
                self.log("INFO", f"Created backtest task: {self.run_id}")
            else:
                self.log("WARN", f"Failed to create backtest task: {result.error}")

        except Exception as e:
            self.log("ERROR", f"Error creating backtest task: {e}")
