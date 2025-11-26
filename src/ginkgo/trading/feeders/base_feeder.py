from typing import TYPE_CHECKING, Callable, Optional
import pandas as pd

from ginkgo.libs import datetime_normalize, cache_with_expiration
from ginkgo.trading.core.backtest_base import BacktestBase
from ginkgo.trading.mixins.time_mixin import TimeMixin
from ginkgo.trading.events.base_event import EventBase


class BaseFeeder(BacktestBase, TimeMixin):
    """
    Feed something like price info, news...
    """

    def __init__(self, name="basic_feeder", timestamp=None, bar_service=None, *args, **kwargs):
        BacktestBase.__init__(self, name=name, *args, **kwargs)
        TimeMixin.__init__(self, timestamp=timestamp, *args, **kwargs)
        self._engine_put = None

        # 依赖注入：数据服务（支持测试Mock）
        if bar_service is None:
            from ginkgo.data import container
            self.bar_service = container.bar_service()
        else:
            self.bar_service = bar_service

    def set_event_publisher(self, publisher: Callable[[EventBase], None]) -> None:
        """
        Inject an event publisher (typically engine.put) for pushing events back to engine.
        """
        self._engine_put = publisher

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            self.log("ERROR", f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    def is_code_on_market(self, code: str, *args, **kwargs) -> bool:
        raise NotImplementedError()

    @cache_with_expiration
    def get_daybar(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        """统一的日线数据获取入口（供回测/实盘子类复用或覆盖）。

        - 默认使用 data.get_bars 读取指定日期的日线数据
        - 时间边界校验通过 self.validate_time_access（子类可覆盖）
        - 允许访问历史数据，禁止访问未来数据
        """
        if self.now is None:
            self.log("ERROR", "Time need to be sync.")
            return pd.DataFrame()

        dt = datetime_normalize(date)
        if dt is None:
            self.log("ERROR", f"Invalid date: {date}")
            return pd.DataFrame()

        # 时间边界校验（子类可覆盖 validate_time_access 以实现更严格策略）
        try:
            validator = getattr(self, "validate_time_access", None)
            if callable(validator):
                if not validator(self.now, dt):
                    return pd.DataFrame()
            else:
                # 默认：不可访问未来
                if dt.date() > self.now.date():
                    self.log("CRITICAL", f"CurrentDate: {self.now} you cannot get future({dt}) info.")
                    return pd.DataFrame()
        except Exception as e:
            self.log("ERROR", f"Time boundary validation failed: {e}")
            return pd.DataFrame()

        # 读取指定日期的日线数据
        try:
            df = self._load_daybar(code, dt)
            return df if df is not None else pd.DataFrame()
        except Exception as e:
            self.log("ERROR", f"Failed to load daybar for {code} at {dt}: {e}")
            return pd.DataFrame()

    def _load_daybar(self, code: str, dt, *args, **kwargs) -> pd.DataFrame:
        """默认的数据加载实现（可被子类覆盖）。"""
        try:
            # 调用BarService，获取ServiceResult包装的结果
            result = self.bar_service.get_bars(
                code=code,
                start_date=dt.date(),
                end_date=dt.date()
            )

            # 检查ServiceResult并解包数据
            if result.success and result.data:
                # BarService现在返回ModelList，使用to_dataframe()转换
                return result.data.to_dataframe()
            else:
                self.log("ERROR", f"Failed to get bars data: {result.error}")
                return pd.DataFrame()

        except Exception as e:
            self.log("ERROR", f"Error in _load_daybar for {code} at {dt}: {e}")
            return pd.DataFrame()

    # 订阅/广播机制已移除，兴趣集合通过 EventInterestUpdate 维护
