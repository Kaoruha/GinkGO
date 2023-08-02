import datetime
import pandas as pd
from ginkgo.libs import datetime_normalize
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo import GLOG
from ginkgo.enums import PRICEINFO_TYPES


class MatchMakingBase(object):
    def __init__(self):
        self._now = None
        self._price = pd.DataFrame()
        self._order = []

    @property
    def now(self) -> datetime.datetime:
        return self._now

    @property
    def price(self) -> pd.DataFrame:
        return self._price

    def on_time_goes_by(self, time: any):
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

    def on_stock_price(self, event: EventPriceUpdate):
        # TODO Check the source
        time = None
        try:
            time = event.timestamp
        except Exception as e:
            pass

        # Update Current Time
        if time is None:
            GLOG.ERROR(f"Price Event has no time. It is illegal")
            return
        if time < self._now:
            GLOG.ERROR(
                f"Current Time is {self.now} the price come from past {event.timestamp}"
            )
            return
        elif time > self._now:
            GLOG.ERROR(
                f"Current Time is {self.now} the price come from future {event.timestamp}"
            )
            return
        # One Frame just accept one line a code
        if self._price.shape[0] > 0:
            q = self._price[self._price.code == event.code]
            if q.shape[0] > 1:
                GLOG.ERROR(
                    f"Got 2 lines with {event.code} at this frame. Something Wrong."
                )
                return
            elif q.shape[0] == 1:
                GLOG.WARN(
                    f"{event.code} already in line at this frame. Drop this price event."
                )
                return
        # Deal with the tick
        ptype = event.price_type
        if ptype == PRICEINFO_TYPES.TICK:
            GLOG.WARN("MatchMaking not support tick info income now.")
            return
        # Deal with the bar
        elif ptype == PRICEINFO_TYPES.BAR:
            self._price = pd.concat([self._price, event.to_dataframe()], axis=0)
            self._price = self._price.reset_index(drop=True)

    def on_stock_order(self):
        # If sim, run try_match
        # If live, send the order to broker
        raise NotImplemented

    def query_order(self):
        # if sim, return the info in self.price
        # if live, ask the remote the order status
        raise NotImplemented
