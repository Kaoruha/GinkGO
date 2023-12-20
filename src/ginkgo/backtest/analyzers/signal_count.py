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
        self.set_stage(RECORDSTAGE_TYPES.SIGNALGENERATION)
        self.count = 0

    def record(self, stage, *args, **kwargs) -> None:
        super(SignalCount, self).record(stage, *args, **kwargs)
        if stage != self.active_stage:
            return
        self.count += 1
        self.add_data(self.count)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {self.count}")
        self.add_record()
