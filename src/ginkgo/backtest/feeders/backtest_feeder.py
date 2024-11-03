"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities.

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""

import time
import pandas as pd
from rich.progress import Progress

from ginkgo.backtest.feeders.base_feeder import BaseFeeder
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.backtest.bar import Bar
from ginkgo.libs import datetime_normalize, GLOG, cache_with_expiration


class BacktestFeeder(BaseFeeder):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, *args, **kwargs):
        super(BacktestFeeder, self).__init__(*args, **kwargs)

    def broadcast(self, *args, **kwargs):
        if self.put is None:
            GLOG.ERROR(f"No Engine bind. Skip broadcast.")
            return
        if self.now is None:
            GLOG.ERROR(f"Time need to be sync. Skip broadcast.")
            return
        if len(self.subscribers) == 0:
            GLOG.WARN(f"No portfolio subscribe. No target to broadcast.")
            return

        for sub in self.subscribers:
            interesting_list = sub.interested

            if len(interesting_list) == 0:
                # No interested, Go Next Subscriber
                continue
            # Get data
            df = pd.DataFrame()
            with Progress() as progress:
                task1 = progress.add_task("Get Data", total=len(interesting_list))
                for code in interesting_list:
                    progress.update(
                        task1,
                        advance=1,
                        description=f"Code Scan [light_coral]{code}[/light_coral]",
                    )
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
                    event = EventPriceUpdate(b)
                    print(f"准备推送新的价格数据 {event.code}")
                    print(self.now)
                    print(event)
                    time.sleep(2)
                    self.put(event)
                    progress.update(task2, advance=1, description=f"Broadcast {event.code}")
                    GLOG.DEBUG(f"Broadcast Price Update {event.code} on {event.timestamp}")

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

    def get_count_of_price(self, date, interested, *args, **kwargs):
        pass

    def is_code_on_market(self, code, date, *args, **kwargs) -> bool:
        df = self.get_daybar(code, date)
        return True if df.shape[0] == 1 else False

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next frame.
        """
        # Time goes
        super(BacktestFeeder, self).on_time_goes_by(time, *args, **kwargs)
