"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities. 

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""
from ginkgo.backtest.feeds.base_feed import BaseFeed
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.backtest.bar import Bar
from ginkgo.libs import datetime_normalize, GinkgoSingleLinkedList

import time
import pandas as pd
from rich.progress import Progress


class BacktestFeed(BaseFeed):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

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
            GLOG.WARN(f"No portfolio subscribe. No target to broadcast.")
            return

        for sub in self.subscribers:
            interesting_list = sub.value.interested

            if len(interesting_list) == 0:
                # No interested, Go Next Subscriber
                continue
            # Get data
            df = pd.DataFrame()
            with Progress() as progress:
                task1 = progress.add_task("Get Data", total=len(interesting_list))
                for i in interesting_list:
                    code = i.value
                    GLOG.DEBUG(f"Got {code}")
                    progress.update(
                        task1,
                        advance=1,
                        description=f"Code Scan [light_coral]{code}[/light_coral]",
                    )
                    if code is None:
                        continue
                    new_df = self.get_daybar(code, self.now)
                    if new_df.shape[0] > 0:
                        df = pd.concat([df, new_df], ignore_index=True)
                # Broadcast
                if df.shape[0] == 0:
                    continue

                task2 = progress.add_task("Broadcast", total=df.shape[0])
                for i, r in df.iterrows():
                    b = Bar()
                    b.set(r)
                    GLOG.DEBUG(f"Generate {code} Bar.")
                    event = EventPriceUpdate(b)
                    # print("准备推送新的价格数据")
                    # print(self.now)
                    # print(event)
                    # time.sleep(5)
                    self.engine.put(event)
                    progress.update(
                        task2, advance=1, description=f"Broadcast {event.code}"
                    )
                    GLOG.DEBUG(
                        f"Broadcast Price Update {event.code} on {event.timestamp}"
                    )

    def get_count_of_price(self, date, interested, *args, **kwargs):
        # Do Cache
        # Both count and price
        if date > self.now:
            return 0
        count = 0
        if self._cache is None:
            self._cache = GDATA.get_daybar_df("", date_start=date, date_end=date)
        if self._cache.shape[0] == 0:
            return 0
        if self._cache is None:
            return 0
        codes = self._cache["code"].values
        for i in interested:
            if i.value in codes:
                count += 1
        if self._portfolio_cache is None:
            self._portfolio_cache = count
        return self._portfolio_cache

    def is_code_on_market(self, code, date, *args, **kwargs) -> bool:
        df = self.get_daybar(code, date)
        return True if df.shape[0] == 1 else False

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next frame.
        """
        # Time goes
        super(BacktestFeed, self).on_time_goes_by(time, *args, **kwargs)
