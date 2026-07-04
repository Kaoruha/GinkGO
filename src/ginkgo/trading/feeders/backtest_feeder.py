# Upstream: TimeControlledEventEngine, BaseEngine
# Downstream: feeders.base_feeder, feeders.interfaces, trading.events, entities.Bar, trading.time, libs, enums.SOURCE_TYPES
# Role: 回测数据馈送器实现，基于BarService加载历史K线数据，按交易日逐步推送EventPriceUpdate事件给引擎






"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities.

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""

import time
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Callable, Optional, Set
from rich.progress import Progress

from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.trading.feeders.mixins.feeder_publish_mixin import FeederPublishMixin
from ginkgo.trading.mixins.subscribable_mixin import SubscribableMixin, subscribes
from ginkgo.trading.feeders.interfaces import (
    IBacktestDataFeeder, DataFeedStatus
)
from ginkgo.trading.events import EventPriceUpdate, EventBase
from ginkgo.entities import Bar
from ginkgo.entities.mixins import TimeMixin
from ginkgo.trading.time.interfaces import ITimeProvider
from ginkgo.trading.time.providers import TimeBoundaryValidator
from ginkgo.libs import datetime_normalize, cache_with_expiration, GLOG
from ginkgo.enums import SOURCE_TYPES, EVENT_TYPES
from ginkgo.data.mappers import BarMapper


