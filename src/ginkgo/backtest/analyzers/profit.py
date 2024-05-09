from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class Profit(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "ProfitAna", *args, **kwargs):
        super(Profit, self).__init__(name, *args, **kwargs)
        self.set_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._last_worth = None

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return
        if self._last_worth is None:
            self._last_worth = self.portfolio.worth
            value = 0
        else:
            value = self.portfolio.worth - self._last_worth
            self._last_worth = self.portfolio.worth
        self.add_data(value)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {value}")
        self.add_record()
