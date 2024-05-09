from ginkgo.backtest.signal import Signal
from ginkgo.backtest.backtest_base import BacktestBase


class BaseSizer(BacktestBase):
    def __init__(self, name: str = "BaseZiser", *args, **kwargs):
        super(BaseSizer, self).__init__(name, *args, **kwargs)
        self._portfolio = None
        self._data_feeder = None

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def cal(self, signal: Signal):
        raise NotImplementedError()
