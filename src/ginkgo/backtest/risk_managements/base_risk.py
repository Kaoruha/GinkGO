from ginkgo.backtest.order import Order
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class BaseRiskManagement(BacktestBase):
    def __init__(self, name: str = "baseriskmanagement", *args, **kwargs):
        super(BaseRiskManagement, self).__init__(name, *args, **kwargs)
        self._data_feeder = None

    def bind_data_feeder(self, feeder, *args, **kwargs):
        self._data_feeder = feeder

    def cal(self, order: Order):
        return order
