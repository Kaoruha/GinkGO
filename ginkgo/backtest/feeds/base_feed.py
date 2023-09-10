"""
The `Handler` class should deal with the event.
"""
import pandas as pd
from ginkgo.libs import GinkgoSingleLinkedList
from ginkgo.libs import datetime_normalize
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class BaseFeed(BacktestBase):
    def __init__(self, *args, **kwargs):
        super(BaseFeed, self).__init__(*args, **kwargs)
        self._subscribers = GinkgoSingleLinkedList()

    @property
    def subscribers(self) -> GinkgoSingleLinkedList:
        return self._subscribers

    def subscribe(self, guys) -> None:
        # TODO Type Filter
        self._subscribers.append(guys)

    def broadcast(self) -> None:
        raise NotImplementedError()

    def get_daybar(self, code: str, date: any) -> pd.DataFrame:
        GLOG.INFO(f"Trying get history bar, {code}  date:{date}")
        if code is None or date is None:
            return pd.DataFrame()
        datetime = datetime_normalize(date)
        if self.now is None:
            GLOG.CRITICAL(f"Time need to be sync.")
            return
        else:
            if datetime > self._now:
                GLOG.WARN(
                    f"CurrentDate: {self.now} you can not get the future({datetime}) info."
                )
                return pd.DataFrame()
            else:
                return GDATA.get_daybar_df(code, date, date)