class BacktestFeeder(FeederPublishMixin, SubscribableMixin, BaseFeeder, IBacktestDataFeeder):
    """
    回测数据馈送器
    
    继承原有BaseFeeder功能，同时实现IBacktestDataFeeder接口，
    提供时间边界验证和完整的回测数据馈送功能。
    """
    
    __abstract__ = False

    def __init__(self, name="backtest_feeder", bar_service=None, *args, **kwargs):
        super().__init__(name=name, bar_service=bar_service, *args, **kwargs)

        self.status = DataFeedStatus.IDLE

        # 时间控制组件（由Engine注入）
        self.time_controller: Optional[ITimeProvider] = None
        self.time_boundary_validator: Optional[TimeBoundaryValidator] = None

        # 数据缓存
        self._data_cache: Dict[str, Any] = {}

        # 兴趣集（通过EventInterestUpdate动态更新）
        self._interested_codes: List[str] = []

        # 无数据 code WARN 去重（#6586）：同一 code 整个回测内 "No bar data" 至多 WARN 一次。
        # 预过滤后仍可能出现的"当日无 bar"（停牌等）走此去重，避免逐日刷屏。
        self._warned_no_data: Set[str] = set()
        
    # === IDataFeeder 基础接口实现 ===

    def initialize(self) -> bool:
        """初始化回测数据馈送器"""
        try:
            # 初始化时间边界验证器（如果time_controller已注入）
            if self.time_controller:
                self.time_boundary_validator = TimeBoundaryValidator(self.time_controller)

            self.status = DataFeedStatus.IDLE
            GLOG.INFO("BacktestFeeder initialized successfully")
            return True

        except Exception as e:
            GLOG.ERROR(f"BacktestFeeder initialization failed: {e}")
            return False
    
    def start(self) -> bool:
        """启动回测数据馈送"""
        try:
            if self.status != DataFeedStatus.IDLE:
                return False
                
            self.status = DataFeedStatus.CONNECTED
            GLOG.INFO("BacktestFeeder started successfully")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"BacktestFeeder start failed: {e}")
            return False
    
    def stop(self) -> bool:
        """停止回测数据馈送"""
        try:
            self.status = DataFeedStatus.DISCONNECTED
            self._data_cache.clear()
            GLOG.INFO("BacktestFeeder stopped")
            return True
            
        except Exception as e:
            GLOG.ERROR(f"BacktestFeeder stop failed: {e}")
            return False
    
    def get_status(self) -> DataFeedStatus:
        """获取当前状态"""
        return self.status

    def set_time_provider(self, time_controller: ITimeProvider) -> None:
        """设置时间控制器"""
        # 调用父类TimeMixin的set_time_provider
        super().set_time_provider(time_controller)
        self.time_controller = time_controller
        # 自动初始化时间边界验证器
        self.time_boundary_validator = TimeBoundaryValidator(time_controller)

    def validate_time_access(self, request_time: datetime, data_time: datetime) -> bool:
        """验证时间访问权限（防止未来数据泄露）"""
        if self.time_boundary_validator:
            return self.time_boundary_validator.can_access_time(data_time, request_time)
        
        # 默认验证：不能访问未来数据
        if self.now and data_time.date() > self.now.date():
            GLOG.CRITICAL(f"CurrentDate: {self.now} you cannot get future({data_time}) info.")
            return False
        return True
    
    # === IBacktestDataFeeder 扩展接口实现 ===
    
    def advance_time(self, target_time: datetime, *args, **kwargs) -> bool:
        """推进到指定时间，主动推送价格事件到引擎。

        #6586：无数据 code 过滤下沉到本层——
          1. 用 bar_service.get_available_codes 与 _interested_codes 取交集（feedable），
             剔除 DB 中完全无 bar 的 code，不为其查询/发事件/WARN；
          2. 按日批量取当日全市场复权 bar（一次 get(code=None)，消除逐股 N+1）；
          3. feedable code 当日无 bar 时 WARN，且整个回测内同一 code 至多 WARN 一次。
        """
        try:
            # 调用父类TimeMixin的advance_time
            success = super().advance_time(target_time, *args, **kwargs)
            if not success:
                return False

            # 使用事件更新的兴趣集
            if len(self._interested_codes) == 0:
                GLOG.WARN(f"BacktestFeeder: No interested symbols at {target_time.date()}")
                return True

            # 1. 预过滤：interested ∩ available（剔除 DB 中完全无 bar 数据的 code）
            feedable = self._compute_feedable_codes()
            if len(feedable) == 0:
                GLOG.WARN(f"BacktestFeeder: No feedable symbols at {target_time.date()}")
                return True

            GLOG.INFO(
                f"BacktestFeeder: Advancing to {target_time.date()}, "
                f"feeding {len(feedable)}/{len(self._interested_codes)} symbols"
            )

            # 2. 批量取当日复权 bar（一次查询，消除逐股 N+1），按 code 索引
            bars_by_code = self._fetch_day_bars_batch(target_time)

            # 3. 对 feedable code 发事件；当日无 bar 的走 WARN 去重
            event_count = 0
            for code in feedable:
                bar = bars_by_code.get(code)
                if bar is None:
                    self._warn_no_data_once(code, target_time)
                    continue
                event = EventPriceUpdate(payload=bar)
                event.set_source(SOURCE_TYPES.BACKTESTFEEDER)
                self.publish_price_update(event)
                event_count += 1

            GLOG.INFO(f"BacktestFeeder: Published {event_count} price events for {target_time.date()}")
            return True

        except Exception as e:
            GLOG.ERROR(f"BacktestFeeder: Error advancing time to {target_time}: {e}")
            return False

    def _compute_feedable_codes(self) -> List[str]:
        """interested ∩ available：剔除 DB 中完全无 bar 数据的 code（#6586）。

        - available 取自 bar_service.get_available_codes（DB 中实际有 bar 的 code 集合）；
        - _interested_codes 由事件链维护，**不改写它**（保护事件契约，见 ADR-019 与
          arch_backtest_feeder_interested_event_driven），预过滤结果只作用于"实际取 bar 的循环"；
        - get_available_codes 失败时降级为全 interested（不阻断回测，保留旧行为）。
        """
        result = self.bar_service.get_available_codes()
        if not result.success or not result.data:
            GLOG.WARN(
                f"BacktestFeeder: get_available_codes unavailable, "
                f"falling back to all {len(self._interested_codes)} interested codes"
            )
            return list(self._interested_codes)

        available = set(result.data)
        feedable = [c for c in self._interested_codes if c in available]
        dropped = len(self._interested_codes) - len(feedable)
        if dropped > 0:
            GLOG.INFO(
                f"BacktestFeeder: prefiltered {dropped} code(s) without bar data; "
                f"feeding {len(feedable)}/{len(self._interested_codes)}"
            )
        return feedable

    def _fetch_day_bars_batch(self, target_time: datetime) -> Dict[str, Any]:
        """批量取当日全市场复权 bar，按 code 索引返回（#6586 消除 N+1）。

        走 bar_service.get(code=None)（多股复权分支），一次查询取当日全部 code 的 bar
        并按 code 索引；调用方只用 feedable 子集。相比逐股 bar_service.get，把每日 N 次
        DB round-trip 压成 1 次（#5163 宽 universe 性能根因）。保留复权语义，与原
        _generate_price_events 单股 get(code) 一致。
        """
        bars_by_code: Dict[str, Any] = {}
        result = self.bar_service.get(
            code=None,
            start_date=target_time.date(),
            end_date=target_time.date(),
        )
        if not result.success or not result.data:
            return bars_by_code

        bar_entities = BarMapper.from_models(result.data)
        for bar in bar_entities:
            code = getattr(bar, "code", None)
            if code is not None:
                bars_by_code.setdefault(code, bar)
        return bars_by_code

    def _warn_no_data_once(self, code: str, target_time: datetime) -> None:
        """同一 code 的 "No bar data" WARN 整个回测内至多输出一次（#6586 刷屏根因）。"""
        if code in self._warned_no_data:
            return
        self._warned_no_data.add(code)
        GLOG.WARN(f"BacktestFeeder: No bar data for {code} at {target_time.date()}")
    
    @TimeMixin.validate_time(['start_time', 'end_time'])
    def get_historical_data(self,
                          symbols: List[str],
                          start_time: datetime,
                          end_time: datetime,
                          data_type: str = "bar") -> pd.DataFrame:
        """
        获取历史数据（带时间边界验证）

        Args:
            symbols: 股票代码列表
            start_time: 起始时间（验证时间边界）
            end_time: 结束时间（验证时间边界）
            data_type: 数据类型，默认"bar"

        Returns:
            pd.DataFrame: 包含所有股票历史数据的DataFrame
                - 如果有数据：返回拼接后的DataFrame，包含code列区分不同股票
                - 如果无数据：返回空DataFrame（时间合法但没有数据）
                - 如果不支持的数据类型：返回空DataFrame
            None: 时间验证失败（未来数据泄露，装饰器拦截）
        """
        dfs = []

        try:
            for symbol in symbols:
                if data_type == "bar":
                    result = self.bar_service.get(symbol, start_date=start_time.date(),
                                    end_date=end_time.date())
                    if result.success and result.data:
                        df = result.data.to_dataframe()
                    else:
                        GLOG.ERROR(f"Failed to get bars for {symbol}: {result.error}")
                        continue
                    if not df.empty:
                        dfs.append(df)
                else:
                    GLOG.WARN(f"Unsupported data type: {data_type}")

        except Exception as e:
            GLOG.ERROR(f"Error getting historical data: {e}")

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def get_data_range(self) -> tuple[datetime, datetime]:
        """获取数据时间范围（从已加载数据推断）"""
        # 如果没有配置，尝试从数据中推断
        return self._infer_data_range()
    
    # === 原有接口兼容性保持 ===
    
    # 订阅/广播机制已移除：通过引擎推进 advance_to_time 注入价格事件

    def get_daybar(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        """保持接口，委托父类统一实现；时间边界由本类的 validate_time_access 生效。"""
        return super().get_daybar(code, date, *args, **kwargs)

        
    # === 内部实现方法 ===
    
    def _generate_price_events(self, code: str, target_time: datetime) -> List[EventBase]:
        """为指定股票生成价格事件"""
        events = []

        try:
            # 通过注入的bar_service获取MBar模型数据
            result = self.bar_service.get(
                code=code,
                start_date=target_time.date(),
                end_date=target_time.date()
            )

            if not result.success or not result.data:
                GLOG.WARN(f"BacktestFeeder: No bar data for {code} at {target_time.date()}")
                return events

            # 转换ModelList → 业务对象列表（ADR-010: 走 Mapper 层，不再经 to_entities 懒转换）
            bar_entities = BarMapper.from_models(result.data)

            # 转换第一个Bar实体
            bar = bar_entities[0] if bar_entities else None
            if bar is None:
                GLOG.WARN(f"BacktestFeeder: Failed to convert bar entity for {code}")
                return events

            GLOG.INFO(
                f"BacktestFeeder: Bar data loaded for {code} at {target_time.date()} | "
                f"O:{bar.open} H:{bar.high} L:{bar.low} C:{bar.close} V:{bar.volume}"
            )

            event = EventPriceUpdate(payload=bar)
            event.set_source(SOURCE_TYPES.BACKTESTFEEDER)
            events.append(event)

        except Exception as e:
            GLOG.ERROR(f"BacktestFeeder: Error generating price events for {code}: {e}")

        return events

    def bind_engine(self, engine) -> None:
        super().bind_engine(engine)
        # 入方向：注册组件订阅的事件处理器（ADR-017，与出方向 _engine_put 对称）
        self.register_handlers(engine)

    # === 新增：兴趣集合事件处理 ===
    @subscribes(EVENT_TYPES.INTERESTUPDATE)
    def on_interest_update(self, event: "EventInterestUpdate") -> None:
        try:
            codes = getattr(event, 'codes', []) or []
            # 合并更新（此处简单使用去重并集）
            merged = set(self._interested_codes)
            merged.update(codes)
            self._interested_codes = sorted(list(merged))
            GLOG.INFO(f"Interest update: received {len(codes)} codes, total {len(self._interested_codes)} symbols: {self._interested_codes}")
        except Exception as e:
            GLOG.ERROR(f"Failed to update interested codes: {e}")
    
    def _infer_data_range(self) -> tuple[datetime, datetime]:
        """从时间控制器推断数据范围"""
        # 使用时间控制器当前时间
        default_start = datetime(2020, 1, 1)
        try:
            if self.time_controller is not None:
                default_end = self.time_controller.now()
            else:
                from ginkgo.trading.time.clock import now as clock_now
                default_end = clock_now()
        except Exception:
            from ginkgo.trading.time.clock import now as clock_now
            default_end = clock_now()
        return default_start, default_end
