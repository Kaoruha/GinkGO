import pandas as pd
from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECORDSTAGE_TYPES


class MaxDrawdown(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(MaxDrawdown, self).__init__(name, *args, **kwargs)
        self.set_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._max_worth = None

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return
        if self._max_worth is None:
            self._max_worth = self.portfolio.worth
            value = 0
        else:
            if self.portfolio.worth > self._max_worth:
                self._max_worth = self.portfolio.worth
                value = 0
            else:
                value = (self.portfolio.worth - self._max_worth) / self._max_worth
        self.add_data(value)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {value}")
        self.add_record()
