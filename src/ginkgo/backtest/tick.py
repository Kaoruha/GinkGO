import datetime
import pandas as pd
from functools import singledispatchmethod
from ginkgo.libs import base_repr, datetime_normalize
from ginkgo.backtest.base import Base
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class Tick(Base):
    def __init__(self, *args, **kwargs) -> None:
        super(Tick, self).__init__(*args, **kwargs)
        self._code = "default tick"
        self._price = 0
        self._volume = 0
        self._direction = None
        self._timestamp = datetime.datetime.now()

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        price: float,
        volume: int,
        direction: TICKDIRECTION_TYPES,
        timestamp: any,
    ) -> None:
        self._code = code
        self._price = price
        self._volume = volume
        self._direction = direction
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series) -> None:
        self._code = df.code
        self._price = df.price
        self._volume = df.volume
        self._direction = df.direction
        self._timestamp = df.timestamp

        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df.source))

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> float:
        return self._price

    @property
    def volume(self) -> int:
        return self._volume

    @property
    def direction(self) -> TICKDIRECTION_TYPES:
        return self._direction

    @property
    def timestamp(self) -> datetime.datetime:
        return self._timestamp

    def __repr__(self) -> str:
        return base_repr(self, "DB" + Tick.__name__.capitalize(), 12, 46)
