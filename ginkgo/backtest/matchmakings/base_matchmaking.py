import datetime
import pandas as pd
from ginkgo.libs import datetime_normalize

class MatchMakingBase(object):
    def __init__(self):
        self._now = None
        self._price = pd.DataFrame()

    @property
    def now(self) -> datetime.datetime:
        return self._now
    @property
    def price(self) -> pd.DataFrame:
        return self._price

    def on_time_goes_by(self, time:any):
        time = datetime_normalize(time)
        if time is None:
            print("Format not support, can not update time")
            return
        if self._now is None:
            self._now = time
        else:
            if time < self.now:
                print("We can not go back such as a time traveller")
                return
            elif time == self.now:
                print("time not goes on")
                return
            else:
                # Go next frame
                self._now = time
                # Reset the price
                self._price = pd.DataFrame()

    def on_stock_price(self):
        pass

    def on_stock_order(self):
        raise NotImplemented

    def query_order(self):
        raise NotImplemented
