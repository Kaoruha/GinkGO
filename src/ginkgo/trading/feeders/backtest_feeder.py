# Upstream: Backtest Engines, Portfolio Manager
# Downstream: Data Layer, Event System
# Role: Backtest Feeder数据馈送器继承BaseFeeder提供BacktestFeeder回测数据数据推送






"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities.

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""

import time
import pandas as pd
from datetime import datetime, date, timedelta
from typing import List, Dict, Any, Callable, Optional
from rich.progress import Progress

from ginkgo.trading.feeders.base_feeder import BaseFeeder
from ginkgo.entities.mixins import EngineBindableMixin
from ginkgo.trading.feeders.interfaces import (
    IBacktestDataFeeder, DataFeedStatus
)
from ginkgo.trading.events import EventPriceUpdate, EventBase
from ginkgo.entities import Bar
from ginkgo.entities.mixins import TimeMixin
from ginkgo.trading.time.interfaces import ITimeProvider
from ginkgo.trading.time.providers import TimeBoundaryValidator
from ginkgo.libs import datetime_normalize, cache_with_expiration, GLOG
from ginkgo.enums import SOURCE_TYPES


class BacktestFeeder(EngineBindableMixin, BaseFeeder, IBacktestDataFeeder):
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
        self.event_publisher: Optional[Callable[[EventBase], None]] = None

        # 数据缓存
        self._data_cache: Dict[str, Any] = {}

        # 兴趣集（通过EventInterestUpdate动态更新）
        self._interested_codes: List[str] = []
        
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
    
    def set_event_publisher(self, publisher: Callable[[EventBase], None]) -> None:
        """设置事件发布器"""
        self.event_publisher = publisher
        # 保持与原有接口的兼容性
        self.put = publisher
    
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
        """推进到指定时间，主动推送价格事件到引擎"""
        try:
            # 调用父类TimeMixin的advance_time
            success = super().advance_time(target_time, *args, **kwargs)
            if not success:
                return False

            print(f"📅 DATAFEEDER ADVANCE_TIME: {target_time.date()}")
            print(f"📅 DATAFEEDER CURRENT INTERESTED ({len(self._interested_codes)}): {self._interested_codes}")

            # 使用事件更新的兴趣集
            if len(self._interested_codes) == 0:
                GLOG.WARN(f"No interested symbols at {target_time}")
                return True

            # 为每个股票生成并推送价格更新事件
            event_count = 0
            for code in self._interested_codes:
                price_events = self._generate_price_events(code, target_time)
                for event in price_events:
                    if self.event_publisher:
                        self.event_publisher(event)
                        event_count += 1

            print(f"📅 DATAFEEDER GENERATED {event_count} price events for {len(self._interested_codes)} symbols")
            GLOG.INFO(f"Published {event_count} events for time {target_time}")
            return True

        except Exception as e:
            GLOG.ERROR(f"Error advancing time to {target_time}: {e}")
            return False
    
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
            print(f"🔍 DATAFEEDER DEBUG: Querying data for {code} at {target_time.date()}")
            print(f"🔍 DATAFEEDER DEBUG: bar_service type: {type(self.bar_service)}")
            print(f"🔍 DATAFEEDER DEBUG: bar_service bound: {self.bar_service is not None}")

            result = self.bar_service.get(
                code=code,
                start_date=target_time.date(),
                end_date=target_time.date()
            )

            print(f"🔍 DATAFEEDER DEBUG: result.success: {result.success}")
            if hasattr(result, 'data'):
                print(f"🔍 DATAFEEDER DEBUG: result.data type: {type(result.data)}")
                if hasattr(result.data, 'empty'):
                    print(f"🔍 DATAFEEDER DEBUG: result.data.empty: {result.data.empty()}")

            if not result.success or result.data.empty():
                GLOG.WARN(f"❌ No data found for {code} at {target_time}")
                print(f"❌ DATAFEEDER WARNING: No data found for {code} at {target_time}")
                return events

            # 转换ModelList → 业务对象列表
            bar_entities = result.data.to_entities()

            # 🔍 [DEBUG] 检查返回的Bar数量
            print(f"🔍 [BAR COUNT] {code}: Found {len(bar_entities)} bars for {target_time.date()}")

            # 转换第一个Bar实体
            bar = bar_entities[0] if bar_entities else None
            if bar is None:
                GLOG.WARN(f"❌ Failed to convert bar entity for {code}")
                return events

            # 创建价格更新事件，使用Bar实体作为payload
            GLOG.INFO(f"✅ Creating EventPriceUpdate for {code}")
            event = EventPriceUpdate(payload=bar)
            event.set_source(SOURCE_TYPES.BACKTESTFEEDER)
            events.append(event)

            GLOG.INFO(f"🚀 EventPriceUpdate created for {code}")

        except Exception as e:
            GLOG.ERROR(f"Error generating price events for {code}: {e}")

        return events

    # === 新增：兴趣集合事件处理 ===
    def on_interest_update(self, event: "EventInterestUpdate") -> None:
        try:
            codes = getattr(event, 'codes', []) or []
            # 合并更新（此处简单使用去重并集）
            merged = set(self._interested_codes)
            merged.update(codes)
            self._interested_codes = sorted(list(merged))
            print(f"📅 DATAFEEDER INTEREST UPDATE: Received {len(codes)} codes: {codes}")
            print(f"📅 DATAFEEDER TOTAL INTERESTED: {len(self._interested_codes)} codes: {self._interested_codes}")
            GLOG.INFO(f"Updated interested codes: {len(self._interested_codes)} symbols")
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
