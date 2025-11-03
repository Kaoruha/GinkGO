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
from ginkgo.trading.feeders.interfaces import (
    IBacktestDataFeeder, DataFeedStatus
)
from ginkgo.trading.events import EventPriceUpdate, EventBase
from ginkgo.trading.entities.bar import Bar
from ginkgo.trading.entities.time_related import TimeRelated
from ginkgo.trading.time.interfaces import ITimeProvider
from ginkgo.trading.time.providers import TimeBoundaryValidator
from ginkgo.libs import datetime_normalize, cache_with_expiration
from ginkgo.enums import SOURCE_TYPES


class BacktestFeeder(BaseFeeder, IBacktestDataFeeder):
    """
    回测数据馈送器
    
    继承原有BaseFeeder功能，同时实现IBacktestDataFeeder接口，
    提供时间边界验证和完整的回测数据馈送功能。
    """
    
    __abstract__ = False

    def __init__(self, name="backtest_feeder", bar_service=None, *args, **kwargs):
        super(BacktestFeeder, self).__init__(name=name, bar_service=bar_service, *args, **kwargs)

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
            self.log("INFO", "BacktestFeeder initialized successfully")
            return True

        except Exception as e:
            self.log("ERROR", f"BacktestFeeder initialization failed: {e}")
            return False
    
    def start(self) -> bool:
        """启动回测数据馈送"""
        try:
            if self.status != DataFeedStatus.IDLE:
                return False
                
            self.status = DataFeedStatus.CONNECTED
            self.log("INFO", "BacktestFeeder started successfully")
            return True
            
        except Exception as e:
            self.log("ERROR", f"BacktestFeeder start failed: {e}")
            return False
    
    def stop(self) -> bool:
        """停止回测数据馈送"""
        try:
            self.status = DataFeedStatus.DISCONNECTED
            self._data_cache.clear()
            self.log("INFO", "BacktestFeeder stopped")
            return True
            
        except Exception as e:
            self.log("ERROR", f"BacktestFeeder stop failed: {e}")
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
        self.time_controller = time_controller
        # 自动初始化时间边界验证器
        self.time_boundary_validator = TimeBoundaryValidator(time_controller)

    def validate_time_access(self, request_time: datetime, data_time: datetime) -> bool:
        """验证时间访问权限（防止未来数据泄露）"""
        if self.time_boundary_validator:
            return self.time_boundary_validator.can_access_time(data_time, request_time)
        
        # 默认验证：不能访问未来数据
        if self.now and data_time.date() > self.now.date():
            self.log("CRITICAL", f"CurrentDate: {self.now} you cannot get future({data_time}) info.")
            return False
        return True
    
    # === IBacktestDataFeeder 扩展接口实现 ===
    
    def advance_to_time(self, target_time: datetime) -> None:
        """推进到指定时间，主动推送价格事件到引擎"""
        try:
            # 更新内部时间
            self.advance_time(target_time)

            # 使用事件更新的兴趣集
            if len(self._interested_codes) == 0:
                self.log("WARN", f"No interested symbols at {target_time}")
                return

            # 为每个股票生成并推送价格更新事件
            event_count = 0
            for code in self._interested_codes:
                price_events = self._generate_price_events(code, target_time)
                for event in price_events:
                    if self.event_publisher:
                        self.event_publisher(event)
                        event_count += 1

            self.log("INFO", f"Published {event_count} events for time {target_time}")

        except Exception as e:
            self.log("ERROR", f"Error advancing to time {target_time}: {e}")
    
    @TimeRelated.validate_time(['start_time', 'end_time'])
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
                    df = self.bar_service.get_bars(symbol, start_date=start_time.date(),
                                end_date=end_time.date(), as_dataframe=True)
                    if not df.empty:
                        dfs.append(df)
                else:
                    self.log("WARN", f"Unsupported data type: {data_type}")

        except Exception as e:
            self.log("ERROR", f"Error getting historical data: {e}")

        return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()
    
    def get_data_range(self) -> tuple[datetime, datetime]:
        """获取数据时间范围（从已加载数据推断）"""
        # 如果没有配置，尝试从数据中推断
        return self._infer_data_range()
    
    # === 原有接口兼容性保持 ===
    
    # 订阅/广播机制已移除：通过引擎推进 advance_to_time 注入价格事件

    def get_daybar(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        """保持接口，委托父类统一实现；时间边界由本类的 validate_time_access 生效。"""
        return super(BacktestFeeder, self).get_daybar(code, date, *args, **kwargs)

    def advance_time(self, time: any, *args, **kwargs):
        """时间推进回调 - 增强版本"""
        # 调用父类方法保持兼容性
        super(BacktestFeeder, self).advance_time(time, *args, **kwargs)
        
        # 新增：自动触发数据广播
        self.log("INFO", f"⏰ Time goes by: {time}, engine should call advance_to_time() explicitly")
    
    # === 内部实现方法 ===
    
    def _generate_price_events(self, code: str, target_time: datetime) -> List[EventBase]:
        """为指定股票生成价格事件"""
        events = []

        try:
            # 通过注入的bar_service获取MBar模型数据
            bars = self.bar_service.get_bars(
                code=code,
                start_date=target_time.date(),
                end_date=target_time.date(),
                as_dataframe=False
            )

            if not bars:
                self.log("WARN", f"❌ No data found for {code} at {target_time}")
                return events

            # 转换MBar → Bar实体
            self.log("INFO", f"✅ Creating Bar and EventPriceUpdate for {code}")
            bar = Bar.from_model(bars[0])

            event = EventPriceUpdate(price_info=bar)
            event.set_source(SOURCE_TYPES.BACKTESTFEEDER)
            events.append(event)

            self.log("INFO", f"🚀 EventPriceUpdate created for {code}")

        except Exception as e:
            self.log("ERROR", f"Error generating price events for {code}: {e}")

        return events

    # === 新增：兴趣集合事件处理 ===
    def on_interest_update(self, event: "EventInterestUpdate") -> None:
        try:
            codes = getattr(event, 'codes', []) or []
            # 合并更新（此处简单使用去重并集）
            merged = set(self._interested_codes)
            merged.update(codes)
            self._interested_codes = sorted(list(merged))
            self.log("INFO", f"Updated interested codes: {len(self._interested_codes)} symbols")
        except Exception as e:
            self.log("ERROR", f"Failed to update interested codes: {e}")
    
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
