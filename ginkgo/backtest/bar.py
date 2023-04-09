import datetime
import pandas as pd
from types import FunctionType, MethodType
from enum import Enum
from functools import singledispatchmethod
from ginkgo.libs.ginkgo_pretty import base_repr
from ginkgo.libs.ginkgo_pretty import pretty_repr, base_repr
from ginkgo.libs.ginkgo_normalize import datetime_normalize
from ginkgo.enums import FREQUENCY_TYPES


class Bar(object):
    def __init__(
        self,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        timestamp,
    ) -> None:
        self.__timestamp = None  # DateTime
        self.code = "sh.600001"
        self.open = 0
        self.high = 0
        self.low = 0
        self.close = 0
        self.volume = 0

        self.set(code, open_, high, low, close, volume, frequency, timestamp)

    @singledispatchmethod
    def set(self) -> None:
        pass

    @property
    def to_dataframe(self) -> pd.DataFrame:
        item = {}
        methods = ["delete", "query", "registry", "metadata", "to_dataframe"]
        for param in self.__dir__():
            if param in methods:
                continue
            if param.startswith("_"):
                continue
            if isinstance(self.__getattribute__(param), MethodType):
                continue
            if isinstance(self.__getattribute__(param), FunctionType):
                continue

            if isinstance(self.__getattribute__(param), Enum):
                item[param] = self.__getattribute__(param).value
            else:
                item[param] = self.__getattribute__(param)

        df = pd.DataFrame.from_dict(item, orient="index")
        return df

    @set.register
    def _(
        self,
        code: str,
        open_: float,
        high: float,
        low: float,
        close: float,
        volume: int,
        frequency: FREQUENCY_TYPES,
        timestamp: datetime.datetime,
    ) -> None:
        self.open = open_
        self.high = high
        self.low = low
        self.close = close
        self.frequency = frequency
        self.volume = volume

        self.__timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, bar: pd.DataFrame):
        # TODO read from data model
        pass

    @property
    def timestamp(self) -> datetime.datetime:
        return self.__timestamp

    @property
    def open_(self) -> float:
        return self.open

    @property
    def chg(self) -> float:
        r = self.close - self.open
        r = round(r, 2)
        return r

    @property
    def amplitude(self) -> float:
        r = self.high - self.low
        r = round(r, 2)
        return r

    def __repr__(self) -> str:
        return base_repr(self, Bar.__name__, 12, 60)
