import pandas as pd
import datetime
from functools import singledispatchmethod

from ginkgo.backtest.base import Base
from ginkgo.libs import datetime_normalize
from ginkgo.data.models import MAdjustfactor


class Adjsutfactor(Base):
    def __init__(
        self,
        code: str,
        foreadjustfactor: float,
        backadjustfactor: float,
        adjustfactor: float,
        timestamp: any,
        *args,
        **kwargs
    ):
        super(Adjsutfactor, self).__init__(*args, **kwargs)
        self.set(code, foreadjustfactor, backadjustfactor, adjustfactor, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        foreadjustfactor: float,
        backadjustfactor: float,
        adjustfactor: float,
        timestamp: any,
        *args,
        **kwargs
    ) -> None:
        self._code = code
        self._foreadjustfacor = foreadjustfactor
        self._backadjustfactor = backadjustfactor
        self._adjustfactor = adjustfactor
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, model: MAdjustfactor, *args, **kwargs):
        self._code = model.code
        self._foreadjustfacor = model.foreadjustfactor
        self._backadjustfactor = model.backadjustfactor
        self._adjustfactor = model.adjustfactor
        self._timestamp = model.timestamp

    @set.register
    def _(self, df: pd.DataFrame) -> None:
        self._code = df["code"]
        self._foreadjustfacor = df["foreadjustfactor"]
        self._backadjustfactor = df["backadjustfactor"]
        self._adjustfactor = df["adjustfactor"]
        self._timestamp = df["timestamp"]

    @property
    def code(self) -> str:
        return self._code

    @property
    def foreadjustfactor(self) -> float:
        return self._foreadjustfacor

    @property
    def backadjustfactor(self) -> float:
        return self._backadjustfactor

    @property
    def adjustfactor(self) -> float:
        return self._adjustfactor

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp
