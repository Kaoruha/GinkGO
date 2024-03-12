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
        self._cache = {}

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

        key = f"{code}{date}daybar"

        if key in self._cache:
            return self._cache[key]
        else:
            df = GDATA.get_daybar_df(code, date, date)
            self._cache[key] = df
            return df
