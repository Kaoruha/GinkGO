from ginkgo.backtest.order import Order


class BaseRiskManagement:
    def __init__(self, *args, **kwargs):
        self._portfolio = None

    @property
    def portfolio(self):
        return self._portfolio

    def bind_portfolio(self, portfolio):
        self._portfolio = portfolio

    def cal(self, order: Order):
        return order
