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
from ginkgo.data import get_bars
from ginkgo.libs import datetime_normalize, cache_with_expiration
from ginkgo.enums import SOURCE_TYPES


class BacktestFeeder(BaseFeeder):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name="backtest_feeder", *args, **kwargs):
        super(BacktestFeeder, self).__init__(name, *args, **kwargs)

    def broadcast(self, *args, **kwargs):
        if self.put is None:
            self.log("ERROR", f"No Engine bind. Skip broadcast.")
            return
        if self.now is None:
            self.log("ERROR", f"Time need to be sync. Skip broadcast.")
            return
        if len(self.subscribers) == 0:
            self.log("WARN", f"No portfolio subscribe. No target to broadcast.")
            return

        self.get_tracked_symbols()
        try:
            if len(self.interested) == 0:
                self.log("WARN", f"No interested symbols. Nothing to broadcast.")
                return
            for code in self.interested:
                price_df = self.get_daybar(code, self.now)
                if price_df.shape[0] == 0:
                    continue
                bar = Bar()
                bar.set(price_df.iloc[0])
                event = EventPriceUpdate(price_info=bar)
                event.set_source(SOURCE_TYPES.BACKTESTFEEDER)
                self.put(event)
        except Exception as e:
            import pdb

            pdb.set_trace()
            print(e)
        finally:
            pass

    @cache_with_expiration
    def get_daybar(self, code: str, date: any, *args, **kwargs) -> pd.DataFrame:
        if self.now is None:
            self.log("ERROR", f"Time need to be sync.")
            return pd.DataFrame()
        datetime = datetime_normalize(date).date()
        datetime = datetime_normalize(datetime)

        if datetime > self._now:
            self.log.CRITICAL(f"CurrentDate: {self.now} you can not get the future({datetime}) info.")
            return pd.DataFrame()
        if datetime < self._now:
            self.log.CRITICAL(f"CurrentDate: {self.now} you can not get the past({datetime}) info.")
            return pd.DataFrame()

        df = get_bars(code, start_date=datetime, end_date=datetime, as_dataframe=True)
        return df

    # def is_code_on_market(self, code, date, *args, **kwargs) -> bool:
    #     df = self.get_daybar(code, date)
    #     return True if df.shape[0] == 1 else False

    def on_time_goes_by(self, time: any, *args, **kwargs):
        """
        Go next frame.
        """
        # Time goes
        super(BacktestFeeder, self).on_time_goes_by(time, *args, **kwargs)
