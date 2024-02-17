from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class SharpRatio(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(SharpRatio, self).__init__(name, *args, **kwargs)
        self.set_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._base_value = None
        self._days = 0
        self._annual_returns = []
        self._base_profit = 0.05

    def record(self, stage, *args, **kwargs) -> None:
        super(SharpRatio, self).record(stage, *args, **kwargs)
        if stage != self.active_stage:
            return
        if self._base_value is None:
            self._base_value = self.portfolio.worth
        self._days += 1
        if self._days > 365:
            self._days = self._days - 365
            self._base_value = self.portfolio.worth

        times = int(365 / self._days)
        annual_return = (self.portfolio.worth / self._base_value) ** times - 1
        self._annual_returns.append(annual_return)
        std = pd.Series(self._annual_returns).std()
        try:
            value = (annual_return - self._base_profit) / std
        except Exception as e:
            print(e)
            value = -1
        self.add_data(value)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {value}")
        self.add_record()
