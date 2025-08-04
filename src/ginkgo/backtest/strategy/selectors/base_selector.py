from ginkgo.backtest.core.backtest_base import BacktestBase


class BaseSelector(BacktestBase):
    def __init__(self, name: str = "BaseSelector", *args, **kwargs) -> None:
        super(BaseSelector, self).__init__(name, *args, **kwargs)
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def pick(self, time: any = None, *args, **kwargs) -> list[str]:
        r = []
        return r
