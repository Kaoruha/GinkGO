from typing import Optional
from ginkgo.backtest.entities.signal import Signal
from ginkgo.backtest.entities.order import Order
from ginkgo.backtest.core.backtest_base import BacktestBase
from ginkgo.enums import DIRECTION_TYPES


class BaseSizer(BacktestBase):
    def __init__(self, name: str = "BaseSizer", *args, **kwargs):
        super(BaseSizer, self).__init__(name, *args, **kwargs)
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def cal(self, portfolio_info, signal: Signal, *args, **kwargs) -> Optional[Order]:
        raise NotImplementedError("Sizer must implement cal method")
