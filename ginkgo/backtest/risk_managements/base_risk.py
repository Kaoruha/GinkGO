from ginkgo.backtest.order import Order
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.backtest.backtest_base import BacktestBase


class BaseRiskManagement(BacktestBase):
    def __init__(self, name: str = "baseriskmanagement", *args, **kwargs):
        super(BaseRiskManagement, self).__init__(name, *args, **kwargs)
        self._portfolio = None

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def cal(self, order: Order):
        return order
