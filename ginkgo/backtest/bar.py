import datetime
import pandas as pd
from types import FunctionType, MethodType
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr, pretty_repr, base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.backtest.base import Base
from ginkgo.enums import FREQUENCY_TYPES


class Bar(Base):
    def __init__(
        self,
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        timestamp,
    ) -> None:
        self.__timestamp = None  # DateTime
        self._code = "default_code"
        self._open = 0
        self._high = 0
        self._low = 0
        self._close = 0
        self._volume = 0

        self.set(code, open, high, low, close, volume, frequency, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        open: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        timestamp: datetime.datetime,
    ) -> None:
        self._code = code
        self._open = open
        self._high = high
        self._low = low
        self._close = close
        self._frequency = frequency
        self._volume = volume

        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series):
        # TODO read from data model
        pass

    @property
    def code(self) -> str:
        return self._code

    @property
    def open(self) -> float:
        return self._open

    @property
    def high(self) -> float:
        return self._high

    @property
    def low(self) -> float:
        return self._low

    @property
    def close(self) -> float:
        return self._close

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def frequency(self) -> FREQUENCY_TYPES:
        return self._frequency

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    @property
    def chg(self) -> float:
        r = self._close - self._open
        r = round(r, 4)
        return r

    @property
    def amplitude(self) -> float:
        r = self._high - self._low
        r = round(r, 2)
        return r

    def __repr__(self) -> str:
        return base_repr(self, Bar.__name__, 12, 60)
