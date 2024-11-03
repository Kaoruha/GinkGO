import pandas as pd
from typing import TYPE_CHECKING, List
from decimal import Decimal


from ginkgo.backtest.backtest_base import BacktestBase
from ginkgo.data.operations import add_analyzer_record
from ginkgo.libs import datetime_normalize, to_decimal, Number
from ginkgo.enums import GRAPHY_TYPES, RECORDSTAGE_TYPES


class BaseAnalyzer(BacktestBase):
    def __init__(self, name: str, *args, **kwargs):
        super(BaseAnalyzer, self).__init__(name, *args, **kwargs)
        self._active_stage = []
        self._record_stage = RECORDSTAGE_TYPES.NEWDAY
        self._analyzer_id = ""
        self._portfolio_id = ""
        self._data = pd.DataFrame(columns=["timestamp", self._name])
        self._graph_type = GRAPHY_TYPES.OTHER

    def set_graph_type(self, graph_type: GRAPHY_TYPES, *args, **kwargs) -> None:
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
    def portfolio_id(self) -> str:
        return self._portfolio_id

    def set_portfolio_id(self, value: str) -> None:
        self._portfolio_id = value

    @property
    def active_stage(self) -> List[RECORDSTAGE_TYPES]:
        return self._active_stage

    @property
    def record_stage(self) -> RECORDSTAGE_TYPES:
        return self._record_stage

    def add_active_stage(self, stage: RECORDSTAGE_TYPES, *args, **kwargs) -> None:
        """
        Add Active Stage, active will activate the counter.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            None
        """
        if stage not in self._active_stage:
            self._active_stage.append(stage)

    def set_record_stage(self, stage: RECORDSTAGE_TYPES, *args, **kwargs) -> None:
        """
        Set Record Stage, record will interact with the db.
        Args:
            stage(enum): newday, signalgeneration, ordersend, orderfilled, ordercanceled
        Returns:
            new record stage
        """
        if isinstance(stage, RECORDSTAGE_TYPES):
            self._record_stage = stage
        else:
            pass

    @property
    def name(self) -> str:
        return self._name

    def activate(self, stage, *args, **kwargs) -> None:
        raise NotImplemented(
            "ANALYZER should complete the Function activate(), activate() will activate the analyzer counter."
        )

    def record(self, stage, *args, **kwargs) -> None:
        raise NotImplemented("ANALYZER should complete the Function record(), record() will store the data into db.")

    def add_data(self, value: Number, *args, **kwargs) -> None:
        """
        Add data with the date self.now to dataframe. If the time is already in dataframe, will update the value.
        Args:
            value(Number): new data
        Returns:
            None
        """
        if self.now is None:
            return

        value = to_decimal(value)

        date = self.now.strftime("%Y-%m-%d %H:%M:%S")
        if date in self._data["timestamp"].values:
            # Update value
            self._data.loc[self._data["timestamp"] == date, self._name] = value
        else:
            # Insert new value
            self._data = pd.concat(
                [
                    self._data,
                    pd.DataFrame([[date, to_decimal(value)]], columns=["timestamp", self._name]),
                ]
            )

    def get_data(self, time: any, *args, **kwargs) -> Decimal:
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
    def values(self) -> pd.DataFrame:
        return self._data

    @property
    def data(self) -> pd.DataFrame:
        return self._data

    def add_record(self, *args, **kwargs) -> None:
        """
        Add record to database.
        """
        if self.now is None:
            return
        date = self.now.strftime("%Y-%m-%d %H:%M:%S")
        if date not in self.value["timestamp"].values:
            return
        # TODO

    @property
    def mean(self) -> Decimal:
        mean = self._data[self._name].mean()
        return to_decimal(mean)

    @property
    def variance(self) -> Decimal:
        var = self._data[self._name].var()
        return to_decimal(var)
