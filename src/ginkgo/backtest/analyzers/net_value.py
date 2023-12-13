from ginkgo.backtest.analyzers.base_analyzer import BaseAnalyzer
from ginkgo.libs.ginkgo_logger import GLOG
from ginkgo.enums import RECRODSTAGE_TYPES
import pandas as pd


class NetValue(BaseAnalyzer):
    __abstract__ = False

    def __init__(self, name: str, *args, **kwargs):
        super(NetValue, self).__init__(name, *args, **kwargs)
        self._active_stage = RECRODSTAGE_TYPES.NEWDAY

    def record(self, stage, *args, **kwargs) -> None:
        super(NetValue, self).record(stage, *args, **kwargs)
        if stage != self._active_stage:
            return
        value = self.portfolio.worth
        self.add_data(value)
        GLOG.DEBUG(f"{self.now} {self.portfolio.name} have {self.name} {value}")
        self.add_record()
