from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.backtest.backtest_base import BacktestBase
import pandas as pd
from ginkgo.data.models import MAnalyzer
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs import datetime_normalize

from src.ginkgo.enums import GRAPHY_TYPES


class BaseAnalyzer(BacktestBase):
    def __init__(self, name: str, *args, **kwargs):
        super(BaseAnalyzer, self).__init__(name, *args, **kwargs)
        self._active_stage = RECORDSTAGE_TYPES.NEWDAY
        self._portfolio = None
        self._analyzer_id = ""
        self._data = pd.DataFrame(columns=["timestamp", self._name])
        self._box_range = 20
        self._graph_type = GRAPHY_TYPES.OTHER

    def set_graph_type(self, graph_type: GRAPHY_TYPES):
        self._graph_type = graph_type

    @property
    def analyzer_id(self) -> str:
        return self._analyzer_id

    def set_analyzer_id(self, analyzer_id: str):
        self._analyzer_id = analyzer_id

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def active_stage(self) -> RECORDSTAGE_TYPES:
        return self._active_stage

    def set_stage(self, stage: RECORDSTAGE_TYPES) -> None:
        if isinstance(stage, RECORDSTAGE_TYPES):
            self._active_stage = stage

    def bind_portfolio(self, portfolio, *args, **kwargs):
        """
        When portfolio add index, will auto run this function to pass portfolio itselft to index.
        """
        self._portfolio = portfolio

    @property
    def name(self) -> str:
        return self._name

    def record(self, stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return

    def add_data(self, value: float) -> None:
        """
        Add data with the date self.now to dataframe. If the time is already in dataframe, will update the value.
        """
        if self.now is None:
            return
        date = self.now.strftime("%Y-%m-%d %H:%M:%S")
        if date in self._data["timestamp"].values:
            self._data.loc[self._data["timestamp"] == date, self._name] = value
        else:
            self._data = pd.concat(
                [
                    self._data,
                    pd.DataFrame([[date, value]], columns=["timestamp", self._name]),
                ]
            )

    def get_data(self, time: any) -> float:
        """
        Try get the data at time from dataframe.
        """
        time = datetime_normalize(time)
        date = time.strftime("%Y-%m-%d %H:%M:%S")
        if date in self._data["timestamp"].values:
            return self._data[self._data["timestamp"] == date][self._name].values[0]
        else:
            return None

    @property
    def value(self) -> pd.DataFrame:
        return self._data

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def add_record(self) -> None:
        """
        Add record to database.
        """
        o = MAnalyzer()
        if self.now is None:
            return
        date = self.now.strftime("%Y-%m-%d %H:%M:%S")
        if date not in self.value["timestamp"].values:
            return
        value = self.value[self.value["timestamp"] == date][self.name].values[0]
        o.set(self.backtest_id, self.now, value, self.name, self.analyzer_id)
        GDATA.add(o)

    @property
    def mean(self) -> float:
        return self._data[self._name].mean()

    @property
    def variance(self) -> float:
        return self._data[self._name].var()
