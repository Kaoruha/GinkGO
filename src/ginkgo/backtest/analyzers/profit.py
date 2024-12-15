from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class Profit(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "ProfitAna", *args, **kwargs):
        super(Profit, self).__init__(name, *args, **kwargs)
        self.add_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._last_worth = None

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        # TODO
        return
        if stage != self.active_stage:
            return
        if self._last_worth is None:
            # self._last_worth = self.portfolio.worth
            value = 0
        else:
            pass
            # value = self.portfolio.worth - self._last_worth
            # self._last_worth = self.portfolio.worth
        self.add_data(value)
        self.add_record()
