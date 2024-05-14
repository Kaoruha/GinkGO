from typing import TYPE_CHECKING

from ginkgo.libs.ginkgo_links import GinkgoSingleLinkedList
import pandas as pd
from ginkgo.libs import datetime_normalize
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class BaseFeed(BacktestBase):
    """
    Feed something like price info, news...
    """

    def __init__(self, *args, **kwargs):
        super(BaseFeed, self).__init__(*args, **kwargs)
        self._subscribers = GinkgoSingleLinkedList()
        self._cache = None
        self._portfolio_cache = None

    @property
    def subscribers(self) -> GinkgoSingleLinkedList:
        return self._subscribers

    def subscribe(self, guys: any) -> None:
        # TODO Type Filter
        self._subscribers.append(guys)

    def broadcast(self) -> None:
        """
        pass info to each subscriber.
        """
        raise NotImplementedError()

    def is_code_on_market(self, code: str) -> bool:
        raise NotImplementedError()

    def get_daybar(self, code: str, date: any) -> pd.DataFrame:
        if code is None or date is None:
            return pd.DataFrame()

        datetime = datetime_normalize(date)
        if self.now is None:
            GLOG.ERROR(f"Time need to be sync.")
            return pd.DataFrame()

        if datetime > self._now:
            GLOG.CRITICAL(
                f"CurrentDate: {self.now} you can not get the future({datetime}) info."
            )
            return pd.DataFrame()

        if self._cache is None:
            self._cache = GDATA.get_daybar_df("", date_start=date, date_end=date)
        if self._cache.shape[0] == 0:
            return pd.DataFrame()
        else:
            return self._cache[self._cache.code == code]

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next frame.
        """
        # Time goes
        super(BaseFeed, self).on_time_goes_by(time, *args, **kwargs)
        self._cache = None
        self._portfolio_cache = None
