import pandas as pd
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ginkgo.backtest.portfolios.base_portfolio import BasePortfolio

from ginkgo.enums import RECORDSTAGE_TYPES
from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.data.models import MAnalyzer
from ginkgo.data.ginkgo_data import GDATA
from ginkgo.libs import datetime_normalize
from ginkgo.enums import GRAPHY_TYPES


class BaseAnalyzer(BacktestBase):
    def __init__(self, name: str, *args, **kwargs):
        super(BaseAnalyzer, self).__init__(name, *args, **kwargs)
        self._active_stage = RECORDSTAGE_TYPES.NEWDAY
        self._record_stage = RECORDSTAGE_TYPES.NEWDAY
        self._portfolio = None
        self._analyzer_id = ""
        self._data = pd.DataFrame(columns=["timestamp", self._name])
        self._box_range = 20
        self._graph_type = GRAPHY_TYPES.OTHER

    def set_graph_type(self, graph_type: GRAPHY_TYPES):
        """
        Set Graph Type.
        Args:
            graph_type(enum): Bar, Line
        Returns:
            None
        """
        self._graph_type = graph_type

    @property
    def analyzer_id(self) -> str:
        return self._analyzer_id

    def set_analyzer_id(self, analyzer_id: str) -> str:
        """
        Analyzer ID update.
        Args:
            analyzer_id(str): new ID
        Returns:
            new Analyzer ID
        """
        self._analyzer_id = analyzer_id
        return self.analyzer_id

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def active_stage(self) -> RECORDSTAGE_TYPES:
        return self._active_stage

    @property
    def record_stage(self) -> RECORDSTAGE_TYPES:
        return self._record_stage

    def set_stage(self, stage: RECORDSTAGE_TYPES) -> RECORDSTAGE_TYPES:
        """
        [Obsolete]Replaced by Function set_active_stage()
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            new active stage
        """
        if isinstance(stage, RECORDSTAGE_TYPES):
            self._active_stage = stage
        return self.active_stage

    def set_active_stage(self, stage: RECORDSTAGE_TYPES) -> RECORDSTAGE_TYPES:
        """
        Set Active Stage, active will activate the counter.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            new active stage
        """
        if not isinstance(stage, RECORDSTAGE_TYPES):
            return
        self._active_stage = stage
        return self.active_stage

    def set_record_stage(self, stage: RECORDSTAGE_TYPES) -> RECORDSTAGE_TYPES:
        """
        Set Record Stage, record will interact with the db.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            new record stage
        """
        if not isinstance(stage, RECORDSTAGE_TYPES):
            return

        self._record_stage = stage
        return self.record_stage

    def bind_portfolio(
        self, portfolio: "BasePortfolio", *args, **kwargs
    ) -> "BasePortfolio":
        """
        When portfolio add index, will auto run this function to pass portfolio itselft to index.
        Args:
            potfolio(Portfolio): target portfolio
        Returns:
            Binded Portfolio
        """
        self._portfolio = portfolio
        return self.portfolio

    @property
    def name(self) -> str:
        return self._name

    def activate(self, stage, *args, **kwargs) -> None:
        raise NotImplemented(
            "Analyzer should complete the Function activate(), activate() will activate the analyzer counter."
        )

    def record(self, stage, *args, **kwargs) -> None:
        raise NotImplemented(
            "Analyzer should complete the Function record(), record() will store the data into db."
        )

    def add_data(self, value: float) -> None:
        """
        Add data with the date self.now to dataframe. If the time is already in dataframe, will update the value.
        Args:
            value(float): new data
        Returns:
            None
        """
        if self.now is None:
            return

        date = self.now.strftime("%Y-%m-%d %H:%M:%S")
        if date in self._data["timestamp"].values:
            # Update value
            self._data.loc[self._data["timestamp"] == date, self._name] = value
        else:
            # Insert new value
            self._data = pd.concat(
                [
                    self._data,
                    pd.DataFrame(
                        [[date, round(value, 6)]], columns=["timestamp", self._name]
                    ),
                ]
            )

    def get_data(self, time: any) -> float:
        """
        Try get the data at time from dataframe.
        Args:
            time(any): query time
        Returns:
            the value at query time
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
        value = float(value)
        value = round(value, 6)
        o.set(self.backtest_id, self.now, value, self.name, self.analyzer_id)
        GDATA.add(o)

    @property
    def mean(self) -> float:
        return self._data[self._name].mean()

    @property
    def variance(self) -> float:
        return self._data[self._name].var()
