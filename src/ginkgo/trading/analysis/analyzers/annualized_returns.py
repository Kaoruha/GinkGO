import pandas as pd
from ginkgo.trading.analysis.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.enums import RECORDSTAGE_TYPES


class AnnualizedReturn(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(AnnualizedReturn, self).__init__(name, *args, **kwargs)
        self.set_activate_stage(RECORDSTAGE_TYPES.NEWDAY)
        self._base_value = None
        self._days = 0

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return
        if self._base_value is None:
            # self._base_value = self.portfolio.worth
            # TODO
            pass
        self._days += 1
        if self._days > 365:
            self._days = self._days - 365
            # self._base_value = self.portfolio.worth
            # TODO

        times = int(365 / self._days)
        # value = (self.portfolio.worth / self._base_value) ** times - 1
        value = 2
        if value > 1000:
            value = 1000
        self.add_data(value)
        self.add_record()
