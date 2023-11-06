"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities. 

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""
import pandas as pd
from ginkgo.backtest.feeds.base_feed import BaseFeed
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.backtest.bar import Bar
from ginkgo.libs import datetime_normalize, GinkgoSingleLinkedList


class BacktestFeed(BaseFeed):
    abstract = False

    def __init__(self, *args, **kwargs):
        super(BacktestFeed, self).__init__(*args, **kwargs)
        self._engine = None

    @property
    def engine(self):
        return self._engine

    def bind_engine(self, engine):
        self._engine = engine
        if self._engine.datafeeder is None:
            self._engine.bind_datafeeder(self)

    def broadcast(self, *args, **kwargs):
        if len(self.subscribers) == 0:
            GLOG.ERROR(f"No portfolio subscribe. No target to broadcast.")
            return

        for sub in self.subscribers:
            interesting_list = sub.value.interested
            if len(interesting_list) == 0:
                continue
            # Get data
            df = pd.DataFrame()
            for i in interesting_list:
                code = i.value
                if code is None:
                    continue
                new_df = self.get_daybar(code, self.now)
                df = pd.concat([df, new_df], ignore_index=True)
            # Broadcast
            if df.shape[0] == 0:
                continue
            for i, r in df.iterrows():
                b = Bar()
                b.set(r)
                event = EventPriceUpdate(b)
                self.engine.put(event)

    def get_count_of_price(self, date, interested, *args, **kwargs):
        # Do Cache
        # Both count and price
        if date > self.now:
            return 0
        count = 0
        # print("!!!!!!!!")
        # print(date)
        # print(self.now)
        # print(interested)
        for i in interested:
            df = self.get_daybar(i.value, date)
            if df.shape[0] == 1:
                count += 1
        # print(count)
        # print("!!!!!!!!")
        return count

    def is_code_on_market(self, code, date, *args, **kwargs) -> bool:
        df = self.get_daybar(code, date)
        if df.shape[0] == 1:
            return True
        else:
            return False
