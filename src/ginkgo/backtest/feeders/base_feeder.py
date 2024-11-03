from typing import TYPE_CHECKING, List
import pandas as pd

from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration
from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.data.operations import get_bars


class BaseFeeder(BacktestBase):
    """
    Feed something like price info, news...
    """

    def __init__(self, *args, **kwargs):
        super(BaseFeeder, self).__init__(*args, **kwargs)
        self._subscribers = []  # Init subscribers
        self._portfolio_interested_cache = {}
        self._engine_put = None

    def put(self, event) -> None:
        """
        Put event to eventengine.
        """
        if self._engine_put is None:
            GLOG.ERROR(f"Engine put not bind. Events can not put back to the engine.")
            return
        self._engine_put(event)

    @property
    def subscribers(self) -> List:
        return self._subscribers

    def subscribe(self, guys: any) -> None:
        # TODO Type Filter
        self._subscribers.append(guys)

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
            GLOG.ERROR(f"Time need to be sync.")
            return pd.DataFrame()

        datetime = datetime_normalize(date).date()
        datetime = datetime_normalize(datetime)

        if datetime > self._now:
            GLOG.CRITICAL(f"CurrentDate: {self.now} you can not get the future({datetime}) info.")
            return pd.DataFrame()
        if datetime < self._now:
            GLOG.CRITICAL(f"CurrentDate: {self.now} you can not get the past({datetime}) info.")
            return pd.DataFrame()

        df = get_bars(code, start_date=date, end_date=date)
        return df

    def on_time_goes_by(self, time: any, *args, **kwargs) -> None:
        """
        Go next frame.
        """
        # Time goes
        super(BaseFeeder, self).on_time_goes_by(time, *args, **kwargs)
        self._portfolio_interested_cache = {}
