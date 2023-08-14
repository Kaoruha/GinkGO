from ginkgo.backtest.signal import Signal
from ginkgo.backtest.feeds import BaseFeed, BarFeed


class BaseSizer(object):
    def __init__(self, *args, **kwargs):
        self._portfolio = None
        self._feed = None

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def feed(self):
        return self._feed

    def bind_feed(self, feed: BaseFeed):
        self._feed = feed

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def cal(self, signal: Signal):
        raise NotImplementedError()
