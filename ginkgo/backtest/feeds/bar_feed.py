"""
The `Datahandler` class will provide access to historical price and volume data for a given set of securities. 

- Loading historical price and volume data for a given set of securities.

- Retrieving price and volume data for a given date and security.

- Get the Live Trading system's price and volume.
"""
import pandas as pd
from ginkgo.backtest.feeds.base_feed import BaseFeed
from ginkgo import GLOG
from ginkgo.backtest.events import EventPriceUpdate
from ginkgo.backtest.bar import Bar
from ginkgo.data.ginkgo_data import GDATA


class BarFeed(BaseFeed):
    def __init__(self, *args, **kwargs):
        super(BarFeed, self).__init__(*args, **kwargs)
        self._portfolio = None

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def broadcast(self):
        if self._portfolio is None:
            GLOG.CRITICAL(f"Portfolio not bind. Can not broadcast.")
            return

        for sub in self.subscribers:
            time = self._portfolio.now
            interesting_list = self._portfolio.interested
            # Get data
            df = pd.DataFrame()
            for code in interesting_list:
                new_df = GDATA.get_daybar_df(code, time, time)
                df = pd.concat([df, new_df], ignore_index=True)
            # Broadcast
            for i, r in df.ittrows():
                b = Bar()
                b.set(r)
                event = EventPriceUpdate(b)
                sub.on_price_update(event)
