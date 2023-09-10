from ginkgo.backtest.signal import Signal


class BaseSizer(object):
    def __init__(self, *args, **kwargs):
        self._portfolio = None
        self._feed = None

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def cal(self, signal: Signal):
        raise NotImplementedError()
