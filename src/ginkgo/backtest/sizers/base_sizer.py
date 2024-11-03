from ginkgo.backtest.signal import Signal
from ginkgo.backtest.backtest_base import BacktestBase


class BaseSizer(BacktestBase):
    def __init__(self, name: str = "BaseZiser", *args, **kwargs):
        super(BaseSizer, self).__init__(name, *args, **kwargs)
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def cal(self, signal: Signal):
        raise NotImplementedError()
