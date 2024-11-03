from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class SignalCount(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(SignalCount, self).__init__(name, *args, **kwargs)
        self.set_activate_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        self.count = 0
        self.last_day = None

    def activate(self, portfolio, *args, **kwargs) -> None:
        if self.last_day is None:
            self.last_day = portfolio.now
        if self.last_day != portfolio.now:
            return
        self.count = 0
        self.last_day = portfolio.now
        self.count += 1

    def record(self, *args, **kwargs) -> None:
        return
        # self.add_data(self.count)
        # self.add_record()
