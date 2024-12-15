import datetime
import pandas as pd
from decimal import Decimal
from functools import singledispatchmethod
from ginkgo.libs import base_repr, datetime_normalize, Number, to_decimal
from ginkgo.backtest.base import Base
from ginkgo.enums import SOURCE_TYPES, TICKDIRECTION_TYPES


class Tick(Base):
    def __init__(
        self,
        code: str = "defaultcode",
        price: Number = 0,
        volume: int = 0,
        direction: TICKDIRECTION_TYPES = TICKDIRECTION_TYPES.OTHER,
        timestamp: any = datetime.datetime.now(),
        source: SOURCE_TYPES = SOURCE_TYPES.OTHER,
        *args,
        **kwargs
    ) -> None:
        super(Tick, self).__init__(*args, **kwargs)
        self._code = code
        self._price = to_decimal(price)
        self._volume = int(volume)
        self._direction = direction
        self._timestamp = datetime_normalize(timestamp)
        self.source = source

    @singledispatchmethod
    def set(self) -> None:
        pass

    @set.register
    def _(
        self,
        code: str,
        price: Number,
        volume: int,
        direction: TICKDIRECTION_TYPES,
        timestamp: any,
        source: SOURCE_TYPES,
        *args,
        **kwargs
    ) -> None:
        self._code = code
        self._price = price
        self._volume = volume
        self._direction = direction
        self._timestamp = datetime_normalize(timestamp)

    @set.register
    def _(self, df: pd.Series, *args, **kwargs) -> None:
        self._code = df["code"]
        self._price = to_decimal(df["price"])
        self._volume = df["volume"]
        self._direction = df["direction"]
        self._timestamp = datetime_normalize(df["timestamp"])

        if "source" in df.keys():
            self.set_source(SOURCE_TYPES(df["source"]))

    @property
    def code(self) -> str:
        return self._code

    @property
    def price(self) -> Decimal:
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
