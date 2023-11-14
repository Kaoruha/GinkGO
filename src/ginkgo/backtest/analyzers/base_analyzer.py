from ginkgo.enums import RECRODSTAGE_TYPES
import pandas as pd


class BaseAnalyzer(object):
    def __init__(self, name: str, *args, **kwargs):
        self._name = name
        self._active_stage = RECRODSTAGE_TYPES.NEWDAY
        self._portfolio = None
        self._data = pd.DataFrame(columns=["timestamp",self._name])

    @property
    def portfolio(self):
        return self._portfolio

    @property
    def active_stage(self) -> RECRODSTAGE_TYPES:
        return self._active_stage

    def bind_portfolio(self, portfolio, *args, **kwargs):
        """
        When portfolio add index, will auto run this function to pass portfolio itselft to index.
        """
        self._portfolio = portfolio

    @property
    def name(self) -> str:
        return self._name

    def record(self,stage, *args, **kwargs) -> None:
        if stage != self.active_stage:
            return

    @property
    def value(self) -> any:
        return self._data
