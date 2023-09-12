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

    def bind_data_feeder(self, data_feeder):
        self._data_feeder = data_feeder

    @property
    def data_feeder(self):
        if self._data_feeder is None:
            self._data_feeder = self.portfolio.engine.datafeeder
        return self._data_feeder

    def cal(self, signal: Signal):
        raise NotImplementedError()
