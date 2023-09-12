from ginkgo.backtest.backtest_base import BacktestBase


class BaseSelector(BacktestBase):
    def __init__(self, name: str = "BaseSelector", *args, **kwargs) -> None:
        super(BaseSelector, self).__init__(*args, **kwargs)
        self.set_name(name)
        self._portfolio = None

    def bind_portfolio(self, portfolio) -> None:
        self._portfolio = portfolio

    @property
    def portfolio(self):
        return self._portfolio

    def pick(self) -> list:
        r = []
        return r
