from typing import TYPE_CHECKING, List
import pandas as pd

from ginkgo.libs import datetime_normalize, cache_with_expiration
from ginkgo.backtest.core.backtest_base import BacktestBase
from ginkgo.data.containers import container


class BaseFeeder(BacktestBase):
    """
    Feed something like price info, news...
    """

    def __init__(self, name="basic_feeder", *args, **kwargs):
        super(BaseFeeder, self).__init__(name, *args, **kwargs)
        self._subscribers = []  # Init subscribers
        self._engine_put = None
        self._interested = []

    @property
    def interested(self) -> List:
        return self._interested

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            self.log("ERROR", f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def subscribers(self) -> List:
        return self._subscribers

    def add_subscriber(self, guy: any) -> None:
        if guy not in self._subscribers:
            self._subscribers.append(guy)

    def broadcast(self, *args, **kwargs) -> None:
        """
        broadcast info to each subscriber.
        """
        raise NotImplementedError()

    def is_code_on_market(self, code: str, *args, **kwargs) -> bool:
        raise NotImplementedError()

    @cache_with_expiration
    def get_daybar(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        if self.now is None:
            self.log("ERROR", f"Time need to be sync.")
            return pd.DataFrame()

        datetime = datetime_normalize(date).date()
        datetime = datetime_normalize(datetime)

        # 只限制访问未来数据，允许访问历史数据
        if datetime > self._now:
            self.log("ERROR", f"CurrentDate: {self.now} you can not get the future({datetime}) info.")
            return pd.DataFrame()
        
        # 移除对历史数据的限制 - 策略需要历史数据计算指标
        if datetime < self._now:
            self.log("DEBUG", f"Accessing historical data: {datetime}")

        bar_crud = container.cruds.bar()
        df = bar_crud.get_page_filtered(code=code, start_date=date, end_date=date)
        return df

    def get_tracked_symbols(self, *args, **kwargs) -> None:
        self.log("INFO", f"Get interested codes from {[i.name for i in self._subscribers]}")
        self._interested = []
        for i in self.subscribers:
            codes = i.interested
            for j in codes:
                if j not in self._interested:
                    self._interested.append(j)
