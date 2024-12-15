from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class SharpeRatio(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(SharpeRatio, self).__init__(name, *args, **kwargs)
        self.set_activate_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._base_value = None
        self._days = 0
        self._annual_returns = []
        self._base_profit = 0.05

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return
        if self._base_value is None:
            # self._base_value = self.portfolio.worth
            pass
        self._days += 1
        if self._days > 365:
            self._days = self._days - 365
            # self._base_value = self.portfolio.worth

        times = int(365 / self._days)
        # annual_return = (self.portfolio.worth / self._base_value) ** times - 1
        self._annual_returns.append(annual_return)
        std = pd.Series(self._annual_returns).std()
        try:
            value = (annual_return - self._base_profit) / std
        except Exception as e:
            print(e)
            value = -1
        self.add_data(value)
        self.add_record()
