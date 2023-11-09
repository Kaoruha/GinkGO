from ginkgo.backtest.indexes.base_index import BaseIndex
from ginkgo.enums import RECRODSTAGE_TYPES
import pandas as pd


class NetValue(BaseIndex):
    def __init__(self, name: str, *args, **kwargs):
        super(NetValue, self).__init__(name, *args, **kwargs)
        self._active_stage = RECRODSTAGE_TYPES.NEWDAY


    def record(self, stage, *args, **kwargs) -> None:
        super(NetValue, self).record(stage, *args, **kwargs)
        date = self.portfolio.now
        value = self.portfolio.worth
        new_line = pd.DataFrame([[date,value]], columns=["timestamp", self.name])
        self._data = pd.concat([self._data, new_line], axis=0)
        print(f"{date} {self.portfolio.name} have {self.name} {value}")
        print(self.value)
