import pandas as pd
from ginkgo.backtest.signal import Signal
from ginkgo.backtest.backtest_base import BacktestBase


class StrategyBase(BacktestBase):
    def __init__(self, name: str = "Strategy", *args, **kwargs):
        super(StrategyBase, self).__init__(name, *args, **kwargs)
        self._raw = {}
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    @property
    def data_feeder(self):
        return self._data_feeder

    def cal(self, portfolio_info, event, *args, **kwargs) -> Signal:
        pass
