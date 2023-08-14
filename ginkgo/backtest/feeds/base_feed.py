"""
The `Handler` class should deal with the event.
"""
import pandas as pd
from ginkgo.libs import GinkgoSingleLinkedList
from ginkgo.libs import datetime_normalize
from ginkgo.data.ginkgo_data import GDATA
from ginkgo import GLOG


class BaseFeed(object):
    def __init__(self, *args, **kwargs):
        self._subscribers = GinkgoSingleLinkedList()
        self._now = None

    @property
    def subscribers(self) -> GinkgoSingleLinkedList:
        return self._subscribers

    def subscribe(self, guys) -> None:
        # TODO Type Filter
        self._subscribers.append(guys)

    def broadcast(self) -> None:
        raise NotImplementedError()

    def on_time_goes_by(self, date: any) -> None:
        date = datetime_normalize(date)
        self._now = date

    def get_history(self, code: str, date: any) -> pd.DataFrame:
        print(f"Trying get history bar, {code}  date:{date}")
        if code is None or date is None:
            return pd.DataFrame()
        datetime = datetime_normalize(date)
        if self._now is None:
            return GDATA.get_daybar_df(code, date, date)
        else:
            if datetime > self._now:
                GLOG.WARN(f"CurrentDate: {self._now} you can not get the future info.")
                return pd.DataFrame()
            else:
                return GDATA.get_daybar_df(code, date, date)
