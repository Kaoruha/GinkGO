from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECORDSTAGE_TYPES
import pandas as pd


class NetValue(BaseAnalyzer):
    # The class with this __abstract__  will rebuild the class from bytes.
    # If not run time function will pass the class.
    __abstract__ = False

    def __init__(self, name: str = "netvalue", *args, **kwargs):
        super(NetValue, self).__init__(name, *args, **kwargs)
        self.set_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.set_active_stage(RECORDSTAGE_TYPES.NEWDAY)
        self.set_record_stage(RECORDSTAGE_TYPES.NEWDAY)

    def activate(self, stage, *args, **kwargs) -> None:
        pass

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return
        value = self.portfolio.worth
        if stage != self.record_stage:
            return
        self.add_data(value)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {value}")
        self.add_record()
